"""Small single-user authentication API for private deployments."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..security import (
    AUTH_ENABLED,
    SESSION_COOKIE,
    clear_auth_cookies,
    create_session,
    new_csrf_token,
    set_auth_cookies,
    validate_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(data: LoginRequest):
    if not AUTH_ENABLED:
        response = JSONResponse({"authenticated": True, "auth_enabled": False})
        set_auth_cookies(response, "", new_csrf_token())
        return response

    from ..security import AUTH_PASSWORD
    import hmac

    if not hmac.compare_digest(data.password, AUTH_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid password")
    response = JSONResponse({"authenticated": True, "auth_enabled": True})
    set_auth_cookies(response, create_session(), new_csrf_token())
    return response


@router.get("/me")
async def me(request: Request):
    authenticated = not AUTH_ENABLED or validate_session(request.cookies.get(SESSION_COOKIE))
    response = JSONResponse({"authenticated": authenticated, "auth_enabled": AUTH_ENABLED})
    if authenticated:
        response.set_cookie("vn_csrf", new_csrf_token(), httponly=False, samesite="lax", path="/")
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse({"authenticated": False})
    clear_auth_cookies(response)
    return response
