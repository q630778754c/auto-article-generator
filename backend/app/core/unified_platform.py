"""统一平台 HTTP 客户端（spec 4.3.2 / design 2.2.1）。

封装 httpx.AsyncClient，自动注入 app_id/app_secret，超时 5s，HTTPS 强制。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import UnifiedPlatformError

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 15.0


class UnifiedPlatformClient:
    """统一平台 API 客户端，所有方法异步可调用。"""

    def __init__(self) -> None:
        s = get_settings()
        self._base_url = s.unified_platform_base_url.rstrip("/")
        self._app_id = s.unified_platform_app_id
        self._app_secret = s.unified_platform_app_secret
        if not self._base_url.startswith("https://"):
            raise UnifiedPlatformError(f"统一平台 base_url 必须为 HTTPS：{self._base_url}")
        logger.info("unified_platform init base_url=%s app_id=%s app_secret=%s", self._base_url, "SET" if self._app_id else "EMPTY", "SET" if self._app_secret else "EMPTY")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=5.0, pool=5.0),
                verify=True,
            )
        return self._client

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = {**payload, "app_id": self._app_id, "app_secret": self._app_secret}
        url = f"{self._base_url}{path}"
        start = time.monotonic()
        client = await self._get_client()
        try:
            resp = await client.post(url, json=body)
        except httpx.TimeoutException:
            logger.warning("unified_platform timeout path=%s", path)
            raise UnifiedPlatformError("统一平台响应超时，请稍后重试") from None
        except httpx.HTTPError as exc:
            logger.warning("unified_platform network error path=%s err=%s", path, type(exc).__name__)
            raise UnifiedPlatformError("统一平台网络异常") from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("unified_platform POST %s status=%d elapsed=%dms", path, resp.status_code, elapsed_ms)
        if resp.status_code != 200:
            body_preview = resp.text[:500]
            logger.error("unified_platform POST %s status=%d body=%s app_id=%s", path, resp.status_code, body_preview, "SET" if self._app_id else "EMPTY")
            raise UnifiedPlatformError(f"统一平台返回非 200：{resp.status_code}，详情：{body_preview}")
        data = resp.json()
        if not isinstance(data, dict):
            raise UnifiedPlatformError("统一平台响应格式异常")
        return data

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        query = dict(params or {})
        query["app_id"] = self._app_id
        query["app_secret"] = self._app_secret
        start = time.monotonic()
        client = await self._get_client()
        try:
            resp = await client.get(url, params=query)
        except httpx.TimeoutException:
            logger.warning("unified_platform timeout path=%s", path)
            raise UnifiedPlatformError("统一平台响应超时，请稍后重试") from None
        except httpx.HTTPError as exc:
            logger.warning("unified_platform network error path=%s err=%s", path, type(exc).__name__)
            raise UnifiedPlatformError("统一平台网络异常") from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("unified_platform GET %s status=%d elapsed=%dms", path, resp.status_code, elapsed_ms)
        if resp.status_code != 200:
            body_preview = resp.text[:500]
            logger.error("unified_platform GET %s status=%d body=%s app_id=%s", path, resp.status_code, body_preview, "SET" if self._app_id else "EMPTY")
            raise UnifiedPlatformError(f"统一平台返回非 200：{resp.status_code}，详情：{body_preview}")
        data = resp.json()
        if not isinstance(data, dict):
            raise UnifiedPlatformError("统一平台响应格式异常")
        return data

    @staticmethod
    def _check_success(data: dict[str, Any]) -> dict[str, Any]:
        if data.get("code") not in (0, 200, "0", "200"):
            msg = data.get("message", "统一平台操作失败")
            raise UnifiedPlatformError(msg)
        return data.get("data", data)

    async def send_code(self, email: str) -> dict[str, Any]:
        data = await self._post("/send-code", {"email": email})
        return self._check_success(data)

    async def register(self, email: str, code: str, password: str, nickname: str = "") -> dict[str, Any]:
        data = await self._post("/register", {"email": email, "code": code, "password": password, "nickname": nickname})
        return self._check_success(data)

    async def login(self, email: str, password: str) -> dict[str, Any]:
        data = await self._post("/login", {"email": email, "password": password})
        return self._check_success(data)

    async def verify_login(self, email: str, code: str) -> dict[str, Any]:
        data = await self._post("/verify-login", {"email": email, "code": code})
        return self._check_success(data)

    async def reset_password(self, email: str, code: str, new_password: str) -> dict[str, Any]:
        data = await self._post("/reset-password", {"email": email, "code": code, "new_password": new_password})
        return self._check_success(data)

    async def verify_token(self, token: str) -> dict[str, Any]:
        data = await self._post("/verify-token", {"token": token})
        return self._check_success(data)

    async def list_users(self, keyword: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        data = await self._get("/admin/users", {"keyword": keyword, "page": page, "page_size": page_size})
        return self._check_success(data)

    async def get_user(self, user_id: str) -> dict[str, Any]:
        data = await self._get(f"/admin/users/{user_id}")
        return self._check_success(data)

    async def update_user(self, user_id: str, **fields: Any) -> dict[str, Any]:
        data = await self._post(f"/admin/users/{user_id}", fields)
        return self._check_success(data)

    async def toggle_user(self, user_id: str, status: str) -> dict[str, Any]:
        data = await self._post(f"/admin/users/{user_id}/toggle", {"status": status})
        return self._check_success(data)

    async def unbind_user(self, user_id: str) -> dict[str, Any]:
        data = await self._post(f"/admin/users/{user_id}/unbind", {})
        return self._check_success(data)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


_client: UnifiedPlatformClient | None = None


def get_unified_platform_client() -> UnifiedPlatformClient:
    global _client
    if _client is None:
        _client = UnifiedPlatformClient()
    return _client