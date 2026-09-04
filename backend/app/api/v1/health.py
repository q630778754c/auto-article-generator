"""健康检查端点（task 11.8）。

提供两层：
- /api/v1/health          轻量探活（兼容 v1），仅返回 200 状态
- /api/v1/health/deep     深度探活，返回 build_version / git_sha / build_time / uptime_sec / storage_backend

被 Render healthCheckPath + cron-job.org / UptimeRobot / GitHub Actions 保活调用。
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import TraceLogger

router = APIRouter(prefix="/health", tags=["健康检查"])
logger = TraceLogger("health")

_PROCESS_START_TS = time.time()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@router.get("")
async def health() -> dict:
    """轻量探活端点：返回 200 与 status=healthy（兼容既有 v1 测试）。"""
    return {"code": 0, "message": "ok", "data": {"status": "healthy"}}


@router.get("/deep")
async def health_deep() -> dict:
    """深度探活：暴露构建元信息，便于部署后核对版本与后端。"""
    settings = get_settings()
    git_sha = (
        os.environ.get("RENDER_GIT_COMMIT")
        or os.environ.get("GIT_SHA")
        or os.environ.get("GITHUB_SHA")
        or ""
    )
    build_time = (
        os.environ.get("RENDER_BUILD_STARTED_AT")
        or os.environ.get("BUILD_TIME")
        or ""
    )
    data = {
        "status": "healthy",
        "build_version": settings.build_version,
        "git_sha": git_sha[:12] if git_sha else "",
        "build_time": build_time,
        "uptime_sec": int(time.time() - _PROCESS_START_TS),
        "storage_backend": settings.storage_backend,
        "server_time": _utcnow_iso(),
    }
    return {"code": 0, "message": "ok", "data": data}