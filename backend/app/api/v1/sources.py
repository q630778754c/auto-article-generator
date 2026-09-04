"""资讯源路由（design 2.5.2 B组）。"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core import database
from app.models import NewsSource
from app.schemas.common import PageRequest, PageResponse

router = APIRouter()


class SourceCreate(BaseModel):
    name: str
    source_type: str
    url: str
    max_items_per_poll: int = 20
    fetch_rules: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    enabled: int | None = None
    max_items_per_poll: int | None = None
    fetch_rules: str | None = None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@router.get("")
async def list_sources(page: int = 1, page_size: int = 20, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        from sqlalchemy import select, func
        total = await s.scalar(select(func.count()).select_from(NewsSource))
        result = await s.execute(
            select(NewsSource).order_by(NewsSource.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "name": r.name, "source_type": r.source_type, "url": r.url,
             "enabled": r.enabled, "run_status": r.run_status,
             "max_items_per_poll": r.max_items_per_poll, "fail_count": r.fail_count}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.post("")
async def create_source(req: SourceCreate, user: dict = Depends(get_current_user)):
    now = _now()
    async with database.get_session() as s:
        src = NewsSource(name=req.name, source_type=req.source_type, url=req.url,
                        max_items_per_poll=req.max_items_per_poll, fetch_rules=req.fetch_rules,
                        created_at=now, updated_at=now)
        s.add(src)
        await s.flush()
        return {"code": 0, "message": "ok", "data": {"id": src.id}}


@router.put("/{source_id}")
async def update_source(source_id: int, req: SourceUpdate, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        from sqlalchemy import select
        result = await s.execute(select(NewsSource).where(NewsSource.id == source_id))
        src = result.scalar()
        if not src:
            from app.core.exceptions import ParamError
            raise ParamError("资讯源不存在")
        if req.name is not None: src.name = req.name
        if req.url is not None: src.url = req.url
        if req.enabled is not None: src.enabled = req.enabled
        if req.max_items_per_poll is not None: src.max_items_per_poll = req.max_items_per_poll
        if req.fetch_rules is not None: src.fetch_rules = req.fetch_rules
        src.updated_at = _now()
    return {"code": 0, "message": "ok", "data": None}


@router.delete("/{source_id}")
async def delete_source(source_id: int, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        from sqlalchemy import select
        result = await s.execute(select(NewsSource).where(NewsSource.id == source_id))
        src = result.scalar()
        if src:
            await s.delete(src)
    return {"code": 0, "message": "ok", "data": None}