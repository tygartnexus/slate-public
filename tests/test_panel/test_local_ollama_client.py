"""Tests for the local Ollama-backed Panel client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from slate.panel.local_ollama_client import LocalOllamaVisionClient


@pytest.fixture
def _png(tmp_path: Path) -> Path:
    p = tmp_path / "frame_0000.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\nfakebytes")
    return p


def test_local_ollama_client_posts_prompt_and_images(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    captured: dict[str, Any] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"response": '{"publish_ready": true, "summary": "ok", "flags": []}'}

    def fake_post(
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
    ) -> _Response:
        captured.update(
            {"url": url, "json": json, "headers": headers, "timeout": timeout}
        )
        return _Response()

    monkeypatch.setattr("slate.panel.local_ollama_client.requests.post", fake_post)

    client = LocalOllamaVisionClient(
        url="http://localhost:11434",
        model="gemma4:latest",
        timeout_seconds=17,
    )
    response = client.analyze("judge this", [_png])

    assert response.ok
    assert response.text.startswith('{"publish_ready"')
    assert response.model == "gemma4:latest"
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["json"]["model"] == "gemma4:latest"
    assert captured["json"]["prompt"] == "judge this"
    assert captured["json"]["images"]
    assert captured["json"]["stream"] is False
    assert captured["headers"] == {"Content-Type": "application/json"}
    assert captured["timeout"] == 17


def test_local_ollama_client_connection_error_returns_provider_error(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    import requests

    def fake_post(*_args: object, **_kwargs: object) -> object:
        raise requests.ConnectionError("refused")

    monkeypatch.setattr("slate.panel.local_ollama_client.requests.post", fake_post)

    client = LocalOllamaVisionClient()
    response = client.analyze("prompt", [_png])

    assert not response.ok
    assert "ollama: refused" in (response.error or "")
