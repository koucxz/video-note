"""Streaming file deduplication - hashes while writing to avoid OOM."""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

_CHUNK = 1024 * 1024


class FileDeduplicator:
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def process_upload(self, source, filename: str) -> Tuple[str, Path, bool]:
        ext = Path(filename).suffix.lower()
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="vn_", suffix=ext or ".bin", dir=str(self.upload_dir))
        os.close(tmp_fd)
        sha = hashlib.sha256()

        try:
            with open(tmp_path, "wb") as out:
                if isinstance(source, (bytes, bytearray)):
                    sha.update(source)
                    out.write(source)
                else:
                    reader = getattr(source, "read", None)
                    if reader is None:
                        raise TypeError(f"Unsupported upload source: {type(source)!r}")
                    import inspect
                    if inspect.iscoroutinefunction(reader):
                        while True:
                            chunk = await reader(_CHUNK)
                            if not chunk:
                                break
                            sha.update(chunk)
                            out.write(chunk)
                    else:
                        while True:
                            chunk = reader(_CHUNK)
                            if not chunk:
                                break
                            sha.update(chunk)
                            out.write(chunk)

            file_hash = sha.hexdigest()[:16]
            final_path = self.upload_dir / f"{file_hash}{ext}"
            if final_path.exists():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                return file_hash, final_path, False

            os.replace(tmp_path, final_path)
            return file_hash, final_path, True
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
