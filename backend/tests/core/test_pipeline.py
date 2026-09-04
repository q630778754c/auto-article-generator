"""编排层单测：状态迁移 + PipelineEngine + Scheduler。"""

from __future__ import annotations

import pytest

from app.pipeline.states import (
    ArticleStatus, Step, can_transition, next_step,
    TERMINAL_STATES, TRANSITIONS,
)


class TestStateTransitions:
    def test_normal_flow(self):
        assert can_transition(ArticleStatus.PENDING_REWRITE, ArticleStatus.REWRITING)
        assert can_transition(ArticleStatus.REWRITING, ArticleStatus.IMAGE_GENERATING)
        assert can_transition(ArticleStatus.IMAGE_GENERATING, ArticleStatus.REVIEWING)
        assert can_transition(ArticleStatus.REVIEWING, ArticleStatus.PUBLISHING)
        assert can_transition(ArticleStatus.PUBLISHING, ArticleStatus.DONE)

    def test_send_back_edge(self):
        assert can_transition(ArticleStatus.REVIEWING, ArticleStatus.REWRITING)

    def test_terminal_no_transition(self):
        for terminal in TERMINAL_STATES:
            for target in ArticleStatus:
                assert not can_transition(terminal, target)

    def test_invalid_transition(self):
        assert not can_transition(ArticleStatus.PENDING_REWRITE, ArticleStatus.DONE)
        assert not can_transition(ArticleStatus.PENDING_REWRITE, ArticleStatus.PUBLISHING)
        assert not can_transition(ArticleStatus.DONE, ArticleStatus.REWRITING)

    def test_failure_branches(self):
        assert can_transition(ArticleStatus.PENDING_REWRITE, ArticleStatus.FAILED)
        assert can_transition(ArticleStatus.REWRITING, ArticleStatus.FAILED)
        assert can_transition(ArticleStatus.REWRITING, ArticleStatus.VIOLATION_BLOCKED)
        assert can_transition(ArticleStatus.REVIEWING, ArticleStatus.VIOLATION_BLOCKED)

    def test_awaiting_confirm(self):
        assert can_transition(ArticleStatus.REVIEWING, ArticleStatus.AWAITING_CONFIRM)
        assert can_transition(ArticleStatus.AWAITING_CONFIRM, ArticleStatus.PUBLISHING)
        assert can_transition(ArticleStatus.AWAITING_CONFIRM, ArticleStatus.ARCHIVED_PAUSED)

    def test_next_step(self):
        assert next_step(ArticleStatus.PENDING_REWRITE) == Step.REWRITE
        assert next_step(ArticleStatus.REWRITING) == Step.IMAGE
        assert next_step(ArticleStatus.IMAGE_GENERATING) == Step.REVIEW
        assert next_step(ArticleStatus.REVIEWING) == Step.PUBLISH
        assert next_step(ArticleStatus.PUBLISHING) == Step.DONE
        assert next_step(ArticleStatus.DONE) is None


class TestPipelineEngine:
    @pytest.mark.asyncio
    async def test_start(self):
        from app.pipeline.engine import PipelineEngine, EngineState
        engine = PipelineEngine(concurrency=5, daily_limit=50)
        status = await engine.start()
        assert status.state == EngineState.RUNNING
        assert status.daily_limit == 50

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        from app.pipeline.engine import PipelineEngine, EngineState
        engine = PipelineEngine()
        await engine.start()
        status = await engine.pause()
        assert status.state == EngineState.PAUSED
        status = await engine.resume()
        assert status.state == EngineState.RUNNING

    @pytest.mark.asyncio
    async def test_stop(self):
        from app.pipeline.engine import PipelineEngine, EngineState
        engine = PipelineEngine()
        await engine.start()
        status = await engine.stop()
        assert status.state == EngineState.STOPPED

    @pytest.mark.asyncio
    async def test_daily_quota_gate(self):
        from app.pipeline.engine import PipelineEngine
        engine = PipelineEngine(daily_limit=3)
        await engine.start()
        assert engine.can_accept()
        engine.mark_flow()
        engine.mark_flow()
        engine.mark_flow()
        assert not engine.can_accept()
        engine.reset_daily_quota()
        assert engine.can_accept()

    @pytest.mark.asyncio
    async def test_is_stagnant_idle(self):
        from app.pipeline.engine import PipelineEngine
        engine = PipelineEngine()
        assert not engine.is_stagnant()

    @pytest.mark.asyncio
    async def test_pending_count(self):
        from app.pipeline.engine import PipelineEngine
        engine = PipelineEngine()
        assert engine.pending_count() == 0


class TestScheduler:
    def test_job_definitions_complete(self):
        from app.scheduler.jobs import JOB_DEFINITIONS
        ids = {j["id"] for j in JOB_DEFINITIONS}
        expected = {
            "collect_poll", "credential_health_check", "daily_reset",
            "alert_resend", "platform_audit_check", "publish_queue_drain",
            "metrics_rollup", "pipeline_watchdog",
            "stagnation_heal_check", "sla_alert_check",
        }
        assert ids == expected

    def test_scheduler_runner_create(self):
        from app.scheduler.runner import SchedulerRunner
        runner = SchedulerRunner()
        assert runner is not None

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        from app.scheduler.runner import SchedulerRunner
        runner = SchedulerRunner()
        await runner.start()
        await runner.stop()