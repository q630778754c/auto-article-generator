"""PlatformAdapter 抽象与强类型凭证（design 2.4.1）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.security import Cipher


@dataclass
class OauthCredential:
    """OAuth 凭证（Token 型）。"""
    access_token: str
    refresh_token: str = ""
    expires_at: str = ""


@dataclass
class CookieCredential:
    """Cookie 会话凭证。"""
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class PublishContent:
    """待发布内容。"""
    title: str
    content: str
    images: list[bytes] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    cover_image: bytes | None = None


@dataclass
class PublishReceipt:
    """发布回执。"""
    success: bool
    platform_article_id: str = ""
    platform_url: str = ""
    audit_status: str = "pending"
    fail_reason: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """渠道健康状态。"""
    healthy: bool
    status: str = "normal"
    detail: str = ""


@dataclass
class PlatformConfig:
    """平台适配规格。"""
    title_max: int = 30
    content_max: int = 50000
    image_min: int = 0
    image_max: int = 9
    tags_max: int = 5
    requires_browser: bool = False


class PlatformAdapter(ABC):
    """平台适配器抽象。"""

    platform: str = ""

    @abstractmethod
    async def publish(self, content: PublishContent, credential: OauthCredential | CookieCredential) -> PublishReceipt:
        ...

    @abstractmethod
    async def check_health(self, credential: OauthCredential | CookieCredential) -> HealthStatus:
        ...

    @abstractmethod
    async def query_by_title(self, title: str, credential: OauthCredential | CookieCredential) -> PublishReceipt | None:
        ...

    @abstractmethod
    def get_default_config(self) -> PlatformConfig:
        ...

    def parse_credential(self, cipher_text: str, cipher: Cipher, cred_type: str) -> OauthCredential | CookieCredential:
        """解密并解析凭证为强类型对象。"""
        plaintext = cipher.decrypt(cipher_text)
        if cred_type == "oauth":
            import json
            data = json.loads(plaintext) if plaintext else {}
            return OauthCredential(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                expires_at=data.get("expires_at", ""),
            )
        else:
            import json
            data = json.loads(plaintext) if plaintext else {}
            return CookieCredential(
                cookies=data.get("cookies", {}),
                headers=data.get("headers", {}),
            )