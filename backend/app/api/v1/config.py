"""系统配置路由（design 2.5.2 C组）。"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core import database
from app.core.exceptions import ParamError
from app.models import SystemConfig

router = APIRouter()

_VALID_CATEGORIES = {"collect_source", "ai_service", "pipeline_strategy", "publish_rule"}
_VALID_EFFECT_MODES = {"immediate", "restart"}


class ConfigUpsert(BaseModel):
    config_key: str
    config_value: str
    category: str
    effect_mode: str = "immediate"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@router.get("")
async def list_config(category: str | None = None, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        stmt = select(SystemConfig).order_by(SystemConfig.category, SystemConfig.config_key)
        if category:
            stmt = stmt.where(SystemConfig.category == category)
        result = await s.execute(stmt)
        items = [
            {"config_key": r.config_key, "config_value": r.config_value,
             "category": r.category, "effect_mode": r.effect_mode,
             "version": r.version, "updated_by": r.updated_by, "updated_at": r.updated_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items}}


@router.put("/{config_key}")
async def upsert_config(config_key: str, req: ConfigUpsert, user: dict = Depends(get_current_user)):
    if req.category not in _VALID_CATEGORIES:
        raise ParamError(f"非法配置分类：{req.category}")
    if req.effect_mode not in _VALID_EFFECT_MODES:
        raise ParamError(f"非法生效模式：{req.effect_mode}")
    now = _now()
    async with database.get_session() as s:
        result = await s.execute(select(SystemConfig).where(SystemConfig.config_key == config_key))
        cfg = result.scalar()
        if cfg:
            cfg.config_value = req.config_value
            cfg.category = req.category
            cfg.effect_mode = req.effect_mode
            cfg.version += 1
            cfg.updated_by = user["username"]
            cfg.updated_at = now
        else:
            cfg = SystemConfig(
                config_key=config_key, config_value=req.config_value,
                category=req.category, effect_mode=req.effect_mode,
                version=1, updated_by=user["username"], updated_at=now,
            )
            s.add(cfg)
    return {"code": 0, "message": "ok", "data": None}


@router.delete("/{config_key}")
async def delete_config(config_key: str, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        result = await s.execute(select(SystemConfig).where(SystemConfig.config_key == config_key))
        cfg = result.scalar()
        if cfg:
            await s.delete(cfg)
    return {"code": 0, "message": "ok", "data": None}