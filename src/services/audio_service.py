"""音频处理服务"""
import logging
import aiofiles
from pathlib import Path
from ..utils.video_utils import run_ffmpeg

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
        video_input = str(video_path).replace("\\", "/")
        audio_output = str(audio_path).replace("\\", "/")
        cmd = [
            "ffmpeg", "-i", video_input,
            "-vn",
            "-acodec", "aac",        # AAC 比 libmp3lame 快 3-5 倍
            "-b:a", "64k",            # Whisper 只需要语音质量，64k 足够
            "-ar", "16000",           # 16kHz 采样率，Whisper 推荐
            "-ac", "1",               # 单声道，语音识别不需要立体声
            "-y",
            audio_output
        ]

        try:
            proc = await run_ffmpeg(cmd)
            if proc.returncode != 0:
                raise RuntimeError(f"音频提取失败: {proc.stderr.decode('utf-8', errors='replace')[-500:]}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"音频提取异常: {type(e).__name__}: {e}")
        
        logger.info(f"音频提取完成: {audio_path}")
        return str(audio_path)
    
    async def get_duration(self, video_path: str) -> float:
        video_input = str(video_path).replace("\\", "/")
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_input
        ]
        try:
            proc = await run_ffmpeg(cmd)
            return float(proc.stdout.decode().strip()) if proc.returncode == 0 else 0.0
        except (ValueError, RuntimeError):
            return 0.0
