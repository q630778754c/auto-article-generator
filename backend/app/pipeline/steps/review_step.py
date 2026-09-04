"""审核环节Step（spec 5.4.1）。"""

from __future__ import annotations

from app.pipeline.steps.base import BaseStep, StepResult
from app.pipeline.states import ArticleStatus


class ReviewStep(BaseStep):
    step_name = "review"

    def __init__(self, review_service):
        self._service = review_service

    async def execute(self, article_id: int, *, title: str, content: str,
                      source_content: str = "", round_no: int = 1,
                      image_descriptions: list[str] | None = None) -> StepResult:
        try:
            decision = await self._service.review(
                title=title, content=content,
                image_descriptions=image_descriptions,
                source_content=source_content, round_no=round_no,
            )

            if decision.action == "pass":
                return StepResult(
                    success=True,
                    next_status=ArticleStatus.PUBLISHING.value,
                    detail={"action": "pass", "report": decision.report.__dict__ if hasattr(decision.report, '__dict__') else {}},
                )
            elif decision.action == "hard_block":
                return StepResult(
                    success=False,
                    next_status=ArticleStatus.VIOLATION_BLOCKED.value,
                    error=decision.reason,
                    detail={"action": "hard_block"},
                )
            else:
                return StepResult(
                    success=False,
                    next_status=ArticleStatus.REWRITING.value,
                    error=decision.reason,
                    detail={"action": "send_back", "round_no": round_no},
                )
        except Exception as exc:
            return StepResult(success=False, next_status=ArticleStatus.FAILED.value, error=str(exc))