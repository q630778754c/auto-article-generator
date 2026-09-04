"""百家号适配器（开放API型，design 2.4.2）。"""

from __future__ import annotations

from app.publisher.base import (
    PlatformAdapter, PublishContent, PublishReceipt,
    HealthStatus, PlatformConfig, OauthCredential, CookieCredential,
)
from app.publisher.executors.http_executor import HttpExecutor


class BaijiahaoAdapter(PlatformAdapter):
    platform = "baijiahao"

    def __init__(self):
        self._http = HttpExecutor(timeout=30)

    async def publish(self, content: PublishContent, credential: OauthCredential | CookieCredential) -> PublishReceipt:
        cfg = self.get_default_config()
        if len(content.title) > cfg.title_max:
            content.title = content.title[:cfg.title_max]
        if isinstance(credential, OauthCredential):
            headers = {"Authorization": f"Bearer {credential.access_token}"}
        else:
            headers = credential.headers
        try:
            resp = await self._http.request(
                "POST", "https://baijiahao.baidu.com/builder/rc-api/article/submit",
                headers=headers, json_body={"title": content.title, "content": content.content},
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("errno") == 0:
                item = data.get("data", {})
                return PublishReceipt(success=True, platform_article_id=str(item.get("article_id", "")), platform_url=item.get("url", ""))
            return PublishReceipt(success=False, fail_reason=data.get("errmsg", "未知错误"), raw_response=data)
        except Exception as exc:
            return PublishReceipt(success=False, fail_reason=str(exc))

    async def check_health(self, credential: OauthCredential | CookieCredential) -> HealthStatus:
        if isinstance(credential, OauthCredential) and credential.access_token:
            return HealthStatus(healthy=True)
        return HealthStatus(healthy=False, status="credential_expired")

    async def query_by_title(self, title: str, credential: OauthCredential | CookieCredential) -> PublishReceipt | None:
        return None

    def get_default_config(self) -> PlatformConfig:
        return PlatformConfig(title_max=30, content_max=50000, image_min=0, image_max=9, tags_max=5)