"""VideoNote main application."""
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from urllib.parse import parse_qs
from pathlib import Path

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from .api import upload_router, upload_chunked_router, task_router, note_router, storage_router, model_config_router, settings_router
from .api.ws_manager import ws_manager
from .core.engine import get_engine
from .api.auth import PUBLIC_PATHS, auth_enabled, check_request_auth, router as auth_router

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
    # 公网部署：关闭交互式文档与 OpenAPI schema，避免把全部接口清单暴露给扫描器
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    openapi_tags=[
        {"name": "upload", "description": "Video upload and processing"},
        {"name": "tasks", "description": "Task management and status"},
        {"name": "notes", "description": "Note retrieval and export"},
        {"name": "storage", "description": "Storage and file management"},
    ]
)


@app.middleware("http")
async def _auth_guard(request, call_next):
    """单用户登录守卫：未登录一律 401。OPTIONS 预检与公开路径放行。"""
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    if not auth_enabled():
        return await call_next(request)
    if not check_request_auth(
        request.headers.get("authorization"),
        request.headers.get("x-vn-token"),
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "未登录或登录已过期"},
        )
    return await call_next(request)


_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
_allow_any_origin = "*" in _cors_origins
app.add_middleware(
    CORSMiddleware,
    # 用 header 传 token，不依赖 cookie，所以允许任意源时可以不启用 credentials
    allow_origins=["*"] if _allow_any_origin else _cors_origins,
    allow_credentials=not _allow_any_origin,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(upload_chunked_router)
app.include_router(task_router)
app.include_router(note_router)
app.include_router(storage_router)
app.include_router(model_config_router)
app.include_router(settings_router)

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


def _ws_token_ok(websocket: WebSocket) -> bool:
    """WebSocket 握手鉴权：token 走 query 参数（浏览器 WebSocket API 不能自定义头）。

    支持登录签发的 Bearer token 与静态 API_TOKEN；鉴权关闭时放行（本地开发）。
    """
    if not auth_enabled():
        return True
    qs = parse_qs(websocket.scope.get("query_string", b"").decode("utf-8", "ignore"))
    token = (qs.get("token") or [""])[0]
    return check_request_auth(f"Bearer {token}", token)


@app.websocket("/ws/task/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    # Starlette 1.x 要求 websocket 参数显式标注类型，否则会被当成必填 query 参数并拒绝握手
    if not _ws_token_ok(websocket):
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
    if not _ws_token_ok(websocket):
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


@app.exception_handler(HTTPException)
async def _http_exception_handler(request, exc: HTTPException):
    """5xx 统一脱敏：内部异常文本只写服务端日志，不回显给客户端。"""
    if exc.status_code >= 500:
        logger.error("HTTP %s %s: %s", exc.status_code, request.url.path, exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": "服务器内部错误，请稍后重试"})
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"error": "服务器内部错误"})
