"""改写服务：RewriteService / WordCalibrator / TitleGuard（spec 5.2.1）。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.ai.llm_provider import LLMProvider, LLMMessage, LLMOptions, LLMResponse
from app.ai.prompts.rewrite_body import render as render_body
from app.ai.prompts.rewrite_title import render as render_title, SENSATIONAL_BLACKLIST
from app.collector.fingerprint import digest
from app.collector.topic_filter import screen
from app.core.logging import TraceLogger

logger = TraceLogger("rewrite")


@dataclass
class RewriteDraft:
    title: str
    content: str
    fingerprint: str
    model_used: str
    style: str
    word_count: int = 0
    hit_violation: bool = False
    violation_rule: str = ""


class TitleGuard:
    """标题守卫：夸大词黑名单命中重新生成。"""

    @staticmethod
    def contains_sensational(title: str) -> str | None:
        for word in SENSATIONAL_BLACKLIST:
            if word in title:
                return word
        return None

    @staticmethod
    def truncate(title: str, max_len: int) -> str:
        return title[:max_len] if len(title) > max_len else title


class WordCalibrator:
    """字数校准器：800~2000字校验。"""

    @staticmethod
    def check_range(content: str, word_min: int = 800, word_max: int = 2000) -> tuple[bool, str]:
        count = len(content)
        if count < word_min:
            return False, "too_short"
        if count > word_max:
            return False, "too_long"
        return True, "ok"

    @staticmethod
    def word_count(content: str) -> int:
        return len(content)


class RewriteService:
    """改写环节业务服务。"""

    def __init__(self, provider: LLMProvider, model: str = "deepseek-chat"):
        self._provider = provider
        self._model = model

    async def rewrite_article(
        self, *, source_title: str, source_content: str, style: str = "casual",
        word_min: int = 800, word_max: int = 2000,
    ) -> RewriteDraft:
        prompt = render_body(
            style=style, word_min=word_min, word_max=word_max,
            source_title=source_title, source_content=source_content,
        )
        messages = [LLMMessage(role="system", content=prompt), LLMMessage(role="user", content="请改写。")]
        opts = LLMOptions(temperature=0.7, max_tokens=4096, timeout_sec=120, response_format_json=True)

        resp = await self._provider.chat(messages, opts)
        data = resp.parse_json()

        title = data.get("title", source_title)
        content = data.get("content", "")

        title = TitleGuard.truncate(title, 30)
        fp = digest(title, content)
        word_count = WordCalibrator.word_count(content)

        hit_word = TitleGuard.contains_sensational(title)
        violation = False
        violation_rule = ""
        if hit_word:
            violation = True
            violation_rule = hit_word
        else:
            filter_result = screen(title, content)
            if not filter_result.passed:
                violation = True
                violation_rule = filter_result.rule_name

        return RewriteDraft(
            title=title, content=content, fingerprint=fp,
            model_used=self._model, style=style, word_count=word_count,
            hit_violation=violation, violation_rule=violation_rule,
        )

    async def rewrite_title(self, source_title: str, max_len: int = 30) -> str:
        prompt = render_title(source_title=source_title, max_len=max_len)
        messages = [LLMMessage(role="system", content=prompt), LLMMessage(role="user", content="请改写标题。")]
        opts = LLMOptions(temperature=0.5, max_tokens=100, timeout_sec=60)

        resp = await self._provider.chat(messages, opts)
        title = resp.content.strip()
        return TitleGuard.truncate(title, max_len)