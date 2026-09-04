"""审核服务：ReviewService / SimilarityChecker / ReviewDecider（spec 5.4.1）。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.ai.llm_provider import LLMProvider, LLMMessage, LLMOptions
from app.ai.prompts.four_dim_review import render as render_review
from app.core.logging import TraceLogger

logger = TraceLogger("review")


@dataclass
class ReviewReport:
    compliance_result: str
    originality_score: int
    quality_score: int
    image_text_score: float
    similarity_score: float
    opinion: str = ""
    round_no: int = 1
    model_used: str = ""
    slop_dimensions: dict = None


@dataclass
class ReviewDecision:
    action: str  # pass / send_back / hard_block
    report: ReviewReport
    reason: str = ""


class SimilarityChecker:
    """本地相似度检测（difflib SequenceMatcher，零外部依赖）。"""

    @staticmethod
    def similarity(text1: str, text2: str) -> float:
        return SequenceMatcher(None, text1[:500], text2[:500]).ratio()


class ReviewDecider:
    """三分支决策器。"""

    @staticmethod
    def decide(
        report: ReviewReport,
        *,
        originality_threshold: int = 70,
        similarity_threshold: float = 0.30,
        quality_threshold: int = 70,
        image_text_threshold: float = 0.6,
    ) -> ReviewDecision:
        if report.compliance_result == "severe_violation":
            return ReviewDecision(action="hard_block", report=report, reason="合规严重违规")

        if report.originality_score < originality_threshold:
            return ReviewDecision(action="send_back", report=report, reason=f"原创度{report.originality_score}<{originality_threshold}")

        if report.similarity_score >= similarity_threshold:
            return ReviewDecision(action="send_back", report=report, reason=f"相似度{report.similarity_score:.2f}>={similarity_threshold}")

        if report.quality_score < quality_threshold:
            return ReviewDecision(action="send_back", report=report, reason=f"质量{report.quality_score}<{quality_threshold}")

        if report.image_text_score < image_text_threshold:
            return ReviewDecision(action="send_back", report=report, reason=f"图文一致{report.image_text_score:.2f}<{image_text_threshold}")

        return ReviewDecision(action="pass", report=report)


class ReviewService:
    """审核环节业务服务。"""

    def __init__(self, provider: LLMProvider, model: str = "deepseek-chat"):
        self._provider = provider
        self._model = model

    async def review(
        self, *, title: str, content: str, image_descriptions: list[str] | None = None,
        source_content: str = "", round_no: int = 1,
    ) -> ReviewDecision:
        prompt = render_review(title=title, content=content, image_descriptions=image_descriptions)
        messages = [LLMMessage(role="system", content=prompt), LLMMessage(role="user", content="请审核。")]
        opts = LLMOptions(temperature=0.3, max_tokens=2048, timeout_sec=60, response_format_json=True)

        resp = await self._provider.chat(messages, opts)
        data = resp.parse_json()

        similarity = SimilarityChecker.similarity(content, source_content) if source_content else 0.0

        report = ReviewReport(
            compliance_result=data.get("compliance_result", "fail"),
            originality_score=data.get("originality_score", 0),
            quality_score=data.get("quality_score", 0),
            image_text_score=data.get("image_text_score", 0.0),
            similarity_score=similarity,
            opinion=data.get("opinion", ""),
            round_no=round_no,
            model_used=self._model,
            slop_dimensions=data.get("slop_dimensions"),
        )

        decision = ReviewDecider.decide(report)
        logger.info(f"审核完成 round={round_no} action={decision.action} reason={decision.reason}")
        return decision