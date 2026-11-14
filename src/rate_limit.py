"""Small process-local rate limiter for expensive API endpoints.

It is deliberately conservative: the provider-side budget remains the final
spend control, while this layer prevents accidental bursts on one instance.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

WINDOW_SECONDS = 60
LIMITS = {
    ("POST", "/api/auth/login"): 10,
    ("POST", "/api/upload"): 5,
    ("POST", "/api/rag/ask"): 30,
    ("POST", "/api/note/"): 30,
    ("POST", "/api/task/"): 30,
}

_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = Lock()


def _limit_for(method: str, path: str) -> int | None:
    for (allowed_method, prefix), limit in LIMITS.items():
        if method == allowed_method and path.startswith(prefix):
            return limit
    return None


def allow_request(client_id: str, method: str, path: str) -> bool:
    limit = _limit_for(method, path)
    if limit is None:
        return True
    now = time.monotonic()
    key = (client_id, f"{method}:{path.split('?')[0]}")
    with _lock:
        events = _events[key]
        while events and now - events[0] >= WINDOW_SECONDS:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True
