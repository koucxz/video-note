"""Upload API - streaming upload, dedup with instant return for known files."""
import asyncio
import json
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..core.engine import get_engine, _clamp_param
from ..core.dedup import UploadTooLargeError
from ..utils.video_utils import get_video_duration

from ..services.ai_service import DEFAULT_NOTE_STYLE, VALID_NOTE_STYLES

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = int(__import__("os").getenv("MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))
MAX_DURATION_SECONDS = int(__import__("os").getenv("MAX_VIDEO_DURATION_SECONDS", str(3600)))


@router.post("/api/upload", tags=["upload"],
    summary="Upload and process video",
    description="Upload a video file for AI-powered note generation. Supports deduplication - uploading the same file twice returns the existing result.")
async def upload_video(
    file: UploadFile = File(...),
    language: str = Form(default="zh"),
    note_style: str = Form(default=DEFAULT_NOTE_STYLE),
    processing_options: str = Form(default="{}"),
):
    if not file.filename:
        raise HTTPException(400, "No file selected")

    ext = Path(file.filename).suffix.lower()
    allowed = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format: {ext}")

    if language not in ("zh", "en"):
        language = "zh"
    if note_style not in VALID_NOTE_STYLES:
        note_style = DEFAULT_NOTE_STYLE

    # Parse and validate processing options
    try:
        raw_opts = json.loads(processing_options) if processing_options else {}
    except (json.JSONDecodeError, TypeError):
        raw_opts = {}

    overrides = {}
    if "keyframe_interval" in raw_opts:
        overrides["keyframe_interval"] = _clamp_param("keyframe_interval", raw_opts["keyframe_interval"])
    if "segment_duration" in raw_opts:
        overrides["segment_duration"] = _clamp_param("segment_duration", raw_opts["segment_duration"])

    # Check file size
    content_length = file.size if hasattr(file, "size") else None
    if content_length and content_length > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large; max {MAX_FILE_SIZE / 1024 / 1024:.0f}MB")

    try:
        engine = get_engine()

        # Streaming upload
        file_hash, file_path, is_new = await engine.dedup.process_upload(
            file, file.filename, max_bytes=MAX_FILE_SIZE
        )

        # Check if same file already completed
        existing = engine.checkpoint.find_task_by_hash(file_hash)
        if existing:
            return {
                "task_id": existing["id"],
                "filename": file.filename,
                "is_new_upload": False,
                "already_completed": True,
                "language": language,
                "note_style": note_style,
                "message": "File already processed - returning existing note",
            }

        # Check video duration
        duration = await get_video_duration(str(file_path))
        if duration <= 0:
            try:
                file_path.unlink()
            except OSError:
                pass
            raise HTTPException(400, "无法读取视频文件，请上传有效的视频文件")
        duration_warning = None
        if duration > MAX_DURATION_SECONDS:
            raise HTTPException(413, f"Video is too long; maximum is {MAX_DURATION_SECONDS // 60} minutes")
        elif duration > MAX_DURATION_SECONDS * 0.8:
            duration_warning = f"Video is {duration/60:.0f} minutes long. Processing may take several minutes."

        task = engine.create_task(
            file.filename, file_hash, file_path,
            language=language, note_style=note_style,
            processing_overrides=overrides if overrides else None,
        )

        # Track the async task so GC doesn't cancel it
        t = asyncio.create_task(_process_with_error_handling(engine, task.id, str(file_path)))
        engine._running_tasks.add(t)
        t.add_done_callback(engine._running_tasks.discard)

        response = {
            "task_id": task.id,
            "filename": file.filename,
            "is_new_upload": is_new,
            "language": language,
            "note_style": note_style,
            "processing_overrides": overrides,
            "message": "Processing started",
        }
        if duration_warning:
            response["duration_warning"] = duration_warning
        return response
    except HTTPException:
        raise
    except UploadTooLargeError as exc:
        raise HTTPException(413, str(exc))
    except Exception as exc:
        logger.error("Upload failed: %s", exc)
        raise HTTPException(500, f"Upload failed: {exc}")


async def _process_with_error_handling(engine, task_id: str, video_path: str):
    try:
        await engine.process_video(task_id, video_path)
    except Exception as exc:
        logger.error("Processing failed %s: %s", task_id, exc)
