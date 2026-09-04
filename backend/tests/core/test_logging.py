"""core/logging 单测。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.core.logging import (
    mask_sensitive,
    set_trace_id,
    get_trace_id,
    TraceLogger,
    setup_logging,
    utcnow_iso,
)


class TestMaskSensitive:
    def test_api_key(self):
        text = "api_key=sk-abcdefgh12345678"
        masked = mask_sensitive(text)
        assert "sk-abcdefgh12345678" not in masked
        assert "****" in masked

    def test_password(self):
        text = "password=mySecretPass123"
        masked = mask_sensitive(text)
        assert "mySecretPass123" not in masked

    def test_bearer_token(self):
        text = "authorization=abc123def456"
        masked = mask_sensitive(text)
        assert "abc123def456" not in masked

    def test_sk_prefix(self):
        text = "using sk-ABCDEFGHIJKLMN token"
        masked = mask_sensitive(text)
        assert "sk-ABCDEFGHIJKLMN" not in masked

    def test_empty(self):
        assert mask_sensitive("") == ""

    def test_no_sensitive(self):
        text = "这是一条普通日志消息"
        assert mask_sensitive(text) == text


class TestTraceId:
    def test_set_get(self):
        token = set_trace_id("trace-abc-123")
        assert get_trace_id() == "trace-abc-123"
        set_trace_id("-")  # reset

    def test_default(self):
        set_trace_id("-")
        assert get_trace_id() == "-"


class TestTraceLogger:
    def test_info(self, capsys):
        setup_logging(level="INFO")
        logger = TraceLogger("test_step")
        logger.info("测试消息")
        captured = capsys.readouterr()
        assert "测试消息" in captured.out

    def test_step_in_output(self, capsys):
        setup_logging(level="DEBUG")
        logger = TraceLogger("my_step")
        logger.debug("debug消息")
        captured = capsys.readouterr()
        assert "my_step" in captured.out


class TestSetupLogging:
    def test_idempotent(self, tmp_path):
        setup_logging(log_dir=tmp_path, level="INFO")
        setup_logging(log_dir=tmp_path, level="DEBUG")
        # 不崩溃即通过

    def test_creates_log_dir(self, tmp_path):
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=log_dir, level="INFO")
        assert log_dir.exists()


class TestUtcnowIso:
    def test_format(self):
        ts = utcnow_iso()
        assert "T" in ts
        assert "+" in ts or "Z" in ts