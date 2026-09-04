"""HTTP 执行器：httpx 复用 Cookie/Header 请求级模拟（design 2.4.1）。"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import TraceLogger

logger = TraceLogger("http_exec")


class HttpExecutor:
    """HTTP 请求执行器。"""

    def __init__(self, timeout: int = 30):
        self._timeout = timeout

    async def request(
        self,
        method: str,
        url: str,
        *,
        cookies: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> httpx.Response:
        all_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        if headers:
            all_headers.update(headers)

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            resp = await client.request(
                method, url,
                cookies=cookies or {},
                headers=all_headers,
                json=json_body,
                data=data,
                files=files,
            )
            logger.info(f"HTTP {method} {url} -> {resp.status_code}")
            return resp