"""Task API with error_kind in response."""
from fastapi import APIRouter, HTTPException, Body
from ..core.engine import get_engine

router = APIRouter()


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


@router.delete("/api/task/{task_id}", tags=["tasks"],
    summary="Delete task and files",
    description="Delete a task and its associated files (note and video if no other tasks reference it).")
async def delete_task(task_id: str):
    from pathlib import Path
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
    if task.get("video_path"):
        video_hash = task.get("video_hash")
        other = engine.checkpoint.find_task_by_hash(video_hash) if video_hash else None
        if not other or other["id"] == task_id:
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
    from pathlib import Path
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

    if task.get("video_path"):
        video_hash = task.get("video_hash")
        other = engine.checkpoint.find_task_by_hash(video_hash) if video_hash else None
        if not other or other["id"] == task_id:
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
