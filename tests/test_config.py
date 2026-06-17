"""Config helper tests — env-var parsing branches.

These manipulate ``os.environ`` via monkeypatch so they stay hermetic and never
depend on the host's real environment.
"""

from __future__ import annotations

import pytest

from slate import config


def test_env_str_returns_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLATE_TEST_STR", raising=False)
    assert config.env_str("SLATE_TEST_STR", "fallback") == "fallback"


def test_env_str_returns_value_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLATE_TEST_STR", "configured")
    assert config.env_str("SLATE_TEST_STR", "fallback") == "configured"


def test_env_bool_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLATE_TEST_BOOL", raising=False)
    assert config.env_bool("SLATE_TEST_BOOL", default=True) is True
    assert config.env_bool("SLATE_TEST_BOOL", default=False) is False


@pytest.mark.parametrize("raw", ["", "0", "false", "no", "off", "FALSE", "Off", "  no  "])
def test_env_bool_falsey_strings(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("SLATE_TEST_BOOL", raw)
    assert config.env_bool("SLATE_TEST_BOOL", default=True) is False


@pytest.mark.parametrize("raw", ["1", "true", "yes", "on", "anything"])
def test_env_bool_truthy_strings(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("SLATE_TEST_BOOL", raw)
    assert config.env_bool("SLATE_TEST_BOOL", default=False) is True


def test_env_int_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLATE_TEST_INT", raising=False)
    assert config.env_int("SLATE_TEST_INT", 42) == 42


def test_env_int_default_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLATE_TEST_INT", "")
    assert config.env_int("SLATE_TEST_INT", 7) == 7


def test_env_int_parses_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLATE_TEST_INT", "  256 ")
    assert config.env_int("SLATE_TEST_INT", 7) == 256


def test_env_int_falls_back_on_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLATE_TEST_INT", "not-a-number")
    assert config.env_int("SLATE_TEST_INT", 99) == 99


def test_max_image_dim_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLATE_MAX_IMAGE_DIM", raising=False)
    assert config.max_image_dim() == config.DEFAULT_MAX_IMAGE_DIM


def test_max_image_dim_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLATE_MAX_IMAGE_DIM", "512")
    assert config.max_image_dim() == 512


def test_provider_timeout_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SLATE_PROVIDER_TIMEOUT", raising=False)
    assert config.provider_timeout() == config.DEFAULT_PROVIDER_TIMEOUT


def test_provider_timeout_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLATE_PROVIDER_TIMEOUT", "30")
    assert config.provider_timeout() == 30
