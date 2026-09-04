"""APScheduler 调度装配（design 2.1.5(2)，ADR-012 热生效）。

AsyncIOScheduler + 运行时 reschedule 支持配置热生效。
"""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.core.logging import TraceLogger
from app.scheduler.jobs import JOB_DEFINITIONS

logger = TraceLogger("sched_runner")


class SchedulerRunner:
    """调度器装配器。"""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._job_ids: set[str] = set()

    async def start(self) -> None:
        """启动调度器，注册全部任务。"""
        for job_def in JOB_DEFINITIONS:
            trigger = self._build_trigger(job_def)
            self._scheduler.add_job(
                job_def["func"],
                trigger=trigger,
                id=job_def["id"],
                replace_existing=True,
            )
            self._job_ids.add(job_def["id"])

        self._scheduler.start()
        logger.info(f"调度器启动，注册{len(self._job_ids)}个任务")

    async def stop(self) -> None:
        """停止调度器。"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("调度器停止")

    def reschedule(self, job_id: str, **trigger_args) -> None:
        """运行时 reschedule（配置热生效关键，ADR-012）。"""
        if job_id not in self._job_ids:
            logger.warn(f"reschedule失败：任务{job_id}不存在")
            return

        trigger = IntervalTrigger(**trigger_args)
        self._scheduler.reschedule_job(job_id, trigger=trigger)
        logger.info(f"任务{job_id}已reschedule: {trigger_args}")

    def get_next_run_time(self, job_id: str) -> str | None:
        """获取任务下次执行时间。"""
        job = self._scheduler.get_job(job_id)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None

    @staticmethod
    def _build_trigger(job_def: dict):
        trigger_type = job_def["trigger"]
        if trigger_type == "interval":
            kwargs = {k: v for k, v in job_def.items()
                     if k in ("seconds", "minutes", "hours", "days")}
            return IntervalTrigger(**kwargs)
        elif trigger_type == "cron":
            kwargs = {k: v for k, v in job_def.items()
                     if k in ("hour", "minute", "second", "day", "month", "day_of_week")}
            return CronTrigger(**kwargs)
        return IntervalTrigger(minutes=60)