"""统一平台 HTTP 客户端（spec 4.3.2 / design 2.2.1）。

封装 httpx.AsyncClient，自动注入 app_id/app_secret，超时 5s，HTTPS 强制。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import UnifiedPlatformBizError, UnifiedPlatformError

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
            logger.error("unified_platform POST %s status=%d body=%s app_id=%s", path, resp.status_code, resp.text[:500], "SET" if self._app_id else "EMPTY")
            self._raise_for_status(resp)
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
            logger.error("unified_platform GET %s status=%d body=%s app_id=%s", path, resp.status_code, resp.text[:500], "SET" if self._app_id else "EMPTY")
            self._raise_for_status(resp)
        data = resp.json()
        if not isinstance(data, dict):
            raise UnifiedPlatformError("统一平台响应格式异常")
        return data

    @staticmethod
    def _platform_message(text: str) -> str:
        """从统一平台响应体提取人类可读的错误消息。

        平台错误体形如 {"success":false,"message":"验证码错误或已过期"}，
        直接透出原始 JSON 会让前端无法判断真实原因。
        """
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                for key in ("message", "detail", "error"):
                    val = obj.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
        except (ValueError, TypeError):
            pass
        return text.strip()[:200] or "未知错误"

    @staticmethod
    def decode_platform_jwt(token: str) -> dict[str, Any] | None:
        """解码统一平台 JWT（HS256 自包含）并校验 exp，返回 payload 或 None。

        统一平台不提供 token 校验端点（/verify-token 恒返回 401 未授权），
        只能本地解码 payload 提取用户身份。无法校验签名，属于已知妥协：
        攻击者可伪造结构合法但无法获得平台写权限的 token。
        """
        import base64
        import binascii

        parts = token.split(".")
        if len(parts) != 3:
            return None

        def _b64(seg: str) -> bytes:
            return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))

        try:
            payload = json.loads(_b64(parts[1]))
        except (ValueError, TypeError, binascii.Error):
            return None
        if not isinstance(payload, dict):
            return None
        exp = payload.get("exp")
        if isinstance(exp, (int, float)) and time.time() > float(exp):
            return None
        if not (payload.get("email") or payload.get("id")):
            return None
        return payload

    @staticmethod
    def jwt_ttl(token: str) -> int | None:
        """平台 JWT 剩余有效期（秒），解析失败返回 None。"""
        payload = UnifiedPlatformClient.decode_platform_jwt(token)
        if not payload:
            return None
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return None
        return max(60, int(float(exp) - time.time()))

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        """按 HTTP 状态码分级抛错：4xx 是业务校验失败，5xx 才是服务故障。"""
        detail = UnifiedPlatformClient._platform_message(resp.text)
        if 400 <= resp.status_code < 500:
            raise UnifiedPlatformBizError(f"认证平台返回：{detail}")
        raise UnifiedPlatformError(f"认证平台服务异常（HTTP {resp.status_code}）：{detail}")

    @staticmethod
    def _check_success(data: dict[str, Any]) -> dict[str, Any]:
        code = data.get("code")
        success = data.get("success")
        msg = data.get("message", "")
        if code in (0, 200, "0", "200"):
            return data.get("data", data)
        if success is True:
            return data.get("data", data)
        if "成功" in msg or "success" in msg.lower() or "ok" == msg.lower():
            return data.get("data", data)
        # HTTP 200 但业务失败（如 {"success":false,"message":"邮箱已注册"}）：
        # 必须当业务错误处理，否则会被前端当成"服务不可用"而丢失真实原因。
        raise UnifiedPlatformBizError(msg or "认证平台校验失败")

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