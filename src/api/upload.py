"""Upload API - streaming upload, dedup with instant return for known files."""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from ..core.engine import get_engine, _clamp_param
from ..utils.video_utils import get_video_duration, quick_hash_file
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

    # 记录快速指纹，下次同文件上传前就能直接判定「服务器已有」，无需再传
    try:
        quick = await asyncio.to_thread(quick_hash_file, str(file_path))
        file_size = Path(file_path).stat().st_size
        engine.checkpoint.update_task(task.id, quick_hash=quick or "", file_size=file_size)
    except Exception as exc:
        logger.warning("quick_hash failed for %s: %s", file_path, exc)

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


class PrecheckRequest(BaseModel):
    filename: str
    size: int
    quick_hash: str = ""


class ReuseRequest(BaseModel):
    video_hash: str
    filename: str = ""
    language: str = "zh"
    note_style: str = DEFAULT_NOTE_STYLE
    processing_options: str = "{}"


@router.post("/api/upload/precheck", tags=["upload"],
    summary="Check if the video is already on the server before uploading",
    description="Client sends filename + size + a sampled quick hash. If a matching source video exists, the upload can be skipped entirely.")
async def precheck_upload(req: PrecheckRequest):
    if not req.filename:
        raise HTTPException(400, "No file selected")
    ext = Path(req.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}")
    if req.size <= 0:
        raise HTTPException(400, "Invalid file size")

    engine = get_engine()
    candidates = engine.checkpoint.find_tasks_by_filename(req.filename)
    # 文件被改名的场景：再按字节数捞一遍候选，靠快速指纹确认
    seen_ids = {c["id"] for c in candidates}
    for c in engine.checkpoint.find_tasks_by_size(req.size):
        if c["id"] not in seen_ids:
            candidates.append(c)
            seen_ids.add(c["id"])

    for cand in candidates:
        video_path = cand.get("video_path")
        if not video_path:
            continue
        path = Path(video_path)
        try:
            if not path.exists() or path.stat().st_size != req.size:
                continue
        except OSError:
            continue

        stored = cand.get("quick_hash") or ""
        if not stored:
            stored = await asyncio.to_thread(quick_hash_file, video_path)
            if stored:
                engine.checkpoint.update_task(cand["id"], quick_hash=stored, file_size=req.size)

        # 任一侧拿不到指纹时退回「同名 + 同大小」判定
        if not req.quick_hash or not stored or stored == req.quick_hash:
            video_hash = cand.get("video_hash")
            siblings = [c for c in engine.checkpoint.find_any_tasks_by_hash(video_hash)] or [cand]
            return {
                "found": True,
                "video_hash": video_hash,
                "filename": req.filename,
                "size": req.size,
                "tasks": [{
                    "task_id": c["id"],
                    "language": c.get("language") or "zh",
                    "note_style": c.get("note_style") or DEFAULT_NOTE_STYLE,
                    "status": c.get("status"),
                } for c in siblings],
            }

    return {"found": False, "filename": req.filename, "size": req.size}


@router.post("/api/upload/reuse", tags=["upload"],
    summary="Start processing an existing source video without uploading",
    description="Reuses a video already stored on the server (matched by precheck) and processes it with the requested language/style.")
async def reuse_upload(req: ReuseRequest):
    if not req.video_hash:
        raise HTTPException(400, "video_hash is required")

    engine = get_engine()
    src = engine.checkpoint.find_any_task_by_hash(req.video_hash)
    if not src:
        raise HTTPException(404, "This video is not on the server")
    video_path = src.get("video_path")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(410, "Source video has been removed from the server")

    filename = req.filename or src.get("original_filename") or "video"
    _, language, note_style, overrides, _ = parse_upload_options(
        filename, req.language, req.note_style, req.processing_options
    )
    logger.info("Reusing stored video %s for %s/%s", req.video_hash[:12], language, note_style)
    return await finalize_upload(
        filename, req.video_hash, video_path, False, language, note_style, overrides
    )


async def _process_with_error_handling(engine, task_id: str, video_path: str):
    try:
        await engine.process_video(task_id, video_path)
    except Exception as exc:
        logger.error("Processing failed %s: %s", task_id, exc)
