"""Upload API - streaming upload, dedup with instant return for known files."""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..core.engine import get_engine, _clamp_param
from ..utils.video_utils import get_video_duration
from ..services.ai_service import DEFAULT_NOTE_STYLE, VALID_NOTE_STYLES

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_DURATION_SECONDS = 6 * 3600  # 6 hours
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}


def parse_upload_options(filename: str, language: str, note_style: str, processing_options: str):
    """校验上传参数，返回 (ext, language, note_style, overrides, raw_opts)。"""
    if not filename:
        raise HTTPException(400, "No file selected")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}")

    if language not in ("zh", "en"):
        language = "zh"
    if note_style not in VALID_NOTE_STYLES:
        note_style = DEFAULT_NOTE_STYLE

    try:
        raw_opts = json.loads(processing_options) if processing_options else {}
    except (json.JSONDecodeError, TypeError):
        raw_opts = {}

    overrides = {}
    if "keyframe_interval" in raw_opts:
        overrides["keyframe_interval"] = _clamp_param("keyframe_interval", raw_opts["keyframe_interval"])
    if "segment_duration" in raw_opts:
        overrides["segment_duration"] = _clamp_param("segment_duration", raw_opts["segment_duration"])

    return ext, language, note_style, overrides, raw_opts


async def finalize_upload(filename: str, file_hash: str, file_path,
                          is_new: bool, language: str, note_style: str,
                          overrides: dict) -> dict:
    """文件已落盘后的公共收尾：去重命中 / 时长校验 / 建任务 / 起处理协程。"""
    engine = get_engine()

    # 只有「同视频 + 同语言 + 同风格」才算已完成，可直接复用；
    # 换语言/换风格必须重新生成，否则会拿到上一份语言的笔记。
    existing = engine.checkpoint.find_task_by_hash(
        file_hash, language=language, note_style=note_style)
    if existing:
        return {
            "task_id": existing["id"],
            "filename": filename,
            "is_new_upload": False,
            "already_completed": True,
            "reused_video": True,
            "language": language,
            "note_style": note_style,
            "message": "Same video already processed in this language and style - returning existing note",
        }

    # 文件已在服务器上（同 hash）但语言/风格不同：不重复上传，直接按新参数重跑
    reused_video = not is_new

    duration = await get_video_duration(str(file_path))
    duration_warning = None
    if duration > MAX_DURATION_SECONDS:
        duration_warning = f"Video is {duration/3600:.1f} hours long. Processing may take a while and consume significant API credits."
    elif duration > 3600:
        duration_warning = f"Video is {duration/60:.0f} minutes long. Processing may take several minutes."

    task = engine.create_task(
        filename, file_hash, file_path,
        language=language, note_style=note_style,
        processing_overrides=overrides if overrides else None,
    )

    t = asyncio.create_task(_process_with_error_handling(engine, task.id, str(file_path)))
    engine._running_tasks.add(t)
    t.add_done_callback(engine._running_tasks.discard)

    response = {
        "task_id": task.id,
        "filename": filename,
        "is_new_upload": is_new,
        "reused_video": reused_video,
        "language": language,
        "note_style": note_style,
        "processing_overrides": overrides,
        "message": "Processing started",
    }
    if duration_warning:
        response["duration_warning"] = duration_warning
    return response


@router.post("/api/upload", tags=["upload"],
    summary="Upload and process video",
    description="Upload a video file for AI-powered note generation. Supports deduplication - uploading the same file twice returns the existing result.")
async def upload_video(
    file: UploadFile = File(...),
    language: str = Form(default="zh"),
    note_style: str = Form(default=DEFAULT_NOTE_STYLE),
    processing_options: str = Form(default="{}"),
):
    _, language, note_style, overrides, raw_opts = parse_upload_options(
        file.filename, language, note_style, processing_options
    )

    content_length = file.size if hasattr(file, "size") else None
    if content_length and content_length > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large: {content_length / 1024 / 1024 / 1024:.1f}GB, max 2GB")

    try:
        engine = get_engine()

        # 并发数由服务端 ProcessingConfig 统一控制，忽略客户端传值

        file_hash, file_path, is_new = await engine.dedup.process_upload(file, file.filename)
        return await finalize_upload(
            file.filename, file_hash, file_path, is_new, language, note_style, overrides
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upload failed: %s", exc)
        raise HTTPException(500, f"Upload failed: {exc}")


async def _process_with_error_handling(engine, task_id: str, video_path: str):
    try:
        await engine.process_video(task_id, video_path)
    except Exception as exc:
        logger.error("Processing failed %s: %s", task_id, exc)
