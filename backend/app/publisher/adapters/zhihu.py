"""知乎适配器（Cookie会话型，design 2.4.2）。"""

from __future__ import annotations

from app.publisher.base import (
    PlatformAdapter, PublishContent, PublishReceipt,
    HealthStatus, PlatformConfig, OauthCredential, CookieCredential,
)
from app.publisher.executors.http_executor import HttpExecutor


class ZhihuAdapter(PlatformAdapter):
    platform = "zhihu"

    def __init__(self):
        self._http = HttpExecutor(timeout=30)

    async def publish(self, content: PublishContent, credential: OauthCredential | CookieCredential) -> PublishReceipt:
        cfg = self.get_default_config()
        if len(content.title) > cfg.title_max:
            content.title = content.title[:cfg.title_max]
        if not isinstance(credential, CookieCredential):
            return PublishReceipt(success=False, fail_reason="知乎需要Cookie凭证")
        try:
            resp = await self._http.request(
                "POST", "https://zhuanlan.zhihu.com/api/articles",
                cookies=credential.cookies, headers=credential.headers,
                json_body={"title": content.title, "content": content.content, "column": None},
            )
            data = resp.json()
            if resp.status_code == 200 and "id" in data:
                return PublishReceipt(success=True, platform_article_id=str(data["id"]), platform_url=f"https://zhuanlan.zhihu.com/p/{data['id']}")
            return PublishReceipt(success=False, fail_reason=data.get("error", {}).get("message", "未知错误"), raw_response=data)
        except Exception as exc:
            return PublishReceipt(success=False, fail_reason=str(exc))

    async def check_health(self, credential: OauthCredential | CookieCredential) -> HealthStatus:
        if not isinstance(credential, CookieCredential) or not credential.cookies:
            return HealthStatus(healthy=False, status="credential_expired")
        try:
            resp = await self._http.request("GET", "https://www.zhihu.com/api/v4/me", cookies=credential.cookies, headers=credential.headers)
            return HealthStatus(healthy=resp.status_code == 200)
        except Exception:
            return HealthStatus(healthy=False, status="credential_expired")

    async def query_by_title(self, title: str, credential: OauthCredential | CookieCredential) -> PublishReceipt | None:
        return None

    def get_default_config(self) -> PlatformConfig:
        return PlatformConfig(title_max=100, content_max=50000, image_min=0, image_max=9, tags_max=5)