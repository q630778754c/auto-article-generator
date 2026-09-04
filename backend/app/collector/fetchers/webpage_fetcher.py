"""网页栏目抓取器：httpx + BeautifulSoup4（spec 5.1.1）。

selectolax 替换为 lxml + beautifulsoup4（Python 3.14 兼容）。
"""

from __future__ import annotations

from bs4 import BeautifulSoup
import httpx

from app.collector.fetchers.base import SourceFetcher, RawItem
from app.core.logging import TraceLogger

logger = TraceLogger("web_fetch")


class WebPageFetcher(SourceFetcher):
    async def fetch(self, source_url: str, fetch_rules: dict | None = None, since: str = "") -> list[RawItem]:
        rules = fetch_rules or {}
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(source_url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                html = resp.text

            soup = BeautifulSoup(html, "lxml")
            items: list[RawItem] = []

            item_selector = rules.get("item_selector", "article, .item, .news-item")
            title_selector = rules.get("title_selector", "h2, h3, .title")
            link_selector = rules.get("link_selector", "a")
            content_selector = rules.get("content_selector", "p, .summary")

            for element in soup.select(item_selector):
                title_el = element.select_one(title_selector)
                link_el = element.select_one(link_selector)
                title = title_el.get_text(strip=True) if title_el else ""
                url = link_el.get("href", "") if link_el else ""
                if url and not url.startswith("http"):
                    url = source_url.rstrip("/") + "/" + url.lstrip("/")

                content = ""
                for p in element.select(content_selector):
                    content += p.get_text(strip=True) + " "

                if title and url:
                    items.append(RawItem(title=title, content=content.strip(), url=url))

            logger.info(f"网页抓取 source={source_url} count={len(items)}")
            return items
        except Exception as exc:
            logger.error(f"网页抓取失败 source={source_url} error={exc}")
            return []