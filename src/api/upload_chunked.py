"""Chunked / resumable upload API - for large videos over unstable networks.

流程：
  POST /api/upload/init      -> 拿 upload_id 和已上传分片列表（可续传）
  POST /api/upload/chunk     -> 逐片上传（可并发、可乱序、失败重传）
  POST /api/upload/complete  -> 按序合并分片，交给原有去重 + 处理流程
  DELETE /api/upload/session/{upload_id} -> 放弃本次上传

upload_id 由「文件名 + 大小 + 分片大小」稳定推导，所以同一文件刷新页面后
再次 init 会自动拿回已传分片，实现断点续传。
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..core.engine import get_engine, _clamp_param
from .upload import MAX_FILE_SIZE, finalize_upload, parse_upload_options

logger = logging.getLogger(__name__)
router = APIRouter()

CHUNK_DIR = Path("./data/temp/chunks")
SESSION_TTL_SECONDS = 24 * 3600
MAX_CHUNK_BYTES = 16 * 1024 * 1024


class InitRequest(BaseModel):
    filename: str
    size: int
    chunk_size: int = 2 * 1024 * 1024
    total_chunks: int


class CompleteRequest(BaseModel):
    upload_id: str
    language: str = "zh"
    note_style: str = "standard"
    processing_options: str = "{}"


def _session_dir(upload_id: str) -> Path:
    # 只允许十六进制 id，杜绝路径穿越
    if not upload_id or any(c not in "0123456789abcdef" for c in upload_id):
        raise HTTPException(400, "Invalid upload_id")
    return CHUNK_DIR / upload_id


def _read_meta(path: Path) -> dict:
    meta_file = path / "meta.json"
    if not meta_file.exists():
        raise HTTPException(404, "Upload session not found or expired")
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(500, "Upload session is corrupted")


def _received_indexes(path: Path, total_chunks: int) -> List[int]:
    done = []
    for i in range(total_chunks):
        part = path / f"{i}.part"
        if part.exists() and part.stat().st_size > 0:
            done.append(i)
    return done


def _cleanup_expired() -> None:
    if not CHUNK_DIR.exists():
        return
    now = time.time()
    for d in CHUNK_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            created = float(meta.get("created_at", 0))
        except Exception:
            created = d.stat().st_mtime
        if now - created > SESSION_TTL_SECONDS:
            shutil.rmtree(d, ignore_errors=True)


class _ChunkStream:
    """把若干分片文件顺序拼成一个可被 dedup 消费的异步读取流。"""

    def __init__(self, paths: List[Path]):
        self._paths = paths
        self._idx = 0
        self._fh = None

    async def read(self, n: int = 1024 * 1024) -> bytes:
        while True:
            if self._fh is None:
                if self._idx >= len(self._paths):
                    return b""
                self._fh = open(self._paths[self._idx], "rb")
                self._idx += 1
            data = self._fh.read(n)
            if data:
                return data
            self._fh.close()
            self._fh = None

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None


@router.post("/api/upload/init", tags=["upload"],
    summary="Start or resume a chunked upload")
async def init_chunked_upload(req: InitRequest):
    if req.size <= 0 or req.size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large: max {MAX_FILE_SIZE // (1024**3)}GB")

    ext = Path(req.filename).suffix.lower()
    parse_upload_options(req.filename, "zh", "standard", "{}")

    chunk_size = max(256 * 1024, min(int(req.chunk_size), MAX_CHUNK_BYTES))
    total = max(1, int(req.total_chunks))
    if total > 20000:
        raise HTTPException(400, "Too many chunks")

    _cleanup_expired()
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    upload_id = hashlib.sha1(
        f"{req.filename}|{req.size}|{chunk_size}".encode("utf-8")
    ).hexdigest()[:24]

    session = CHUNK_DIR / upload_id
    session.mkdir(parents=True, exist_ok=True)

    meta_file = session / "meta.json"
    if not meta_file.exists():
        meta_file.write_text(json.dumps({
            "filename": req.filename,
            "size": req.size,
            "chunk_size": chunk_size,
            "total_chunks": total,
            "ext": ext,
            "created_at": time.time(),
        }), encoding="utf-8")

    uploaded = _received_indexes(session, total)
    logger.info("Chunked upload init %s (%s, %d bytes, %d/%d done)",
                upload_id, req.filename, req.size, len(uploaded), total)
    return {
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_chunks": total,
        "uploaded": uploaded,
        "resumed": len(uploaded) > 0,
    }


@router.post("/api/upload/chunk", tags=["upload"],
    summary="Upload one chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    index: int = Form(...),
    chunk: UploadFile = File(...),
):
    session = _session_dir(upload_id)
    meta = _read_meta(session)
    total = int(meta["total_chunks"])
    if index < 0 or index >= total:
        raise HTTPException(400, f"Chunk index out of range: {index}")

    target = session / f"{index}.part"
    tmp = session / f"{index}.part.tmp"

    size = 0
    try:
        with open(tmp, "wb") as out:
            while True:
                data = await chunk.read(1024 * 1024)
                if not data:
                    break
                size += len(data)
                if size > MAX_CHUNK_BYTES * 2:
                    raise HTTPException(413, "Chunk too large")
                out.write(data)
        tmp.replace(target)
    except HTTPException:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        logger.error("Chunk upload failed %s#%d: %s", upload_id, index, exc)
        raise HTTPException(500, f"Chunk upload failed: {exc}")

    return {"index": index, "size": size, "received": len(_received_indexes(session, total))}


@router.get("/api/upload/status/{upload_id}", tags=["upload"],
    summary="List received chunks")
async def chunk_status(upload_id: str):
    session = _session_dir(upload_id)
    meta = _read_meta(session)
    total = int(meta["total_chunks"])
    uploaded = _received_indexes(session, total)
    return {
        "upload_id": upload_id,
        "filename": meta["filename"],
        "total_chunks": total,
        "uploaded": uploaded,
        "complete": len(uploaded) == total,
    }


@router.post("/api/upload/complete", tags=["upload"],
    summary="Merge chunks and start processing")
async def complete_chunked_upload(req: CompleteRequest):
    session = _session_dir(req.upload_id)
    meta = _read_meta(session)
    total = int(meta["total_chunks"])
    filename = str(meta["filename"])

    _, language, note_style, overrides, raw_opts = parse_upload_options(
        filename, req.language, req.note_style, req.processing_options
    )

    uploaded = _received_indexes(session, total)
    if len(uploaded) != total:
        missing = [i for i in range(total) if i not in uploaded]
        raise HTTPException(400, f"Missing chunks: {missing[:20]}{'...' if len(missing) > 20 else ''}")

    parts = [session / f"{i}.part" for i in range(total)]
    stream = _ChunkStream(parts)

    try:
        engine = get_engine()

        if "max_concurrent_tasks" in raw_opts:
            new_limit = _clamp_param("max_concurrent_tasks", raw_opts["max_concurrent_tasks"])
            engine.update_concurrency(new_limit)

        file_hash, file_path, is_new = await engine.dedup.process_upload(stream, filename)
        logger.info("Chunks merged %s -> %s (%s)", req.upload_id, file_path, file_hash)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Merge failed %s: %s", req.upload_id, exc)
        raise HTTPException(500, f"Merge failed: {exc}")
    finally:
        stream.close()

    shutil.rmtree(session, ignore_errors=True)

    return await finalize_upload(
        filename, file_hash, file_path, is_new, language, note_style, overrides
    )


@router.delete("/api/upload/session/{upload_id}", tags=["upload"],
    summary="Abort a chunked upload")
async def abort_chunked_upload(upload_id: str):
    session = _session_dir(upload_id)
    shutil.rmtree(session, ignore_errors=True)
    return {"upload_id": upload_id, "aborted": True}
