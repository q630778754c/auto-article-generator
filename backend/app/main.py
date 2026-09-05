"""FastAPI 应用入口与生命周期（spec 4.5、design 2.5.2）。

启动序：建 data 目录 → 校验/生成密钥 → 初始化日志 → 初始化数据库 →
执行迁移 → 加载配置快照 → 建默认管理员 → 恢复流水线（占位）→ 启动调度器（占位）。

冷启动优化（v2 部署）：
- 非必要 SDK（openai/anthropic/boto3/playwright）采用延迟加载，首启不 import
- 仅保留 FastAPI/SQLAlchemy/pydantic/loguru/cryptography 等启动必需依赖
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import get_settings
from app.core import database
from app.core.exceptions import AppException
from app.core.logging import setup_logging, TraceLogger
from app.core.security import load_or_create_key, hash_password, generate_admin_password, Cipher

logger = TraceLogger("main")


_LAZY_IMPORTS: dict[str, Any] = {}
_PROCESS_START_TIME = time.time()


def _lazy_import(module_name: str) -> Any:
    """按需导入重 SDK（openai/anthropic/boto3/playwright）。首启不付出 import 成本。"""
    if module_name not in _LAZY_IMPORTS:
        import importlib

        _LAZY_IMPORTS[module_name] = importlib.import_module(module_name)
    return _LAZY_IMPORTS[module_name]


async def _ensure_dirs(settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.image_dir.mkdir(parents=True, exist_ok=True)


async def _run_migrations() -> None:
    """建表（占位：Alembic 就绪后替换为版本比对+自动迁移，task 2.4）。"""
    try:
        import app.models  # noqa: F401 — 触发 ORM 类注册到 Base.metadata
    except ImportError:
        pass
    assert database.engine is not None
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)


async def _load_config_snapshot() -> None:
    """加载运行层配置快照（占位：system_config 表就绪后替换，task 2.6）。"""
    pass


async def _ensure_admin(settings) -> str | None:
    """建默认管理员；ADMIN_PASSWORD 为空则随机生成并返回明文（仅打印一次）。"""
    admin_user = settings.admin_username
    admin_pass = settings.admin_password or generate_admin_password()
    generated = admin_pass if not settings.admin_password else None

    try:
        async with database.get_session() as session:
            existing = await session.execute(
                text("SELECT id FROM user_account WHERE username = :u"),
                {"u": admin_user},
            )
            if existing.scalar() is not None:
                return None
            await session.execute(
                text(
                    "INSERT INTO user_account (username, password_hash, display_name, created_at, updated_at) "
                    "VALUES (:u, :h, '', datetime('now'), datetime('now'))"
                ),
                {"u": admin_user, "h": hash_password(admin_pass)},
            )
    except Exception as exc:
        logger.warn(f"建管理员跳过：{exc}（ORM 模型就绪后自动恢复）")
        return None

    return generated


async def _restore_pipeline() -> None:
    """恢复流水线挂载点（占位，task 5.x）。"""
    pass


async def _start_scheduler() -> None:
    """启动调度器挂载点（占位，task 5.x）。"""
    pass


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    await _ensure_dirs(settings)
    secret_key = load_or_create_key(settings.resolved_secret_key_file)
    _cipher = Cipher(secret_key)
    setup_logging(log_dir=settings.log_dir, level=settings.log_level)
    logger.info("启动中…")

    await database.init_db()
    await _run_migrations()
    await _load_config_snapshot()

    generated_pass = await _ensure_admin(settings)
    if generated_pass:
        logger.info(
            f"首启已创建管理员 账号={settings.admin_username} "
            f"密码={generated_pass}（请妥善保存，仅显示一次）"
        )
    else:
        logger.info("管理员账号已存在或暂不可建")

    await _restore_pipeline()
    await _start_scheduler()

    from app.core.token_cache import get_token_cache
    from app.core.api_key_limiter import get_api_key_limiter
    get_token_cache()
    get_api_key_limiter()

    if settings.unified_platform_base_url and not settings.unified_platform_base_url.startswith("https://"):
        logger.warning(f"统一平台 base_url 非 HTTPS：{settings.unified_platform_base_url}")

    logger.info("启动完成")
    yield
    logger.info("已关闭")


def create_app() -> FastAPI:
    app = FastAPI(title="全自动AI内容生产与发布系统", version="3.0.0", lifespan=lifespan)

    @app.exception_handler(AppException)
    async def _handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_response())

    @app.get("/api/v1/health")
    async def health() -> dict:
        settings = get_settings()
        uptime = int(time.time() - _PROCESS_START_TIME)
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "status": "healthy",
                "build_version": settings.build_version,
                "storage_backend": settings.storage_backend,
                "start_time": _PROCESS_START_TIME,
                "uptime_seconds": uptime,
            },
        }

    from app.api.v1 import router as v1_router
    app.include_router(v1_router)

    settings = get_settings()
    storage_backend = settings.storage_backend
    if storage_backend == "local":
        images_dir = settings.image_dir
        images_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and (static_dir / "index.html").exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            if path.startswith("api/") or path.startswith("_test/"):
                return JSONResponse(status_code=404, content={"code": 404, "message": "接口不存在", "data": None})
            file_path = static_dir / path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(static_dir / "index.html"))
    else:
        @app.get("/")
        async def index_hint() -> HTMLResponse:
            return HTMLResponse(
                "<html><body><h2>前端未构建</h2>"
                "<p>API 已就绪，访问 <a href='/api/v1/health'>/api/v1/health</a> 探活。</p>"
                "</body></html>"
            )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False)