"""VideoNote main application."""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path

from .api import upload_router, task_router, note_router, storage_router, model_config_router, settings_router, auth_router
from .api.ws_manager import ws_manager
from .core.engine import get_engine
from .security import AUTH_ENABLED, CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, SESSION_SECRET, valid_csrf, validate_session
from .rate_limit import allow_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init engine + reset zombie tasks."""
    if AUTH_ENABLED and not SESSION_SECRET:
        raise RuntimeError("VIDEONOTE_SESSION_SECRET must be set when VIDEONOTE_AUTH_PASSWORD is configured")
    engine = get_engine()
    logger.info("VideoNote engine ready (ASR=%s)", engine.ai.asr_enabled)
    yield


app = FastAPI(
    title="VideoNote API",
    description="""## VideoNote - Video to Notes Converter

Convert videos into structured notes using AI.

### Features
- **Upload videos** - Support MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
- **AI-powered analysis** - Extract keyframes, analyze content with VLM
- **Multiple note styles** - Standard, Detailed, Summary, Action, Academic, Creative
- **Task management** - Track progress, retry failed tasks, cancel processing
- **Export options** - Download as Markdown or PDF
- **Storage management** - Manage uploaded video files

### Workflow
1. Upload a video file
2. System extracts audio and keyframes
3. AI analyzes content and generates notes
4. Download or view the generated notes
""",
    version="1.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "upload", "description": "Video upload and processing"},
        {"name": "tasks", "description": "Task management and status"},
        {"name": "notes", "description": "Note retrieval and export"},
        {"name": "storage", "description": "Storage and file management"},
    ]
)

import os
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_AUTH_BYPASS = {"/api/health", "/api/auth/login", "/api/auth/me", "/api/auth/logout"}
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Protect API routes when a production password is configured.

    Local development remains backwards compatible when VIDEONOTE_AUTH_PASSWORD
    is unset. Production deployments must set both auth password and session
    secret in the environment.
    """
    protected_path = request.url.path.startswith("/api") or request.url.path.startswith("/static/output")
    if AUTH_ENABLED and protected_path:
        # A signed session is stable per browser and avoids collapsing all
        # users behind the frontend container into one rate-limit bucket.
        client_id = request.cookies.get(SESSION_COOKIE, "")
        forwarded_for = request.headers.get("x-forwarded-for", "")
        client_id = client_id or forwarded_for.split(",", 1)[0].strip() or request.headers.get("x-real-ip", "")
        client_id = client_id or (request.client.host if request.client else "unknown")
        if request.url.path.startswith("/api") and not allow_request(client_id, request.method, request.url.path):
            return JSONResponse(status_code=429, content={"detail": "Too many requests"}, headers={"Retry-After": "60"})
        path = request.url.path
        if path not in _AUTH_BYPASS:
            if not validate_session(request.cookies.get(SESSION_COOKIE)):
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})
            if request.method in _MUTATING_METHODS and not valid_csrf(
                request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
            ):
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
    return await call_next(request)

app.include_router(upload_router)
app.include_router(task_router)
app.include_router(note_router)
app.include_router(storage_router)
app.include_router(model_config_router)
app.include_router(settings_router)
app.include_router(auth_router)

output_dir = Path("./data/output")
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/output", StaticFiles(directory=str(output_dir)), name="output")


@app.get("/")
async def root():
    return {"name": "VideoNote", "version": "1.1.0", "description": "Video to Notes"}


@app.get("/api/health")
async def health_check():
    engine = get_engine()
    return {
        "status": "healthy",
        "asr_enabled": engine.ai.asr_enabled,
        "llm_model": engine.config.provider.model,
        "vlm_model": engine.config.vlm.model,
        "concurrency": engine.config.processing.max_concurrent_tasks,
    }

def _websocket_allowed(websocket: WebSocket) -> bool:
    if not AUTH_ENABLED:
        return True
    if not validate_session(websocket.cookies.get(SESSION_COOKIE)):
        return False
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    return origin in {o.strip() for o in cors_origins if o.strip()}


@app.websocket("/ws/task/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    if not _websocket_allowed(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    ws_manager.register(websocket, task_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.unregister(websocket, task_id)

@app.websocket("/ws/all")
async def websocket_all(websocket: WebSocket):
    if not _websocket_allowed(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    ws_manager.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.unregister(websocket)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
