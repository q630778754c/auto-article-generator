"""认证路由（design 2.5.2 A组）。

包含 admin 本地登录 + 统一平台认证（注册/验证码/登录/重置密码/用户管理）。
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_current_user, require_admin
from app.core.security import verify_password, hash_password, create_token
from app.core import database
from app.core.exceptions import AuthError, RateLimitError, UnifiedPlatformError
from app.core.unified_platform import get_unified_platform_client
from app.core.token_cache import get_token_cache
from app.schemas.common import (
    SendCodeRequest, RegisterRequest, VerifyLoginRequest,
    ResetPasswordRequest, PlatformLoginRequest, UpdateUserRequest,
)
from sqlalchemy import select, text

router = APIRouter()

_send_code_timestamps: dict[str, float] = {}
_SEND_CODE_INTERVAL = 60.0


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login")
async def login(req: LoginRequest):
    async with database.get_session() as s:
        result = await s.execute(
            text("SELECT id, username, password_hash FROM user_account WHERE username = :u"),
            {"u": req.username},
        )
        row = result.fetchone()
    if not row or not verify_password(req.password, row[2]):
        from app.core.exceptions import AuthError
        raise AuthError("用户名或密码错误")
    token, _ = create_token()
    local_token = f"local-{token}"
    return {"code": 0, "message": "ok", "data": {"token": local_token, "username": row[1]}}


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": None}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": {"username": user["username"]}}


@router.post("/send-code")
async def send_code(req: SendCodeRequest):
    now = time.monotonic()
    last = _send_code_timestamps.get(req.email, 0)
    if now - last < _SEND_CODE_INTERVAL:
        wait = int(_SEND_CODE_INTERVAL - (now - last))
        raise RateLimitError(f"请等待 {wait} 秒后重试", retry_after=wait)
    _send_code_timestamps[req.email] = now
    client = get_unified_platform_client()
    result = await client.send_code(req.email)
    return {"code": 0, "message": "ok", "data": result}


@router.post("/register")
async def register(req: RegisterRequest):
    client = get_unified_platform_client()
    result = await client.register(req.email, req.code, req.password, req.nickname)
    return {"code": 0, "message": "ok", "data": result}


@router.post("/verify-login")
async def verify_login(req: VerifyLoginRequest):
    client = get_unified_platform_client()
    result = await client.verify_login(req.email, req.code)
    return {"code": 0, "message": "ok", "data": result}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    client = get_unified_platform_client()
    result = await client.reset_password(req.email, req.code, req.new_password)
    return {"code": 0, "message": "ok", "data": result}


@router.post("/platform-login")
async def platform_login(req: PlatformLoginRequest):
    client = get_unified_platform_client()
    result = await client.login(req.email, req.password)
    return {"code": 0, "message": "ok", "data": result}


@router.get("/admin/users")
async def list_users(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(require_admin),
):
    client = get_unified_platform_client()
    result = await client.list_users(keyword, page, page_size)
    return {"code": 0, "message": "ok", "data": result}


@router.get("/admin/users/{user_id}")
async def get_user(user_id: str, user: dict = Depends(require_admin)):
    client = get_unified_platform_client()
    result = await client.get_user(user_id)
    return {"code": 0, "message": "ok", "data": result}


@router.put("/admin/users/{user_id}")
async def update_user(user_id: str, req: UpdateUserRequest, user: dict = Depends(require_admin)):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    client = get_unified_platform_client()
    result = await client.update_user(user_id, **fields)
    return {"code": 0, "message": "ok", "data": result}


@router.post("/admin/users/{user_id}/toggle")
async def toggle_user(user_id: str, user: dict = Depends(require_admin)):
    client = get_unified_platform_client()
    result = await client.toggle_user(user_id, "disabled")
    await get_token_cache().clear()
    return {"code": 0, "message": "ok", "data": result}


@router.delete("/admin/users/{user_id}/unbind")
async def unbind_user(user_id: str, user: dict = Depends(require_admin)):
    client = get_unified_platform_client()
    result = await client.unbind_user(user_id)
    return {"code": 0, "message": "ok", "data": result}
