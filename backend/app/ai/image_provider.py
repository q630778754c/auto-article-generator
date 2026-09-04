"""ImageGenProvider 抽象与默认厂商实现（design 2.3.1）。

复用 llm_provider 的重试/超时/脱敏横切能力。
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.core.exceptions import StepRetryExhaustedError
from app.core.logging import TraceLogger
from app.core.security import mask_sensitive_value

logger = TraceLogger("image")

RETRY_DELAYS = [2, 8, 32]
MAX_RETRIES = 3


@dataclass
class ImageAsset:
    binary: bytes
    width_px: int = 0
    height_px: int = 0
    format: str = "jpg"
    model: str = ""
    prompt: str = ""


@dataclass
class ImageGenOptions:
    timeout_sec: int = 180
    size: str = "1024x1024"


class ImageGenProvider(ABC):
    """文生图适配器抽象。"""

    @abstractmethod
    async def generate(self, prompt: str, options: ImageGenOptions | None = None) -> ImageAsset:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class TongyiWanxiangProvider(ImageGenProvider):
    """通义万相 REST 封装（可配置切换火山方舟）。"""

    def __init__(self, *, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/api/v1"):
        self._api_key = api_key
        self._base_url = base_url

    async def generate(self, prompt: str, options: ImageGenOptions | None = None) -> ImageAsset:
        opts = options or ImageGenOptions()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self._do_generate(prompt, opts)
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[attempt]
                    logger.warn(f"配图失败 attempt={attempt + 1} delay={delay}s error={type(exc).__name__}")
                    await asyncio.sleep(delay)

        raise StepRetryExhaustedError("image_gen", MAX_RETRIES)

    async def _do_generate(self, prompt: str, opts: ImageGenOptions) -> ImageAsset:
        start = time.monotonic()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "wanxiang-v1",
            "input": {"prompt": prompt},
            "parameters": {"size": opts.size, "n": 1},
        }
        async with httpx.AsyncClient(timeout=opts.timeout_sec) as client:
            resp = await client.post(f"{self._base_url}/services/aigc/text2image/image-synthesis", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()

        image_url = data.get("output", {}).get("results", [{}])[0].get("url", "")
        if not image_url:
            raise ValueError("文生图返回无图片URL")

        async with httpx.AsyncClient(timeout=30) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            binary = img_resp.content

        elapsed = time.monotonic() - start
        logger.info(f"配图成功 elapsed={elapsed:.1f}s size={len(binary)}")
        return ImageAsset(binary=binary, model="wanxiang-v1", prompt=prompt)

    async def health_check(self) -> bool:
        return bool(self._api_key)


def create_image_provider(*, provider: str, api_key: str, base_url: str = "") -> ImageGenProvider:
    """工厂：按 provider 字段路由。"""
    return TongyiWanxiangProvider(api_key=api_key, base_url=base_url or "https://dashscope.aliyuncs.com/api/v1")