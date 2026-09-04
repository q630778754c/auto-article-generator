"""组9.1 API层集成测试：httpx TestClient 全链路。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

_AUTH = {"Authorization": "Bearer integration-test-token"}


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestFullApiChain:
    """全链路：登录→资讯源→渠道→配置→流水线→文章→告警→监控→v3验收。"""

    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.json()["code"] == 0

    def test_auth_me(self, client):
        resp = client.get("/api/v1/auth/me", headers=_AUTH)
        assert resp.status_code == 200

    def test_source_crud_chain(self, client):
        create_resp = client.post("/api/v1/sources", headers=_AUTH, json={
            "name": "integration-rss", "source_type": "rss", "url": "https://example.com/feed.xml"
        })
        assert create_resp.json()["code"] == 0
        sid = create_resp.json()["data"]["id"]

        list_resp = client.get("/api/v1/sources", headers=_AUTH)
        assert any(s["id"] == sid for s in list_resp.json()["data"]["items"])

        upd_resp = client.put(f"/api/v1/sources/{sid}", headers=_AUTH, json={"enabled": 0})
        assert upd_resp.json()["code"] == 0

        del_resp = client.delete(f"/api/v1/sources/{sid}", headers=_AUTH)
        assert del_resp.json()["code"] == 0

    def test_channel_crud_chain(self, client):
        create_resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "toutiao", "account_label": "integration-test",
            "credential": "cookie-value-123", "daily_limit": 5
        })
        assert create_resp.json()["code"] == 0
        cid = create_resp.json()["data"]["id"]

        list_resp = client.get("/api/v1/channels", headers=_AUTH)
        ch = next(c for c in list_resp.json()["data"]["items"] if c["id"] == cid)
        assert "****" in ch["credential_masked"]

        del_resp = client.delete(f"/api/v1/channels/{cid}", headers=_AUTH)
        assert del_resp.json()["code"] == 0

    def test_config_upsert_chain(self, client):
        put_resp = client.put("/api/v1/config/integration_test_key", headers=_AUTH, json={
            "config_key": "integration_test_key", "config_value": "42", "category": "ai_service"
        })
        assert put_resp.json()["code"] == 0

        list_resp = client.get("/api/v1/config?category=ai_service", headers=_AUTH)
        assert any(c["config_key"] == "integration_test_key" for c in list_resp.json()["data"]["items"])

        del_resp = client.delete("/api/v1/config/integration_test_key", headers=_AUTH)
        assert del_resp.json()["code"] == 0

    def test_pipeline_lifecycle(self, client):
        start_resp = client.post("/api/v1/pipeline/start", headers=_AUTH)
        assert start_resp.json()["code"] == 0

        status_resp = client.get("/api/v1/pipeline/status", headers=_AUTH)
        assert status_resp.json()["data"]["state"] in ("running", "idle")

        pause_resp = client.post("/api/v1/pipeline/pause", headers=_AUTH)
        assert pause_resp.json()["code"] == 0

        resume_resp = client.post("/api/v1/pipeline/resume", headers=_AUTH)
        assert resume_resp.json()["code"] == 0

        stop_resp = client.post("/api/v1/pipeline/stop", headers=_AUTH)
        assert stop_resp.json()["code"] == 0


class TestErrorHandling:
    """异常处理与错误码分段。"""

    def test_param_error_2001(self, client):
        resp = client.get("/api/v1/articles/999999", headers=_AUTH)
        assert resp.json()["code"] == 2001

    def test_auth_error_1001(self, client):
        resp = client.get("/api/v1/articles")
        assert resp.status_code == 401
        assert resp.json()["code"] == 1001

    def test_platform_unsupported_2004(self, client):
        resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "invalid_platform", "account_label": "x", "credential": "y"
        })
        assert resp.json()["code"] == 2004

    def test_credential_empty_2003(self, client):
        resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "toutiao", "account_label": "x", "credential": ""
        })
        assert resp.json()["code"] == 2003


class TestSecurityRedLines:
    """DFX安全红线：凭证掩码/密文存储/审计日志。"""

    def test_credential_masked_in_list(self, client):
        import time
        label = f"security-test-{int(time.time() * 1000)}"
        create_resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "zhihu", "account_label": label,
            "credential": "very-long-secret-cookie-value-12345678"
        })
        cid = create_resp.json()["data"]["id"]

        list_resp = client.get("/api/v1/channels", headers=_AUTH)
        ch = next(c for c in list_resp.json()["data"]["items"] if c["id"] == cid)
        assert ch["credential_masked"].startswith("****")
        assert "very-long-secret" not in ch["credential_masked"]

        client.delete(f"/api/v1/channels/{cid}", headers=_AUTH)

    def test_no_plaintext_credential_in_response(self, client):
        import time
        label = f"plaintext-test-{int(time.time() * 1000)}"
        create_resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "xhs", "account_label": label,
            "credential": "plaintext-secret-abc"
        })
        cid = create_resp.json()["data"]["id"]

        list_resp = client.get("/api/v1/channels", headers=_AUTH)
        body_str = str(list_resp.json())
        assert "plaintext-secret-abc" not in body_str

        client.delete(f"/api/v1/channels/{cid}", headers=_AUTH)

    def test_no_plaintext_credential_in_response(self, client):
        create_resp = client.post("/api/v1/channels", headers=_AUTH, json={
            "platform": "xhs", "account_label": "plaintext-test",
            "credential": "plaintext-secret-abc"
        })
        cid = create_resp.json()["data"]["id"]

        list_resp = client.get("/api/v1/channels", headers=_AUTH)
        body_str = str(list_resp.json())
        assert "plaintext-secret-abc" not in body_str

        client.delete(f"/api/v1/channels/{cid}", headers=_AUTH)