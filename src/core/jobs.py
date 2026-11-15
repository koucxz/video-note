"""Generic background job executor.

Job state lives in the shared SQLite ``background_jobs`` table (see
``CheckpointManager``) so that a job submitted by one uvicorn worker can be
polled from any other worker. Execution itself is an ``asyncio.create_task``
in the worker that accepted the request; a process crash leaves the row in
``queued``/``running`` and the status endpoint reports it as-is.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Awaitable, Callable, Optional, Set

from .engine import get_engine

logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS = max(1, int(os.getenv("JOBS_MAX_CONCURRENCY", "4")))

_semaphore: Optional[asyncio.Semaphore] = None
_tasks: Set[asyncio.Task] = set()


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
    return _semaphore


def _checkpoint():
    return get_engine().checkpoint


def submit(kind: str, coro_factory: Callable[[str], Awaitable[dict]]) -> dict:
    """Persist a ``queued`` row and schedule ``coro_factory(job_id)``.

    ``coro_factory`` must return the JSON-serialisable result that callers
    expect from the original synchronous endpoint.
    """
    job_id = uuid.uuid4().hex
    _checkpoint().save_job(job_id, kind, status="queued", progress=0.0)
    task = asyncio.create_task(_run(job_id, coro_factory))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"job_id": job_id, "status": "queued", "kind": kind}


def set_progress(job_id: str, progress: float) -> None:
    """Best-effort progress update from inside a running job."""
    try:
        _checkpoint().update_job(job_id, progress=float(progress))
    except Exception:
        logger.debug("Failed to update progress for job %s", job_id, exc_info=True)


async def _run(job_id: str, coro_factory: Callable[[str], Awaitable[dict]]) -> None:
    cp = _checkpoint()
    async with _get_semaphore():
        cp.update_job(job_id, status="running")
        try:
            result = await coro_factory(job_id)
            cp.update_job(
                job_id, status="done", progress=1.0,
                result_json=json.dumps(result, ensure_ascii=False, default=str),
            )
        except asyncio.CancelledError:
            cp.update_job(job_id, status="failed", error="cancelled")
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced through the job row
            logger.error("Background job %s failed: %s", job_id, exc, exc_info=True)
            cp.update_job(job_id, status="failed", error=str(exc))
