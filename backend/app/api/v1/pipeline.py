"""流水线控制路由（design 2.5.2 D组 + v3 6.7无人值守验收）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func

from app.api.deps import get_current_user
from app.core import database
from app.models import PipelineRecord, Article, UnmannedRunStat, AuditLog
from app.pipeline.engine import PipelineEngine

router = APIRouter()

_engine = PipelineEngine()


def _get_engine() -> PipelineEngine:
    return _engine


@router.post("/start")
async def start_pipeline(user: dict = Depends(get_current_user)):
    engine = _get_engine()
    status = await engine.start()
    return {"code": 0, "message": "ok", "data": {
        "state": status.state.value,
        "active_count": status.active_count,
        "pending_count": status.pending_count,
        "daily_output": status.daily_output,
        "daily_limit": status.daily_limit,
        "missing_configs": status.missing_configs,
    }}


@router.post("/pause")
async def pause_pipeline(user: dict = Depends(get_current_user)):
    status = await _get_engine().pause()
    return {"code": 0, "message": "ok", "data": {"state": status.state.value}}


@router.post("/resume")
async def resume_pipeline(user: dict = Depends(get_current_user)):
    status = await _get_engine().resume()
    return {"code": 0, "message": "ok", "data": {"state": status.state.value}}


@router.post("/stop")
async def stop_pipeline(user: dict = Depends(get_current_user)):
    status = await _get_engine().stop()
    return {"code": 0, "message": "ok", "data": {"state": status.state.value}}


@router.get("/status")
async def pipeline_status(user: dict = Depends(get_current_user)):
    engine = _get_engine()
    status = await engine.status()
    return {"code": 0, "message": "ok", "data": {
        "state": status.state.value,
        "active_count": status.active_count,
        "pending_count": status.pending_count,
        "daily_output": status.daily_output,
        "daily_limit": status.daily_limit,
        "is_stagnant": engine.is_stagnant(),
        "missing_configs": status.missing_configs,
    }}


@router.get("/records")
async def list_records(page: int = 1, page_size: int = 20, user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        total = await s.scalar(select(func.count()).select_from(PipelineRecord))
        result = await s.execute(
            select(PipelineRecord).order_by(PipelineRecord.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "trace_id": r.trace_id, "article_id": r.article_id,
             "current_step": r.current_step, "elapsed_sec": r.elapsed_sec,
             "final_state": r.final_state, "created_at": r.created_at, "updated_at": r.updated_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.get("/unmanned/acceptance-report")
async def unmanned_acceptance_report(
    window_hours: int = Query(default=72, ge=1, le=720),
    user: dict = Depends(get_current_user),
):
    """v3 无人值守验收报告（spec 5.6.1 规则2b 验收口径）。"""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import text

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)
    window_start_str = window_start.strftime("%Y-%m-%d")

    async with database.get_session() as s:
        result = await s.execute(
            select(UnmannedRunStat).where(UnmannedRunStat.stat_date >= window_start_str)
        )
        rows = result.scalars().all()

        total_manual = sum(r.manual_intervention_count for r in rows)
        initial_config = sum(r.initial_config_count for r in rows)
        credential_update = sum(r.credential_update_count for r in rows)
        alert_handle = sum(r.alert_handle_count for r in rows)
        manual_confirm = sum(r.manual_confirm_count for r in rows)
        daily_output_sum = sum(r.daily_output for r in rows)
        max_continuous = max((r.continuous_hours for r in rows), default=0)

        audit_result = await s.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= window_start.isoformat())
        )
        total_audit = audit_result.scalar() or 0

    is_qualified = total_manual == 0 and max_continuous >= window_hours
    return {"code": 0, "message": "ok", "data": {
        "window_hours": window_hours,
        "window_start": window_start.isoformat(timespec="seconds"),
        "window_end": now.isoformat(timespec="seconds"),
        "continuous_hours": max_continuous,
        "manual_intervention_count": total_manual,
        "intervention_detail": {
            "initial_config": initial_config,
            "credential_update": credential_update,
            "alert_handle": alert_handle,
            "manual_confirm": manual_confirm,
        },
        "daily_output_total": daily_output_sum,
        "audit_log_total": total_audit,
        "is_qualified": is_qualified,
    }}