"""告警中心路由（design 2.5.2 E组）。"""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func

from app.api.deps import get_current_user
from app.core import database
from app.core.exceptions import ParamError
from app.models import AlertEvent

router = APIRouter()


class AlertConfirm(BaseModel):
    pass


@router.get("")
async def list_alerts(
    level: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
):
    async with database.get_session() as s:
        stmt = select(AlertEvent).order_by(AlertEvent.triggered_at.desc())
        count_stmt = select(func.count()).select_from(AlertEvent)
        if level:
            stmt = stmt.where(AlertEvent.level == level)
            count_stmt = count_stmt.where(AlertEvent.level == level)
        if status:
            stmt = stmt.where(AlertEvent.status == status)
            count_stmt = count_stmt.where(AlertEvent.status == status)
        total = await s.scalar(count_stmt)
        result = await s.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "level": r.level, "source": r.source, "title": r.title,
             "description": r.description, "ref_type": r.ref_type, "ref_value": r.ref_value,
             "status": r.status, "notify_status": r.notify_status,
             "triggered_at": r.triggered_at, "confirmed_by": r.confirmed_by,
             "confirmed_at": r.confirmed_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.post("/{alert_id}/confirm")
async def confirm_alert(alert_id: int, req: AlertConfirm, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    async with database.get_session() as s:
        result = await s.execute(select(AlertEvent).where(AlertEvent.id == alert_id))
        alert = result.scalar()
        if not alert:
            raise ParamError("告警不存在")
        if alert.status == "confirmed":
            raise ParamError("告警已确认")
        alert.status = "confirmed"
        alert.confirmed_by = user["username"]
        alert.confirmed_at = now
    return {"code": 0, "message": "ok", "data": None}