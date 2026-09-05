"""认证依赖：双通道 Bearer Token 校验（spec 4.3.3 / design 2.2.3）。

local- 前缀 Token → admin 本地验证；其他 Token → 统一平台验证 + TokenCache。
"""

from __future__ import annotations

import logging

from fastapi import Depends, Header, Request

from app.core.exceptions import AuthError, InvalidTokenError, UnifiedPlatformError

logger = logging.getLogger(__name__)

LOCAL_TOKEN_PREFIX = "local-"


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """从 Bearer Token 解析当前用户（双通道鉴权）。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("未登录或登录已失效")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AuthError("Token不能为空")

    if token.startswith(LOCAL_TOKEN_PREFIX):
        return {"username": "admin", "token": token, "token_type": "local"}

    from app.core.token_cache import get_token_cache
    cache = get_token_cache()
    cached = await cache.get(token)
    if cached is not None:
        return {"username": cached.get("username", cached.get("email", "")), "token": token, "token_type": "platform", "user_info": cached}

    from app.core.unified_platform import get_unified_platform_client
    client = get_unified_platform_client()
    try:
        user_info = await client.verify_token(token)
    except UnifiedPlatformError:
        raise
    except Exception as exc:
        logger.warning("verify_token unexpected error: %s", type(exc).__name__)
        raise UnifiedPlatformError("统一平台服务不可用") from exc

    if not user_info:
        raise InvalidTokenError()

    await cache.set(token, user_info)
    username = user_info.get("username", user_info.get("email", ""))
    return {"username": username, "token": token, "token_type": "platform", "user_info": user_info}


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """要求管理员角色（local Token 视为 admin）。"""
    if user.get("token_type") == "local":
        return user
    user_info = user.get("user_info", {})
    role = user_info.get("role", user_info.get("is_admin", ""))
    if role in ("admin", True, "true", 1):
        return user
    from app.core.exceptions import PermissionDeniedError
    raise PermissionDeniedError("需要管理员权限")


_SCOPE_PATH_MAP = {
    "rss_only": {"/api/v1/open/collector/rss"},
    "webpage_only": {"/api/v1/open/collector/webpage"},
    "all_collector": {
        "/api/v1/open/collector/rss",
        "/api/v1/open/collector/webpage",
        "/api/v1/open/collector/fingerprint",
        "/api/v1/open/collector/filter",
    },
}


async def get_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    """从 X-API-Key 头验证 API Key（spec 4.3.4）。"""
    from app.core.exceptions import (
        ApiKeyInvalidError, ApiKeyDisabledError, ApiKeyExpiredError,
        PermissionDeniedError, RateLimitError,
    )
    from app.core.api_key_service import get_api_key_service
    from app.core.api_key_limiter import get_api_key_limiter
    from app.core.config import get_snapshot

    if not x_api_key:
        raise ApiKeyInvalidError("缺少 API Key")

    service = get_api_key_service()
    record = await service.verify(x_api_key)
    if record is None:
        raise ApiKeyInvalidError()

    if not record.enabled:
        raise ApiKeyDisabledError()

    if record.expires_at:
        from datetime import datetime, timezone
        try:
            exp = datetime.fromisoformat(record.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                raise ApiKeyExpiredError()
        except ValueError:
            pass

    allowed_paths = _SCOPE_PATH_MAP.get(record.scope, set())
    request_path = request.url.path
    if request_path and request_path not in allowed_paths:
        raise PermissionDeniedError(f"API Key 权限范围 {record.scope} 不允许访问此端点")

    limiter = get_api_key_limiter()
    allowed, retry_after = await limiter.check_rate(record.id, record.rate_limit)
    if not allowed:
        raise RateLimitError(f"API Key 调用频率超限，请 {retry_after} 秒后重试", retry_after=retry_after)

    snapshot = get_snapshot()
    max_concurrent = snapshot.get_int("api_key_config.max_concurrent", 5)
    acquired = await limiter.acquire_concurrency(record.id, max_concurrent)
    if not acquired:
        raise RateLimitError("API Key 并发数超限", retry_after=5)

    return {"api_key": record, "api_key_id": record.id}
