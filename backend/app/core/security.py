"""安全服务（ADR-009）：Fernet 加密、密码哈希、登录 Token、凭证掩码。

- 主密钥首启自动生成并落盘 data/.secret_key，文件权限 600
- 凭证/密钥加解密（Fernet）
- 管理员密码 PBKDF2-HMAC-SHA256 哈希
- 登录 Token 随机64位、默认24h过期
- 凭证掩码 ****末4位（spec 4.3.1）
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

TOKEN_TTL_SECONDS = 24 * 3600
PBKDF2_ITERATIONS = 120_000


def _set_file_permissions(path: Path) -> None:
    """跨平台尽力设置 600 权限（Windows 上忽略失败）。"""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def load_or_create_key(secret_key_file: Path) -> bytes:
    """首启自动生成 Fernet 主密钥并落盘，二次启动复用（幂等）。"""
    secret_key_file.parent.mkdir(parents=True, exist_ok=True)
    if secret_key_file.exists() and secret_key_file.read_bytes().strip():
        key = secret_key_file.read_bytes().strip()
        if _is_valid_fernet_key(key):
            return key
    key = Fernet.generate_key()
    tmp = secret_key_file.with_suffix(secret_key_file.suffix + ".tmp")
    tmp.write_bytes(key)
    _set_file_permissions(tmp)
    tmp.replace(secret_key_file)
    return key


def _is_valid_fernet_key(key: bytes) -> bool:
    try:
        Fernet(key)
        return True
    except Exception:
        return False


class Cipher:
    """Fernet 加解密门面：凭证、API Key 等敏感运行层配置密文存储。"""

    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            return ""

    def mask(self, value: str) -> str:
        return mask_sensitive_value(value)


def mask_sensitive_value(value: str | None) -> str:
    """凭证掩码：输出 ****末4位；空值/短值不崩溃（spec 4.3.1）。"""
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if len(text) <= 4:
        return "****"
    return f"****{text[-4:]}"


@dataclass
class PasswordHash:
    salt: str
    hash_hex: str

    def to_string(self) -> str:
        return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${self.salt}${self.hash_hex}"

    @classmethod
    def parse(cls, raw: str) -> "PasswordHash":
        if not raw or not raw.startswith("pbkdf2_sha256$"):
            return cls(salt="", hash_hex="")
        try:
            _, iterations, salt, hash_hex = raw.split("$")
        except ValueError:
            return cls(salt="", hash_hex="")
        return cls(salt=salt, hash_hex=hash_hex)


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 加盐哈希（不可逆）。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), PBKDF2_ITERATIONS)
    return PasswordHash(salt=salt, hash_hex=digest.hex()).to_string()


def verify_password(password: str, raw_hash: str) -> bool:
    """常量时间比较，避免时序攻击。"""
    parsed = PasswordHash.parse(raw_hash)
    if not parsed.salt or not parsed.hash_hex:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), parsed.salt.encode("ascii"), PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), parsed.hash_hex)



def create_token() -> tuple[str, datetime]:
    """签发登录 Token（随机64位）并返回过期时间；Token 需配合 DB 会话表校验。"""
    token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
    return token, expires_at


def generate_admin_password(length: int = 16) -> str:
    """首启随机生成管理员密码（ADMIN_PASSWORD 为空时）。"""
    if length < 8:
        length = 8
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def random_hex(nbytes: int = 16) -> str:
    return secrets.token_hex(nbytes)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_token_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now_utc() > expires_at

