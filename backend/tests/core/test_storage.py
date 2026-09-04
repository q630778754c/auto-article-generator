"""StorageAdapter 单测（task 10.10）。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.core.security import Cipher, load_or_create_key
from app.services.storage import (
    BitifulStorageAdapter,
    CloudflareR2Adapter,
    LocalStorageAdapter,
    StorageBackendError,
    create_storage_adapter,
    encrypt_credential,
    decrypt_credential,
    reset_storage_adapter_for_tests,
)


class TestLocalStorageAdapter:
    def test_put_and_get_url(self, tmp_path: Path):
        root = tmp_path / "images"
        adapter = LocalStorageAdapter(root=root)
        src = tmp_path / "hello.jpg"
        src.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
        url = adapter.put(src, "2026/09/x.jpg")
        assert url == "/static/images/2026/09/x.jpg"
        assert (root / "2026/09/x.jpg").is_file()

    def test_put_bytes(self, tmp_path: Path):
        adapter = LocalStorageAdapter(root=tmp_path / "img")
        url = adapter.put_bytes(b"binary-data", "k.png", content_type="image/png")
        assert url == "/static/images/k.png"
        assert (tmp_path / "img" / "k.png").read_bytes() == b"binary-data"

    def test_get_url_strips_leading_slash(self, tmp_path: Path):
        adapter = LocalStorageAdapter(root=tmp_path / "img")
        assert adapter.get_url("/a/b.jpg") == "/static/images/a/b.jpg"

    def test_delete_and_exists(self, tmp_path: Path):
        adapter = LocalStorageAdapter(root=tmp_path / "img")
        adapter.put_bytes(b"x", "y.bin")
        assert adapter.exists("y.bin") is True
        assert adapter.delete("y.bin") is True
        assert adapter.exists("y.bin") is False

    def test_delete_missing_returns_false(self, tmp_path: Path):
        adapter = LocalStorageAdapter(root=tmp_path / "img")
        assert adapter.delete("nope.bin") is False

    def test_path_traversal_neutralized(self, tmp_path: Path):
        adapter = LocalStorageAdapter(root=tmp_path / "img")
        path = adapter._resolve("../escape.txt")
        assert ".." not in str(path)

    def test_healthcheck(self, tmp_path: Path):
        adapter = LocalStorageAdapter(root=tmp_path / "img")
        h = adapter.healthcheck()
        assert h["backend"] == "local"
        assert h["ok"] is True


class TestBitifulAdapterWiring:
    def test_missing_config_raises(self):
        with pytest.raises(StorageBackendError):
            BitifulStorageAdapter(
                endpoint="",
                access_key="ak",
                secret_key="sk",
                bucket="b",
                public_base="",
            )

    def test_lazy_client_not_loaded_in_init(self):
        adapter = BitifulStorageAdapter(
            endpoint="https://example.com",
            access_key="ak",
            secret_key="sk",
            bucket="b",
            public_base="https://cdn.example.com",
        )
        assert adapter._client is None

    def test_get_url_uses_public_base(self):
        adapter = BitifulStorageAdapter(
            endpoint="https://example.com",
            access_key="ak",
            secret_key="sk",
            bucket="b",
            public_base="https://cdn.example.com/",
        )
        assert adapter.get_url("foo/bar.jpg") == "https://cdn.example.com/foo/bar.jpg"


class TestCloudflareR2Reserved:
    def test_r2_is_reserved(self):
        with pytest.raises(StorageBackendError):
            CloudflareR2Adapter(
                endpoint="",
                access_key="",
                secret_key="",
                bucket="",
                public_base="",
            )


class TestCreateStorageAdapterFactory:
    def test_create_local(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("app.core.config._settings", None)
        from app.core.config import Settings

        s = Settings(data_dir=tmp_path)
        monkeypatch.setattr("app.core.config._settings", s)
        adapter = create_storage_adapter("local")
        assert adapter.name == "local"
        assert isinstance(adapter, LocalStorageAdapter)

    def test_create_bitiful(self):
        adapter = create_storage_adapter(
            "bitiful",
            endpoint="https://e.com",
            access_key="ak",
            secret_key="sk",
            bucket="b",
            public_base="https://cdn.com",
        )
        assert adapter.name == "bitiful"
        assert isinstance(adapter, BitifulStorageAdapter)

    def test_unknown_backend_raises(self):
        with pytest.raises(StorageBackendError):
            create_storage_adapter("taobao_oss")


class TestCredentialEncryption:
    def test_round_trip(self, tmp_path: Path):
        key_file = tmp_path / ".k"
        key = load_or_create_key(key_file)
        cipher = Cipher(key)
        plaintext = "AKIA-secret-key-12345"
        enc = encrypt_credential(plaintext, cipher)
        assert enc != plaintext
        assert decrypt_credential(enc, cipher) == plaintext

    def test_idempotent_for_already_encrypted(self, tmp_path: Path):
        key_file = tmp_path / ".k"
        cipher = Cipher(load_or_create_key(key_file))
        plaintext = "AKIA-secret-key-12345"
        enc = encrypt_credential(plaintext, cipher)
        enc2 = encrypt_credential(enc, cipher)
        assert enc2 == enc

    def test_empty_unchanged(self, tmp_path: Path):
        cipher = Cipher(load_or_create_key(tmp_path / ".k"))
        assert encrypt_credential("", cipher) == ""
        assert decrypt_credential("", cipher) == ""

    def test_legacy_plaintext_decrypt_passthrough(self, tmp_path: Path):
        cipher = Cipher(load_or_create_key(tmp_path / ".k"))
        assert decrypt_credential("plaintext-not-fernet", cipher) == "plaintext-not-fernet"


class TestSingletonLifecycle:
    def test_get_storage_adapter_uses_settings_backend(self, tmp_path: Path, monkeypatch):
        from app.core import config
        from app.core.config import Settings

        reset_storage_adapter_for_tests()
        s = Settings(data_dir=tmp_path, storage_backend="local")
        monkeypatch.setattr(config, "_settings", s)
        adapter = config._settings and None  # noqa
        from app.services.storage import get_storage_adapter

        a1 = get_storage_adapter()
        a2 = get_storage_adapter()
        assert a1 is a2
        assert a1.name == "local"
        reset_storage_adapter_for_tests()