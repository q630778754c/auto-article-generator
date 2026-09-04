"""资讯源与素材表（spec 6.1 / 6.2）。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewsSource(Base):
    __tablename__ = "news_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    run_status: Mapped[str] = mapped_column(Text, nullable=False, default="normal")
    max_items_per_poll: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    fetch_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    backoff_until: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_success_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("length(name) BETWEEN 1 AND 50", name="ck_source_name_len"),
        CheckConstraint("source_type IN ('rss','web_page')", name="ck_source_type"),
        CheckConstraint("run_status IN ('normal','error','parse_error')", name="ck_source_run_status"),
        CheckConstraint("max_items_per_poll BETWEEN 1 AND 100", name="ck_source_max_items"),
    )


class Material(Base):
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_source.id"), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    origin_published_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[str] = mapped_column(Text, nullable=False)
    original_images: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending_rewrite")
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_material_title_len"),
        CheckConstraint("length(content) >= 50", name="ck_material_content_len"),
        CheckConstraint(
            "status IN ('pending_rewrite','processing','failed','incomplete','topic_blocked','archived')",
            name="ck_material_status",
        ),
        Index("idx_material_status", "status", "collected_at"),
        Index("idx_material_trace", "trace_id"),
    )