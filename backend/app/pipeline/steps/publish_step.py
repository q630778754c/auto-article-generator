"""发布环节Step（spec 5.5.1）。"""

from __future__ import annotations

from app.pipeline.steps.base import BaseStep, StepResult
from app.pipeline.states import ArticleStatus


class PublishStep(BaseStep):
    step_name = "publish"

    def __init__(self, publish_service):
        self._service = publish_service

    async def execute(self, article_id: int, *, title: str, content: str,
                      channels: list[dict] | None = None) -> StepResult:
        if not channels:
            return StepResult(success=True, next_status=ArticleStatus.DONE.value,
                            detail={"published": [], "reason": "无配置渠道"})

        results = []
        all_success = True
        for ch in channels:
            try:
                result = await self._service.publish_to_channel(
                    channel_id=ch.get("id", 0),
                    platform=ch.get("platform", ""),
                    title=title, content=content,
                    credential_cipher=ch.get("credential_cipher", ""),
                    credential_type=ch.get("credential_type", "cookie"),
                )
                results.append({"channel_id": result.channel_id, "platform": result.platform,
                               "success": result.receipt.success})
                if not result.receipt.success:
                    all_success = False
            except Exception as exc:
                results.append({"error": str(exc)})
                all_success = False

        return StepResult(
            success=all_success,
            next_status=ArticleStatus.DONE.value if all_success else ArticleStatus.FAILED.value,
            detail={"published": results},
        )