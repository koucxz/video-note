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
    # The stream endpoint shares this prefix; both forms allow 60/min.
    ("POST", "/api/rag/ask"): 60,
    ("POST", "/api/note/"): 30,
    ("POST", "/api/task/"): 30,
}
# Paths matched exactly, not by prefix: a 2 GB upload arrives as hundreds of
# small requests under /api/upload/ and must never eat into this budget.
EXACT_LIMITS = {
    ("POST", "/api/upload"): 5,
}
_EXEMPT_METHODS = {"GET", "HEAD", "DELETE"}
_EXEMPT_PATHS = {"/api/health"}
_EXEMPT_PREFIXES = ("/api/upload/",)

_events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = Lock()


def _limit_for(method: str, path: str) -> int | None:
    if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
        return None
    exact = EXACT_LIMITS.get((method, path))
    if exact is not None:
        return exact
    for (allowed_method, prefix), limit in LIMITS.items():
        if method == allowed_method and path.startswith(prefix):
            return limit
    return None


def allow_request(client_id: str, method: str, path: str) -> bool:
    # Read-only traffic (health checks, job polling, page loads) is cheap and
    # must never be throttled by the mutating-endpoint budget.
    if method in _EXEMPT_METHODS:
        return True
    if path.split("?", 1)[0] in _EXEMPT_PATHS:
        return True
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
