"""上传 API"""
import asyncio
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from ..core.engine import get_engine

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    language: str = Form(default="zh")
):
    """上传视频并开始处理"""
    if not file.filename:
        raise HTTPException(400, "未选择文件")
    
    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    from pathlib import Path
    ext = Path(file.filename).suffix.lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(400, f"不支持的文件格式: {ext}")
    
    if language not in ("zh", "en"):
        language = "zh"
    
    try:
        engine = get_engine()
        content = await file.read()
        file_hash, file_path, is_new = await engine.dedup.process_upload(content, file.filename)
        task = engine.create_task(file.filename, file_hash, file_path, language=language)
        
        asyncio.create_task(
            _process_with_error_handling(engine, task.id, str(file_path))
        )
        
        return {
            "task_id": task.id,
            "filename": file.filename,
            "is_new_upload": is_new,
            "language": language,
            "message": "处理已开始"
        }
        
    except Exception as e:
        logger.error(f"上传失败: {e}")
        raise HTTPException(500, f"上传失败: {str(e)}")

async def _process_with_error_handling(engine, task_id: str, video_path: str):
    try:
        await engine.process_video(task_id, video_path)
    except Exception as e:
        logger.error(f"处理失败 {task_id}: {e}")
