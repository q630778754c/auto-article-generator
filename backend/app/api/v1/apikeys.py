"""API Key 管理路由（spec 4.3.4 / design 2.5.2 B组）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.api_key_service import get_api_key_service
from app.core.exceptions import ParamError

router = APIRouter()

_VALID_SCOPES = {"rss_only", "webpage_only", "all_collector"}


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    scope: str = Field(default="all_collector")
    rate_limit: int = Field(default=100, ge=1, le=1000)
    expires_days: int | None = Field(default=90, ge=1, le=365)


class UpdateApiKeyRequest(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    scope: str | None = None
    rate_limit: int | None = Field(default=None, ge=1, le=1000)
    expires_days: int | None = Field(default=None, ge=1, le=365)


@router.post("")
async def create_api_key(req: CreateApiKeyRequest, user: dict = Depends(get_current_user)):
    if req.scope not in _VALID_SCOPES:
        raise ParamError(f"无效的 scope：{req.scope}，允许 {sorted(_VALID_SCOPES)}", 2006)
    service = get_api_key_service()
    record, plain_key = await service.generate(
        name=req.name,
        scope=req.scope,
        rate_limit=req.rate_limit,
        expires_days=req.expires_days,
        created_by=user.get("username", "admin"),
    )
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": record.id,
            "name": record.name,
            "key": plain_key,
            "key_masked": service.mask_from_prefix(record.key_prefix),
            "scope": record.scope,
            "rate_limit": record.rate_limit,
            "expires_days": record.expires_days,
            "expires_at": record.expires_at,
            "enabled": record.enabled,
            "created_at": record.created_at,
        },
    }


@router.get("")
async def list_api_keys(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    service = get_api_key_service()
    result = await service.list(page, page_size)
    return {"code": 0, "message": "ok", "data": result}


@router.get("/{key_id}")
async def get_api_key(key_id: int, user: dict = Depends(get_current_user)):
    service = get_api_key_service()
    record = await service.get_by_id(key_id)
    if record is None:
        raise ParamError("API Key 不存在", 2007)
    return {"code": 0, "message": "ok", "data": service._to_dict(record)}


@router.put("/{key_id}")
async def update_api_key(key_id: int, req: UpdateApiKeyRequest, user: dict = Depends(get_current_user)):
    if req.scope is not None and req.scope not in _VALID_SCOPES:
        raise ParamError(f"无效的 scope：{req.scope}", 2006)
    service = get_api_key_service()
    record = await service.update(key_id, **req.model_dump())
    if record is None:
        raise ParamError("API Key 不存在", 2007)
    return {"code": 0, "message": "ok", "data": service._to_dict(record)}


@router.post("/{key_id}/toggle")
async def toggle_api_key(key_id: int, user: dict = Depends(get_current_user)):
    service = get_api_key_service()
    record = await service.toggle(key_id)
    if record is None:
        raise ParamError("API Key 不存在", 2007)
    return {"code": 0, "message": "ok", "data": service._to_dict(record)}


@router.delete("/{key_id}")
async def delete_api_key(key_id: int, user: dict = Depends(get_current_user)):
    service = get_api_key_service()
    ok = await service.delete(key_id)
    if not ok:
        raise ParamError("API Key 不存在", 2007)
    return {"code": 0, "message": "ok", "data": None}


@router.get("/{key_id}/usage")
async def get_api_key_usage(key_id: int, user: dict = Depends(get_current_user)):
    service = get_api_key_service()
    record = await service.get_by_id(key_id)
    if record is None:
        raise ParamError("API Key 不存在", 2007)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "total_calls": record.total_calls,
            "success_calls": record.success_calls,
            "fail_calls": record.fail_calls,
            "last_used_at": record.last_used_at,
        },
    }