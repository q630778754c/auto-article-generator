"""core/config 单测。"""

from __future__ import annotations

import pytest

from app.core.config import (
    Settings,
    RuntimeSnapshot,
    get_settings,
    validate_value,
    SNAPSHOT,
    _DEFAULT_RUNTIME,
    _RANGE_RULES,
)


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.app_host == "127.0.0.1"
        assert s.app_port == 8000
        assert s.log_level == "INFO"
        assert s.poll_interval_sec == 60
        assert s.pipeline_concurrency == 5

    def test_log_level_uppercase(self):
        s = Settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_log_level_invalid(self):
        with pytest.raises(ValueError):
            Settings(log_level="TRACE")

    def test_port_range(self):
        with pytest.raises(ValueError):
            Settings(app_port=0)
        with pytest.raises(ValueError):
            Settings(app_port=70000)

    def test_resolved_secret_key_file_default(self):
        s = Settings()
        path = s.resolved_secret_key_file
        assert path.name == ".secret_key"

    def test_log_dir(self):
        s = Settings()
        assert s.log_dir.name == "logs"

    def test_image_dir(self):
        s = Settings()
        assert s.image_dir.name == "images"


class TestGetSettings:
    def test_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestRuntimeSnapshot:
    def test_get_str(self):
        snap = RuntimeSnapshot(values={"k": "v"})
        assert snap.get_str("k") == "v"
        assert snap.get_str("missing", "default") == "default"

    def test_get_int(self):
        snap = RuntimeSnapshot(values={"k": "42", "bad": "x"})
        assert snap.get_int("k", 0) == 42
        assert snap.get_int("bad", 99) == 99
        assert snap.get_int("missing", 7) == 7

    def test_get_float(self):
        snap = RuntimeSnapshot(values={"k": "3.14", "bad": "x"})
        assert snap.get_float("k", 0.0) == pytest.approx(3.14)
        assert snap.get_float("bad", 1.0) == 1.0

    def test_get_bool(self):
        snap = RuntimeSnapshot(values={"t": "true", "f": "false", "one": "1", "yes": "yes"})
        assert snap.get_bool("t", False) is True
        assert snap.get_bool("f", True) is False
        assert snap.get_bool("one", False) is True
        assert snap.get_bool("yes", False) is True
        assert snap.get_bool("missing", True) is True

    def test_get_json(self):
        snap = RuntimeSnapshot(values={"k": "[1,2,3]", "bad": "not json"})
        assert snap.get_json("k") == [1, 2, 3]
        assert snap.get_json("bad") is None
        assert snap.get_json("missing", []) == []


class TestValidateValue:
    def test_valid_within_range(self):
        assert validate_value("collect_source.poll_interval_sec", "60") == "60"

    def test_valid_boundary(self):
        assert validate_value("collect_source.poll_interval_sec", "30") == "30"
        assert validate_value("collect_source.poll_interval_sec", "3600") == "3600"

    def test_invalid_below_range(self):
        from app.core.exceptions import ConfigInvalidValueError
        with pytest.raises(ConfigInvalidValueError):
            validate_value("collect_source.poll_interval_sec", "10")

    def test_invalid_above_range(self):
        from app.core.exceptions import ConfigInvalidValueError
        with pytest.raises(ConfigInvalidValueError):
            validate_value("collect_source.poll_interval_sec", "9999")

    def test_no_rule_passes(self):
        assert validate_value("unknown.key", "anything") == "anything"


class TestDefaultsAndRules:
    def test_defaults_cover_essential_keys(self):
        essential = [
            "collect_source.poll_interval_sec",
            "ai_service.rewrite.provider",
            "pipeline_strategy.concurrency",
            "pipeline_strategy.daily_output_limit",
            "alert.enabled",
        ]
        for key in essential:
            assert key in _DEFAULT_RUNTIME

    def test_range_rules_subset_of_defaults(self):
        for key in _RANGE_RULES:
            assert key in _DEFAULT_RUNTIME

    def test_snapshot_initialized(self):
        assert SNAPSHOT.version == 0
        assert len(SNAPSHOT.values) > 0