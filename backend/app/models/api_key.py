"""API Key 与调用日志表（spec 4.3.4 / design 2.3.2）。"""

from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    key_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="all_collector")
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    expires_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    total_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "scope IN ('rss_only','webpage_only','all_collector')",
            name="ck_apikey_scope",
        ),
        CheckConstraint("rate_limit >= 1 AND rate_limit <= 1000", name="ck_apikey_rate"),
        Index("idx_apikey_name", "name", unique=True),
        Index("idx_apikey_prefix", "key_prefix"),
    )


class ApiKeyCallLog(Base):
    __tablename__ = "api_key_call_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int] = mapped_column(Integer, nullable=False)
    api_key_mask: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_ip: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_calllog_keyid", "api_key_id", "created_at"),
        Index("idx_calllog_time", "created_at"),
    )