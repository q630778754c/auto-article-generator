"""API Key 生成与加密服务（spec 4.3.4 / design 2.3.2）。

生成 `ak-` + 32 位 hex 格式 Key，Fernet 加密存储，掩码展示。
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func, update

from app.core import database
from app.core.config import get_settings
from app.core.security import Cipher, mask_sensitive_value
from app.models import ApiKey


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_cipher() -> Cipher:
    from pathlib import Path
    settings = get_settings()
    key = Path(settings.resolved_secret_key_file).read_bytes().strip()
    return Cipher(key)


class ApiKeyService:
    """API Key 生命周期管理。"""

    def __init__(self) -> None:
        self._cipher = _get_cipher()

    async def generate(
        self,
        name: str,
        scope: str = "all_collector",
        rate_limit: int = 100,
        expires_days: int | None = 90,
        created_by: str = "admin",
    ) -> tuple[ApiKey, str]:
        plain_key = f"ak-{secrets.token_hex(16)}"
        key_prefix = plain_key[:12]
        key_encrypted = self._cipher.encrypt(plain_key)
        expires_at = None
        if expires_days is not None:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat(timespec="seconds")
        now = _now()
        async with database.get_session() as s:
            existing = await s.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.name == name))
            if existing and existing > 0:
                from app.core.exceptions import ParamError
                raise ParamError(f"API Key 名称已存在：{name}", 2005)
            record = ApiKey(
                name=name,
                key_encrypted=key_encrypted,
                key_prefix=key_prefix,
                scope=scope,
                rate_limit=rate_limit,
                expires_days=expires_days,
                expires_at=expires_at,
                enabled=True,
                created_by=created_by,
                total_calls=0,
                success_calls=0,
                fail_calls=0,
                created_at=now,
                updated_at=now,
            )
            s.add(record)
            await s.flush()
            await s.refresh(record)
        return record, plain_key

    @staticmethod
    def mask_from_prefix(key_prefix: str) -> str:
        if len(key_prefix) <= 4:
            return f"{key_prefix}****"
        return f"{key_prefix}****"

    def mask(self, plain_key: str) -> str:
        return mask_sensitive_value(plain_key)

    async def verify(self, plain_key: str) -> ApiKey | None:
        if not plain_key.startswith("ak-"):
            return None
        key_prefix = plain_key[:12]
        async with database.get_session() as s:
            result = await s.execute(select(ApiKey).where(ApiKey.key_prefix == key_prefix))
            candidates = result.scalars().all()
            for record in candidates:
                decrypted = self._cipher.decrypt(record.key_encrypted)
                if decrypted == plain_key:
                    return record
        return None

    async def get_by_id(self, key_id: int) -> ApiKey | None:
        async with database.get_session() as s:
            result = await s.execute(select(ApiKey).where(ApiKey.id == key_id))
            return result.scalar_one_or_none()

    async def list(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        async with database.get_session() as s:
            total = await s.scalar(select(func.count()).select_from(ApiKey))
            offset = (page - 1) * page_size
            result = await s.execute(
                select(ApiKey).order_by(ApiKey.id.desc()).offset(offset).limit(page_size)
            )
            records = result.scalars().all()
        return {
            "items": [self._to_dict(r) for r in records],
            "total": total or 0,
            "page": page,
            "page_size": page_size,
        }

    def _to_dict(self, record: ApiKey) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "key_masked": self.mask_from_prefix(record.key_prefix),
            "scope": record.scope,
            "rate_limit": record.rate_limit,
            "expires_days": record.expires_days,
            "expires_at": record.expires_at,
            "enabled": record.enabled,
            "created_by": record.created_by,
            "total_calls": record.total_calls,
            "success_calls": record.success_calls,
            "fail_calls": record.fail_calls,
            "last_used_at": record.last_used_at,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    async def update(self, key_id: int, **fields: Any) -> ApiKey | None:
        allowed = {"name", "scope", "rate_limit", "expires_days", "expires_at", "enabled"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return await self.get_by_id(key_id)
        updates["updated_at"] = _now()
        async with database.get_session() as s:
            await s.execute(update(ApiKey).where(ApiKey.id == key_id).values(**updates))
            result = await s.execute(select(ApiKey).where(ApiKey.id == key_id))
            return result.scalar_one_or_none()

    async def toggle(self, key_id: int) -> ApiKey | None:
        record = await self.get_by_id(key_id)
        if record is None:
            return None
        return await self.update(key_id, enabled=not record.enabled)

    async def delete(self, key_id: int) -> bool:
        record = await self.get_by_id(key_id)
        if record is None:
            return False
        async with database.get_session() as s:
            result = await s.execute(select(ApiKey).where(ApiKey.id == key_id))
            r = result.scalar_one_or_none()
            if r:
                await s.delete(r)
        return True

    async def increment_usage(self, key_id: int, success: bool) -> None:
        now = _now()
        async with database.get_session() as s:
            stmt = update(ApiKey).where(ApiKey.id == key_id).values(
                total_calls=ApiKey.total_calls + 1,
                success_calls=ApiKey.success_calls + (1 if success else 0),
                fail_calls=ApiKey.fail_calls + (0 if success else 1),
                last_used_at=now,
                updated_at=now,
            )
            await s.execute(stmt)


_service: ApiKeyService | None = None


def get_api_key_service() -> ApiKeyService:
    global _service
    if _service is None:
        _service = ApiKeyService()
    return _service