"""爬虫开放 API 包（spec 4.3.4 / design 2.5.2 D组）。"""

from fastapi import APIRouter

from app.api.v1.open.collector import router as collector_router
from app.api.v1.open.docs import router as docs_router

router = APIRouter()
router.include_router(collector_router, prefix="/collector", tags=["爬虫API"])
router.include_router(docs_router, tags=["API文档"])

__all__ = ["router"]
