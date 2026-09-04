"""TraceID 结构化日志（spec 4.4.2 / 4.4.3）。

固定5字段：trace_id / step / status / timestamp / message。
敏感字段（凭证/密钥/cookie）出现即脱敏（spec 4.3.2）。
"""

from __future__ import annotations

import contextvars
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

_trace_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")

_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|apikey|token|secret|password|passwd|pwd)\s*[=:]\s*([^\s,;\"']+)"),
    re.compile(r"(?i)(cookie|set-cookie|authorization|bearer)\s*[=:]\s*([^\s,;\"']+)"),
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{8,}"),
]

_JSON_KEYWORDS = {"access_token", "api_key", "secret_key", "password", "cookie", "token"}


class _MaskingFilter:
    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir

    def __call__(self, record: dict[str, Any]) -> bool:
        message = record["message"]
        if isinstance(message, str):
            record["message"] = mask_sensitive(message)
        return True


def mask_sensitive(text: str) -> str:
    """对含凭证/密钥/cookie 的字符串打码。"""
    if not text:
        return text
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=****{m.group(2)[-4:]}" if m.lastindex else "****", text)
    return text


def _json_format(record: dict[str, Any]) -> str:
    payload = {
        "timestamp": record["time"].isoformat(timespec="milliseconds"),
        "trace_id": _trace_var.get(),
        "step": record["extra"].get("step", "-"),
        "status": record["level"].name.lower(),
        "message": record["message"],
    }
    return json.dumps(payload, ensure_ascii=False, default=str).replace("{", "{{").replace("}", "}}")


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    return _trace_var.set(trace_id)


def get_trace_id() -> str:
    return _trace_var.get()


def bind_step(step: str) -> None:
    logger.bind(step=step)


class TraceLogger:
    """面向业务代码的日志门面：自动注入 trace_id 与 step。"""

    def __init__(self, step: str = "-") -> None:
        self.step = step

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        extra = {"step": self.step, **kwargs}
        logger.bind(**extra).log(level.upper(), message)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("info", message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> None:
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("error", message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log("debug", message, **kwargs)


def setup_logging(log_dir: Path | None = None, level: str = "INFO") -> None:
    """初始化日志：控制台 + 按日滚动文件。幂等，可重复调用。"""
    logger.remove()
    logger.add(
        sys.stdout,
        format=_json_format,
        level=level.upper(),
        filter=_MaskingFilter(Path(log_dir or ".")),
    )
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            format=_json_format,
            level=level.upper(),
            filter=_MaskingFilter(log_dir),
            rotation="00:00",
            retention="180 days",
            encoding="utf-8",
        )


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")