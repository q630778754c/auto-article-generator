"""Playwright 执行器：可选浏览器兜底（ADR-006）。

未安装 Playwright 时，调用方应标记渠道异常并告警，不阻塞其他渠道。
"""

from __future__ import annotations

from typing import Any

from app.core.logging import TraceLogger

logger = TraceLogger("pw_exec")

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


class PlaywrightExecutor:
    """浏览器执行器（可选依赖）。"""

    def __init__(self, timeout: int = 30):
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return _PLAYWRIGHT_AVAILABLE

    async def request(
        self,
        method: str,
        url: str,
        *,
        cookies: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装，请运行: pip install playwright && playwright install chromium")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()

            if cookies:
                await context.add_cookies(cookies)

            page = await context.new_page()
            if json_body and method.upper() == "POST":
                resp = await page.request.post(url, data=json_body, headers=headers or {})
            else:
                resp = await page.request.get(url, headers=headers or {})

            result = {
                "status": resp.status,
                "body": await resp.text(),
                "headers": dict(resp.headers),
            }
            await browser.close()
            return result