"""Video utility functions."""
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffprobe failed for %s: %s", video_path, stderr.decode())
            return 0.0
        import json
        data = json.loads(stdout.decode())
        return float(data.get("format", {}).get("duration", 0))
    except Exception as exc:
        logger.warning("get_video_duration error: %s", exc)
        return 0.0
