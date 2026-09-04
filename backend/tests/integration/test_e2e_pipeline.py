"""组9.2+9.6 流水线端到端与v3专项验收用例。"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.pipeline.engine import PipelineEngine, EngineState
from app.pipeline.states import ArticleStatus, can_transition

_AUTH = {"Authorization": "Bearer e2e-test-token"}


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestPipelineStateTransitions:
    """9.2 流水线状态迁移正确性。"""

    def test_valid_transitions(self):
        assert can_transition(ArticleStatus.PENDING_REWRITE, ArticleStatus.REWRITING)
        assert can_transition(ArticleStatus.REWRITING, ArticleStatus.IMAGE_GENERATING)
        assert can_transition(ArticleStatus.IMAGE_GENERATING, ArticleStatus.REVIEWING)
        assert can_transition(ArticleStatus.REVIEWING, ArticleStatus.PUBLISHING)
        assert can_transition(ArticleStatus.PUBLISHING, ArticleStatus.DONE)

    def test_invalid_transitions(self):
        assert not can_transition(ArticleStatus.PENDING_REWRITE, ArticleStatus.DONE)
        assert not can_transition(ArticleStatus.DONE, ArticleStatus.PENDING_REWRITE)
        assert not can_transition(ArticleStatus.FAILED, ArticleStatus.REWRITING)

    def test_engine_lifecycle(self):
        engine = PipelineEngine()
        assert engine._state == EngineState.IDLE

        import asyncio
        async def run():
            status = await engine.start()
            assert status.state == EngineState.RUNNING

            status = await engine.pause()
            assert status.state == EngineState.PAUSED

            status = await engine.resume()
            assert status.state == EngineState.RUNNING

            status = await engine.stop()
            assert status.state == EngineState.STOPPED

        asyncio.run(run())

    def test_engine_daily_quota_gate(self):
        engine = PipelineEngine(daily_limit=2)
        assert engine.can_accept()
        engine.mark_flow()
        assert engine.can_accept()
        engine.mark_flow()
        assert not engine.can_accept()

        engine.reset_daily_quota()
        assert engine.can_accept()

    def test_engine_stagnation_detection(self):
        engine = PipelineEngine()
        assert not engine.is_stagnant()

        import asyncio
        async def run():
            await engine.start()
        asyncio.run(run())

        engine._last_flow_time = datetime.now(timezone.utc) - timedelta(seconds=400)
        engine._active_count = 0
        assert engine.is_stagnant()


class TestV3SlaMetrics:
    """9.6 v3 SLA采集时延达标率。"""

    def test_sla_endpoint(self, client):
        resp = client.get("/api/v1/metrics/sla", headers=_AUTH)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "compliance_rate" in data
        assert 0 <= data["compliance_rate"] <= 1.0
        assert data["total_samples"] >= 0

    def test_sla_with_date(self, client):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        resp = client.get(f"/api/v1/metrics/sla?stat_date={today}", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["data"]["stat_date"] == today


class TestV3UnmannedAcceptance:
    """9.6 v3 无人值守验收报告。"""

    def test_acceptance_report_default_72h(self, client):
        resp = client.get("/api/v1/pipeline/unmanned/acceptance-report", headers=_AUTH)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["window_hours"] == 72
        assert "is_qualified" in data
        assert "intervention_detail" in data
        assert "initial_config" in data["intervention_detail"]
        assert "credential_update" in data["intervention_detail"]
        assert "alert_handle" in data["intervention_detail"]
        assert "manual_confirm" in data["intervention_detail"]

    def test_acceptance_report_custom_windows(self, client):
        for wh in [24, 72, 168]:
            resp = client.get(f"/api/v1/pipeline/unmanned/acceptance-report?window_hours={wh}", headers=_AUTH)
            assert resp.json()["data"]["window_hours"] == wh

    def test_acceptance_report_qualified_logic(self, client):
        resp = client.get("/api/v1/pipeline/unmanned/acceptance-report?window_hours=24", headers=_AUTH)
        data = resp.json()["data"]
        if data["manual_intervention_count"] == 0 and data["continuous_hours"] >= 24:
            assert data["is_qualified"] is True
        else:
            assert data["is_qualified"] is False


class TestV3ReviewQuality:
    """9.6 v3 审核质量四指标。"""

    def test_review_quality_endpoint(self, client):
        resp = client.get("/api/v1/metrics/review-quality?days=7", headers=_AUTH)
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for item in items:
            assert 0 <= item["first_pass_rate"] <= 1.0
            assert 0 <= item["intercept_rate"] <= 1.0
            assert item["review_total"] >= 0
            assert item["first_pass"] + item["send_back"] + item["hard_block"] <= item["review_total"]


class TestV3SpotCheck:
    """9.6 v3 人工抽查样本。"""

    def test_spot_check_list(self, client):
        resp = client.get("/api/v1/metrics/spot-check", headers=_AUTH)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]

    def test_spot_check_judgment_validation(self, client):
        resp = client.put("/api/v1/metrics/spot-check/1/judge?human_judgment=invalid_value", headers=_AUTH)
        assert resp.status_code == 422


class TestDfxReliability:
    """9.3 DFX可靠性：幂等性/恢复性。"""

    def test_idempotent_startup(self):
        app1 = create_app()
        with TestClient(app1) as c1:
            assert c1.get("/api/v1/health").status_code == 200
        app2 = create_app()
        with TestClient(app2) as c2:
            assert c2.get("/api/v1/health").status_code == 200

    def test_source_delete_idempotent(self, client):
        resp1 = client.delete("/api/v1/sources/999999", headers=_AUTH)
        assert resp1.json()["code"] == 0
        resp2 = client.delete("/api/v1/sources/999999", headers=_AUTH)
        assert resp2.json()["code"] == 0


class TestDfxMaintainability:
    """9.3 DFX可维护性：配置热更新/审计追踪。"""

    def test_config_version_increment(self, client):
        client.put("/api/v1/config/maint_test", headers=_AUTH, json={
            "config_key": "maint_test", "config_value": "v1", "category": "ai_service"
        })
        resp1 = client.get("/api/v1/config?category=ai_service", headers=_AUTH)
        v1 = next(c for c in resp1.json()["data"]["items"] if c["config_key"] == "maint_test")["version"]

        client.put("/api/v1/config/maint_test", headers=_AUTH, json={
            "config_key": "maint_test", "config_value": "v2", "category": "ai_service"
        })
        resp2 = client.get("/api/v1/config?category=ai_service", headers=_AUTH)
        v2 = next(c for c in resp2.json()["data"]["items"] if c["config_key"] == "maint_test")["version"]

        assert v2 == v1 + 1
        client.delete("/api/v1/config/maint_test", headers=_AUTH)

    def test_audit_log_trail(self, client):
        resp = client.get("/api/v1/metrics/audit-logs", headers=_AUTH)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]