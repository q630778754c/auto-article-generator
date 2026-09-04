"""抓取器包入口。"""

from app.collector.fetchers.base import SourceFetcher, RawItem
from app.collector.fetchers.rss_fetcher import RssFetcher
from app.collector.fetchers.webpage_fetcher import WebPageFetcher

__all__ = ["SourceFetcher", "RawItem", "RssFetcher", "WebPageFetcher"]