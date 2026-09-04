"""v3 统计服务：SLA埋点 / 审核质量 / 无人值守 / 抽查样本（spec 4.1.2 / 6.11 / 6.12）。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core import database
from app.core.logging import TraceLogger
from sqlalchemy import select, text

logger = TraceLogger("v3_stats")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class SlaService:
    """采集时延SLA埋点（spec 4.1.2 + 5.1.1 规则3）。"""

    @staticmethod
    async def record_sample(*, source_id: int, material_id: int,
                            origin_published_at: str, collected_at: str,
                            sla_target_sec: int = 180) -> bool:
        from app.models import SlaSample
        try:
            latency = 0
            if origin_published_at and collected_at:
                try:
                    t1 = datetime.fromisoformat(origin_published_at.replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
                    latency = int((t2 - t1).total_seconds())
                except Exception:
                    latency = 0
            is_met = 1 if latency <= sla_target_sec else 0
            stat_date = collected_at[:10] if collected_at else _today()

            async with database.get_session() as s:
                s.add(SlaSample(
                    source_id=source_id, material_id=material_id,
                    origin_published_at=origin_published_at, collected_at=collected_at,
                    latency_sec=latency, sla_target_sec=sla_target_sec,
                    is_met=is_met, stat_date=stat_date,
                ))
            return bool(is_met)
        except Exception as exc:
            logger.error(f"SLA埋点失败: {exc}")
            return False

    @staticmethod
    async def compliance_rate(stat_date: str) -> float:
        from sqlalchemy import text as sa_text
        async with database.engine.connect() as conn:
            result = await conn.execute(sa_text(
                "SELECT COUNT(*) as total, SUM(is_met) as met FROM sla_sample WHERE stat_date = :d"
            ), {"d": stat_date})
            row = result.fetchone()
        if not row or not row[0]:
            return 1.0
        return row[1] / row[0] if row[0] > 0 else 1.0


class ReviewQualityService:
    """审核质量日统计（spec 6.11）。"""

    @staticmethod
    async def incr_review(stat_date: str, outcome: str) -> None:
        from app.models import ReviewQualityDaily
        try:
            async with database.get_session() as s:
                existing = await s.execute(
                    select(ReviewQualityDaily).where(ReviewQualityDaily.stat_date == stat_date)
                )
                row = existing.scalar()
                if not row:
                    row = ReviewQualityDaily(stat_date=stat_date)
                    s.add(row)
                    await s.flush()
                row.review_total += 1
                if outcome == "first_pass":
                    row.first_pass += 1
                elif outcome == "send_back":
                    row.send_back += 1
                elif outcome == "hard_block":
                    row.hard_block += 1
                if row.review_total > 0:
                    row.first_pass_rate = row.first_pass / row.review_total
                    row.intercept_rate = (row.send_back + row.hard_block) / row.review_total
        except Exception as exc:
            logger.error(f"审核质量统计失败: {exc}")

    @staticmethod
    async def incr_platform_reject(stat_date: str) -> None:
        from app.models import ReviewQualityDaily
        try:
            async with database.get_session() as s:
                existing = await s.execute(
                    select(ReviewQualityDaily).where(ReviewQualityDaily.stat_date == stat_date)
                )
                row = existing.scalar()
                if not row:
                    row = ReviewQualityDaily(stat_date=stat_date)
                    s.add(row)
                    await s.flush()
                row.platform_reject_total += 1
                if row.submit_total > 0:
                    row.platform_reject_rate = row.platform_reject_total / row.submit_total
        except Exception as exc:
            logger.error(f"平台拒绝统计失败: {exc}")


class UnmannedRunService:
    """无人值守运行统计（spec 6.12）。"""

    @staticmethod
    async def record_manual_intervention(stat_date: str, action_category: str) -> None:
        from app.models import UnmannedRunStat
        try:
            async with database.get_session() as s:
                existing = await s.execute(
                    select(UnmannedRunStat).where(UnmannedRunStat.stat_date == stat_date)
                )
                row = existing.scalar()
                if not row:
                    row = UnmannedRunStat(stat_date=stat_date)
                    s.add(row)
                    await s.flush()
                row.manual_intervention_count += 1
                if action_category == "initial_config":
                    row.initial_config_count += 1
                elif action_category == "credential_update":
                    row.credential_update_count += 1
                elif action_category == "alert_handle":
                    row.alert_handle_count += 1
                elif action_category == "manual_confirm":
                    row.manual_confirm_count += 1
        except Exception as exc:
            logger.error(f"无人值守统计失败: {exc}")


class SpotCheckService:
    """人工抽查样本（spec 5.4.1 规则8）。"""

    @staticmethod
    async def record_judgment(*, sample_id: int, human_judgment: str, operator: str) -> None:
        from app.models import SpotCheckSample
        try:
            async with database.get_session() as s:
                existing = await s.execute(
                    select(SpotCheckSample).where(SpotCheckSample.id == sample_id)
                )
                row = existing.scalar()
                if row:
                    row.human_judgment = human_judgment
                    row.operator = operator
                    row.judged_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        except Exception as exc:
            logger.error(f"抽查样本记录失败: {exc}")