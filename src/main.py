"""VideoNote main application."""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .api import upload_router, task_router, note_router, storage_router, model_config_router
from .api.ws_manager import ws_manager
from .core.engine import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init engine + reset zombie tasks."""
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
- **Multiple note styles** - Standard, Summary, Action, Academic, Creative
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

app.include_router(upload_router)
app.include_router(task_router)
app.include_router(note_router)
app.include_router(storage_router)
app.include_router(model_config_router)

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

@app.websocket("/ws/task/{task_id}")
async def websocket_task(websocket, task_id: str):
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
async def websocket_all(websocket):
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
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"error": str(exc)})
