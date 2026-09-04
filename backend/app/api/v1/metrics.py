"""监控与日志路由（design 2.5.2 E组 + v3 6.8/6.9 SLA与审核质量看板）。"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text

from app.api.deps import get_current_user
from app.core import database
from app.models import MetricsDaily, ProcessLog, QuotaUsage, AuditLog
from app.models import SlaSample, ReviewQualityDaily, SpotCheckSample

router = APIRouter()


@router.get("/daily")
async def metrics_daily(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(get_current_user),
):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    async with database.get_session() as s:
        result = await s.execute(
            select(MetricsDaily).where(MetricsDaily.stat_date >= since).order_by(MetricsDaily.stat_date.desc())
        )
        items = [
            {"stat_date": r.stat_date, "collected_count": r.collected_count,
             "rewritten_count": r.rewritten_count, "image_count": r.image_count,
             "review_total": r.review_total, "review_passed": r.review_passed,
             "published_count": r.published_count, "publish_ok_json": r.publish_ok_json,
             "e2e_total": r.e2e_total, "e2e_success": r.e2e_success,
             "pipeline_failed": r.pipeline_failed}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items}}


@router.get("/logs")
async def process_logs(
    trace_id: str | None = None,
    step: str | None = None,
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
):
    async with database.get_session() as s:
        stmt = select(ProcessLog).order_by(ProcessLog.id.desc())
        count_stmt = select(func.count()).select_from(ProcessLog)
        if trace_id:
            stmt = stmt.where(ProcessLog.trace_id == trace_id)
            count_stmt = count_stmt.where(ProcessLog.trace_id == trace_id)
        if step:
            stmt = stmt.where(ProcessLog.step == step)
            count_stmt = count_stmt.where(ProcessLog.step == step)
        total = await s.scalar(count_stmt)
        result = await s.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "trace_id": r.trace_id, "step": r.step,
             "status": r.status, "message": r.message, "created_at": r.created_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.get("/quota")
async def quota_usage(user: dict = Depends(get_current_user)):
    async with database.get_session() as s:
        result = await s.execute(select(QuotaUsage))
        items = [
            {"quota_key": r.quota_key, "used": r.used, "limit_value": r.limit_value, "reset_at": r.reset_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items}}


@router.get("/audit-logs")
async def audit_logs(
    page: int = 1,
    page_size: int = 50,
    user: dict = Depends(get_current_user),
):
    async with database.get_session() as s:
        total = await s.scalar(select(func.count()).select_from(AuditLog))
        result = await s.execute(
            select(AuditLog).order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "operator": r.operator, "action": r.action, "target": r.target,
             "detail": r.detail, "action_category": r.action_category, "created_at": r.created_at}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.get("/sla")
async def sla_metrics(
    stat_date: str | None = None,
    user: dict = Depends(get_current_user),
):
    """v3 采集时延SLA看板（spec 4.1.2 + 6.11）。"""
    if not stat_date:
        stat_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    async with database.engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT COUNT(*) as total, SUM(is_met) as met, AVG(latency_sec) as avg_latency, "
            "MAX(latency_sec) as max_latency FROM sla_sample WHERE stat_date = :d"
        ), {"d": stat_date})
        row = result.fetchone()
    total = row[0] or 0
    met = row[1] or 0
    return {"code": 0, "message": "ok", "data": {
        "stat_date": stat_date,
        "total_samples": total,
        "met_count": met,
        "compliance_rate": (met / total) if total > 0 else 1.0,
        "avg_latency_sec": round(row[2], 1) if row[2] else 0,
        "max_latency_sec": row[3] or 0,
    }}


@router.get("/review-quality")
async def review_quality(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(get_current_user),
):
    """v3 审核质量看板（spec 6.11）。"""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    async with database.get_session() as s:
        result = await s.execute(
            select(ReviewQualityDaily).where(ReviewQualityDaily.stat_date >= since)
            .order_by(ReviewQualityDaily.stat_date.desc())
        )
        items = [
            {"stat_date": r.stat_date, "review_total": r.review_total,
             "first_pass": r.first_pass, "send_back": r.send_back, "hard_block": r.hard_block,
             "first_pass_rate": r.first_pass_rate, "intercept_rate": r.intercept_rate,
             "platform_reject_rate": r.platform_reject_rate,
             "platform_reject_total": r.platform_reject_total, "submit_total": r.submit_total}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items}}


@router.get("/spot-check")
async def spot_check_samples(
    judged: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
):
    """v3 人工抽查样本看板（spec 5.4.1 规则8）。"""
    async with database.get_session() as s:
        stmt = select(SpotCheckSample).order_by(SpotCheckSample.id.desc())
        count_stmt = select(func.count()).select_from(SpotCheckSample)
        if judged is True:
            stmt = stmt.where(SpotCheckSample.human_judgment.isnot(None))
            count_stmt = count_stmt.where(SpotCheckSample.human_judgment.isnot(None))
        elif judged is False:
            stmt = stmt.where(SpotCheckSample.human_judgment.is_(None))
            count_stmt = count_stmt.where(SpotCheckSample.human_judgment.is_(None))
        total = await s.scalar(count_stmt)
        result = await s.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
        items = [
            {"id": r.id, "article_id": r.article_id, "review_round": r.review_round,
             "was_intercepted": r.was_intercepted, "human_judgment": r.human_judgment,
             "operator": r.operator, "judged_at": r.judged_at, "stat_week": r.stat_week}
            for r in result.scalars()
        ]
    return {"code": 0, "message": "ok", "data": {"items": items, "total": total or 0, "page": page, "page_size": page_size}}


@router.put("/spot-check/{sample_id}/judge")
async def judge_spot_check(
    sample_id: int,
    human_judgment: str = Query(..., pattern="^(false_kill|keep_intercept)$"),
    user: dict = Depends(get_current_user),
):
    """v3 提交人工抽查判定（spec 5.4.1 规则8）。"""
    from app.services.v3_stats_service import SpotCheckService
    await SpotCheckService.record_judgment(
        sample_id=sample_id, human_judgment=human_judgment, operator=user["username"]
    )
    return {"code": 0, "message": "ok", "data": None}