"""音频处理服务"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class AudioService:
    """音频提取服务"""
    
    def __init__(self):
        self.temp_dir = Path("./data/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract(self, video_path: str) -> str:
        """
        从视频中提取音频
        返回音频文件路径
        """
        video_name = Path(video_path).stem
        audio_path = self.temp_dir / f"{video_name}.mp3"
        
        # 如果音频已存在，直接返回
        if audio_path.exists():
            logger.info(f"音频文件已存在: {audio_path}")
            return str(audio_path)
        
        logger.info(f"开始提取音频: {video_path}")
        
        # 使用 ffmpeg 提取音频
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",  # 不包含视频
            "-acodec", "libmp3lame",
            "-q:a", "2",  # 音频质量
            "-y",  # 覆盖已有文件
            str(audio_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "未知错误"
            logger.error(f"音频提取失败: {error_msg}")
            raise RuntimeError(f"音频提取失败: {error_msg}")
        
        logger.info(f"音频提取完成: {audio_path}")
        return str(audio_path)
    
    async def get_duration(self, video_path: str) -> float:
        """获取视频时长（秒）"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return 0.0
        
        try:
            return float(stdout.decode().strip())
        except ValueError:
            return 0.0
