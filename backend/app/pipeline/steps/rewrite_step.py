"""改写环节Step（spec 5.2.1）。"""

from __future__ import annotations

from app.pipeline.steps.base import BaseStep, StepResult
from app.pipeline.states import ArticleStatus


class RewriteStep(BaseStep):
    step_name = "rewrite"

    def __init__(self, rewrite_service):
        self._service = rewrite_service

    async def execute(self, article_id: int, *, source_title: str, source_content: str,
                      style: str = "casual", word_min: int = 800, word_max: int = 2000,
                      rewrite_count: int = 0) -> StepResult:
        if rewrite_count >= 2:
            return StepResult(success=False, next_status=ArticleStatus.FAILED.value,
                              error="重写次数已达上限2次")

        try:
            draft = await self._service.rewrite_article(
                source_title=source_title, source_content=source_content,
                style=style, word_min=word_min, word_max=word_max,
            )
            if draft.hit_violation:
                return StepResult(success=False, next_status=ArticleStatus.VIOLATION_BLOCKED.value,
                                  error=f"命中违规: {draft.violation_rule}",
                                  detail={"fingerprint": draft.fingerprint})

            return StepResult(
                success=True,
                next_status=ArticleStatus.IMAGE_GENERATING.value,
                detail={"title": draft.title, "content": draft.content,
                        "fingerprint": draft.fingerprint, "word_count": draft.word_count,
                        "model_used": draft.model_used},
            )
        except Exception as exc:
            return StepResult(success=False, next_status=ArticleStatus.FAILED.value, error=str(exc))