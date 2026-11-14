"""视频处理服务"""
import logging
import aiofiles
from pathlib import Path
from typing import List
from ..utils.video_utils import run_ffmpeg

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self):
        self.frames_dir = Path("./data/temp/frames")
        self.frames_dir.mkdir(parents=True, exist_ok=True)

    async def extract_subtitles(self, video_path: str) -> dict:
        """Extract embedded subtitles from video file using ffmpeg.
        Returns {"text": str, "format": str, "found": bool}
        """
        video = Path(video_path)
        temp_dir = Path("./data/temp/subtitles")
        temp_dir.mkdir(parents=True, exist_ok=True)
        stem = video.stem
        srt_path = temp_dir / f"{stem}.srt"
        
        # Try to extract embedded subtitles
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-map", "0:s:0?",
            "-y", str(srt_path),
        ]
        try:
            proc = await run_ffmpeg(cmd)
            if proc.returncode == 0 and srt_path.exists() and srt_path.stat().st_size > 0:
                async with aiofiles.open(srt_path, "r", encoding="utf-8", errors="replace") as f:
                    text = await f.read()
                logger.info("Extracted subtitles: %d chars", len(text))
                return {"text": text, "format": "srt", "found": True}
        except RuntimeError as exc:
            logger.warning("Subtitle extraction failed: %s", exc)
        
        # Check for external subtitle files next to the video
        for ext in (".srt", ".vtt", ".ass", ".ssa"):
            external = video.with_suffix(ext)
            if external.exists():
                try:
                    async with aiofiles.open(external, "r", encoding="utf-8", errors="replace") as f:
                        text = await f.read()
                    logger.info("Found external subtitle: %s", external.name)
                    return {"text": text, "format": ext.lstrip("."), "found": True}
                except Exception:
                    pass
        
        return {"text": "", "format": "", "found": False}
    
    async def extract_keyframes(self, video_path: str, interval: int = 30) -> List[str]:
        video_name = Path(video_path).stem
        output_dir = self.frames_dir / video_name
        output_dir.mkdir(parents=True, exist_ok=True)

        existing_frames = sorted(output_dir.glob("frame_*.jpg"))
        if existing_frames:
            logger.info(f"帧已存在: {len(existing_frames)} 个")
            return [str(f) for f in existing_frames]

        logger.info(f"提取关键帧: 间隔 {interval}s")
        # Use forward slashes for ffmpeg compatibility
        output_pattern = str(output_dir / "frame_%04d.jpg").replace("\\", "/")
        video_input = str(video_path).replace("\\", "/")

        cmd = [
            "ffmpeg", "-i", video_input,
            "-vf", f"fps=1/{interval},scale=640:-1",
            "-q:v", "5",
            "-y",
            output_pattern
        ]

        try:
            proc = await run_ffmpeg(cmd)
            if proc.returncode != 0:
                stderr_text = proc.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"关键帧提取失败: {stderr_text[-500:]}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"关键帧提取异常: {type(e).__name__}: {e}")

        frames = sorted(output_dir.glob("frame_*.jpg"))
        logger.info(f"关键帧提取完成: {len(frames)} 个")
        return [str(f) for f in frames]
    
    async def get_video_info(self, video_path: str) -> dict:
        import json
        video_input = str(video_path).replace("\\", "/")
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_input
        ]
        try:
            proc = await run_ffmpeg(cmd)
            return json.loads(proc.stdout.decode()) if proc.returncode == 0 else {}
        except (json.JSONDecodeError, RuntimeError):
            return {}
