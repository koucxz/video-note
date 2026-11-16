"""VideoNote main application."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path

from .api import upload_router, upload_chunked_router, task_router, note_router, storage_router, model_config_router, settings_router, auth_router
from .core.engine import get_engine
from .security import (
    AUTH_ENABLED, CSRF_COOKIE, CSRF_HEADER, SESSION_SECRET,
    get_session_value, is_token_auth, valid_csrf, validate_session,
)
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
    # Each uvicorn worker owns a lazily created process pool; release its
    # children cleanly on shutdown instead of waiting for interpreter exit.
    try:
        from .core.executors import shutdown_pool
        shutdown_pool()
    except Exception as exc:  # noqa: BLE001 - shutdown must not fail startup
        logger.warning("Process pool shutdown failed: %s", exc)


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

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

_AUTH_BYPASS = {"/api/health", "/api/auth/login", "/api/auth/me", "/api/auth/logout"}
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Protect API routes when a production password is configured.

    Local development remains backwards compatible when VIDEONOTE_AUTH_PASSWORD
    is unset. Production deployments must set both auth password and session
    secret in the environment.

    Two credential modes share the same signed session string: the same-origin
    443 entry keeps using the vn_session cookie plus double-submit CSRF cookie,
    while the cross-origin Vercel UI uses a Bearer/query token (CSRF-exempt).
    """
    # Preflight must never be rejected by auth. CORSMiddleware is registered
    # outermost and normally short-circuits OPTIONS already; this is a guard.
    if request.method == "OPTIONS":
        return await call_next(request)
    protected_path = request.url.path.startswith("/api") or request.url.path.startswith("/static/output")
    if AUTH_ENABLED and protected_path:
        # A signed session is stable per browser and avoids collapsing all
        # users behind the frontend container into one rate-limit bucket.
        client_id = get_session_value(request) or ""
        forwarded_for = request.headers.get("x-forwarded-for", "")
        client_id = client_id or forwarded_for.split(",", 1)[0].strip() or request.headers.get("x-real-ip", "")
        client_id = client_id or (request.client.host if request.client else "unknown")
        if request.url.path.startswith("/api") and not allow_request(client_id, request.method, request.url.path):
            return JSONResponse(status_code=429, content={"detail": "Too many requests"}, headers={"Retry-After": "60"})
        path = request.url.path
        if path not in _AUTH_BYPASS:
            if not validate_session(get_session_value(request)):
                return JSONResponse(status_code=401, content={"detail": "Authentication required"})
            # Token credentials are injected explicitly by JS, so a cross-site
            # form cannot forge them and no double-submit CSRF cookie is needed.
            if request.method in _MUTATING_METHODS and not is_token_auth(request) and not valid_csrf(
                request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
            ):
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
    return await call_next(request)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Log method/path/status/duration for every HTTP request.

    Registered last among the user middlewares: Starlette puts the most
    recently added one outermost, so this wraps auth/rate-limit and measures the
    whole request. CORSMiddleware is added afterwards so it sits outermost and
    answers preflight before auth can 401 it. Slow requests (>500ms) are logged
    on one WARNING line.
    """
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000.0
        logger.warning("%s %s 500 %.1fms (unhandled)", request.method, request.url.path, duration_ms)
        raise
    duration_ms = (time.perf_counter() - start) * 1000.0
    response.headers["X-Process-Time"] = f"{duration_ms:.2f}"
    line = "%s %s %s %.1fms" % (request.method, request.url.path, response.status_code, duration_ms)
    if duration_ms > 500:
        logger.warning(line)
    else:
        logger.info(line)
    return response


# Registered *after* every @app.middleware("http") decorator: Starlette's
# add_middleware inserts at index 0, so the last one added is outermost. CORS
# must wrap auth/timing to answer OPTIONS preflight before auth can 401 it and
# to attach CORS headers to 401/403 JSON responses. Headers are listed
# explicitly so credentials=True preflight still allows them on every version.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

app.include_router(upload_router)
app.include_router(upload_chunked_router)
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
        "web_concurrency": os.getenv("WEB_CONCURRENCY", "2"),
    }


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Return shared background-job state (works from any uvicorn worker)."""
    job = await asyncio.to_thread(get_engine().checkpoint.get_job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"data": job}

def _websocket_allowed(websocket: WebSocket) -> bool:
    if not AUTH_ENABLED:
        return True
    # A cross-origin browser cannot send the SameSite=Lax vn_session cookie, so
    # the Vercel frontend appends ?token=<signed session> to the WebSocket URL.
    if not validate_session(get_session_value(websocket)):
        return False
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    return origin in {o.strip() for o in cors_origins if o.strip()}


def _task_ws_payload(task_id: str, task) -> dict | None:
    """Same JSON shape as ws_manager.broadcast_task_update previously sent."""
    if not task:
        return None
    return {
        "task_id": task_id,
        "status": task.get("status"),
        "stage": task.get("stage"),
        "progress": task.get("progress"),
        "error": task.get("error"),
        "error_kind": task.get("error_kind", "unknown"),
    }


def _read_task_payload(task_id: str):
    return _task_ws_payload(task_id, get_engine().checkpoint.get_task(task_id))


def _read_all_payloads():
    cp = get_engine().checkpoint
    return [_task_ws_payload(t["id"], t) for t in cp.get_all_tasks()]


async def _ws_wait(websocket: WebSocket, timeout: float = 1.0) -> None:
    """Poll cadence that also wakes immediately on a client message/close."""
    try:
        await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
    except asyncio.TimeoutError:
        pass


@app.websocket("/ws/task/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    """Cross-worker safe progress: read the shared DB instead of relying on
    in-process ws_manager broadcasts (which never reach other workers)."""
    if not _websocket_allowed(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    last_sent = None
    try:
        while True:
            payload = await asyncio.to_thread(_read_task_payload, task_id)
            if payload and payload != last_sent:
                await websocket.send_text(json.dumps(payload, ensure_ascii=False))
                last_sent = payload
            await _ws_wait(websocket)
    except Exception:
        pass


@app.websocket("/ws/all")
async def websocket_all(websocket: WebSocket):
    if not _websocket_allowed(websocket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    last: dict[str, str] = {}
    baseline_done = False
    try:
        while True:
            payloads = await asyncio.to_thread(_read_all_payloads)
            current: dict[str, str] = {}
            for payload in payloads:
                if not payload:
                    continue
                sig = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                tid = payload["task_id"]
                current[tid] = sig
                # First poll only establishes the baseline; the global feed
                # (like the old in-process broadcast) reports changes only.
                if baseline_done and last.get(tid) != sig:
                    await websocket.send_text(sig)
            last = current
            baseline_done = True
            await _ws_wait(websocket)
    except Exception:
        pass


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
