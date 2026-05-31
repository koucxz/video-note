"""视频处理服务"""
import asyncio
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class VideoService:
    """视频处理服务"""
    
    def __init__(self):
        self.frames_dir = Path("./data/temp/frames")
        self.frames_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract_keyframes(self, video_path: str, interval: int = 30) -> List[str]:
        """
        从视频中提取关键帧
        interval: 提取间隔（秒）
        返回帧图片路径列表
        """
        video_name = Path(video_path).stem
        output_dir = self.frames_dir / video_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查是否已有帧
        existing_frames = sorted(output_dir.glob("frame_*.jpg"))
        if existing_frames:
            logger.info(f"帧已存在: {len(existing_frames)} 个")
            return [str(f) for f in existing_frames]
        
        logger.info(f"开始提取关键帧: {video_path}, 间隔: {interval}秒")
        
        # 使用 ffmpeg 提取帧
        output_pattern = str(output_dir / "frame_%04d.jpg")
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps=1/{interval}",  # 每 interval 秒一帧
            "-q:v", "2",  # 图片质量
            "-y",
            output_pattern
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "未知错误"
            logger.error(f"关键帧提取失败: {error_msg}")
            raise RuntimeError(f"关键帧提取失败: {error_msg}")
        
        # 获取提取的帧
        frames = sorted(output_dir.glob("frame_*.jpg"))
        logger.info(f"关键帧提取完成: {len(frames)} 个")
        
        return [str(f) for f in frames]
    
    async def get_video_info(self, video_path: str) -> dict:
        """获取视频信息"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return {}
        
        import json
        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError:
            return {}
