"""音频处理服务"""
import asyncio
import logging
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.temp_dir = Path("./data/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract(self, video_path: str) -> str:
        video_name = Path(video_path).stem
        audio_path = self.temp_dir / f"{video_name}.m4a"
        
        # 兼容旧的 mp3 文件
        old_path = self.temp_dir / f"{video_name}.mp3"
        if old_path.exists():
            logger.info(f"旧音频文件已存在: {old_path}")
            return str(old_path)
        
        if audio_path.exists():
            logger.info(f"音频文件已存在: {audio_path}")
            return str(audio_path)
        
        logger.info(f"提取音频: {video_path}")
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn",
            "-acodec", "aac",        # AAC 比 libmp3lame 快 3-5 倍
            "-b:a", "64k",            # Whisper 只需要语音质量，64k 足够
            "-ar", "16000",           # 16kHz 采样率，Whisper 推荐
            "-ac", "1",               # 单声道，语音识别不需要立体声
            "-y",
            str(audio_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"音频提取失败: {stderr.decode()}")
        
        logger.info(f"音频提取完成: {audio_path}")
        return str(audio_path)
    
    async def get_duration(self, video_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        try:
            return float(stdout.decode().strip()) if process.returncode == 0 else 0.0
        except ValueError:
            return 0.0
