"""API Key 速率限制器：滑动窗口 + 并发信号量（spec 4.3.4 / design 2.4.3）。"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Any

_WINDOW_SECONDS = 60.0


class ApiKeyRateLimiter:
    """每 Key 滑动窗口速率限制 + 并发信号量控制。"""

    def __init__(self) -> None:
        self._windows: dict[int, deque[float]] = defaultdict(deque)
        self._concurrent: dict[int, int] = defaultdict(int)
        self._max_concurrent: dict[int, int] = {}
        self._lock = asyncio.Lock()

    async def check_rate(self, api_key_id: int, rate_limit: int) -> tuple[bool, int]:
        """检查滑动窗口内调用次数是否超限，返回 (allowed, retry_after)。"""
        now = time.monotonic()
        async with self._lock:
            dq = self._windows[api_key_id]
            while dq and dq[0] <= now - _WINDOW_SECONDS:
                dq.popleft()
            if len(dq) >= rate_limit:
                retry_after = int(_WINDOW_SECONDS - (now - dq[0])) + 1
                return False, max(retry_after, 1)
            dq.append(now)
            return True, 0

    async def acquire_concurrency(self, api_key_id: int, max_concurrent: int = 5) -> bool:
        """尝试获取并发槽位，非阻塞。"""
        async with self._lock:
            self._max_concurrent[api_key_id] = max_concurrent
            if self._concurrent[api_key_id] >= max_concurrent:
                return False
            self._concurrent[api_key_id] += 1
            return True

    async def release_concurrency(self, api_key_id: int) -> None:
        async with self._lock:
            if self._concurrent[api_key_id] > 0:
                self._concurrent[api_key_id] -= 1

    async def cleanup(self) -> None:
        """清理过期的滑动窗口时间戳。"""
        now = time.monotonic()
        async with self._lock:
            for key_id in list(self._windows.keys()):
                dq = self._windows[key_id]
                while dq and dq[0] <= now - _WINDOW_SECONDS:
                    dq.popleft()
                if not dq:
                    del self._windows[key_id]


_limiter: ApiKeyRateLimiter | None = None


def get_api_key_limiter() -> ApiKeyRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = ApiKeyRateLimiter()
    return _limiter