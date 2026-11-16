"""Storage management API - list and clean uploaded videos."""
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..core.engine import get_engine

router = APIRouter()

VALID_VIDEO_EXT = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}


class CleanRequest(BaseModel):
    hashes: Optional[list[str]] = None


@router.get("/api/storage/uploads", tags=["storage"],
    summary="List uploaded videos",
    description="List all uploaded video files with their original names and sizes.")
async def list_uploads():
    engine = get_engine()
    upload_dir = Path(engine.config.storage.upload_dir)
    
    tasks = engine.checkpoint.get_all_tasks()
    hash_to_name = {}
    for t in tasks:
        h = t.get("video_hash")
        if h and h not in hash_to_name:
            hash_to_name[h] = t["original_filename"]
    
    files = []
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if f.is_file() and f.suffix.lower() in VALID_VIDEO_EXT:
                hash_id = f.stem
                original_name = hash_to_name.get(hash_id, f"{hash_id}{f.suffix}")
                files.append({
                    "hash": hash_id,
                    "filename": original_name,
                    "size": f.stat().st_size,
                })
    
    files.sort(key=lambda x: x["size"], reverse=True)
    total_size = sum(f["size"] for f in files)
    
    return {
        "files": files,
        "count": len(files),
        "total_size": total_size,
    }


@router.post("/api/storage/uploads/clean", tags=["storage"],
    summary="Clean uploaded videos",
    description="Delete uploaded video files. Pass a list of hashes to clean specific files, or null to clean all.")
async def clean_uploads(body: CleanRequest = CleanRequest()):
    engine = get_engine()
    upload_dir = Path(engine.config.storage.upload_dir)
    hashes = body.hashes

    if not upload_dir.exists():
        return {"deleted": 0, "freed_bytes": 0, "skipped": 0}

    # 正在排队/处理的任务还要拿它当素材，清掉就等于把源头抽走（曾导致关键帧阶段报文件不存在）
    try:
        active = engine.checkpoint.active_video_hashes()
    except Exception:
        active = set()

    deleted = 0
    freed = 0
    skipped = 0

    def _clean_one(f: Path) -> None:
        nonlocal deleted, freed, skipped
        if f.stem in active:
            skipped += 1
            return
        try:
            size = f.stat().st_size
            f.unlink()
        except OSError:
            return
        deleted += 1
        freed += size

    if hashes is None:
        for f in upload_dir.iterdir():
            if f.is_file() and f.suffix.lower() in VALID_VIDEO_EXT:
                _clean_one(f)
    else:
        for h in hashes:
            for ext in VALID_VIDEO_EXT:
                f = upload_dir / f"{h}{ext}"
                if f.exists():
                    _clean_one(f)

    return {"deleted": deleted, "freed_bytes": freed, "skipped": skipped}
