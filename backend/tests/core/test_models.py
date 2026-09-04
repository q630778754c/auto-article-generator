"""ORM 模型单测：19张表建表 + 约束校验 + 外键。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.core import database


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@pytest_asyncio.fixture
async def db_with_tables(tmp_path, monkeypatch):
    """临时数据库 + 全部19张表。"""
    import app.core.config as cfg
    monkeypatch.setattr(cfg, "_settings", None)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "test.db")
    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "SessionLocal", None)

    import app.models  # noqa: F401
    await database.init_db()
    assert database.engine is not None
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)
    yield
    if database.engine is not None:
        await database.engine.dispose()
        monkeypatch.setattr(database, "engine", None)
        monkeypatch.setattr(database, "SessionLocal", None)


class TestTableCreation:
    @pytest.mark.asyncio
    async def test_all_19_tables_exist(self, db_with_tables):
        assert database.engine is not None
        async with database.engine.connect() as conn:
            names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        expected = {
            "user_account", "news_source", "material", "article",
            "review_report", "article_image", "publish_channel", "publish_record",
            "pipeline_record", "system_config", "alert_event", "audit_log",
            "process_log", "metrics_daily", "quota_usage",
            "sla_sample", "review_quality_daily", "unmanned_run_stat", "spot_check_sample",
        }
        assert expected.issubset(set(names))
        assert len(expected) == 19


class TestUniqueConstraints:
    @pytest.mark.asyncio
    async def test_material_fingerprint_unique(self, db_with_tables):
        from app.models import NewsSource, Material
        now = _utcnow()
        async with database.get_session() as s:
            src = NewsSource(name="test", source_type="rss", url="http://x", created_at=now, updated_at=now)
            s.add(src)
            await s.flush()
            m1 = Material(fingerprint="fp1", source_id=src.id, source_url="u", title="t" * 10,
                          content="c" * 60, collected_at=now, trace_id="tr1")
            s.add(m1)
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                m2 = Material(fingerprint="fp1", source_id=1, source_url="u", title="t" * 10,
                              content="c" * 60, collected_at=now, trace_id="tr2")
                s.add(m2)

    @pytest.mark.asyncio
    async def test_publish_record_channel_fp_unique(self, db_with_tables):
        from app.models import PublishRecord
        now = _utcnow()
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(PublishRecord(article_id=1, channel_id=1, channel_article_fp="dup_fp",
                                    created_at=now, updated_at=now))
            async with database.get_session() as s:
                s.add(PublishRecord(article_id=2, channel_id=2, channel_article_fp="dup_fp",
                                    created_at=now, updated_at=now))

    @pytest.mark.asyncio
    async def test_channel_platform_label_unique(self, db_with_tables):
        from app.models import PublishChannel
        now = _utcnow()
        cfg_json = '{"title_max":30}'
        async with database.get_session() as s:
            s.add(PublishChannel(platform="toutiao", account_label="acc1",
                                 credential_cipher="c", adapter_config=cfg_json,
                                 created_at=now, updated_at=now))
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(PublishChannel(platform="toutiao", account_label="acc1",
                                     credential_cipher="c2", adapter_config=cfg_json,
                                     created_at=now, updated_at=now))


class TestCheckConstraints:
    @pytest.mark.asyncio
    async def test_article_style_enum(self, db_with_tables):
        from app.models import Article
        now = _utcnow()
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(Article(material_id=1, fingerprint="fp", title="t", content="c",
                              style="invalid", model_used="m", created_at=now, updated_at=now))

    @pytest.mark.asyncio
    async def test_article_rewrite_count_range(self, db_with_tables):
        from app.models import Article
        now = _utcnow()
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(Article(material_id=1, fingerprint="fp", title="t", content="c",
                              style="casual", rewrite_count=5, model_used="m",
                              created_at=now, updated_at=now))

    @pytest.mark.asyncio
    async def test_review_score_range(self, db_with_tables):
        from app.models import ReviewReport
        now = _utcnow()
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(ReviewReport(article_id=1, compliance_result="pass",
                                   originality_score=150, quality_score=80,
                                   image_text_score=0.5, similarity_score=0.1,
                                   round_no=1, reviewed_at=now, model_used="m"))

    @pytest.mark.asyncio
    async def test_audit_action_category_enum(self, db_with_tables):
        from app.models import AuditLog
        now = _utcnow()
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(AuditLog(operator="admin", action="test", target="x",
                               action_category="invalid_category", created_at=now))


class TestForeignKey:
    @pytest.mark.asyncio
    async def test_material_source_fk(self, db_with_tables):
        from app.models import Material
        now = _utcnow()
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(Material(fingerprint="fp", source_id=999, source_url="u",
                              title="t" * 10, content="c" * 60,
                              collected_at=now, trace_id="tr"))


class TestV3Tables:
    @pytest.mark.asyncio
    async def test_sla_sample_insert(self, db_with_tables):
        from app.models import NewsSource, Material, SlaSample
        now = _utcnow()
        async with database.get_session() as s:
            src = NewsSource(name="s", source_type="rss", url="http://x", created_at=now, updated_at=now)
            s.add(src)
            await s.flush()
            m = Material(fingerprint="fp_sla", source_id=src.id, source_url="u", title="t" * 10,
                         content="c" * 60, collected_at=now, trace_id="tr_sla")
            s.add(m)
            await s.flush()
            s.add(SlaSample(source_id=src.id, material_id=m.id, collected_at=now,
                           latency_sec=120, sla_target_sec=180, is_met=1, stat_date="2026-09-01"))

    @pytest.mark.asyncio
    async def test_review_quality_daily_pk(self, db_with_tables):
        from app.models import ReviewQualityDaily
        async with database.get_session() as s:
            s.add(ReviewQualityDaily(stat_date="2026-09-01", review_total=10, first_pass=8))
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(ReviewQualityDaily(stat_date="2026-09-01", review_total=5))

    @pytest.mark.asyncio
    async def test_unmanned_run_stat_insert(self, db_with_tables):
        from app.models import UnmannedRunStat
        async with database.get_session() as s:
            s.add(UnmannedRunStat(stat_date="2026-09-01", continuous_hours=24,
                                 manual_intervention_count=0, daily_output=50))

    @pytest.mark.asyncio
    async def test_spot_check_judgment_enum(self, db_with_tables):
        from app.models import SpotCheckSample
        with pytest.raises(IntegrityError):
            async with database.get_session() as s:
                s.add(SpotCheckSample(article_id=1, review_round=1, was_intercepted=1,
                                      human_judgment="invalid", stat_week="2026-W36"))