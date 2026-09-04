"""业务异常体系：错误码分段 + 用户可读中文消息（spec 4.6.3）。

错误码分段（design 2.5.1）：
    1xxx 鉴权  2xxx 参数  3xxx 配置  4xxx 流水线  5xxx 发布  6xxx 系统
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorCode:
    code: int
    message: str


class AppException(Exception):
    """业务异常基类。code 用于程序判定，message 用于前端展示（中文可读）。"""

    def __init__(self, code: int, message: str, http_status: int = 400, data: object = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data

    def to_response(self) -> dict:
        return {"code": self.code, "message": self.message, "data": self.data}


class AuthError(AppException):
    def __init__(self, message: str = "未登录或登录已失效", code: int = 1001, http_status: int = 401):
        super().__init__(code, message, http_status)


class InvalidTokenError(AuthError):
    def __init__(self, message: str = "登录已失效，请重新登录"):
        super().__init__(message, 1002, 401)


class ParamError(AppException):
    def __init__(self, message: str = "参数错误", code: int = 2001, http_status: int = 400):
        super().__init__(code, message, http_status)


class ConfigError(AppException):
    def __init__(self, message: str = "配置错误", code: int = 3001, http_status: int = 400):
        super().__init__(code, message, http_status)


class ConfigInvalidValueError(ConfigError):
    def __init__(self, key: str, value: object):
        super().__init__(f"配置项 {key} 的值 {value} 超出允许范围，已拒绝保存", 3003)


class PipelineError(AppException):
    def __init__(self, message: str = "流水线执行失败", code: int = 4001, http_status: int = 409):
        super().__init__(code, message, http_status)


class StepPausedError(PipelineError):
    """外部依赖连续失败触发环节暂停（spec 4.2.5）。"""

    def __init__(self, step: str, reason: str):
        super().__init__(f"{step}环节已暂停：{reason}", 4002, 503)


class StepRetryExhaustedError(PipelineError):
    def __init__(self, step: str, retries: int):
        super().__init__(f"{step}环节重试 {retries} 次后仍失败，流水线终止", 4003)


class PublishError(AppException):
    def __init__(self, message: str = "发布失败", code: int = 5001, http_status: int = 409):
        super().__init__(code, message, http_status)


class ChannelLockedError(PublishError):
    def __init__(self, channel_label: str):
        super().__init__(f"渠道 {channel_label} 正在发布其他文章，请等待", 5002, 423)


class CredentialInvalidError(PublishError):
    def __init__(self, channel_label: str):
        super().__init__(f"渠道 {channel_label} 登录凭证已失效，请更新凭证", 5003, 401)


class QuotaExceededError(AppException):
    def __init__(self, quota_key: str, reset_at: str = ""):
        msg = f"{quota_key} 今日配额已用尽"
        msg += f"，将于 {reset_at} 后恢复" if reset_at else "，明日自动恢复"
        super().__init__(6002, msg, 429)


class SystemError(AppException):
    def __init__(self, message: str = "系统内部错误", code: int = 6001, http_status: int = 500):
        super().__init__(code, message, http_status)


# 常用业务校验异常（design 2.5.1）
class SourceUrlEmptyError(ParamError):
    def __init__(self):
        super().__init__("资讯源地址不能为空", 2002)


class CredentialEmptyError(ParamError):
    def __init__(self):
        super().__init__("渠道凭证不能为空", 2003)


class PlatformUnsupportedError(ParamError):
    def __init__(self, platform: str):
        super().__init__(f"暂不支持的平台：{platform}", 2004)