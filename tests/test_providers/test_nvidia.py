"""NVIDIA provider tests — request construction + response/error handling.

Every test monkeypatches ``requests.post`` (or the encode helper) so no NVIDIA
endpoint is ever contacted and no API key is required. The provider is always
constructed with an explicit ``api_key`` unless the test specifically exercises
the missing-key path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import requests
from PIL import Image

from slate.manifest import Manifest
from slate.providers.nvidia import (
    DEFAULT_CROSSCHECK_MODEL,
    DEFAULT_PRIMARY_MODEL,
    NvidiaProvider,
)


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        status: int = 200,
        text: str = "",
        raise_on_json: bool = False,
    ) -> None:
        self._payload = payload
        self.status_code = status
        self.text = text
        self._raise_on_json = raise_on_json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]

    def json(self) -> dict[str, Any]:
        if self._raise_on_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


def _chat_response(content: Any) -> dict[str, Any]:
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def tiny_png(tmp_path: Path) -> Path:
    p = tmp_path / "frame.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(p, "PNG")
    return p


# ---------------------------------------------------------------------------
# Construction / defaults
# ---------------------------------------------------------------------------


def test_defaults_resolve_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "env-key")
    monkeypatch.setenv("NVIDIA_API_BASE_URL", "https://example.test/v1/")
    provider = NvidiaProvider()
    assert provider.label == "nvidia"
    assert provider.model == DEFAULT_PRIMARY_MODEL
    assert provider.api_key == "env-key"
    # trailing slash stripped
    assert provider.base_url == "https://example.test/v1"
    assert provider.max_tokens == 700


def test_explicit_args_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "env-key")
    provider = NvidiaProvider(
        label="nvidia-crosscheck",
        model=DEFAULT_CROSSCHECK_MODEL,
        api_key="explicit-key",
        base_url="http://local/v1",
        timeout_seconds=12,
        max_image_dim=256,
    )
    assert provider.label == "nvidia-crosscheck"
    assert provider.model == DEFAULT_CROSSCHECK_MODEL
    assert provider.api_key == "explicit-key"
    assert provider.base_url == "http://local/v1"
    assert provider.timeout_seconds == 12
    assert provider.max_image_dim == 256


def test_base_url_falls_back_to_public_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_BASE_URL", raising=False)
    provider = NvidiaProvider(api_key="k")
    assert provider.base_url == "https://integrate.api.nvidia.com/v1"


# ---------------------------------------------------------------------------
# Happy path / request construction
# ---------------------------------------------------------------------------


def test_happy_path_builds_request(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("headers")
        captured["timeout"] = kwargs.get("timeout")
        return _FakeResponse(_chat_response('{"character_visible": true, "severity": "ok"}'))

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(
        api_key="secret-key", model="nvidia/test-model", base_url="http://nv/v1", timeout_seconds=42
    )
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))

    assert result.ok
    assert result.provider == "nvidia"
    assert result.model == "nvidia/test-model"
    assert result.signals["character_visible"] is True

    assert captured["url"] == "http://nv/v1/chat/completions"
    assert captured["timeout"] == 42
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["headers"]["Content-Type"] == "application/json"

    body = captured["json"]
    assert body["model"] == "nvidia/test-model"
    assert body["temperature"] == 0
    assert body["max_tokens"] == 700
    content = body["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_list_content_is_joined_and_parsed(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path
) -> None:
    """Some models return ``content`` as a list of parts; the provider joins
    their ``text`` fields before JSON parsing."""

    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(_chat_response([{"text": '{"character_visible": false}'}]))

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert result.ok
    assert result.signals["character_visible"] is False


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_missing_api_key_short_circuits(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise AssertionError("network must not be touched without a key")

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider()
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "NVIDIA_API_KEY is not configured" in (result.error or "")
    assert result.signals == {}


def test_read_error_surfaces(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    def boom(*args: Any, **kwargs: Any) -> str:
        raise OSError("cannot read frame")

    monkeypatch.setattr("slate.providers.nvidia.encode_image_b64", boom)
    provider = NvidiaProvider(api_key="k")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "cannot read frame" in (result.error or "")


def test_http_error_includes_status_and_body(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path
) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({}, status=429, text="rate limited, slow down")

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k", model="nvidia/test-model")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "HTTP 429" in (result.error or "")
    assert "rate limited" in (result.error or "")
    assert "nvidia/test-model" in (result.error or "")


def test_http_error_without_response(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    """An HTTPError lacking an attached response degrades gracefully."""

    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise requests.HTTPError("boom")  # response defaults to None

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k", model="nvidia/test-model")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "HTTP ?" in (result.error or "")


def test_request_exception_surfaces(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise requests.ConnectionError("connection reset")

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k", model="nvidia/test-model")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "connection reset" in (result.error or "")
    assert "nvidia/test-model" in (result.error or "")


def test_bad_json_response(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({}, raise_on_json=True)

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k", model="nvidia/test-model")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "bad json" in (result.error or "")


def test_no_choices_returned(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({"choices": []})

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k", model="nvidia/test-model")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "no choices returned" in (result.error or "")


def test_unparseable_model_content_is_error(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path
) -> None:
    """A 200 whose model text is not JSON surfaces the parse error from the
    shared parser (``error`` key promoted to ProviderResult.error)."""

    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse(_chat_response("I cannot help with that."))

    monkeypatch.setattr("slate.providers.nvidia.requests.post", fake_post)
    provider = NvidiaProvider(api_key="k", model="nvidia/test-model")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "did not return JSON" in (result.error or "")
