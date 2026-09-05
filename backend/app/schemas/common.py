"""统一响应、分页、脱敏 Schema 基座（design 2.5.2 C 组）。"""

from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel, Field, field_serializer

from app.core.security import mask_sensitive_value

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包装：{code, message, data}。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageRequest(BaseModel):
    """分页请求参数（越界兜底）。"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PageResponse(BaseModel, Generic[T]):
    """分页响应。"""

    items: Sequence[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size > 0 else 0


class MaskedStr(str):
    """凭证脱敏字符串：序列化时自动掩码。"""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(str)

    def __repr__(self) -> str:
        return repr(mask_sensitive_value(str(self)))


class MaskedCredentialMixin(BaseModel):
    """渠道凭证脱敏混入：序列化时 credential_cipher 恒输出掩码。"""

    credential_cipher: str = ""

    @field_serializer("credential_cipher")
    def _mask_credential(self, v: str) -> str:
        return mask_sensitive_value(v)


class SendCodeRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    email: str
    code: str
    password: str
    nickname: str = ""


class VerifyLoginRequest(BaseModel):
    email: str
    code: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


class PlatformLoginRequest(BaseModel):
    email: str
    password: str


class UpdateUserRequest(BaseModel):
    nickname: str | None = None
    status: str | None = None