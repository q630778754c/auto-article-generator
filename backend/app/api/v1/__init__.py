"""API v1 包入口。"""

from fastapi import APIRouter

from app.api.v1 import auth, sources, channels, config, pipeline, articles, alerts, metrics, health

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(sources.router, prefix="/sources", tags=["资讯源"])
router.include_router(channels.router, prefix="/channels", tags=["发布渠道"])
router.include_router(config.router, prefix="/config", tags=["配置"])
router.include_router(pipeline.router, prefix="/pipeline", tags=["流水线"])
router.include_router(articles.router, prefix="/articles", tags=["文章"])
router.include_router(alerts.router, prefix="/alerts", tags=["告警"])
router.include_router(metrics.router, prefix="/metrics", tags=["监控"])
router.include_router(health.router, prefix="", tags=["健康检查"])