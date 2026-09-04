"""main.py 入口单测：启动探活 + 首启幂等。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class TestHealthCheck:
    def test_health_returns_200(self):
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            body = resp.json()
            assert body["code"] == 0
            assert body["message"] == "ok"
            assert body["data"]["status"] == "healthy"


class TestRootPath:
    def test_root_serves_frontend(self):
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/")
            assert resp.status_code == 200
            assert "root" in resp.text or "html" in resp.text


class TestExceptionHandler:
    def test_app_exception_handler(self):
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/v1/articles/999999", headers={"Authorization": "Bearer test"})
            assert resp.status_code == 400
            body = resp.json()
            assert body["code"] == 2001
            assert "文章不存在" in body["message"]

    def test_auth_exception_http_status(self):
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/v1/auth/me")
            assert resp.status_code == 401


class TestIdempotentStartup:
    def test_double_start_no_crash(self):
        app1 = create_app()
        with TestClient(app1) as c1:
            assert c1.get("/api/v1/health").status_code == 200

        app2 = create_app()
        with TestClient(app2) as c2:
            assert c2.get("/api/v1/health").status_code == 200