"""core/security 单测。"""

from __future__ import annotations

import pytest

from app.core.security import (
    load_or_create_key,
    Cipher,
    mask_sensitive_value,
    hash_password,
    verify_password,
    create_token,
    generate_admin_password,
    random_hex,
    sha256_hex,
    now_utc,
    is_token_expired,
    TOKEN_TTL_SECONDS,
)


class TestLoadOrCreateKey:
    def test_generate_new(self, tmp_path):
        key_file = tmp_path / ".secret_key"
        key = load_or_create_key(key_file)
        assert key_file.exists()
        assert len(key) > 0
        from cryptography.fernet import Fernet
        Fernet(key)  # 验证是合法 Fernet 密钥

    def test_reuse_existing(self, tmp_path):
        key_file = tmp_path / ".secret_key"
        key1 = load_or_create_key(key_file)
        key2 = load_or_create_key(key_file)
        assert key1 == key2

    def test_creates_parent_dir(self, tmp_path):
        key_file = tmp_path / "deep" / "nested" / ".secret_key"
        key = load_or_create_key(key_file)
        assert key_file.exists()


class TestCipher:
    def test_encrypt_decrypt_roundtrip(self, tmp_path):
        key = load_or_create_key(tmp_path / "k")
        cipher = Cipher(key)
        plaintext = "sk-deepseek-abcdef123456"
        encrypted = cipher.encrypt(plaintext)
        assert encrypted != plaintext
        assert cipher.decrypt(encrypted) == plaintext

    def test_encrypt_empty(self, tmp_path):
        cipher = Cipher(load_or_create_key(tmp_path / "k"))
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_decrypt_invalid_returns_empty(self, tmp_path):
        cipher = Cipher(load_or_create_key(tmp_path / "k"))
        assert cipher.decrypt("not-a-valid-token") == ""


class TestMaskSensitiveValue:
    def test_long_value(self):
        assert mask_sensitive_value("sk-1234567890abcdef") == "****cdef"

    def test_short_value(self):
        assert mask_sensitive_value("abc") == "****"

    def test_empty(self):
        assert mask_sensitive_value("") == ""
        assert mask_sensitive_value(None) == ""


class TestPasswordHash:
    def test_hash_verify_roundtrip(self):
        password = "MySecurePass123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
        assert not verify_password("wrong", hashed)

    def test_hash_format(self):
        hashed = hash_password("test")
        assert hashed.startswith("pbkdf2_sha256$")

    def test_verify_empty_hash(self):
        assert not verify_password("test", "")
        assert not verify_password("test", "invalid")


class TestToken:
    def test_create_token(self):
        token, expires_at = create_token()
        assert len(token) == 64
        assert not is_token_expired(expires_at)

    def test_token_expired(self):
        from datetime import datetime, timedelta, timezone
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert is_token_expired(past)

    def test_token_ttl(self):
        assert TOKEN_TTL_SECONDS == 86400


class TestAdminPassword:
    def test_generate_length(self):
        pwd = generate_admin_password()
        assert len(pwd) == 16

    def test_generate_custom_length(self):
        pwd = generate_admin_password(24)
        assert len(pwd) == 24

    def test_generate_min_length(self):
        pwd = generate_admin_password(4)
        assert len(pwd) >= 8

    def test_no_ambiguous_chars(self):
        pwd = generate_admin_password(100)
        for ch in pwd:
            assert ch not in "IO0l1"


class TestUtilities:
    def test_random_hex(self):
        h = random_hex(16)
        assert len(h) == 32
        assert all(c in "0123456789abcdef" for c in h)

    def test_sha256_hex(self):
        assert sha256_hex("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

    def test_now_utc(self):
        from datetime import datetime, timezone
        t = now_utc()
        assert t.tzinfo is not None