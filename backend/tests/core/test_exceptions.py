"""core/exceptions 单测：错误码分段 + to_response。"""

from __future__ import annotations

import pytest

from app.core.exceptions import (
    AppException,
    AuthError,
    InvalidTokenError,
    ParamError,
    ConfigError,
    ConfigInvalidValueError,
    PipelineError,
    StepPausedError,
    StepRetryExhaustedError,
    PublishError,
    ChannelLockedError,
    CredentialInvalidError,
    QuotaExceededError,
    SystemError,
    SourceUrlEmptyError,
    CredentialEmptyError,
    PlatformUnsupportedError,
)


class TestErrorCodeRanges:
    """错误码分段（design 2.5.1）：1xxx鉴权 2xxx参数 3xxx配置 4xxx流水线 5xxx发布 6xxx系统。"""

    def test_auth_range(self):
        assert 1000 <= AuthError().code < 2000
        assert 1000 <= InvalidTokenError().code < 2000

    def test_param_range(self):
        assert 2000 <= ParamError().code < 3000
        assert 2000 <= SourceUrlEmptyError().code < 3000
        assert 2000 <= CredentialEmptyError().code < 3000
        assert 2000 <= PlatformUnsupportedError("x").code < 3000

    def test_config_range(self):
        assert 3000 <= ConfigError().code < 4000
        assert 3000 <= ConfigInvalidValueError("k", "v").code < 4000

    def test_pipeline_range(self):
        assert 4000 <= PipelineError().code < 5000
        assert 4000 <= StepPausedError("rewrite", "fail").code < 5000
        assert 4000 <= StepRetryExhaustedError("rewrite", 3).code < 5000

    def test_publish_range(self):
        assert 5000 <= PublishError().code < 6000
        assert 5000 <= ChannelLockedError("头条").code < 6000
        assert 5000 <= CredentialInvalidError("知乎").code < 6000

    def test_system_range(self):
        assert 6000 <= SystemError().code < 7000
        assert 6000 <= QuotaExceededError("llm").code < 7000


class TestToResponse:
    def test_to_response_shape(self):
        exc = AppException(1234, "测试消息", 400, {"k": "v"})
        resp = exc.to_response()
        assert resp == {"code": 1234, "message": "测试消息", "data": {"k": "v"}}

    def test_to_response_data_none(self):
        exc = ParamError("参数缺失")
        resp = exc.to_response()
        assert resp["data"] is None
        assert resp["code"] == 2001

    def test_http_status(self):
        assert AuthError().http_status == 401
        assert ParamError().http_status == 400
        assert SystemError().http_status == 500
        assert QuotaExceededError("x").http_status == 429
        assert ChannelLockedError("x").http_status == 423


class TestMessages:
    """异常消息非空且为中文可读。"""

    @pytest.mark.parametrize("exc", [
        AuthError(),
        InvalidTokenError(),
        ParamError(),
        ConfigError(),
        ConfigInvalidValueError("ai_service.image.image_count", "99"),
        PipelineError(),
        StepPausedError("rewrite", "API不可用"),
        StepRetryExhaustedError("review", 3),
        PublishError(),
        ChannelLockedError("今日头条"),
        CredentialInvalidError("小红书"),
        QuotaExceededError("llm_daily"),
        SystemError(),
        SourceUrlEmptyError(),
        CredentialEmptyError(),
        PlatformUnsupportedError("facebook"),
    ])
    def test_message_nonempty_chinese(self, exc):
        assert exc.message
        assert any('\u4e00' <= ch <= '\u9fff' for ch in exc.message)