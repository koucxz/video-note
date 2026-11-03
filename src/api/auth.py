"""单用户登录鉴权：账号密码来自服务端环境变量，不提供注册。

- AUTH_USERNAME / AUTH_PASSWORD 未配置时，鉴权整体关闭（本地开发用）。
- 登录成功签发 HMAC 签名 token（无第三方依赖），前端放 localStorage。
- 中间件支持两种凭证：Authorization: Bearer <token>（浏览器）
  或 X-VN-Token: <API_TOKEN>（脚本 / curl 调用）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

AUTH_USERNAME = os.getenv("AUTH_USERNAME", "").strip()
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "")
AUTH_SECRET = (os.getenv("AUTH_SECRET", "") or AUTH_PASSWORD or "").strip()
TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", str(30 * 24 * 3600)))  # 默认 30 天

# 无需登录即可访问的路径
PUBLIC_PATHS = {"/", "/api/health", "/api/auth/login", "/api/auth/config"}


def auth_enabled() -> bool:
    return bool(AUTH_USERNAME and AUTH_PASSWORD)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + TOKEN_TTL}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def verify_token(token: str) -> Optional[dict]:
    if not token or "." not in token or not AUTH_SECRET:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(_b64d(sig), expected):
            return None
        payload = json.loads(_b64d(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def check_request_auth(authorization: Optional[str], api_token: Optional[str]) -> bool:
    """中间件调用：返回 True 表示放行。"""
    if not auth_enabled():
        return True

    # 脚本 / curl：静态 API_TOKEN
    static_token = os.getenv("API_TOKEN", "").strip()
    if static_token and api_token and hmac.compare_digest(api_token, static_token):
        return True

    if authorization and authorization.lower().startswith("bearer "):
        return verify_token(authorization[7:].strip()) is not None

    return False


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/api/auth/config", tags=["auth"], summary="前端探测是否需要登录")
async def auth_config():
    return {
        "auth_required": auth_enabled(),
        "registration": False,
    }


@router.post("/api/auth/login", tags=["auth"], summary="账号密码登录")
async def login(req: LoginRequest):
    if not auth_enabled():
        raise HTTPException(400, "服务端未启用登录（缺少 AUTH_USERNAME / AUTH_PASSWORD）")

    ok_user = hmac.compare_digest(req.username.strip().lower(), AUTH_USERNAME.lower())
    ok_pass = hmac.compare_digest(req.password, AUTH_PASSWORD)
    if not (ok_user and ok_pass):
        logger.warning("Login failed for user=%r", req.username)
        raise HTTPException(401, "用户名或密码错误")

    logger.info("Login success: %s", AUTH_USERNAME)
    return {
        "token": issue_token(AUTH_USERNAME),
        "username": AUTH_USERNAME,
        "expires_in": TOKEN_TTL,
    }


@router.get("/api/auth/me", tags=["auth"], summary="当前登录用户")
async def me(authorization: Optional[str] = Header(default=None)):
    if not auth_enabled():
        return {"username": "anonymous", "auth_required": False}
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "未登录或登录已过期")
    return {"username": payload.get("sub"), "auth_required": True}
