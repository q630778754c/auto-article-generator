"""存储后端抽象层（task 10.2）。

设计目标：
- 通过 STORAGE_BACKEND 环境变量在 local / bitiful 之间热切换
- 业务代码不感知存储协议差异，统一调用 put / get_url / delete / exists
- 单例懒加载（首次访问时构造，避免冷启动 SDK 加载成本）
- 抽象接口稳定，便于将来增加 cloudflare_r2 / aliyun_oss / s3 等
"""

from __future__ import annotations

import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.core.logging import TraceLogger

logger = TraceLogger("storage")

STORAGE_BACKEND_LOCAL = "local"
STORAGE_BACKEND_BITIFUL = "bitiful"
SUPPORTED_BACKENDS = {STORAGE_BACKEND_LOCAL, STORAGE_BACKEND_BITIFUL}


class StorageAdapter(ABC):
    """存储后端统一接口。"""

    name: str = "abstract"

    @abstractmethod
    def put(self, source_path: str | Path, key: str) -> str:
        """上传文件，返回对外可访问的 URL（本地为 /static/images/{key}）。"""

    @abstractmethod
    def put_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        """上传字节流，返回 URL。"""

    @abstractmethod
    def get_url(self, key: str) -> str:
        """根据 key 返回对外可访问 URL（不实际检查存在性）。"""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除对象；返回是否成功。"""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """判断对象是否存在。"""

    def healthcheck(self) -> dict[str, Any]:
        """健康探针：子类可覆写（如 S3 list-bucket）。"""
        return {"backend": self.name, "ok": True}


class StorageBackendError(RuntimeError):
    """存储后端操作失败。"""


class CloudflareR2Adapter(StorageAdapter):
    """Cloudflare R2 适配器（reserved，task 10.8）。

    ⚠️ 当前实现为预留接口，尚未启用（main.py 与 create_storage_adapter 未挂载）。
    启用时需把 STORAGE_BACKEND=r2 加入 SUPPORTED_BACKENDS 并在 factory 中分支。
    """

    name = "cloudflare_r2"

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, public_base: str) -> None:
        raise StorageBackendError(
            "Cloudflare R2 适配器为预留接口（task 10.8 reserved），当前未启用；"
            "如需启用请修改 storage.py 的 create_storage_adapter。"
        )

    def put(self, source_path: str | Path, key: str) -> str:  # pragma: no cover
        raise NotImplementedError

    def put_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:  # pragma: no cover
        raise NotImplementedError

    def get_url(self, key: str) -> str:  # pragma: no cover
        raise NotImplementedError

    def delete(self, key: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover
        raise NotImplementedError


class LocalStorageAdapter(StorageAdapter):
    """本地文件系统存储（开发/单机部署）。"""

    name = "local"

    def __init__(self, root: Path, public_prefix: str = "/static/images") -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._public_prefix = public_prefix.rstrip("/")

    def _resolve(self, key: str) -> Path:
        normalized = key.lstrip("/").replace("..", "_")
        return self._root / normalized

    def put(self, source_path: str | Path, key: str) -> str:
        src = Path(source_path)
        if not src.exists():
            raise StorageBackendError(f"本地文件不存在: {src}")
        dst = self._resolve(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        return self.get_url(key)

    def put_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        dst = self._resolve(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return self.get_url(key)

    def get_url(self, key: str) -> str:
        normalized = key.lstrip("/")
        return f"{self._public_prefix}/{normalized}"

    def delete(self, key: str) -> bool:
        path = self._resolve(key)
        if path.is_file():
            path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()


class BitifulStorageAdapter(StorageAdapter):
    """Bitiful 对象存储（S3 兼容协议，boto3）。"""

    name = "bitiful"

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_base: str,
    ) -> None:
        if not endpoint or not access_key or not secret_key or not bucket:
            raise StorageBackendError(
                "Bitiful 配置缺失：endpoint / access_key / secret_key / bucket 必填"
            )
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._public_base = public_base.rstrip("/") if public_base else ""
        self._client: Any | None = None

    def _client_lazy(self) -> Any:
        if self._client is None:
            try:
                import boto3
                from botocore.client import Config as BotoConfig
            except ImportError as exc:
                raise StorageBackendError(
                    "Bitiful 适配器需要 boto3，请确认 requirements.txt"
                ) from exc
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._client

    def put(self, source_path: str | Path, key: str) -> str:
        src = Path(source_path)
        if not src.exists():
            raise StorageBackendError(f"本地文件不存在: {src}")
        client = self._client_lazy()
        client.upload_file(str(src), self._bucket, key.lstrip("/"))
        return self.get_url(key)

    def put_bytes(self, data: bytes, key: str, content_type: str = "image/jpeg") -> str:
        client = self._client_lazy()
        client.put_object(
            Bucket=self._bucket,
            Key=key.lstrip("/"),
            Body=data,
            ContentType=content_type,
        )
        return self.get_url(key)

    def get_url(self, key: str) -> str:
        normalized = key.lstrip("/")
        if self._public_base:
            return f"{self._public_base}/{normalized}"
        client = self._client_lazy()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": normalized},
            ExpiresIn=3600,
        )

    def delete(self, key: str) -> bool:
        client = self._client_lazy()
        client.delete_object(Bucket=self._bucket, Key=key.lstrip("/"))
        return True

    def exists(self, key: str) -> bool:
        client = self._client_lazy()
        try:
            client.head_object(Bucket=self._bucket, Key=key.lstrip("/"))
            return True
        except Exception:
            return False

    def healthcheck(self) -> dict[str, Any]:
        try:
            client = self._client_lazy()
            client.head_bucket(Bucket=self._bucket)
            return {"backend": self.name, "ok": True, "bucket": self._bucket}
        except Exception as exc:
            return {"backend": self.name, "ok": False, "error": str(exc)[:120]}


_adapter_singleton: StorageAdapter | None = None
_adapter_lock = threading.Lock()


def create_storage_adapter(backend: str, **kwargs: Any) -> StorageAdapter:
    """根据 backend 名称构造适配器实例（不缓存）。"""
    if backend == STORAGE_BACKEND_LOCAL:
        from app.core.config import get_settings

        settings = get_settings()
        root = kwargs.get("root") or settings.image_dir
        return LocalStorageAdapter(root=Path(root))
    if backend == STORAGE_BACKEND_BITIFUL:
        return BitifulStorageAdapter(
            endpoint=kwargs.get("endpoint", os.environ.get("BITIFUL_ENDPOINT", "")),
            access_key=kwargs.get("access_key", os.environ.get("BITIFUL_ACCESS_KEY", "")),
            secret_key=kwargs.get("secret_key", os.environ.get("BITIFUL_SECRET_KEY", "")),
            bucket=kwargs.get("bucket", os.environ.get("BITIFUL_BUCKET", "")),
            public_base=kwargs.get("public_base", os.environ.get("BITIFUL_PUBLIC_BASE", "")),
        )
    raise StorageBackendError(f"未知存储后端: {backend}（支持 {sorted(SUPPORTED_BACKENDS)}）")


def get_storage_adapter() -> StorageAdapter:
    """全局单例（懒加载）。根据 settings.storage_backend 解析。"""
    global _adapter_singleton
    if _adapter_singleton is None:
        with _adapter_lock:
            if _adapter_singleton is None:
                from app.core.config import get_settings

                settings = get_settings()
                _adapter_singleton = create_storage_adapter(settings.storage_backend)
                logger.info(f"存储后端初始化 backend={_adapter_singleton.name}")
    return _adapter_singleton


def reset_storage_adapter_for_tests() -> None:
    """单测钩子：清理单例缓存以便切换 backend。"""
    global _adapter_singleton
    with _adapter_lock:
        _adapter_singleton = None


def encrypt_credential(plaintext: str, cipher: Any) -> str:
    """加密 Bitiful/R2 凭证（task 10.9）。落库或落 .env 时使用密文。

    cipher: app.core.security.Cipher 实例。
    """
    if plaintext is None or plaintext == "":
        return ""
    if not plaintext.startswith("gAAAAA"):
        return cipher.encrypt(plaintext)
    return plaintext


def decrypt_credential(ciphertext: str, cipher: Any) -> str:
    """解密 Bitiful/R2 凭证，传入 Cipher。解密失败回退原文便于兼容。"""
    if not ciphertext:
        return ""
    if ciphertext.startswith("gAAAAA"):
        try:
            return cipher.decrypt(ciphertext)
        except Exception:
            return ""
    return ciphertext