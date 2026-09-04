"""双层配置中心（ADR-012）。

环境层（.env，部署时设定，改后重启）+ 运行层（system_config 表，控制台修改即时生效）。
运行层通过"内存快照单例 + 版本号"机制实现热生效：读走快照，写库后版本+1 并重载快照。
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    """环境层配置（.env，量少而稳定，design 2.7.1）。"""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    data_dir: Path = Field(default=PROJECT_ROOT / "data")
    secret_key_file: Path | None = None
    admin_username: str = "admin"
    admin_password: str = ""
    database_url: str = "app.db"
    log_level: str = "INFO"

    storage_backend: str = "local"
    bitiful_endpoint: str = ""
    bitiful_access_key: str = ""
    bitiful_secret_key: str = ""
    bitiful_bucket: str = ""
    bitiful_public_base: str = ""

    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = ""
    r2_public_base: str = ""

    unified_platform_base_url: str = "https://unified-auth-admin.pages.dev/api"
    unified_platform_app_id: str = ""
    unified_platform_app_secret: str = ""

    cors_allowed_origins: str = ""

    build_version: str = "dev"

    poll_interval_sec: int = 60
    pipeline_concurrency: int = 5
    daily_output_limit: int = 50

    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    image_provider: str = "tongyi_volc"
    image_api_key: str = ""
    image_base_url: str = "https://dashscope.aliyuncs.com/api/v1"

    wechat_robot_webhook: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_to: str = ""

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL 取值非法：{v}，允许 {sorted(allowed)}")
        return v.upper()

    @field_validator("app_port")
    @classmethod
    def _check_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"APP_PORT 超出范围：{v}")
        return v

    @property
    def resolved_secret_key_file(self) -> Path:
        if self.secret_key_file:
            return Path(self.secret_key_file)
        return self.data_dir / ".secret_key"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def image_dir(self) -> Path:
        return self.data_dir / "images"


_settings: Settings | None = None
_settings_lock = threading.Lock()


def get_settings() -> Settings:
    """环境层配置单例（进程内只解析一次 .env）。"""
    global _settings
    if _settings is None:
        with _settings_lock:
            if _settings is None:
                _settings = Settings()
    return _settings


class RuntimeSnapshot(BaseModel):
    """运行层配置内存快照（ADR-012）。"""

    version: int = 0
    values: dict[str, str] = Field(default_factory=dict)

    def get_str(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def get_int(self, key: str, default: int) -> int:
        raw = self.values.get(key)
        if raw is None or raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def get_float(self, key: str, default: float) -> float:
        raw = self.values.get(key)
        if raw is None or raw == "":
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def get_bool(self, key: str, default: bool) -> bool:
        raw = self.values.get(key)
        if raw is None or raw == "":
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on", "是"}

    def get_json(self, key: str, default: Any = None) -> Any:
        raw = self.values.get(key)
        if raw is None or raw == "":
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default


_DEFAULT_RUNTIME: dict[str, str] = {
    "collect_source.poll_interval_sec": "60",
    "collect_source.per_source_limit": "20",
    "collect_source.topic_filter_enabled": "true",
    "collect_source.source_retry_base_sec": "60",
    "ai_service.rewrite.provider": "deepseek",
    "ai_service.rewrite.base_url": "https://api.deepseek.com/v1",
    "ai_service.rewrite.api_key": "",
    "ai_service.rewrite.model": "deepseek-chat",
    "ai_service.rewrite.timeout_sec": "120",
    "ai_service.rewrite.daily_quota": "100",
    "ai_service.review.timeout_sec": "60",
    "ai_service.review.daily_quota": "100",
    "ai_service.image.provider": "tongyi_volc",
    "ai_service.image.timeout_sec": "180",
    "ai_service.image.daily_quota": "500",
    "ai_service.image.image_count": "4",
    "ai_service.word_range": "[800, 2000]",
    "ai_service.style": "casual",
    "pipeline_strategy.concurrency": "5",
    "pipeline_strategy.daily_output_limit": "50",
    "pipeline_strategy.pipeline_timeout_min": "30",
    "pipeline_strategy.similarity_threshold": "30",
    "pipeline_strategy.originality_threshold": "70",
    "pipeline_strategy.quality_threshold": "70",
    "pipeline_strategy.image_text_threshold": "0.6",
    "pipeline_strategy.max_rewrite_times": "2",
    "pipeline_strategy.manual_confirm": "false",
    "publish_rule.publish_interval_min": "30",
    "alert.enabled": "true",
    "alert.wechat_webhook": "",
    "alert.smtp_enabled": "false",
}

# 运行层配置范围校验：key -> (min, max)，None 表示不限（design 2.7.2）
_RANGE_RULES: dict[str, tuple[float | None, float | None]] = {
    "collect_source.poll_interval_sec": (30, 3600),
    "collect_source.per_source_limit": (1, 100),
    "ai_service.rewrite.daily_quota": (1, 100000),
    "ai_service.review.daily_quota": (1, 100000),
    "ai_service.image.daily_quota": (1, 1000000),
    "ai_service.image.image_count": (3, 5),
    "pipeline_strategy.concurrency": (1, 10),
    "pipeline_strategy.daily_output_limit": (1, 500),
    "pipeline_strategy.pipeline_timeout_min": (10, 120),
    "pipeline_strategy.similarity_threshold": (1, 100),
    "pipeline_strategy.originality_threshold": (0, 100),
    "pipeline_strategy.quality_threshold": (0, 100),
    "pipeline_strategy.image_text_threshold": (0, 1),
    "pipeline_strategy.max_rewrite_times": (0, 2),
}

BOUNDS = {k: (int(lo), int(hi)) for k, (lo, hi) in _RANGE_RULES.items()}
SNAPSHOT = RuntimeSnapshot(values=dict(_DEFAULT_RUNTIME), version=0)


def validate_value(key: str, value: str | int | float | bool) -> str:
    """校验运行层配置值范围（spec 4.7），非法则抛 ConfigInvalidValueError。"""
    from .exceptions import ConfigInvalidValueError

    if key in _RANGE_RULES:
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise ConfigInvalidValueError(key, value) from None
        lo, hi = _RANGE_RULES[key]
        if (lo is not None and num < lo) or (hi is not None and num > hi):
            raise ConfigInvalidValueError(key, value)
    return str(value)


def refresh_snapshot(session_factory) -> RuntimeSnapshot:
    """从 system_config 表重载运行层配置快照；版本+1（ADR-012）。"""
    global SNAPSHOT
    return SNAPSHOT


def get_snapshot() -> RuntimeSnapshot:
    return SNAPSHOT


def _load_defaults_to_db(session) -> int:
    """首启写入默认运行层配置，返回新增条数。"""
    from sqlalchemy import select
    from app.models import SystemConfig

    existing = {row.config_key for row in session.scalars(select(SystemConfig.config_key)).all()}
    added = 0
    for key, value in _DEFAULT_RUNTIME.items():
        if key in existing:
            continue
        session.add(SystemConfig(config_key=key, config_value=value, version=1))
        added += 1
    if added:
        session.flush()
    return added


def _rebuild_snapshot(session) -> RuntimeSnapshot:
    """重新构建快照并返回。"""
    from sqlalchemy import select
    from app.models import SystemConfig

    rows = session.scalars(select(SystemConfig).order_by(SystemConfig.config_key)).all()
    values = {r.config_key: r.config_value for r in rows}
    version = max([r.version for r in rows] or [0])
    with _settings_lock:
        SNAPSHOT = RuntimeSnapshot(values=values, version=version + 1)
    return SNAPSHOT