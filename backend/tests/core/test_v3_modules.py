"""v3 新增模块单元测试。"""

import asyncio
import pytest

from app.core.exceptions import (
    UnifiedPlatformError, ApiKeyInvalidError, ApiKeyExpiredError,
    ApiKeyDisabledError, RateLimitError, PermissionDeniedError,
)
from app.core.token_cache import TokenCache
from app.core.api_key_limiter import ApiKeyRateLimiter


class TestExceptions:
    def test_unified_platform_error(self):
        e = UnifiedPlatformError("timeout")
        assert e.code == 6003
        assert e.http_status == 503

    def test_api_key_invalid_error(self):
        e = ApiKeyInvalidError()
        assert e.code == 1003
        assert e.http_status == 401

    def test_api_key_expired_error(self):
        e = ApiKeyExpiredError()
        assert e.code == 1004
        assert e.http_status == 401

    def test_api_key_disabled_error(self):
        e = ApiKeyDisabledError()
        assert e.code == 1005
        assert e.http_status == 401

    def test_rate_limit_error(self):
        e = RateLimitError(retry_after=30)
        assert e.code == 6004
        assert e.http_status == 429
        assert e.retry_after == 30
        assert e.data == {"retry_after": 30}

    def test_permission_denied_error(self):
        e = PermissionDeniedError()
        assert e.code == 1006
        assert e.http_status == 403

    def test_to_response(self):
        e = RateLimitError("too fast", retry_after=10)
        resp = e.to_response()
        assert resp["code"] == 6004
        assert "too fast" in resp["message"]
        assert resp["data"] == {"retry_after": 10}


class TestTokenCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = TokenCache(ttl=60, capacity=100)
        await cache.set("token123", {"username": "test"})
        result = await cache.get("token123")
        assert result is not None
        assert result["username"] == "test"

    @pytest.mark.asyncio
    async def test_get_miss(self):
        cache = TokenCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        cache = TokenCache(ttl=0, capacity=100)
        await cache.set("token", {"user": "test"})
        await asyncio.sleep(0.01)
        result = await cache.get("token")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self):
        cache = TokenCache()
        await cache.set("token", {"user": "test"})
        await cache.invalidate("token")
        result = await cache.get("token")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = TokenCache()
        await cache.set("t1", {"u": 1})
        await cache.set("t2", {"u": 2})
        await cache.clear()
        assert await cache.get("t1") is None
        assert await cache.get("t2") is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        cache = TokenCache(ttl=60, capacity=2)
        await cache.set("t1", {"u": 1})
        await cache.set("t2", {"u": 2})
        await cache.set("t3", {"u": 3})
        assert await cache.get("t1") is None
        assert await cache.get("t2") is not None
        assert await cache.get("t3") is not None


class TestApiKeyRateLimiter:
    @pytest.mark.asyncio
    async def test_check_rate_allowed(self):
        limiter = ApiKeyRateLimiter()
        allowed, retry = await limiter.check_rate(1, 10)
        assert allowed is True
        assert retry == 0

    @pytest.mark.asyncio
    async def test_check_rate_exceeded(self):
        limiter = ApiKeyRateLimiter()
        for _ in range(3):
            await limiter.check_rate(1, 3)
        allowed, retry = await limiter.check_rate(1, 3)
        assert allowed is False
        assert retry > 0

    @pytest.mark.asyncio
    async def test_concurrency_acquire_release(self):
        limiter = ApiKeyRateLimiter()
        acquired = await limiter.acquire_concurrency(1, 2)
        assert acquired is True
        acquired2 = await limiter.acquire_concurrency(1, 2)
        assert acquired2 is True
        acquired3 = await limiter.acquire_concurrency(1, 2)
        assert acquired3 is False
        await limiter.release_concurrency(1)
        acquired4 = await limiter.acquire_concurrency(1, 2)
        assert acquired4 is True
        await limiter.release_concurrency(1)
        await limiter.release_concurrency(1)