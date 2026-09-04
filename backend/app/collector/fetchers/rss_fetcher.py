"""RSS 抓取器：feedparser + httpx（spec 5.1.1）。"""

from __future__ import annotations

import feedparser
import httpx

from app.collector.fetchers.base import SourceFetcher, RawItem
from app.core.logging import TraceLogger

logger = TraceLogger("rss")


class RssFetcher(SourceFetcher):
    async def fetch(self, source_url: str, fetch_rules: dict | None = None, since: str = "") -> list[RawItem]:
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(source_url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                xml_data = resp.text

            feed = feedparser.parse(xml_data)
            items: list[RawItem] = []
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                content = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
                url = entry.get("link", "").strip()
                pub_date = entry.get("published", "")
                images = []
                if entry.get("media_content"):
                    images = [m.get("url", "") for m in entry.media_content if m.get("url")]
                if title and url:
                    items.append(RawItem(title=title, content=content, url=url, origin_published_at=pub_date, images=images))

            logger.info(f"RSS抓取 source={source_url} count={len(items)}")
            return items
        except Exception as exc:
            logger.error(f"RSS抓取失败 source={source_url} error={exc}")
            return []