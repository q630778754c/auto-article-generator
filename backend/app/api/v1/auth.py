"""认证路由（design 2.5.2 A组）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.security import verify_password, hash_password, create_token
from app.core import database
from sqlalchemy import select, text

router = APIRouter()


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
    return {"code": 0, "message": "ok", "data": {"token": token, "username": row[1]}}


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": None}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": {"username": user["username"]}}