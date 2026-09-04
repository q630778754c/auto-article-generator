"""v3 增量统计表（spec 4.1.2 / 6.11 / 6.12 / 5.4.1）。

sla_sample：采集时延样本
review_quality_daily：审核质量日统计
unmanned_run_stat：无人值守运行统计
spot_check_sample：人工抽查样本
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SlaSample(Base):
    __tablename__ = "sla_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_source.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(Integer, ForeignKey("material.id"), nullable=False)
    origin_published_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[str] = mapped_column(Text, nullable=False)
    latency_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    sla_target_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    is_met: Mapped[int] = mapped_column(Integer, nullable=False)
    stat_date: Mapped[str] = mapped_column(Text, nullable=False)


class ReviewQualityDaily(Base):
    __tablename__ = "review_quality_daily"

    stat_date: Mapped[str] = mapped_column(Text, primary_key=True)
    review_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_pass: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    send_back: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hard_block: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_pass_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intercept_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    platform_reject_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    platform_reject_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submit_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UnmannedRunStat(Base):
    __tablename__ = "unmanned_run_stat"

    stat_date: Mapped[str] = mapped_column(Text, primary_key=True)
    continuous_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_intervention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    initial_config_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credential_update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_handle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_confirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_target_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=72)

    __table_args__ = (
        CheckConstraint("continuous_hours >= 0", name="ck_unmanned_continuous_hours"),
        CheckConstraint("manual_intervention_count >= 0", name="ck_unmanned_manual_count"),
    )


class SpotCheckSample(Base):
    __tablename__ = "spot_check_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("article.id"), nullable=False)
    review_round: Mapped[int] = mapped_column(Integer, nullable=False)
    was_intercepted: Mapped[int] = mapped_column(Integer, nullable=False)
    human_judgment: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator: Mapped[str | None] = mapped_column(Text, nullable=True)
    judged_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    stat_week: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("review_round BETWEEN 1 AND 3", name="ck_spot_review_round"),
        CheckConstraint("human_judgment IN ('false_kill','keep_intercept')", name="ck_spot_judgment"),
    )