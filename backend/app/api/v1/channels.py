"""发布渠道路由（design 2.5.2 B组）。"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import get_current_user
from app.core import database
from app.core.exceptions import ParamError, CredentialEmptyError, PlatformUnsupportedError
from app.core.security import mask_sensitive_value
from app.models import PublishChannel

router = APIRouter()

_VALID_PLATFORMS = {"toutiao", "penguin", "zhihu", "xhs", "baijiahao"}


class ChannelCreate(BaseModel):
    platform: str
    account_label: str
    credential: str
    credential_type: str = "cookie"
    daily_limit: int = 10
    min_interval_min: int = 30
    adapter_config: str = "{}"


class ChannelUpdate(BaseModel):
    credential: str | None = None
    enabled: int | None = None
    daily_limit: int | None = None
    min_interval_min: int | None = None
    adapter_config: str | None = None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_cipher():
    from app.core.security import Cipher
    from app.core.config import get_settings
    from pathlib import Path
    settings = get_settings()
    key = Path(settings.resolved_secret_key_file).read_bytes().strip()
    return Cipher(key)


@router.get("")
async def list_channels(page: int = 1, page_size: int = 20, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        total = await s.scalar(select(func.count()).select_from(PublishChannel))
        result = await s.execute(
            select(PublishChannel).order_by(PublishChannel.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "platform": r.platform, "account_label": r.account_label,
             "credential_type": r.credential_type,
             "credential_masked": mask_sensitive_value(r.credential_cipher),
             "enabled": r.enabled, "health_status": r.health_status,
             "daily_limit": r.daily_limit, "min_interval_min": r.min_interval_min,
             "consecutive_fail": r.consecutive_fail,
             "last_published_at": r.last_published_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.post("")
async def create_channel(req: ChannelCreate, user: dict = Depends(get_current_user)):
    if req.platform not in _VALID_PLATFORMS:
        raise PlatformUnsupportedError(req.platform)
    if not req.credential:
        raise CredentialEmptyError()
    cipher = _get_cipher()
    now = _now()
    async with database.get_session() as s:
        ch = PublishChannel(
            platform=req.platform, account_label=req.account_label,
            credential_cipher=cipher.encrypt(req.credential),
            credential_type=req.credential_type,
            daily_limit=req.daily_limit, min_interval_min=req.min_interval_min,
            adapter_config=req.adapter_config,
            created_at=now, updated_at=now,
        )
        s.add(ch)
        await s.flush()
        return {"code": 0, "message": "ok", "data": {"id": ch.id}}


@router.put("/{channel_id}")
async def update_channel(channel_id: int, req: ChannelUpdate, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        result = await s.execute(select(PublishChannel).where(PublishChannel.id == channel_id))
        ch = result.scalar()
        if not ch:
            raise ParamError("渠道不存在")
        if req.credential is not None:
            if not req.credential:
                raise CredentialEmptyError()
            cipher = _get_cipher()
            ch.credential_cipher = cipher.encrypt(req.credential)
        if req.enabled is not None:
            ch.enabled = req.enabled
        if req.daily_limit is not None:
            ch.daily_limit = req.daily_limit
        if req.min_interval_min is not None:
            ch.min_interval_min = req.min_interval_min
        if req.adapter_config is not None:
            ch.adapter_config = req.adapter_config
        ch.updated_at = _now()
    return {"code": 0, "message": "ok", "data": None}


@router.delete("/{channel_id}")
async def delete_channel(channel_id: int, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        result = await s.execute(select(PublishChannel).where(PublishChannel.id == channel_id))
        ch = result.scalar()
        if ch:
            await s.delete(ch)
    return {"code": 0, "message": "ok", "data": None}