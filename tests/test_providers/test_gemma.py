"""Gemma provider tests — request payload + error handling.

These tests monkeypatch ``requests.post`` so no actual Ollama daemon is needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import requests
from PIL import Image

from slate.manifest import Manifest
from slate.providers.gemma import GemmaProvider


class _FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        status: int = 200,
        raise_on_json: bool = False,
    ) -> None:
        self._payload = payload
        self.status_code = status
        self._raise_on_json = raise_on_json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]

    def json(self) -> dict[str, Any]:
        if self._raise_on_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload


@pytest.fixture
def tiny_png(tmp_path: Path) -> Path:
    p = tmp_path / "frame.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(p, "PNG")
    return p


def test_gemma_happy_path(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _FakeResponse({"response": '{"character_visible": true}'})

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)

    provider = GemmaProvider(url="http://localhost:11434", model="gemma4:latest")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))

    assert result.ok
    assert result.signals["character_visible"] is True
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["json"]["model"] == "gemma4:latest"
    assert isinstance(captured["json"]["images"], list)
    assert len(captured["json"]["images"]) == 1
    assert captured["json"]["format"] == "json"
    assert captured["json"]["options"]["num_predict"] == 2048


def test_gemma_num_predict_override(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["json"] = kwargs.get("json")
        return _FakeResponse({"response": '{"character_visible": true}'})

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)
    monkeypatch.setenv("GEMMA_NUM_PREDICT", "3072")

    provider = GemmaProvider(url="http://localhost:11434", model="gemma4:latest")
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))

    assert result.ok
    assert captured["json"]["options"]["num_predict"] == 3072


def test_gemma_connection_error(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)
    provider = GemmaProvider()
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))

    assert not result.ok
    assert "ollama" in (result.error or "")
    assert "connection refused" in (result.error or "")


def test_gemma_bad_json(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({"response": "this is not json at all"})

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)
    provider = GemmaProvider()
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "did not return JSON" in (result.error or "")


def test_gemma_read_error(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    """An OSError reading/encoding the frame surfaces as a provider error."""

    def boom(*args: Any, **kwargs: Any) -> str:
        raise OSError("disk gone")

    monkeypatch.setattr("slate.providers.gemma.encode_image_b64", boom)
    provider = GemmaProvider()
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "read" in (result.error or "")
    assert "disk gone" in (result.error or "")


def test_gemma_response_not_json(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    """A 200 whose body isn't valid JSON (``resp.json()`` raises) is reported."""

    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({}, raise_on_json=True)

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)
    provider = GemmaProvider()
    result = provider.analyze_frame(tiny_png, Manifest(shot_id="x"))
    assert not result.ok
    assert "ollama: bad json" in (result.error or "")


def test_gemma_warm_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _FakeResponse({"response": "ok"})

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)
    provider = GemmaProvider(url="http://localhost:11434", model="gemma4:latest")
    assert provider.warm() is True
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["json"]["model"] == "gemma4:latest"


def test_gemma_warm_returns_false_when_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise requests.ConnectionError("no daemon")

    monkeypatch.setattr("slate.providers.gemma.requests.post", fake_post)
    provider = GemmaProvider()
    assert provider.warm() is False
