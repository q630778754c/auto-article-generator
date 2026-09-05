"""Token 验证缓存：内存 LRU + TTL（spec 4.3.2 / design 2.2.2）。

缓存键为 Token 的 SHA256 哈希值，TTL 60 秒，LRU 容量上限 1000 条。
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from typing import Any

_TTL_SECONDS = 60
_LRU_CAPACITY = 1000


class TokenCache:
    """内存 LRU + TTL 缓存，避免重复调用统一平台 verify-token。"""

    def __init__(self, ttl: int = _TTL_SECONDS, capacity: int = _LRU_CAPACITY) -> None:
        self._ttl = ttl
        self._capacity = capacity
        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def get(self, token: str) -> dict[str, Any] | None:
        key = self._hash_token(token)
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry["expire_at"]:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return entry["user_info"]

    async def set(self, token: str, user_info: dict[str, Any]) -> None:
        key = self._hash_token(token)
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = {"user_info": user_info, "expire_at": time.monotonic() + self._ttl}
            while len(self._store) > self._capacity:
                self._store.popitem(last=False)

    async def invalidate(self, token: str) -> None:
        key = self._hash_token(token)
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


_token_cache: TokenCache | None = None


def get_token_cache() -> TokenCache:
    global _token_cache
    if _token_cache is None:
        _token_cache = TokenCache()
    return _token_cache