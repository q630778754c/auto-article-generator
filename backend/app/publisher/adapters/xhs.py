"""小红书适配器（笔记体裁，最复杂，design 2.4.2）。

图片先传后发时序；标题≤20字、正文≤1000字、图3~9张。
"""

from __future__ import annotations

from app.publisher.base import (
    PlatformAdapter, PublishContent, PublishReceipt,
    HealthStatus, PlatformConfig, OauthCredential, CookieCredential,
)
from app.publisher.executors.http_executor import HttpExecutor
from app.publisher.executors.playwright_executor import PlaywrightExecutor
from app.core.logging import TraceLogger

logger = TraceLogger("xhs")


class XhsAdapter(PlatformAdapter):
    platform = "xhs"

    def __init__(self, use_browser: bool = False):
        self._http = HttpExecutor(timeout=30)
        self._pw = PlaywrightExecutor(timeout=30)
        self._use_browser = use_browser

    async def publish(self, content: PublishContent, credential: OauthCredential | CookieCredential) -> PublishReceipt:
        cfg = self.get_default_config()
        if len(content.title) > cfg.title_max:
            content.title = content.title[:cfg.title_max]
        if len(content.content) > cfg.content_max:
            content.content = content.content[:cfg.content_max]
        if len(content.images) < cfg.image_min:
            return PublishReceipt(success=False, fail_reason=f"小红书至少需要{cfg.image_min}张图片")

        if not isinstance(credential, CookieCredential):
            return PublishReceipt(success=False, fail_reason="小红书需要Cookie凭证")

        if self._use_browser and not self._pw.available:
            logger.warn("小红书声明需要浏览器但Playwright未安装，降级为HTTP")
            self._use_browser = False

        try:
            image_ids = []
            for img in content.images:
                upload_id = await self._upload_image(img, credential)
                if upload_id:
                    image_ids.append(upload_id)

            if not image_ids:
                return PublishReceipt(success=False, fail_reason="图片上传全部失败")

            resp = await self._http.request(
                "POST", "https://edith.xiaohongshu.com/api/sns/web/v1/feed",
                cookies=credential.cookies, headers=credential.headers,
                json_body={"title": content.title, "desc": content.content, "image_ids": image_ids, "tags": content.tags},
            )
            data = resp.json()
            if data.get("success"):
                item = data.get("data", {})
                return PublishReceipt(success=True, platform_article_id=str(item.get("note_id", "")), platform_url=f"https://www.xiaohongshu.com/discovery/item/{item.get('note_id', '')}")
            return PublishReceipt(success=False, fail_reason=data.get("msg", "未知错误"), raw_response=data)
        except Exception as exc:
            return PublishReceipt(success=False, fail_reason=str(exc))

    async def _upload_image(self, image: bytes, credential: CookieCredential) -> str:
        try:
            resp = await self._http.request(
                "POST", "https://edith.xiaohongshu.com/api/sns/web/v1/upload",
                cookies=credential.cookies, headers=credential.headers,
                files={"file": image},
            )
            data = resp.json()
            return str(data.get("data", {}).get("file_id", ""))
        except Exception:
            return ""

    async def check_health(self, credential: OauthCredential | CookieCredential) -> HealthStatus:
        if not isinstance(credential, CookieCredential) or not credential.cookies:
            return HealthStatus(healthy=False, status="credential_expired")
        return HealthStatus(healthy=True)

    async def query_by_title(self, title: str, credential: OauthCredential | CookieCredential) -> PublishReceipt | None:
        return None

    def get_default_config(self) -> PlatformConfig:
        return PlatformConfig(title_max=20, content_max=1000, image_min=3, image_max=9, tags_max=10, requires_browser=False)