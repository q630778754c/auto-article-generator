"""抓取器抽象与数据结构（design 2.2.1）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawItem:
    """抓取到的原始素材条目。"""
    title: str
    content: str
    url: str
    origin_published_at: str = ""
    images: list[str] = field(default_factory=list)


class SourceFetcher(ABC):
    """抓取器抽象接口。"""

    @abstractmethod
    async def fetch(self, source_url: str, fetch_rules: dict | None = None, since: str = "") -> list[RawItem]:
        ...