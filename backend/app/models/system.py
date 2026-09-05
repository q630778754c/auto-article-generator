"""系统支撑表：配置/告警/审计/日志/指标/配额（spec 6.9~6.10 / 4.3.6 / 4.4.2 / 5.7.1）。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    config_key: Mapped[str] = mapped_column(Text, primary_key=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    effect_mode: Mapped[str] = mapped_column(Text, nullable=False, default="immediate")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category IN ('collect_source','ai_service','pipeline_strategy','publish_rule','unified_platform','api_key_config')",
            name="ck_config_category",
        ),
    )


class AlertEvent(Base):
    __tablename__ = "alert_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="unconfirmed")
    notify_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    notified_channels: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_at: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("level IN ('P0','P1','P2')", name="ck_alert_level"),
        CheckConstraint("source IN ('collect','rewrite','image','review','publish','system')", name="ck_alert_source"),
        CheckConstraint("status IN ('unconfirmed','confirmed')", name="ck_alert_status"),
        CheckConstraint("notify_status IN ('sent','pending','failed')", name="ck_alert_notify"),
        Index("idx_alert_level", "level", "status", "triggered_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "action_category IN ('initial_config','credential_update','alert_handle','manual_confirm','non_whitelist')",
            name="ck_audit_category",
        ),
        Index("idx_audit_time", "created_at"),
    )


class ProcessLog(Base):
    __tablename__ = "process_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)
    step: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "step IN ('collect','rewrite','image','review','publish','system')",
            name="ck_plog_step",
        ),
        Index("idx_log_trace", "trace_id", "step"),
        Index("idx_log_time", "created_at"),
    )


class MetricsDaily(Base):
    __tablename__ = "metrics_daily"

    stat_date: Mapped[str] = mapped_column(Text, primary_key=True)
    collected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rewritten_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publish_ok_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    e2e_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    e2e_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class QuotaUsage(Base):
    __tablename__ = "quota_usage"

    quota_key: Mapped[str] = mapped_column(Text, primary_key=True)
    used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    reset_at: Mapped[str] = mapped_column(Text, nullable=False)