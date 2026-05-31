"""任务 API"""
import asyncio
from fastapi import APIRouter, HTTPException
from ..core.engine import get_engine
from ..models.task import TaskStatus

router = APIRouter()

@router.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态"""
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    
    if not task:
        raise HTTPException(404, "任务不存在")
    
    return {
        "task_id": task["id"],
        "status": task["status"],
        "stage": task["stage"],
        "progress": task["progress"],
        "filename": task["original_filename"],
        "error": task["error"]
    }

@router.post("/api/task/{task_id}/retry")
async def retry_task(task_id: str):
    """重试失败的任务"""
    engine = get_engine()
    
    try:
        engine.retry_task(task_id)
        return {"message": "重试已启动"}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"重试失败: {str(e)}")

@router.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    
    if not task:
        raise HTTPException(404, "任务不存在")
    
    engine.checkpoint.delete_task(task_id)
    return {"message": "任务已删除"}
