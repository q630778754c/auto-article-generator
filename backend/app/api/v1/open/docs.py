"""爬虫开放 API 文档（spec 4.3.5 / design 2.5.2 E组）。

HTML 在线文档、Markdown 文档、OpenAPI 3.0 JSON、Swagger UI。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from app.core.config import get_settings

router = APIRouter()

_API_VERSION = "v3.0"
_DOC_UPDATED = datetime.now(timezone.utc).strftime("%Y-%m-%d")

_MARKDOWN = f"""# 爬虫开放 API 文档

> **版本**：{_API_VERSION}  **更新日期**：{_DOC_UPDATED}

## 概述

### 认证方式
所有开放 API 端点需通过 `X-API-Key` 请求头传递 API Key 进行认证。
API Key 可在管理平台的"API Key 管理"页面创建。

### 基础 URL
```
https://aag-api.loca.lt/api/v1/open
```

### 通用响应格式
```json
{{"code": 0, "message": "ok", "data": {{...}}}}
```
- `code=0` 表示成功，非 0 表示失败
- `message` 为用户可读的提示信息
- `data` 为业务数据

## API Key 获取流程
1. 登录管理平台
2. 进入"API Key 管理"页面
3. 点击"创建 API Key"
4. 填写名称、权限范围、速率限制、有效期
5. 创建成功后复制完整 Key 值（仅显示一次）

## 端点详情

### 1. RSS 抓取
`POST /collector/rss`

**请求参数**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | - | RSS 源地址 |
| limit | int | 否 | 20 | 返回条目上限（1-100）|
| skip_filter | bool | 否 | false | 是否跳过敏感词过滤 |

**响应**
```json
{{
  "code": 0, "message": "ok",
  "data": {{
    "items": [{{"title": "...", "content": "...", "url": "...", "fingerprint": "..."}}],
    "total": 15,
    "fingerprints": ["sha256hex", ...]
  }}
}}
```

**示例**
```bash
curl -X POST https://aag-api.loca.lt/api/v1/open/collector/rss \\
  -H "X-API-Key: ak-xxxxx" \\
  -H "Content-Type: application/json" \\
  -d '{{"url": "https://example.com/feed.xml", "limit": 10}}'
```

```python
import httpx
resp = httpx.post(
    "https://aag-api.loca.lt/api/v1/open/collector/rss",
    headers={{"X-API-Key": "ak-xxxxx"}},
    json={{"url": "https://example.com/feed.xml", "limit": 10}},
)
print(resp.json())
```

```javascript
const resp = await fetch('https://aag-api.loca.lt/api/v1/open/collector/rss', {{
  method: 'POST',
  headers: {{ 'X-API-Key': 'ak-xxxxx', 'Content-Type': 'application/json' }},
  body: JSON.stringify({{ url: 'https://example.com/feed.xml', limit: 10 }}),
}});
console.log(await resp.json());
```

### 2. 网页抓取
`POST /collector/webpage`

**请求参数**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | - | 网页地址 |
| fetch_rules | object | 否 | null | 抓取选择器配置 |
| limit | int | 否 | 20 | 返回条目上限（1-100）|
| skip_filter | bool | 否 | false | 是否跳过敏感词过滤 |

**fetch_rules 配置**
| 字段 | 默认值 | 说明 |
|------|--------|------|
| item_selector | `article, .item, .news-item` | 条目选择器 |
| title_selector | `h2, h3, .title` | 标题选择器 |
| link_selector | `a` | 链接选择器 |
| content_selector | `p, .summary` | 内容选择器 |

### 3. 指纹计算与去重
`POST /collector/fingerprint`

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| items | array | 是 | 待计算条目列表（1-500条）|

每条含 `title` 和 `content` 字段。

**响应**
```json
{{
  "code": 0, "message": "ok",
  "data": {{
    "fingerprints": ["sha256hex", ...],
    "deduped": [{{"index": 0, "fingerprint": "...", "title": "..."}}],
    "duplicates": [{{"index": 1, "fingerprint": "...", "title": "..."}}]
  }}
}}
```

### 4. 敏感词过滤
`POST /collector/filter`

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 标题 |
| content | string | 是 | 内容 |

**响应**
```json
{{"code": 0, "message": "ok", "data": {{"passed": true, "rule_name": ""}}}}
```

## 错误码说明
| HTTP状态码 | 触发场景 | 解决建议 |
|-----------|---------|---------|
| 400 | 参数错误 | 检查请求参数格式与范围 |
| 401 | API Key 缺失/无效/禁用/过期 | 检查 X-API-Key 头，确认 Key 有效 |
| 403 | 权限范围不足 | 使用具有对应权限的 API Key |
| 429 | 速率限制/并发超限 | 等待 Retry-After 秒后重试 |
| 502 | 抓取源不可达 | 检查目标 URL 是否可访问 |
| 504 | 抓取超时（30s）| 目标站点响应过慢，稍后重试 |
"""

_HTML_MD_ESCAPED = _MARKDOWN.replace("`", "\\`")

_HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>爬虫开放 API 文档 v{_API_VERSION}</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }}
h1 {{ color: #1890ff; }} h2 {{ color: #0066cc; margin-top: 32px; }} h3 {{ color: #0066cc; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f5f5; }} code, pre {{ background: #f6f8fa; padding: 2px 6px; border-radius: 3px; }}
pre {{ padding: 12px; overflow-x: auto; }} .version {{ color: #999; }}
</style>
</head>
<body>
<h1>爬虫开放 API 文档</h1>
<p class="version">版本 {_API_VERSION} · 更新日期 {_DOC_UPDATED}</p>
<div id="content"></div>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
const md = `{_HTML_MD_ESCAPED}`;
document.getElementById('content').innerHTML = marked.parse(md);
</script>
</body>
</html>
"""

_OPENAPI_JSON = {
    "openapi": "3.0.3",
    "info": {
        "title": "爬虫开放 API",
        "version": _API_VERSION,
        "description": "RSS/网页抓取、指纹计算、敏感词过滤开放 API",
    },
    "components": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            }
        }
    },
    "security": [{"ApiKeyAuth": []}],
    "paths": {
        "/collector/rss": {
            "post": {
                "summary": "RSS 抓取",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string", "description": "RSS 源地址"},
                                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                                    "skip_filter": {"type": "boolean", "default": False},
                                },
                                "required": ["url"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "抓取成功"}},
            }
        },
        "/collector/webpage": {
            "post": {
                "summary": "网页抓取",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "fetch_rules": {"type": "object"},
                                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                                    "skip_filter": {"type": "boolean", "default": False},
                                },
                                "required": ["url"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "抓取成功"}},
            }
        },
        "/collector/fingerprint": {
            "post": {
                "summary": "指纹计算与去重",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}}},
                                    }
                                },
                                "required": ["items"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "计算成功"}},
            }
        },
        "/collector/filter": {
            "post": {
                "summary": "敏感词过滤",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
                                "required": ["title", "content"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "过滤完成"}},
            }
        },
    },
}

_SWAGGER_HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>爬虫开放 API - Swagger UI</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({{
  url: '/api/v1/open/docs.json',
  dom_id: '#swagger-ui',
  presets: [SwaggerUIBundle.presets.apis],
  layout: 'BaseLayout',
}});
</script>
</body>
</html>
"""


@router.get("/docs", response_class=HTMLResponse)
async def get_html_docs():
    return HTMLResponse(content=_HTML)


@router.get("/docs.md", response_class=PlainTextResponse)
async def get_markdown_docs():
    return PlainTextResponse(content=_MARKDOWN, media_type="text/markdown")


@router.get("/docs.json", response_class=JSONResponse)
async def get_openapi_json():
    return JSONResponse(content=_OPENAPI_JSON)


@router.get("/docs/swagger", response_class=HTMLResponse)
async def get_swagger_ui():
    return HTMLResponse(content=_SWAGGER_HTML)