"""core/database 单测。"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.core import database


@pytest_asyncio.fixture
async def initialized_db(tmp_path, monkeypatch):
    """用临时目录初始化数据库。"""
    import app.core.config as cfg
    monkeypatch.setattr(cfg, "_settings", None)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "test.db")
    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "SessionLocal", None)
    await database.init_db()
    yield
    if database.engine is not None:
        await database.engine.dispose()
        monkeypatch.setattr(database, "engine", None)
        monkeypatch.setattr(database, "SessionLocal", None)


class TestResolveDatabaseUrl:
    def test_plain_filename(self, tmp_path, monkeypatch):
        import app.core.config as cfg
        monkeypatch.setattr(cfg, "_settings", None)
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        monkeypatch.setenv("DATABASE_URL", "my.db")
        url = database.resolve_database_url()
        assert url.startswith("sqlite+aiosqlite:///")
        assert "my.db" in url

    def test_sqlite_prefix(self, tmp_path, monkeypatch):
        import app.core.config as cfg
        monkeypatch.setattr(cfg, "_settings", None)
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        url = database.resolve_database_url()
        assert url == "sqlite+aiosqlite:///:memory:"


class TestInitDb:
    @pytest.mark.asyncio
    async def test_init_creates_engine(self, initialized_db):
        assert database.engine is not None
        assert database.SessionLocal is not None

    @pytest.mark.asyncio
    async def test_ping(self, initialized_db):
        result = await database.ping_db()
        assert result is True

    @pytest.mark.asyncio
    async def test_ping_no_engine(self):
        original = database.engine
        database.engine = None
        try:
            assert await database.ping_db() is False
        finally:
            database.engine = original


class TestGetSession:
    @pytest.mark.asyncio
    async def test_session_query(self, initialized_db):
        async with database.get_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, initialized_db):
        with pytest.raises(Exception):
            async with database.get_session() as session:
                await session.execute(text("SELECT * FROM nonexistent_table"))
