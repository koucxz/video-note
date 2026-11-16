"""Task API with error_kind in response."""
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body
from ..core.engine import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()

_ACTIVE_STATUSES = ("processing", "pending")


def _maybe_delete_video(engine, task: dict, task_id: str) -> None:
    """Unlink the uploaded video. Only used when the caller explicitly asks for it.

    Deleting a history record must NOT drop the video: the file is deduplicated
    by content hash, so several records (or a later re-upload) point at the same
    `{hash}.mp4`, and 设置-存储管理 is the single place that frees disk space.
    Wiping it here made new uploads "disappear" from storage right after the
    record was deleted, and previously killed in-flight duplicate tasks.
    """
    video_path = task.get("video_path")
    if not video_path:
        return
    video_hash = task.get("video_hash")
    if video_hash:
        try:
            shared = engine.checkpoint.count_other_tasks_by_hash(video_hash, task_id)
        except Exception as exc:  # noqa: BLE001 - never fail a delete on this check
            logger.warning("Hash reference check failed for %s: %s", task_id, exc)
            shared = 0
        if shared:
            logger.info("Keeping %s: %d other task(s) share hash %s", video_path, shared, video_hash)
            return
    if task.get("status") in _ACTIVE_STATUSES:
        try:
            engine.cancel_task(task_id)
        except Exception:
            pass
    try:
        p = Path(video_path)
        if p.exists():
            p.unlink()
    except OSError:
        pass


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


@router.patch("/api/task/{task_id}/name", tags=["tasks"])
async def rename_task(task_id: str, body: dict = Body(...)):
    """Update the user-facing name of a note record without renaming the source file."""
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    name = body.get("name") if isinstance(body, dict) else None
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(422, "Name is required")
    name = name.strip()
    if len(name) > 160:
        raise HTTPException(422, "Name is too long")
    engine.checkpoint.update_task(task_id, display_name=name, updated_at=datetime.now())
    return {"task_id": task_id, "name": name}


@router.delete("/api/task/{task_id}", tags=["tasks"],
    summary="Delete task record",
    description="Delete a task record and its note. The uploaded video stays on disk "
                "and is freed from 设置-存储管理 (pass ?with_file=true to remove it now).")
async def delete_task(task_id: str, with_file: bool = False):
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
    
    if with_file:
        _maybe_delete_video(engine, task, task_id)
    
    try:
        if getattr(engine, "vector", None) is not None:
            engine.vector.remove_note(task_id)
    except Exception:
        pass
    engine.checkpoint.delete_task(task_id)
    return {"message": "Task deleted", "video_kept": not with_file}


def _delete_one(engine, task_id: str, with_file: bool = False):
    """Delete a single task record (and its note)."""
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

    if with_file:
        _maybe_delete_video(engine, task, task_id)

    try:
        if getattr(engine, "vector", None) is not None:
            engine.vector.remove_note(task_id)
    except Exception:
        pass
    engine.checkpoint.delete_task(task_id)
    return True


@router.post("/api/tasks/batch-delete", tags=["tasks"],
    summary="Batch delete tasks",
    description="Delete multiple task records by task IDs. Source videos are kept unless delete_files is true.")
async def batch_delete_tasks(data: dict = Body(...)):
    task_ids = data.get("task_ids", [])
    with_file = bool(data.get("delete_files"))
    if not task_ids:
        return {"deleted": 0, "total": 0}
    engine = get_engine()
    count = 0
    for tid in task_ids:
        if _delete_one(engine, tid, with_file):
            count += 1
    return {"deleted": count, "total": len(task_ids), "video_kept": not with_file}
