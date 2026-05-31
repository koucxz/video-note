"""笔记 API"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..core.engine import get_engine

router = APIRouter()

@router.get("/api/history")
async def get_history():
    """获取历史记录"""
    engine = get_engine()
    tasks = engine.checkpoint.get_all_tasks()
    
    return [{
        "task_id": t["id"],
        "videoName": t["original_filename"],
        "status": t["status"],
        "createdAt": t["created_at"],
        "progress": t["progress"],
        "notePath": t["note_path"]
    } for t in tasks]

@router.get("/api/note/{task_id}")
async def get_note(task_id: str):
    """获取生成的笔记"""
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    
    if not task:
        raise HTTPException(404, "任务不存在")
    
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "笔记不存在或尚未生成")
    
    return FileResponse(
        task["note_path"],
        media_type="text/markdown",
        filename=f"{Path(task['original_filename']).stem}.md"
    )

@router.get("/api/note/{task_id}/content")
async def get_note_content(task_id: str):
    """获取笔记内容（JSON 格式）"""
    engine = get_engine()
    task = engine.checkpoint.get_task(task_id)
    
    if not task:
        raise HTTPException(404, "任务不存在")
    
    if not task["note_path"] or not Path(task["note_path"]).exists():
        raise HTTPException(404, "笔记不存在或尚未生成")
    
    content = Path(task["note_path"]).read_text(encoding="utf-8")
    return {
        "task_id": task_id,
        "filename": task["original_filename"],
        "content": content
    }
