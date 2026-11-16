"""Storage management API - list and clean uploaded videos.

Two kinds of disk usage are surfaced here:

1. finished uploads in `<data>/uploads` - one `{sha256[:16]}.ext` per distinct
   video, shared by every task that used the same file (dedup by content hash);
2. unfinished chunked sessions in `<data>/tmp_uploads/<upload_id>` - a browser
   that closed mid-upload leaves up to a few hundred MB of parts behind. They
   used to be invisible until the 12 h sweeper ran, which made "I uploaded a
   video and storage shows nothing" look like a bug.

Deleting a history record no longer removes the video (see api/task.py): the
record is metadata, this page is the one place that frees disk space.
"""
import asyncio
import json
import re
import shutil
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from ..core.engine import get_engine

router = APIRouter()

VALID_VIDEO_EXT = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
_ACTIVE_STATUSES = {'processing', 'pending', 'paused'}
_SESSION_ID_RE = re.compile(r'^[0-9a-f]{32}$')


class CleanRequest(BaseModel):
    hashes: Optional[list[str]] = None


def _sessions_root(upload_dir: Path) -> Path:
    """Half-finished chunked uploads live next to (not inside) the upload dir."""
    return upload_dir.parent / "tmp_uploads"


def _list_sessions(upload_dir: Path) -> list[dict]:
    root = _sessions_root(upload_dir)
    if not root.exists():
        return []

    sessions = []
    for child in root.iterdir():
        if not child.is_dir() or not _SESSION_ID_RE.match(child.name):
            continue
        try:
            meta = json.loads((child / "meta.json").read_text("utf-8"))
        except (OSError, ValueError):
            continue

        received = 0
        parts = 0
        for part in child.glob("p*"):
            try:
                received += part.stat().st_size
                parts += 1
            except OSError:
                continue

        total = int(meta.get("size") or 0)
        sessions.append({
            "upload_id": child.name,
            "filename": meta.get("filename") or child.name,
            "size": total,
            "received_bytes": received,
            "received_parts": parts,
            "total_parts": int(meta.get("total_parts") or 0),
            "percent": round(received * 100 / total) if total else 0,
            "created_at": meta.get("created_at"),
        })

    sessions.sort(key=lambda s: s["received_bytes"], reverse=True)
    return sessions


@router.get("/api/storage/uploads", tags=["storage"],
    summary="List uploaded videos and unfinished uploads",
    description="List every uploaded video file with its original name and size, plus chunked "
                "upload sessions that never finished (they still occupy disk).")
async def list_uploads():
    engine = get_engine()
    upload_dir = Path(engine.config.storage.upload_dir)

    tasks = engine.checkpoint.get_all_tasks()
    by_hash: dict[str, list[dict]] = {}
    for t in tasks:
        h = t.get("video_hash")
        if h:
            by_hash.setdefault(h, []).append(t)

    files = []
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            if not (f.is_file() and f.suffix.lower() in VALID_VIDEO_EXT):
                continue
            hash_id = f.stem
            owners = by_hash.get(hash_id, [])
            named = next((o["original_filename"] for o in owners if o.get("original_filename")), None)
            files.append({
                "hash": hash_id,
                "filename": named or f"{hash_id}{f.suffix}",
                "size": f.stat().st_size,
                "task_count": len(owners),
                "in_use": any(o.get("status") in _ACTIVE_STATUSES for o in owners),
            })

    files.sort(key=lambda x: x["size"], reverse=True)
    sessions = _list_sessions(upload_dir)
    total_size = sum(f["size"] for f in files)

    return {
        "files": files,
        "count": len(files),
        "total_size": total_size,
        "sessions": sessions,
        "session_count": len(sessions),
        "sessions_size": sum(s["received_bytes"] for s in sessions),
    }


@router.delete("/api/storage/sessions/{upload_id}", tags=["storage"],
    summary="Discard an unfinished upload session")
async def delete_session(upload_id: str):
    engine = get_engine()
    if not _SESSION_ID_RE.match(upload_id or ""):
        raise HTTPException(404, "上传会话不存在")
    session = _sessions_root(Path(engine.config.storage.upload_dir)) / upload_id
    if not session.exists():
        raise HTTPException(404, "上传会话不存在或已过期")
    await asyncio.to_thread(shutil.rmtree, session, True)
    return {"ok": True}


@router.post("/api/storage/uploads/clean", tags=["storage"],
    summary="Clean uploaded videos",
    description="Delete uploaded video files. Pass {\"hashes\": [...]} to clean specific files, "
                "or {\"hashes\": null} / an empty body to clean all. A bare list is accepted too.")
async def clean_uploads(body: Any = Body(default=None)):
    engine = get_engine()
    upload_dir = Path(engine.config.storage.upload_dir)

    # 老版本前端直接 body 里塞数组（会被 422 拒掉），两种形状都收
    if body is None:
        hashes = None
    elif isinstance(body, list):
        hashes = [str(h) for h in body]
    elif isinstance(body, dict):
        hashes = body.get("hashes")
        if isinstance(hashes, str):
            hashes = [hashes]
    else:
        hashes = None

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
