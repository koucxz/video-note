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
                    "path": str(f.resolve()),
                })
    
    files.sort(key=lambda x: x["size"], reverse=True)
    total_size = sum(f["size"] for f in files)
    
    return {
        "files": files,
        "count": len(files),
        "total_size": total_size,
        "upload_dir": str(upload_dir.resolve()),
        "output_dir": str(Path(engine.config.storage.output_dir).resolve()),
    }


@router.post("/api/storage/uploads/clean", tags=["storage"],
    summary="Clean uploaded videos",
    description="Delete uploaded video files. Pass a list of hashes to clean specific files, or null to clean all.")
async def clean_uploads(body: CleanRequest = CleanRequest()):
    engine = get_engine()
    upload_dir = Path(engine.config.storage.upload_dir)
    hashes = body.hashes
    
    if not upload_dir.exists():
        return {"deleted": 0, "freed_bytes": 0}
    
    deleted = 0
    freed = 0
    
    if hashes is None:
        for f in upload_dir.iterdir():
            if f.is_file() and f.suffix.lower() in VALID_VIDEO_EXT:
                size = f.stat().st_size
                try:
                    f.unlink()
                    deleted += 1
                    freed += size
                except OSError:
                    pass
    else:
        for h in hashes:
            for ext in VALID_VIDEO_EXT:
                f = upload_dir / f"{h}{ext}"
                if f.exists():
                    size = f.stat().st_size
                    try:
                        f.unlink()
                        deleted += 1
                        freed += size
                    except OSError:
                        pass
    
    return {"deleted": deleted, "freed_bytes": freed}
