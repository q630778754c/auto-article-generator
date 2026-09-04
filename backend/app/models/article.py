"""文章、审核报告、配图表（spec 6.3 / 6.4 / 6.5）。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("material.id"), nullable=False, unique=True)
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    style: Mapped[str] = mapped_column(Text, nullable=False)
    rewrite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("style IN ('casual','professional','narrative','listicle')", name="ck_article_style"),
        CheckConstraint("rewrite_count BETWEEN 0 AND 2", name="ck_article_rewrite_count"),
        CheckConstraint(
            "status IN ('draft','in_review','approved','rejected','violation_blocked','archived','awaiting_confirm')",
            name="ck_article_status",
        ),
        Index("idx_article_status", "status"),
    )


class ReviewReport(Base):
    __tablename__ = "review_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("article.id"), nullable=False)
    compliance_result: Mapped[str] = mapped_column(Text, nullable=False)
    originality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    image_text_score: Mapped[float] = mapped_column(Float, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    opinion: Mapped[str | None] = mapped_column(Text, nullable=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_at: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("compliance_result IN ('pass','fail','severe_violation')", name="ck_review_compliance"),
        CheckConstraint("originality_score BETWEEN 0 AND 100", name="ck_review_originality"),
        CheckConstraint("quality_score BETWEEN 0 AND 100", name="ck_review_quality"),
        CheckConstraint("image_text_score BETWEEN 0 AND 1", name="ck_review_image_text"),
        CheckConstraint("round_no BETWEEN 1 AND 3", name="ck_review_round"),
        Index("idx_report_article", "article_id", "round_no"),
    )


class ArticleImage(Base):
    __tablename__ = "article_image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("article.id"), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    origin_flag: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_cover: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gen_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    gen_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="success")

    __table_args__ = (
        CheckConstraint("origin_flag IN ('ai_generated','original_fallback')", name="ck_image_origin"),
        CheckConstraint("status IN ('success','degraded_text_only','failed')", name="ck_image_status"),
        Index("idx_image_article", "article_id"),
    )