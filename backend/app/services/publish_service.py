"""发布服务：PublishService（spec 5.5.1）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.publisher.base import (
    PlatformAdapter, PublishContent, PublishReceipt,
    OauthCredential, CookieCredential,
)
from app.publisher.adapters import ADAPTERS
from app.core.security import Cipher
from app.core.logging import TraceLogger

logger = TraceLogger("publish")


@dataclass
class PublishResult:
    channel_id: int
    platform: str
    receipt: PublishReceipt
    fingerprint: str = ""


class PublishService:
    """发布环节业务服务。"""

    def __init__(self, cipher: Cipher):
        self._cipher = cipher
        self._adapters: dict[str, PlatformAdapter] = {}

    def _get_adapter(self, platform: str) -> PlatformAdapter:
        if platform not in self._adapters:
            cls = ADAPTERS.get(platform)
            if not cls:
                raise ValueError(f"不支持的平台: {platform}")
            self._adapters[platform] = cls()
        return self._adapters[platform]

    async def publish_to_channel(
        self, *, channel_id: int, platform: str,
        title: str, content: str, images: list[bytes] | None = None,
        credential_cipher: str = "", credential_type: str = "cookie",
        tags: list[str] | None = None,
    ) -> PublishResult:
        adapter = self._get_adapter(platform)
        credential = adapter.parse_credential(credential_cipher, self._cipher, credential_type)

        pub_content = PublishContent(
            title=title, content=content,
            images=images or [], tags=tags or [],
        )

        receipt = await adapter.publish(pub_content, credential)
        import hashlib
        fp = hashlib.sha256(f"{platform}:{title}:{content[:100]}".encode()).hexdigest()

        logger.info(f"发布 channel={channel_id} platform={platform} success={receipt.success}")
        return PublishResult(channel_id=channel_id, platform=platform, receipt=receipt, fingerprint=fp)

    async def check_channel_health(
        self, *, platform: str, credential_cipher: str, credential_type: str = "cookie",
    ):
        adapter = self._get_adapter(platform)
        credential = adapter.parse_credential(credential_cipher, self._cipher, credential_type)
        return await adapter.check_health(credential)