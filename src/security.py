"""Authentication and request security helpers for production deployments.

Authentication is opt-in for local development and enabled automatically when
VIDEONOTE_AUTH_PASSWORD is configured. Production deployments should also set
VIDEONOTE_SESSION_SECRET to a long random value.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

SESSION_COOKIE = "vn_session"
CSRF_COOKIE = "vn_csrf"
CSRF_HEADER = "X-CSRF-Token"
SESSION_TTL_SECONDS = max(3600, int(os.getenv("VIDEONOTE_SESSION_TTL", "604800")))

AUTH_PASSWORD = os.getenv("VIDEONOTE_AUTH_PASSWORD", "")
SESSION_SECRET = os.getenv("VIDEONOTE_SESSION_SECRET", "")
AUTH_ENABLED = bool(AUTH_PASSWORD)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(value: str) -> str:
    secret = SESSION_SECRET.encode("utf-8")
    return _b64encode(hmac.new(secret, value.encode("utf-8"), hashlib.sha256).digest())


def create_session() -> str:
    if AUTH_ENABLED and not SESSION_SECRET:
        raise RuntimeError("VIDEONOTE_SESSION_SECRET must be set when authentication is enabled")
    payload = {"iat": int(time.time()), "exp": int(time.time()) + SESSION_TTL_SECONDS}
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_sign(body)}"


def validate_session(value: Optional[str]) -> bool:
    if not AUTH_ENABLED:
        return True
    if not value or "." not in value or not SESSION_SECRET:
        return False
    body, signature = value.rsplit(".", 1)
    expected = _sign(body)
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(_b64decode(body))
        return int(payload.get("exp", 0)) >= int(time.time())
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def valid_csrf(cookie_value: Optional[str], header_value: Optional[str]) -> bool:
    return bool(cookie_value and header_value and hmac.compare_digest(cookie_value, header_value))


def set_auth_cookies(response, session: str, csrf: str) -> None:
    secure = os.getenv("VIDEONOTE_COOKIE_SECURE", "true").lower() in {"1", "true", "yes", "on"}
    response.set_cookie(
        SESSION_COOKIE, session, max_age=SESSION_TTL_SECONDS, httponly=True,
        secure=secure, samesite="lax", path="/",
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=SESSION_TTL_SECONDS, httponly=False,
        secure=secure, samesite="lax", path="/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
