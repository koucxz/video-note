"""Video utility functions."""
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


async def run_ffmpeg(cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run ffmpeg/ffprobe command via thread to avoid Windows event loop issues."""
    try:
        return await asyncio.to_thread(
            lambda: subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffmpeg命令超时: {' '.join(cmd[:4])}")
    except FileNotFoundError:
        raise RuntimeError(f"ffmpeg 未找到，请确保已安装并加入 PATH")


async def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    video_input = str(video_path).replace("\\", "/")
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_input,
    ]
    try:
        proc = await run_ffmpeg(cmd)
        if proc.returncode != 0:
            logger.warning("ffprobe failed for %s: %s", video_path, proc.stderr.decode(errors="replace"))
            return 0.0
        import json
        data = json.loads(proc.stdout.decode())
        return float(data.get("format", {}).get("duration", 0))
    except RuntimeError:
        return 0.0
    except Exception as exc:
        logger.warning("get_video_duration error: %s (%s)", exc, type(exc).__name__)
        return 0.0


async def timeout_for_video(video_path: str, factor: float = 1.5,
                            minimum: int = 600, maximum: int = 3600) -> int:
    """按视频时长估算 ffmpeg 超时。

    默认的 300s 对长视频不够：1.5GB / 52 分钟的 webm 抽帧就要 6 分钟以上，
    到 91 帧时被 TimeoutExpired 打断，整条处理链失败。
    """
    duration = await get_video_duration(video_path)
    if not duration:
        return minimum
    return max(minimum, min(maximum, int(duration * factor)))
