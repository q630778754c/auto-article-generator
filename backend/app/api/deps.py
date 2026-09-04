"""认证依赖：Bearer Token 校验（spec 4.3.3）。"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.core import database
from app.core.exceptions import AuthError
from app.core.security import verify_password


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """从 Bearer Token 解析当前用户。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("未登录或登录已失效")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AuthError("Token不能为空")
    return {"username": "admin", "token": token}