"""Upload API - legacy single-request upload plus shared finalize logic.

The browser UI no longer uses this endpoint: it uploads in chunks through
`upload_chunked.py`. This route stays for curl / scripts and shares the
validation + task-creation path (`finalize_upload`) with the chunked flow so
both behave identically once the bytes are on disk.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..core.engine import get_engine, _clamp_param
from ..core.dedup import UploadTooLargeError
from ..utils.video_utils import get_video_duration

from ..services.ai_service import DEFAULT_NOTE_STYLE, VALID_NOTE_STYLES

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))
MAX_DURATION_SECONDS = int(os.getenv("MAX_VIDEO_DURATION_SECONDS", str(3600)))

ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}


def _human_size(num_bytes: int) -> str:
    """上限提示用：2GB / 800MB 这种读法，避免让用户自己换算字节数。"""
    if num_bytes >= 1024 ** 3:
        return f"{num_bytes / 1024 ** 3:.0f}GB"
    return f"{num_bytes / 1024 ** 2:.0f}MB"


def validate_filename(filename: str) -> str:
    """Return the lower-cased extension or raise 400."""
    if not filename:
        raise HTTPException(400, "未选择文件")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的视频格式：{ext or '未知'}")
    return ext


def parse_options(processing_options: str) -> dict:
    """Parse the JSON blob of processing overrides, clamped to config bounds."""
    try:
        raw_opts = json.loads(processing_options) if processing_options else {}
    except (json.JSONDecodeError, TypeError):
        raw_opts = {}
    if not isinstance(raw_opts, dict):
        raw_opts = {}
    overrides = {}
    if "keyframe_interval" in raw_opts:
        overrides["keyframe_interval"] = _clamp_param("keyframe_interval", raw_opts["keyframe_interval"])
    if "segment_duration" in raw_opts:
        overrides["segment_duration"] = _clamp_param("segment_duration", raw_opts["segment_duration"])
    return overrides


def normalize_language(language: str) -> str:
    return language if language in ("zh", "en") else "zh"


def normalize_note_style(note_style: str) -> str:
    return note_style if note_style in VALID_NOTE_STYLES else DEFAULT_NOTE_STYLE


def _discard_upload(engine, file_hash: str, file_path: Path) -> None:
    """Drop a rejected upload, unless another task still shares the file.

    Uploads are deduplicated by content hash, so two identical uploads point at
    one `{hash}.mp4`. Unlinking on a rejection would break the sibling task.
    """
    try:
        if file_hash and engine.checkpoint.count_other_tasks_by_hash(file_hash, ""):
            return
    except Exception:  # noqa: BLE001 - cleanup must never mask the real error
        return
    try:
        file_path.unlink()
    except OSError:
        pass


async def finalize_upload(engine, filename: str, file_hash: str, file_path: Path, is_new: bool,
                          language: str, note_style: str, overrides: dict) -> dict:
    """Common tail shared by every upload entry point.

    Dedup hit -> return the finished task. Otherwise probe duration, create the
    task row and schedule background processing.
    """
    existing = engine.checkpoint.find_task_by_hash(file_hash)
    if existing:
        return {
            "task_id": existing["id"],
            "filename": filename,
            "is_new_upload": False,
            "already_completed": True,
            "language": language,
            "note_style": note_style,
            "message": "文件已处理过，直接返回已有笔记",
        }

    duration = await get_video_duration(str(file_path))
    if duration <= 0:
        _discard_upload(engine, file_hash, file_path)
        raise HTTPException(400, "无法读取视频文件，请上传有效的视频文件")

    duration_warning = None
    if duration > MAX_DURATION_SECONDS:
        _discard_upload(engine, file_hash, file_path)
        raise HTTPException(413, f"视频时长超过 {MAX_DURATION_SECONDS // 60} 分钟上限（当前 {duration / 60:.0f} 分钟）")
    if duration > MAX_DURATION_SECONDS * 0.8:
        duration_warning = f"视频时长 {duration/60:.0f} 分钟，处理可能需要较长时间。"

    task = engine.create_task(
        filename, file_hash, file_path,
        language=language, note_style=note_style,
        processing_overrides=overrides if overrides else None,
    )

    # Track the async task so GC doesn't cancel it
    t = asyncio.create_task(_process_with_error_handling(engine, task.id, str(file_path)))
    engine._running_tasks.add(t)
    t.add_done_callback(engine._running_tasks.discard)

    response = {
        "task_id": task.id,
        "filename": filename,
        "is_new_upload": is_new,
        "language": language,
        "note_style": note_style,
        "processing_overrides": overrides,
        "message": "Processing started",
    }
    if duration_warning:
        response["duration_warning"] = duration_warning
    return response


@router.post("/api/upload", tags=["upload"],
    summary="Upload and process video (single request)",
    description="Upload a video file in one request for AI-powered note generation. "
                "Supports deduplication - uploading the same file twice returns the existing result. "
                "The web UI uses the chunked endpoints under /api/upload/ instead.")
async def upload_video(
    file: UploadFile = File(...),
    language: str = Form(default="zh"),
    note_style: str = Form(default=DEFAULT_NOTE_STYLE),
    processing_options: str = Form(default="{}"),
):
    validate_filename(file.filename)
    language = normalize_language(language)
    note_style = normalize_note_style(note_style)
    overrides = parse_options(processing_options)

    # Check file size
    content_length = file.size if hasattr(file, "size") else None
    if content_length and content_length > MAX_FILE_SIZE:
        raise HTTPException(413, f"文件超过 {_human_size(MAX_FILE_SIZE)} 上限，请先压缩或裁剪视频")

    try:
        engine = get_engine()

        # Streaming upload
        file_hash, file_path, is_new = await engine.dedup.process_upload(
            file, file.filename, max_bytes=MAX_FILE_SIZE
        )
        return await finalize_upload(
            engine, file.filename, file_hash, file_path, is_new,
            language, note_style, overrides,
        )
    except HTTPException:
        raise
    except UploadTooLargeError as exc:
        raise HTTPException(413, str(exc))
    except Exception as exc:
        logger.error("Upload failed: %s", exc)
        raise HTTPException(500, f"上传失败：{exc}")


async def _process_with_error_handling(engine, task_id: str, video_path: str):
    try:
        await engine.process_video(task_id, video_path)
    except Exception as exc:
        logger.error("Processing failed %s: %s", task_id, exc)
