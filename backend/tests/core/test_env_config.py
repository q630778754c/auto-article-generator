"""环境变量与配置加载单测（task 11.12）。

覆盖：
- 默认值
- 环境变量覆盖（storage_backend / bitiful_* / cors_allowed_origins）
- 类型校验（log_level / app_port）
- 解析目录属性（resolved_secret_key_file / log_dir / image_dir）
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSettingsDefaults:
    def test_default_storage_backend_is_local(self):
        s = Settings()
        assert s.storage_backend == "local"

    def test_default_bitiful_fields_empty(self):
        s = Settings()
        assert s.bitiful_endpoint == ""
        assert s.bitiful_access_key == ""
        assert s.bitiful_secret_key == ""
        assert s.bitiful_bucket == ""
        assert s.bitiful_public_base == ""

    def test_default_build_version_is_dev(self):
        s = Settings()
        assert s.build_version == "dev"

    def test_default_cors_allowed_origins_empty(self):
        s = Settings()
        assert s.cors_allowed_origins == ""

    def test_default_image_dir_is_data_dir_images(self, tmp_path):
        s = Settings(data_dir=tmp_path)
        assert s.image_dir == tmp_path / "images"


class TestEnvOverride:
    def test_storage_backend_env_override(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "bitiful")
        s = Settings()
        assert s.storage_backend == "bitiful"

    def test_bitiful_env_overrides(self, monkeypatch):
        monkeypatch.setenv("BITIFUL_ENDPOINT", "https://bitiful-east.bitiful.net")
        monkeypatch.setenv("BITIFUL_ACCESS_KEY", "AK_TEST")
        monkeypatch.setenv("BITIFUL_SECRET_KEY", "SK_TEST")
        monkeypatch.setenv("BITIFUL_BUCKET", "my-bucket")
        monkeypatch.setenv("BITIFUL_PUBLIC_BASE", "https://my-bucket.bitiful.net")
        s = Settings()
        assert s.bitiful_endpoint == "https://bitiful-east.bitiful.net"
        assert s.bitiful_access_key == "AK_TEST"
        assert s.bitiful_secret_key == "SK_TEST"
        assert s.bitiful_bucket == "my-bucket"
        assert s.bitiful_public_base == "https://my-bucket.bitiful.net"

    def test_build_version_env_override(self, monkeypatch):
        monkeypatch.setenv("BUILD_VERSION", "v2.0.1")
        s = Settings()
        assert s.build_version == "v2.0.1"

    def test_cors_origins_env_override(self, monkeypatch):
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.com,https://b.com")
        s = Settings()
        assert s.cors_allowed_origins == "https://a.com,https://b.com"


class TestValidation:
    def test_log_level_uppercase_conversion(self):
        s = Settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_log_level_invalid_raises(self):
        with pytest.raises(ValidationError):
            Settings(log_level="TRACE")

    def test_app_port_zero_rejected(self):
        with pytest.raises(ValidationError):
            Settings(app_port=0)

    def test_app_port_too_high_rejected(self):
        with pytest.raises(ValidationError):
            Settings(app_port=70000)


class TestPathProperties:
    def test_resolved_secret_key_file_default(self):
        s = Settings()
        assert s.resolved_secret_key_file.name == ".secret_key"

    def test_resolved_secret_key_file_custom(self, tmp_path):
        custom = tmp_path / "my_secret.key"
        s = Settings(secret_key_file=custom)
        assert s.resolved_secret_key_file == custom

    def test_log_dir(self, tmp_path):
        s = Settings(data_dir=tmp_path)
        assert s.log_dir == tmp_path / "logs"

    def test_image_dir(self, tmp_path):
        s = Settings(data_dir=tmp_path)
        assert s.image_dir == tmp_path / "images"


class TestGetSettingsSingleton:
    def test_returns_same_instance(self):
        from app.core.config import get_settings

        a = get_settings()
        b = get_settings()
        assert a is b