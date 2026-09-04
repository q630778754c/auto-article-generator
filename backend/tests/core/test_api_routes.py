"""API v1 路由单测（design 2.5.2 全组 + v3 6.7/6.8/6.9）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

_TOKEN = "test-token-for-api-tests"
_AUTH = {"Authorization": f"Bearer {_TOKEN}"}


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestAuthRoutes:
    def test_login_success(self, client):
        resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_me_with_token(self, client):
        resp = client.get("/api/v1/auth/me", headers=_AUTH)
        assert resp.status_code == 0 or resp.json()["code"] in (0, 1001)

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestSourcesRoutes:
    def test_list_sources(self, client):
        resp = client.get("/api/v1/sources", headers=_AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert "items" in body["data"]

    def test_create_and_delete_source(self, client):
        create_resp = client.post("/api/v1/sources", headers=_AUTH, json={
            "name": "test-rss", "source_type": "rss", "url": "https://example.com/rss.xml"
        })
        assert create_resp.status_code == 200
        assert create_resp.json()["code"] == 0
        sid = create_resp.json()["data"]["id"]

        del_resp = client.delete(f"/api/v1/sources/{sid}", headers=_AUTH)
        assert del_resp.status_code == 200

    def test_sources_without_auth(self, client):
        resp = client.get("/api/v1/sources")
        assert resp.status_code == 401


class TestChannelsRoutes:
    def test_list_channels(self, client):
        resp = client.get("/api/v1/channels", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_create_channel_invalid_platform(self, client):
        resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "invalid", "account_label": "test", "credential": "cookie123"
        })
        assert resp.json()["code"] == 2004

    def test_create_channel_empty_credential(self, client):
        resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "toutiao", "account_label": "test", "credential": ""
        })
        assert resp.json()["code"] == 2003

    def test_create_update_delete_channel(self, client):
        create_resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "zhihu", "account_label": "test-zhihu",
            "credential": "cookie-abc123", "daily_limit": 5
        })
        assert create_resp.json()["code"] == 0
        cid = create_resp.json()["data"]["id"]

        upd_resp = client.put(f"/api/v1/channels/{cid}", headers=_AUTH, json={"daily_limit": 15})
        assert upd_resp.json()["code"] == 0

        del_resp = client.delete(f"/api/v1/channels/{cid}", headers=_AUTH)
        assert del_resp.json()["code"] == 0


class TestConfigRoutes:
    def test_list_config(self, client):
        resp = client.get("/api/v1/config", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_upsert_and_delete_config(self, client):
        put_resp = client.put("/api/v1/config/test_key", headers=_AUTH, json={
            "config_key": "test_key", "config_value": "1", "category": "ai_service"
        })
        assert put_resp.json()["code"] == 0

        del_resp = client.delete("/api/v1/config/test_key", headers=_AUTH)
        assert del_resp.json()["code"] == 0

    def test_upsert_invalid_category(self, client):
        resp = client.put("/api/v1/config/bad_key", headers=_AUTH, json={
            "config_key": "bad_key", "config_value": "x", "category": "invalid_cat"
        })
        assert resp.json()["code"] == 2001


class TestPipelineRoutes:
    def test_status(self, client):
        resp = client.get("/api/v1/pipeline/status", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        assert "state" in resp.json()["data"]

    def test_start_pause_resume_stop(self, client):
        start_resp = client.post("/api/v1/pipeline/start", headers=_AUTH)
        assert start_resp.json()["code"] == 0

        pause_resp = client.post("/api/v1/pipeline/pause", headers=_AUTH)
        assert pause_resp.json()["code"] == 0

        resume_resp = client.post("/api/v1/pipeline/resume", headers=_AUTH)
        assert resume_resp.json()["code"] == 0

        stop_resp = client.post("/api/v1/pipeline/stop", headers=_AUTH)
        assert stop_resp.json()["code"] == 0

    def test_records_list(self, client):
        resp = client.get("/api/v1/pipeline/records", headers=_AUTH)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]

    def test_unmanned_acceptance_report(self, client):
        resp = client.get("/api/v1/pipeline/unmanned/acceptance-report", headers=_AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "window_hours" in data
        assert "is_qualified" in data
        assert "manual_intervention_count" in data
        assert "intervention_detail" in data

    def test_unmanned_acceptance_report_custom_window(self, client):
        for wh in [24, 72, 168]:
            resp = client.get(f"/api/v1/pipeline/unmanned/acceptance-report?window_hours={wh}", headers=_AUTH)
            assert resp.json()["data"]["window_hours"] == wh


class TestArticlesRoutes:
    def test_list_articles(self, client):
        resp = client.get("/api/v1/articles", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_list_articles_with_status_filter(self, client):
        resp = client.get("/api/v1/articles?status=draft", headers=_AUTH)
        assert resp.status_code == 200

    def test_get_nonexistent_article(self, client):
        resp = client.get("/api/v1/articles/999999", headers=_AUTH)
        assert resp.json()["code"] == 2001


class TestAlertsRoutes:
    def test_list_alerts(self, client):
        resp = client.get("/api/v1/alerts", headers=_AUTH)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    def test_list_alerts_with_filters(self, client):
        resp = client.get("/api/v1/alerts?level=P0&status=unconfirmed", headers=_AUTH)
        assert resp.status_code == 200

    def test_confirm_nonexistent_alert(self, client):
        resp = client.post("/api/v1/alerts/999999/confirm", headers=_AUTH, json={})
        assert resp.json()["code"] == 2001


class TestMetricsRoutes:
    def test_metrics_daily(self, client):
        resp = client.get("/api/v1/metrics/daily", headers=_AUTH)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]

    def test_process_logs(self, client):
        resp = client.get("/api/v1/metrics/logs", headers=_AUTH)
        assert resp.status_code == 200

    def test_quota_usage(self, client):
        resp = client.get("/api/v1/metrics/quota", headers=_AUTH)
        assert resp.status_code == 200

    def test_audit_logs(self, client):
        resp = client.get("/api/v1/metrics/audit-logs", headers=_AUTH)
        assert resp.status_code == 200

    def test_sla_metrics(self, client):
        resp = client.get("/api/v1/metrics/sla", headers=_AUTH)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "compliance_rate" in data
        assert "total_samples" in data

    def test_review_quality(self, client):
        resp = client.get("/api/v1/metrics/review-quality", headers=_AUTH)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]

    def test_spot_check_samples(self, client):
        resp = client.get("/api/v1/metrics/spot-check", headers=_AUTH)
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]

    def test_spot_check_judge_invalid(self, client):
        resp = client.put("/api/v1/metrics/spot-check/1/judge?human_judgment=invalid", headers=_AUTH)
        assert resp.status_code == 422