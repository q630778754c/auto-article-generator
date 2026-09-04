"""发布渠道与发布记录表（spec 6.6 / 6.7）。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PublishChannel(Base):
    __tablename__ = "publish_channel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    account_label: Mapped[str] = mapped_column(Text, nullable=False)
    credential_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    credential_type: Mapped[str] = mapped_column(Text, nullable=False, default="cookie")
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    health_status: Mapped[str] = mapped_column(Text, nullable=False, default="normal")
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    min_interval_min: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    adapter_config: Mapped[str] = mapped_column(Text, nullable=False)
    health_checked_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_published_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_fail: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("platform IN ('toutiao','penguin','zhihu','xhs','baijiahao')", name="ck_channel_platform"),
        CheckConstraint("length(account_label) BETWEEN 1 AND 100", name="ck_channel_label_len"),
        CheckConstraint("credential_type IN ('oauth','cookie')", name="ck_channel_cred_type"),
        CheckConstraint("health_status IN ('normal','credential_expired','abnormal')", name="ck_channel_health"),
        CheckConstraint("daily_limit BETWEEN 1 AND 50", name="ck_channel_daily_limit"),
        CheckConstraint("min_interval_min BETWEEN 5 AND 1440", name="ck_channel_min_interval"),
        UniqueConstraint("platform", "account_label", name="uq_channel_platform_label"),
    )


class PublishRecord(Base):
    __tablename__ = "publish_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("article.id"), nullable=False)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("publish_channel.id"), nullable=False)
    channel_article_fp: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    publish_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_article_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_audit: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("platform_audit IN ('pending','passed','rejected')", name="ck_pr_audit"),
        CheckConstraint(
            "status IN ('queued','publishing','published','failed','audit_rejected','manual_check')",
            name="ck_pr_status",
        ),
        Index("idx_pr_channel_status", "channel_id", "status"),
        Index("idx_pr_article", "article_id"),
    )