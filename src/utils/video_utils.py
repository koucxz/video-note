"""Video utility functions."""
import asyncio
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 上传前去重用的「快速指纹」采样粒度：首/中/尾各取 1MB，不读整个文件
QUICK_HASH_SLICE = 1024 * 1024


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


def quick_hash_file(video_path: str) -> str:
    """上传前去重用的快速指纹：文件大小 + 首/中/尾各 1MB 的 SHA-256。

    与前端 computeQuickHash 的实现必须完全一致（切片偏移与拼接顺序都相同）。
    全量 SHA-256 要读完 1.5GB，浏览器里做不了；采样三片只要 3MB，毫秒级完成。
    """
    path = Path(video_path)
    try:
        size = path.stat().st_size
    except OSError:
        return ""
    if size <= 0:
        return ""

    slices = [(0, min(QUICK_HASH_SLICE, size))]
    mid_start = size // 2
    slices.append((mid_start, min(QUICK_HASH_SLICE, size - mid_start)))
    tail_start = max(0, size - QUICK_HASH_SLICE)
    slices.append((tail_start, size - tail_start))

    digest = hashlib.sha256()
    digest.update(f"{size}:".encode())
    try:
        with open(path, "rb") as fh:
            for offset, length in slices:
                fh.seek(offset)
                remaining = length
                while remaining > 0:
                    chunk = fh.read(min(remaining, QUICK_HASH_SLICE))
                    if not chunk:
                        break
                    digest.update(chunk)
                    remaining -= len(chunk)
    except OSError as exc:
        logger.warning("quick_hash_file failed for %s: %s", video_path, exc)
        return ""
    return digest.hexdigest()
