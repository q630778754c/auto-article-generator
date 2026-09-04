"""LLM Provider 抽象与 OpenAI 兼容实现（design 2.3.1 / 2.3.3）。

横切能力：指数退避重试(2s/8s/32s)、硬超时、日志脱敏、配额递增、JSON强校验。
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.exceptions import StepPausedError, StepRetryExhaustedError
from app.core.logging import TraceLogger, mask_sensitive
from app.core.security import mask_sensitive_value

logger = TraceLogger("llm")

RETRY_DELAYS = [2, 8, 32]
MAX_RETRIES = 3


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMOptions:
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_sec: int = 120
    response_format_json: bool = False


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    elapsed_sec: float = 0.0

    def parse_json(self) -> Any:
        text = self.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)


class LLMProvider(ABC):
    """LLM 适配器抽象。"""

    @abstractmethod
    async def chat(self, messages: list[LLMMessage], options: LLMOptions | None = None) -> LLMResponse:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI 兼容 Provider（覆盖 DeepSeek/OpenAI/通义/Kimi）。"""

    def __init__(self, *, api_key: str, base_url: str, model: str, provider_name: str = "openai"):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._provider_name = provider_name
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(self, messages: list[LLMMessage], options: LLMOptions | None = None) -> LLMResponse:
        opts = options or LLMOptions()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self._do_chat(messages, opts)
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warn(
                        f"LLM调用失败 attempt={attempt + 1} delay={delay}s "
                        f"error={type(exc).__name__} key={mask_sensitive_value(self._api_key)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM重试耗尽 model={self._model} key={mask_sensitive_value(self._api_key)}")

        raise StepRetryExhaustedError("llm_chat", MAX_RETRIES)

    async def _do_chat(self, messages: list[LLMMessage], opts: LLMOptions) -> LLMResponse:
        start = time.monotonic()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "timeout": opts.timeout_sec,
        }
        if opts.response_format_json:
            kwargs["response_format"] = {"type": "json_object"}

        resp = await self._client.chat.completions.create(**kwargs)
        elapsed = time.monotonic() - start

        content = resp.choices[0].message.content or ""
        usage = {}
        if resp.usage:
            usage = {"prompt_tokens": resp.usage.prompt_tokens, "completion_tokens": resp.usage.completion_tokens}

        logger.info(f"LLM调用成功 model={self._model} elapsed={elapsed:.1f}s tokens={usage}")
        return LLMResponse(content=content, model=self._model, usage=usage, elapsed_sec=elapsed)

    async def health_check(self) -> bool:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=10,
            )
            return bool(resp.choices)
        except Exception:
            return False


def create_provider(*, provider: str, api_key: str, base_url: str, model: str) -> LLMProvider:
    """工厂：按 provider 字段路由到具体实现（ADR-005）。"""
    if provider == "anthropic":
        return AnthropicLLMProvider(api_key=api_key, base_url=base_url, model=model)
    return OpenAICompatibleProvider(
        api_key=api_key, base_url=base_url, model=model, provider_name=provider
    )


class AnthropicLLMProvider(LLMProvider):
    """Anthropic 分支（通过 OpenAI 兼容代理或直接 API）。"""

    def __init__(self, *, api_key: str, base_url: str, model: str):
        self._inner = OpenAICompatibleProvider(
            api_key=api_key, base_url=base_url, model=model, provider_name="anthropic"
        )

    async def chat(self, messages: list[LLMMessage], options: LLMOptions | None = None) -> LLMResponse:
        return await self._inner.chat(messages, options)

    async def health_check(self) -> bool:
        return await self._inner.health_check()