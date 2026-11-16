"""Chunked, resumable upload API.

Why this exists: the UI used to send the whole file in one `POST /api/upload`.
On a home uplink a 2 GB video needs ~5 minutes in a single request, which
collides with the browser timeout, restarts from zero after any hiccup, and
forces Starlette to spool the whole body to a temp file before the handler can
even check the size (we measured a 400 rejection that took 67 s because the
full body had to arrive first).

Chunking turns that into many 8 MB requests:

- per-chunk retry + server-side idempotency, so a dropped connection costs one
  chunk instead of the whole file;
- the client can keep 2-3 requests in flight and report real byte progress;
- size/format checks happen at `init`, before a single byte is transferred;
- a reloaded page can ask `GET /api/upload/{id}` which parts already landed.

State lives on disk under `<data>/tmp_uploads/<upload_id>/` so it is shared by
both uvicorn workers and survives a restart.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..core.engine import get_engine
from .upload import (
    MAX_FILE_SIZE,
    MAX_DURATION_SECONDS,
    _human_size,
    finalize_upload,
    normalize_language,
    normalize_note_style,
    parse_options,
    validate_filename,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
MIN_CHUNK_SIZE = 1024 * 1024
MAX_CHUNK_SIZE = 32 * 1024 * 1024
# 半天没人来收尾的分片会话按垃圾清理，避免磁盘被半截文件占满
SESSION_TTL_SECONDS = 12 * 3600
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class InitPayload(BaseModel):
    filename: str
    size: int = Field(gt=0)
    chunk_size: int = Field(default=DEFAULT_CHUNK_SIZE, gt=0)
    language: str = "zh"
    note_style: str = "standard"
    processing_options: str = "{}"


def _ts_dir() -> Path:
    """Where half-finished uploads live (same filesystem as the final uploads)."""
    upload_dir = Path(get_engine().dedup.upload_dir)
    return upload_dir.parent / "tmp_uploads"


def _session_dir(upload_id: str) -> Path:
    if not _SESSION_ID_RE.match(upload_id or ""):
        raise HTTPException(404, "上传会话不存在")
    return _ts_dir() / upload_id


def _read_meta(upload_id: str) -> dict:
    session = _session_dir(upload_id)
    meta_path = session / "meta.json"
    if not meta_path.exists():
        raise HTTPException(404, "上传会话不存在或已过期")
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(409, f"上传会话已损坏：{exc}")


def _part_path(session: Path, index: int) -> Path:
    return session / f"p{index:05d}"


def _expected_part_size(meta: dict, index: int) -> int:
    start = index * meta["chunk_size"]
    return min(meta["chunk_size"], meta["size"] - start)


def _uploaded_parts(session: Path, meta: dict) -> list[int]:
    done = []
    for index in range(meta["total_parts"]):
        part = _part_path(session, index)
        try:
            if part.stat().st_size == _expected_part_size(meta, index):
                done.append(index)
        except OSError:
            continue
    return done


def _scan_sessions() -> list[tuple[Path, dict]]:
    """All readable upload sessions on disk (cheap: one stat + one small json each)."""
    root = _ts_dir()
    if not root.exists():
        return []
    found: list[tuple[Path, dict]] = []
    for child in root.iterdir():
        try:
            if not child.is_dir():
                continue
            with open(child / "meta.json", "r", encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("filename") and meta.get("size") and meta.get("upload_id"):
            found.append((child, meta))
    return found


def _find_reusable(filename: str, size: int) -> tuple[tuple[Path, dict, list[int]] | None, list[Path]]:
    """Find the most advanced session for the same (filename, size).

    The client used to key resume state on `name|size|lastModified`, so anything
    that changed the mtime (re-download, copy, another machine) silently started
    a brand-new session and the old half-uploaded parts were orphaned — which is
    why storage management showed several identical "unfinished uploads" of the
    same video. Matching on the server by name+size makes resume work no matter
    what the browser remembers, and lets us recycle the losers.

    Returns the best candidate plus every duplicate directory for that file.
    """
    best: tuple[Path, dict, list[int]] | None = None
    duplicates: list[Path] = []
    for session, meta in _scan_sessions():
        if meta.get("filename") != filename or int(meta.get("size") or -1) != int(size):
            continue
        done = _uploaded_parts(session, meta)
        if best is None or len(done) > len(best[2]):
            if best is not None:
                duplicates.append(best[0])
            best = (session, meta, done)
        else:
            duplicates.append(session)
    return best, duplicates


def _sweep_stale() -> None:
    root = _ts_dir()
    if not root.exists():
        return
    cutoff = time.time() - SESSION_TTL_SECONDS
    for child in root.iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                logger.info("Cleaned stale upload session %s", child.name)
        except OSError:
            continue


def _assemble(session: Path, meta: dict) -> tuple[str, Path, bool]:
    """Concatenate parts in order while hashing; returns (hash, path, is_new).

    Runs in a worker thread: a 2 GB hash+copy would otherwise stall the event
    loop for several seconds and freeze every other request on that worker.
    """
    ext = meta["ext"]
    declared = meta["size"]
    tmp_path = session / f"assembled{ext}"
    sha = hashlib.sha256()
    written = 0
    with open(tmp_path, "wb") as out:
        for index in range(meta["total_parts"]):
            with open(_part_path(session, index), "rb") as src:
                while True:
                    block = src.read(4 * 1024 * 1024)
                    if not block:
                        break
                    sha.update(block)
                    out.write(block)
                    written += len(block)
    if written != declared:
        tmp_path.unlink(missing_ok=True)
        raise ValueError(f"分片总大小 {_human_size(written)} 与声明的 {_human_size(declared)} 不一致")

    file_hash = sha.hexdigest()[:16]
    upload_dir = Path(get_engine().dedup.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    final_path = upload_dir / f"{file_hash}{ext}"
    if final_path.exists():
        tmp_path.unlink(missing_ok=True)
        return file_hash, final_path, False
    os.replace(tmp_path, final_path)
    return file_hash, final_path, True


@router.post("/init", summary="Start a chunked upload")
async def init_upload(payload: InitPayload):
    ext = validate_filename(payload.filename)
    if payload.size > MAX_FILE_SIZE:
        raise HTTPException(413, f"文件超过 {_human_size(MAX_FILE_SIZE)} 上限，请先压缩或裁剪视频")

    chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, int(payload.chunk_size or DEFAULT_CHUNK_SIZE)))
    total_parts = (payload.size + chunk_size - 1) // chunk_size

    # 同一个文件（文件名+大小一致）之前传了一半：直接接着那个会话传，别再开新目录
    best, duplicates = await asyncio.to_thread(_find_reusable, payload.filename, payload.size)
    if best is not None and best[2]:
        session, meta, done = best
        for dup in duplicates:
            await asyncio.to_thread(shutil.rmtree, dup, True)
        if duplicates:
            logger.info("Recycled %d duplicate upload session(s) for %s",
                        len(duplicates), payload.filename)
        logger.info("Chunked upload resume %s: %s (%d/%d parts already stored)",
                    meta["upload_id"], payload.filename, len(done), meta["total_parts"])
        return {
            "upload_id": meta["upload_id"],
            "chunk_size": meta["chunk_size"],
            "total_parts": meta["total_parts"],
            "uploaded_parts": done,
            "resumed": True,
            "max_size": MAX_FILE_SIZE,
            "max_duration_seconds": MAX_DURATION_SECONDS,
        }

    # 没有可用分片就清掉同名的空壳/更旧的碎片，只保留这次新建的
    for dup in duplicates:
        await asyncio.to_thread(shutil.rmtree, dup, True)

    upload_id = uuid.uuid4().hex
    session = _ts_dir() / upload_id
    session.mkdir(parents=True, exist_ok=True)
    meta = {
        "upload_id": upload_id,
        "filename": payload.filename,
        "ext": ext,
        "size": payload.size,
        "chunk_size": chunk_size,
        "total_parts": total_parts,
        "language": normalize_language(payload.language),
        "note_style": normalize_note_style(payload.note_style),
        "overrides": parse_options(payload.processing_options),
        "created_at": int(time.time()),
    }
    with open(session / "meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)

    await asyncio.to_thread(_sweep_stale)
    logger.info("Chunked upload init %s: %s (%s bytes, %d parts)",
                upload_id, payload.filename, payload.size, total_parts)
    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_parts": total_parts,
        "uploaded_parts": [],
        "max_size": MAX_FILE_SIZE,
        "max_duration_seconds": MAX_DURATION_SECONDS,
    }


@router.get("/{upload_id}", summary="Which parts already landed (resume support)")
async def upload_status(upload_id: str):
    meta = _read_meta(upload_id)
    session = _session_dir(upload_id)
    done = _uploaded_parts(session, meta)
    return {
        "upload_id": upload_id,
        "filename": meta["filename"],
        "size": meta["size"],
        "chunk_size": meta["chunk_size"],
        "total_parts": meta["total_parts"],
        "uploaded_parts": done,
        "received_bytes": sum(_expected_part_size(meta, i) for i in done),
    }


@router.put("/{upload_id}/part/{index}", summary="Upload one chunk (raw body)")
async def upload_part(upload_id: str, index: int, request: Request):
    meta = _read_meta(upload_id)
    if index < 0 or index >= meta["total_parts"]:
        raise HTTPException(400, f"分片序号超出范围：{index}")

    session = _session_dir(upload_id)
    part = _part_path(session, index)
    expected = _expected_part_size(meta, index)

    # 重试幂等：上一轮其实已经写完了，直接认账，不再重复传
    if part.exists():
        try:
            if part.stat().st_size == expected:
                return {"index": index, "size": expected, "skipped": True}
        except OSError:
            pass

    tmp = session / f".p{index:05d}.{uuid.uuid4().hex[:8]}.tmp"
    received = 0
    loop = asyncio.get_running_loop()
    try:
        with open(tmp, "wb") as out:
            async for block in request.stream():
                if not block:
                    continue
                received += len(block)
                if received > expected:
                    raise HTTPException(413, f"分片 {index} 超出预期大小 {_human_size(expected)}")
                await loop.run_in_executor(None, out.write, block)
        if received != expected:
            raise HTTPException(400, f"分片 {index} 不完整：收到 {received} 字节，应为 {expected} 字节")
        os.replace(tmp, part)
    except HTTPException:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        logger.warning("Chunk %s/%s failed: %s", upload_id, index, exc)
        raise HTTPException(500, f"分片写入失败：{exc}")

    return {"index": index, "size": received, "skipped": False}


@router.post("/{upload_id}/complete", summary="Merge chunks and start processing")
async def complete_upload(upload_id: str):
    meta = _read_meta(upload_id)
    session = _session_dir(upload_id)
    done = set(_uploaded_parts(session, meta))
    missing = [i for i in range(meta["total_parts"]) if i not in done]
    if missing:
        preview = ", ".join(str(i) for i in missing[:10])
        raise HTTPException(400, f"还有 {len(missing)} 个分片未上传（编号 {preview}{'…' if len(missing) > 10 else ''}）")

    # 同一会话可能被两个窗口同时 complete（现在 init 会复用会话，这更容易发生）：
    # 用一个原子锁文件保证只有一个人合并，另一个拿到明确的提示而不是 500。
    lock = session / "completing"
    try:
        os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        try:
            stale = (time.time() - lock.stat().st_mtime) > 600
        except OSError:
            stale = False
        if not stale:
            raise HTTPException(409, "该文件正在另一处合并，稍后刷新列表即可")
        lock.unlink(missing_ok=True)

    engine = get_engine()
    try:
        file_hash, file_path, is_new = await asyncio.to_thread(_assemble, session, meta)
    except ValueError as exc:
        lock.unlink(missing_ok=True)
        raise HTTPException(400, str(exc))
    except OSError as exc:
        lock.unlink(missing_ok=True)
        logger.error("Assemble failed for %s: %s", upload_id, exc)
        raise HTTPException(500, f"合并分片失败：{exc}")

    response = await finalize_upload(
        engine, meta["filename"], file_hash, file_path, is_new,
        meta["language"], meta["note_style"], meta["overrides"] or {},
    )
    await asyncio.to_thread(shutil.rmtree, session, True)
    return response


@router.delete("/{upload_id}", summary="Abort a chunked upload")
async def abort_upload(upload_id: str):
    session = _session_dir(upload_id)
    if not session.exists():
        raise HTTPException(404, "上传会话不存在或已过期")
    await asyncio.to_thread(shutil.rmtree, session, True)
    return {"ok": True}
