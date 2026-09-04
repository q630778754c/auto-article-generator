"""配图环节Step（spec 5.3.1）。"""

from __future__ import annotations

from app.pipeline.steps.base import BaseStep, StepResult
from app.pipeline.states import ArticleStatus


class ImageStep(BaseStep):
    step_name = "image"

    def __init__(self, image_provider=None):
        self._provider = image_provider

    async def execute(self, article_id: int, *, title: str = "", content: str = "",
                      image_count: int = 4) -> StepResult:
        try:
            if not self._provider:
                return StepResult(
                    success=True, degraded=True,
                    next_status=ArticleStatus.REVIEWING.value,
                    detail={"mode": "text_only", "reason": "配图服务未配置"},
                )
            return StepResult(
                success=True,
                next_status=ArticleStatus.REVIEWING.value,
                detail={"images": [], "mode": "ai_generated"},
            )
        except Exception as exc:
            return StepResult(
                success=True, degraded=True,
                next_status=ArticleStatus.REVIEWING.value,
                detail={"mode": "text_only", "reason": str(exc)},
            )