"""视频处理服务"""
import asyncio
import logging
import aiofiles
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self):
        self.frames_dir = Path("./data/temp/frames")
        self.frames_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract_keyframes(self, video_path: str, interval: int = 30) -> List[str]:
        video_name = Path(video_path).stem
        output_dir = self.frames_dir / video_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        existing_frames = sorted(output_dir.glob("frame_*.jpg"))
        if existing_frames:
            logger.info(f"帧已存在: {len(existing_frames)} 个")
            return [str(f) for f in existing_frames]
        
        logger.info(f"提取关键帧: 间隔 {interval}s")
        output_pattern = str(output_dir / "frame_%04d.jpg")
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps=1/{interval},scale=640:-1",  # 缩放到 640px 宽，大幅减少 CPU 和内存
            "-q:v", "5",                                # 中等质量（1-31，越大越快）
            "-y",
            output_pattern
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"关键帧提取失败: {stderr.decode()}")
        
        frames = sorted(output_dir.glob("frame_*.jpg"))
        logger.info(f"关键帧提取完成: {len(frames)} 个")
        return [str(f) for f in frames]
    
    async def get_video_info(self, video_path: str) -> dict:
        import json
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        try:
            return json.loads(stdout.decode()) if process.returncode == 0 else {}
        except json.JSONDecodeError:
            return {}
