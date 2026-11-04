"""Task API with error_kind in response."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body
from ..core.engine import get_engine
from ..services.ai_service import DEFAULT_NOTE_STYLE, VALID_NOTE_STYLES

router = APIRouter()


def _video_still_used(engine, video_hash, task_id: str) -> bool:
    """源视频是否还被其它任务引用（不区分状态，避免删掉正在用的文件）。"""
    if not video_hash:
        return False
    return bool(engine.checkpoint.other_task_ids_by_hash(video_hash, task_id))


@router.get("/api/task/{task_id}/status", tags=["tasks"],
    summary="Get task status",
    description="Get the current processing status and progress of a task.")
async def get_task_status(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {
        "task_id": task["id"],
        "status": task["status"],
        "stage": task["stage"],
        "progress": task["progress"],
        "filename": task["original_filename"],
        "error": task.get("error"),
        "error_kind": task.get("error_kind", "unknown"),
    }


@router.post("/api/task/{task_id}/regenerate", tags=["tasks"],
    summary="Regenerate note with another language or style",
    description="Start a new task on the same source video with a different language or note style - no re-upload needed.")
async def regenerate_task(task_id: str, data: dict = Body(default=None)):
    import asyncio
    from .upload import _process_with_error_handling

    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    video_path = task.get("video_path")
    if not video_path or not Path(video_path).exists():
        raise HTTPException(400, "Source video is no longer on the server - please upload it again")

    payload = data or {}
    language = payload.get("language") or task.get("language") or "zh"
    if language not in ("zh", "en"):
        language = "zh"
    note_style = payload.get("note_style") or task.get("note_style") or DEFAULT_NOTE_STYLE
    if note_style not in VALID_NOTE_STYLES:
        note_style = DEFAULT_NOTE_STYLE

    video_hash = task.get("video_hash") or ""
    existing = (engine.checkpoint.find_task_by_hash(video_hash, language=language, note_style=note_style)
                if video_hash else None)
    if existing:
        return {
            "task_id": existing["id"],
            "already_completed": True,
            "language": language,
            "note_style": note_style,
        }

    overrides = task.get("processing_overrides") or {}
    new_task = engine.create_task(
        task.get("original_filename") or "video",
        video_hash, video_path,
        language=language, note_style=note_style,
        processing_overrides=overrides if overrides else None,
    )

    t = asyncio.create_task(_process_with_error_handling(engine, new_task.id, video_path))
    engine._running_tasks.add(t)
    t.add_done_callback(engine._running_tasks.discard)

    return {
        "task_id": new_task.id,
        "already_completed": False,
        "language": language,
        "note_style": note_style,
    }


@router.post("/api/task/{task_id}/retry", tags=["tasks"],
    summary="Retry failed task",
    description="Retry a failed task from the last checkpoint.")
async def retry_task(task_id: str):
    engine = get_engine()
    try:
        engine.retry_task(task_id)
        return {"message": "Retry started"}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Retry failed: {exc}")


@router.post("/api/task/{task_id}/cancel", tags=["tasks"],
    summary="Cancel processing task",
    description="Cancel a running or pending task.")
async def cancel_task(task_id: str):
    engine = get_engine()
    try:
        engine.cancel_task(task_id)
        return {"message": "Task cancelled"}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.delete("/api/task/{task_id}", tags=["tasks"],
    summary="Delete task and files",
    description="Delete a task and its associated files (note and video if no other tasks reference it).")
async def delete_task(task_id: str):
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Delete note file
    if task.get("note_path"):
        try:
            p = Path(task["note_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass
    
    # Delete video file (only if no other tasks reference it)
    if task.get("video_path") and not _video_still_used(engine, task.get("video_hash"), task_id):
        try:
            p = Path(task["video_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass
    
    engine.checkpoint.delete_task(task_id)
    return {"message": "Task and files deleted"}


def _delete_one(engine, task_id: str):
    """Delete a single task and its associated files."""
    task = engine.checkpoint.get_task(task_id)
    if not task:
        return False

    if task.get("note_path"):
        try:
            p = Path(task["note_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass

    if task.get("video_path") and not _video_still_used(engine, task.get("video_hash"), task_id):
        try:
            p = Path(task["video_path"])
            if p.exists():
                p.unlink()
        except OSError:
            pass

    engine.checkpoint.delete_task(task_id)
    return True


@router.post("/api/tasks/batch-delete", tags=["tasks"],
    summary="Batch delete tasks",
    description="Delete multiple tasks and their associated files by task IDs.")
async def batch_delete_tasks(data: dict = Body(...)):
    task_ids = data.get("task_ids", [])
    if not task_ids:
        return {"deleted": 0, "total": 0}
    engine = get_engine()
    count = 0
    for tid in task_ids:
        if _delete_one(engine, tid):
            count += 1
    return {"deleted": count, "total": len(task_ids)}
