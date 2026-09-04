"""SQLite 数据库引擎与会话管理（ADR-003）。

WAL 模式 + busy_timeout 保证并发短写不锁库；单事务短写保证状态变更原子性（spec 4.2.4）。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None

# 长事务并发度限制：状态变更类写入串行化，读不受影响
_write_lock = asyncio.Lock()


class Base(DeclarativeBase):
    pass


def resolve_database_url() -> str:
    """按环境变量解析 SQLite URL；非 sqlite 前缀视为相对 DATA_DIR 的路径。"""
    from .config import get_settings

    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        return url
    return f"sqlite+aiosqlite:///{(settings.data_dir / url).resolve()}"


async def init_db() -> AsyncEngine:
    """初始化引擎与会话工厂；建数据目录并应用 PRAGMA。幂等。"""
    global engine, SessionLocal
    from .config import get_settings
    from .logging import TraceLogger

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    db_url = resolve_database_url()
    if engine is None:
        engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            connect_args={"timeout": 30},
        )

        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    logger = TraceLogger("db")
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA journal_mode"))
        mode = result.scalar()
    logger.info(f"数据库就绪 journal_mode={mode}")
    return engine


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """异步会话上下文管理器；异常回滚，正常提交。"""
    assert SessionLocal is not None, "数据库未初始化，请先调用 init_db()"
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def atomic_commit(session: AsyncSession) -> None:
    """单事务短写提交（spec 4.2.4）：状态变更与时间戳原子落库，全局写锁串行化。"""
    async with _write_lock:
        await session.commit()


async def ping_db() -> bool:
    """探活：供启动健康检查与调度任务使用。"""
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
