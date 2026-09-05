"""爬虫开放 API 路由（spec 4.3.4 / design 2.5.2 D组）。

RSS 抓取、网页抓取、指纹计算、敏感词过滤 — 通过 X-API-Key 鉴权。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import get_api_key
from app.collector.fetchers.rss_fetcher import RssFetcher
from app.collector.fetchers.webpage_fetcher import WebPageFetcher
from app.collector.fingerprint import digest
from app.collector.topic_filter import screen
from app.core.exceptions import ParamError
from app.core.api_key_service import get_api_key_service
from app.core.api_key_limiter import get_api_key_limiter
from app.core.security import mask_sensitive_value
from app.models import ApiKeyCallLog
from app.core import database

logger = logging.getLogger(__name__)

router = APIRouter()

_rss_fetcher = RssFetcher()
_web_fetcher = WebPageFetcher()


class RssFetchRequest(BaseModel):
    url: str
    limit: int = Field(default=20, ge=1, le=100)
    skip_filter: bool = False


class WebpageFetchRequest(BaseModel):
    url: str
    fetch_rules: dict[str, Any] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    skip_filter: bool = False


class FingerprintRequest(BaseModel):
    items: list[dict[str, str]] = Field(min_length=1, max_length=500)


class FilterRequest(BaseModel):
    title: str
    content: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def _write_call_log(
    api_key_id: int,
    api_key_mask: str,
    endpoint: str,
    method: str,
    params: dict,
    status_code: int,
    latency_ms: int,
    result_count: int,
    error_message: str | None,
    client_ip: str,
) -> None:
    try:
        async with database.get_session() as s:
            s.add(ApiKeyCallLog(
                api_key_id=api_key_id,
                api_key_mask=api_key_mask,
                endpoint=endpoint,
                method=method,
                params_json=json.dumps(params, ensure_ascii=False)[:2000],
                status_code=status_code,
                latency_ms=latency_ms,
                result_count=result_count,
                error_message=error_message,
                client_ip=client_ip,
                created_at=_now(),
            ))
    except Exception as exc:
        logger.warning("write call log failed: %s", type(exc).__name__)


async def _process_items(items: list, limit: int, skip_filter: bool) -> tuple[list[dict], list[str]]:
    result = []
    fingerprints = []
    for item in items[:limit]:
        fp = digest(item.title, item.content)
        fingerprints.append(fp)
        entry = {
            "title": item.title,
            "content": item.content,
            "url": item.url,
            "origin_published_at": item.origin_published_at,
            "images": item.images,
            "fingerprint": fp,
        }
        if skip_filter:
            fr = screen(item.title, item.content)
            entry["filtered"] = not fr.passed
            if fr.passed:
                result.append(entry)
            else:
                entry["filter_reason"] = fr.rule_name
                result.append(entry)
        else:
            fr = screen(item.title, item.content)
            if fr.passed:
                result.append(entry)
            else:
                entry["filtered"] = True
                entry["filter_reason"] = fr.rule_name
    return result, fingerprints


@router.post("/rss")
async def fetch_rss(
    req: RssFetchRequest,
    request: Request,
    response: Response,
    key_ctx: dict = Depends(get_api_key),
):
    start = time.monotonic()
    api_key = key_ctx["api_key"]
    api_key_id = key_ctx["api_key_id"]
    key_mask = mask_sensitive_value(api_key.key_prefix + "****")
    client_ip = request.client.host if request.client else ""
    error_msg = None
    status_code = 200
    result_count = 0

    try:
        items = await _rss_fetcher.fetch(req.url)
        result, fingerprints = await _process_items(items, req.limit, req.skip_filter)
        result_count = len(result)
        data = {"items": result, "total": len(items), "fingerprints": fingerprints}
        return {"code": 0, "message": "ok", "data": data}
    except Exception as exc:
        error_msg = str(exc)
        status_code = 500
        logger.error("RSS open API error: %s", error_msg)
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        asyncio.create_task(_write_call_log(
            api_key_id, key_mask, "/api/v1/open/collector/rss", "POST",
            {"url": req.url, "limit": req.limit}, status_code, latency_ms,
            result_count, error_msg, client_ip,
        ))
        asyncio.create_task(get_api_key_service().increment_usage(api_key_id, success=(error_msg is None)))
        await get_api_key_limiter().release_concurrency(api_key_id)


@router.post("/webpage")
async def fetch_webpage(
    req: WebpageFetchRequest,
    request: Request,
    response: Response,
    key_ctx: dict = Depends(get_api_key),
):
    start = time.monotonic()
    api_key = key_ctx["api_key"]
    api_key_id = key_ctx["api_key_id"]
    key_mask = mask_sensitive_value(api_key.key_prefix + "****")
    client_ip = request.client.host if request.client else ""
    error_msg = None
    status_code = 200
    result_count = 0

    try:
        items = await _web_fetcher.fetch(req.url, req.fetch_rules)
        result, fingerprints = await _process_items(items, req.limit, req.skip_filter)
        result_count = len(result)
        data = {"items": result, "total": len(items), "fingerprints": fingerprints}
        return {"code": 0, "message": "ok", "data": data}
    except Exception as exc:
        error_msg = str(exc)
        status_code = 500
        logger.error("webpage open API error: %s", error_msg)
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        asyncio.create_task(_write_call_log(
            api_key_id, key_mask, "/api/v1/open/collector/webpage", "POST",
            {"url": req.url, "limit": req.limit}, status_code, latency_ms,
            result_count, error_msg, client_ip,
        ))
        asyncio.create_task(get_api_key_service().increment_usage(api_key_id, success=(error_msg is None)))
        await get_api_key_limiter().release_concurrency(api_key_id)


@router.post("/fingerprint")
async def calc_fingerprint(
    req: FingerprintRequest,
    key_ctx: dict = Depends(get_api_key),
):
    api_key_id = key_ctx["api_key_id"]
    try:
        fingerprints = []
        seen: dict[str, int] = {}
        deduped = []
        duplicates = []
        for i, item in enumerate(req.items):
            title = item.get("title", "")
            content = item.get("content", "")
            fp = digest(title, content)
            fingerprints.append(fp)
            if fp in seen:
                duplicates.append({"index": i, "fingerprint": fp, "title": title})
            else:
                seen[fp] = i
                deduped.append({"index": i, "fingerprint": fp, "title": title})
        return {
            "code": 0,
            "message": "ok",
            "data": {"fingerprints": fingerprints, "deduped": deduped, "duplicates": duplicates},
        }
    finally:
        await get_api_key_limiter().release_concurrency(api_key_id)


@router.post("/filter")
async def filter_content(
    req: FilterRequest,
    key_ctx: dict = Depends(get_api_key),
):
    api_key_id = key_ctx["api_key_id"]
    try:
        fr = screen(req.title, req.content)
        return {
            "code": 0,
            "message": "ok",
            "data": {"passed": fr.passed, "rule_name": fr.rule_name},
        }
    finally:
        await get_api_key_limiter().release_concurrency(api_key_id)