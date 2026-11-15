"""LLM call governance: concurrency cap, timeout, circuit breaker, answer cache.

State is process-local. With multiple uvicorn workers each process keeps its
own semaphore/breaker/cache, which is the intended trade-off: no extra
services, no new dependencies, bounded per-worker load.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import threading
import time
from collections import OrderedDict

MAX_CONCURRENCY = max(1, int(os.getenv("LLM_MAX_CONCURRENCY", "4")))
TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
FAILURE_THRESHOLD = 5
COOLDOWN_SECONDS = 30.0

_semaphore: asyncio.Semaphore | None = None
_breaker = {"failures": 0, "opened_at": 0.0}


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    return _semaphore


def _breaker_check() -> None:
    if _breaker["failures"] >= FAILURE_THRESHOLD:
        elapsed = time.monotonic() - _breaker["opened_at"]
        if elapsed < COOLDOWN_SECONDS:
            raise RuntimeError(
                f"LLM circuit breaker open, retry in {COOLDOWN_SECONDS - elapsed:.0f}s"
            )
        # Half-open: allow one trial; a success clears the state below.
        _breaker["failures"] = 0


def _record_success() -> None:
    _breaker["failures"] = 0
    _breaker["opened_at"] = 0.0


def _record_failure() -> None:
    _breaker["failures"] += 1
    if _breaker["failures"] == FAILURE_THRESHOLD:
        _breaker["opened_at"] = time.monotonic()


async def guarded_call(coro_factory):
    """Await ``coro_factory()`` under concurrency + timeout + breaker.

    ``coro_factory`` is a zero-argument callable returning a coroutine (or any
    awaitable). Any exception (including a timeout) is counted as a failure
    and re-raised unchanged so callers keep their existing error handling.
    """
    _breaker_check()
    async with _get_semaphore():
        try:
            result = await asyncio.wait_for(coro_factory(), timeout=TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            _record_failure()
            raise
        _record_success()
        return result


class AnswerCache:
    """Small in-memory TTL cache for fully rendered RAG answers."""

    def __init__(self, ttl_seconds: float = 60.0, max_size: int = 512):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._data: "OrderedDict[str, tuple[float, dict]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            ts, value = item
            if now - ts > self.ttl:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: dict) -> None:
        now = time.monotonic()
        with self._lock:
            self._data[key] = (now, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    @staticmethod
    def make_key(question: str, task_ids, last_history: str) -> str:
        ids = ",".join(sorted(task_ids or []))
        raw = f"{question}\x1f{ids}\x1f{last_history or ''}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()


answer_cache = AnswerCache()
