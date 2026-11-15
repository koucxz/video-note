"""Lazily created process pool for CPU-bound, picklable pure functions.

Only module-level functions may be submitted (no ``self``/``engine``/DB
handles). Anything that cannot be pickled is transparently run in a thread
instead, which still keeps it off the event loop without the fork/pickle
constraints of a process pool.
"""
from __future__ import annotations

import asyncio
import logging
import os
import pickle
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)

MAX_WORKERS = max(1, int(os.getenv("EXPORT_PROCESS_WORKERS", "2")))

_pool: Optional[ProcessPoolExecutor] = None


def get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=MAX_WORKERS)
    return _pool


def shutdown_pool() -> None:
    """Release pool workers on application shutdown."""
    global _pool
    if _pool is not None:
        try:
            _pool.shutdown(wait=False, cancel_futures=True)
        finally:
            _pool = None


async def run_cpu(func, *args):
    """Run a CPU-heavy pure function in the process pool when possible.

    Falls back to ``asyncio.to_thread`` when the target is not picklable or
    when the process pool cannot execute it.
    """
    try:
        pickle.dumps((func, args))
    except Exception as exc:  # noqa: BLE001 - any pickling failure is a fallback
        logger.warning("Target %s is not picklable (%s), using a thread", getattr(func, "__name__", func), exc)
        return await asyncio.to_thread(func, *args)

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(get_pool(), func, *args)
    except Exception as exc:  # noqa: BLE001 - pool/fork failure, retry in a thread
        logger.warning(
            "Process pool execution of %s failed (%s), using a thread",
            getattr(func, "__name__", func), exc,
        )
        return await asyncio.to_thread(func, *args)
