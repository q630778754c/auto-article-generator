"""流水线记录表（spec 6.8）。"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PipelineRecord(Base):
    __tablename__ = "pipeline_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("article.id"), nullable=False)
    current_step: Mapped[str] = mapped_column(Text, nullable=False)
    step_detail: Mapped[str] = mapped_column(Text, nullable=False)
    elapsed_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "current_step IN ('collect','rewrite','image','review','publish','done')",
            name="ck_pipeline_step",
        ),
        CheckConstraint(
            "final_state IN ('success','failed','timeout','paused')",
            name="ck_pipeline_final_state",
        ),
        Index("idx_pipeline_state", "final_state", "current_step"),
    )