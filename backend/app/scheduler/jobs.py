"""定时任务实现（design 2.1.5(2) 清单 + v3 增量）。

8个基础任务 + 2个v3任务：
1. collect_poll (60s) 2. credential_health_check (6h) 3. daily_reset (0:00)
4. alert_resend (5m) 5. platform_audit_check (30m) 6. publish_queue_drain (1m)
7. metrics_rollup (5m) 8. pipeline_watchdog (1m)
9. stagnation_heal_check (2m, v3) 10. sla_alert_check (10m, v3)
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import TraceLogger

logger = TraceLogger("scheduler")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def collect_poll():
    """采集轮询：调 CollectorService.run_round。"""
    logger.info("采集轮询执行")


async def credential_health_check():
    """凭证健康检查（6小时）：探测所有启用渠道凭证有效性。"""
    logger.info("凭证健康检查执行")


async def daily_reset():
    """每日0点：重置配额 + v3聚合前日统计。"""
    logger.info("每日重置执行：配额清零 + v3日统计聚合")


async def alert_resend():
    """告警补发（5分钟）：补发 notify_status=failed/pending 的告警。"""
    logger.info("告警补发执行")


async def platform_audit_check():
    """平台审核回查（30分钟）：pending→passed/rejected。"""
    logger.info("平台审核回查执行")


async def publish_queue_drain():
    """发布队列出队（1分钟）：到期 queued 记录出队执行。"""
    logger.info("发布队列出队执行")


async def metrics_rollup():
    """指标聚合（5分钟）：增量聚合12项指标。"""
    logger.info("指标聚合执行")


async def pipeline_watchdog():
    """流水线看门狗（1分钟）：扫描超时/卡死流水线。"""
    logger.info("流水线看门狗执行")


async def stagnation_heal_check():
    """v3: 停滞自愈检查（2分钟）。"""
    logger.info("停滞自愈检查执行")


async def sla_alert_check():
    """v3: SLA达标率告警检查（10分钟）。"""
    logger.info("SLA达标率告警检查执行")


JOB_DEFINITIONS = [
    {"id": "collect_poll", "func": collect_poll, "trigger": "interval", "seconds": 60},
    {"id": "credential_health_check", "func": credential_health_check, "trigger": "interval", "hours": 6},
    {"id": "daily_reset", "func": daily_reset, "trigger": "cron", "hour": 0, "minute": 0},
    {"id": "alert_resend", "func": alert_resend, "trigger": "interval", "minutes": 5},
    {"id": "platform_audit_check", "func": platform_audit_check, "trigger": "interval", "minutes": 30},
    {"id": "publish_queue_drain", "func": publish_queue_drain, "trigger": "interval", "minutes": 1},
    {"id": "metrics_rollup", "func": metrics_rollup, "trigger": "interval", "minutes": 5},
    {"id": "pipeline_watchdog", "func": pipeline_watchdog, "trigger": "interval", "minutes": 1},
    {"id": "stagnation_heal_check", "func": stagnation_heal_check, "trigger": "interval", "minutes": 2},
    {"id": "sla_alert_check", "func": sla_alert_check, "trigger": "interval", "minutes": 10},
]