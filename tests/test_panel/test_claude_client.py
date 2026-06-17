"""Tests for the Claude vision client (:mod:`slate.panel.claude_client`).

The anthropic SDK is mocked end-to-end: ``analyze`` is exercised against a fake
``Anthropic`` class injected via ``monkeypatch`` so no API key is required and
no real HTTP call is ever made. Covers request construction, response parsing,
token-usage extraction, the missing-key short-circuit, frame-read errors, SDK
errors, and response-shape errors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest

import slate.panel.claude_client as cc
from slate.panel.claude_client import (
    DEFAULT_PANEL_MODEL,
    ClaudeResponse,
    ClaudeVisionClient,
    _media_type_for,
)

# ---------------------------------------------------------------------------
# Fake anthropic SDK
# ---------------------------------------------------------------------------


class _Block:
    def __init__(self, text: str | None) -> None:
        if text is not None:
            self.text = text


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Response:
    def __init__(self, content: list[Any], usage: _Usage | None) -> None:
        self.content = content
        if usage is not None:
            self.usage = usage


class _Messages:
    def __init__(self, parent: _FakeAnthropic) -> None:
        self._parent = parent

    def create(self, **kwargs: Any) -> _Response:
        self._parent.calls.append(kwargs)
        if self._parent.raise_on_create is not None:
            raise self._parent.raise_on_create
        return self._parent.response


class _FakeAnthropic:
    """Drop-in for ``anthropic.Anthropic``."""

    instances: ClassVar[list[_FakeAnthropic]] = []

    def __init__(self, *, api_key: str, timeout: int) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        self.raise_on_create: Exception | None = None
        self.response: _Response = _Response(
            content=[_Block("hello world")], usage=_Usage(11, 7)
        )
        self.messages = _Messages(self)
        _FakeAnthropic.instances.append(self)


@pytest.fixture(autouse=True)
def _reset_instances() -> None:
    _FakeAnthropic.instances.clear()


@pytest.fixture
def _png(tmp_path: Path) -> Path:
    p = tmp_path / "frame_0000.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\nfakebytes")
    return p


def _patch_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``from anthropic import Anthropic`` resolve to the fake."""
    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic, raising=True)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_init_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    client = ClaudeVisionClient()
    assert client.api_key == "env-key"
    assert client.model == DEFAULT_PANEL_MODEL
    assert client.max_tokens == 2000
    assert client.timeout_seconds == 300


def test_init_explicit_api_key_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    client = ClaudeVisionClient(api_key="explicit", model="claude-x", max_tokens=10)
    assert client.api_key == "explicit"
    assert client.model == "claude-x"
    assert client.max_tokens == 10


# ---------------------------------------------------------------------------
# analyze — missing key
# ---------------------------------------------------------------------------


def test_analyze_without_key_returns_error(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = ClaudeVisionClient(api_key="")
    resp = client.analyze("prompt", [_png])
    assert not resp.ok
    assert resp.error == "ANTHROPIC_API_KEY not set"
    assert resp.text == ""


# ---------------------------------------------------------------------------
# analyze — success
# ---------------------------------------------------------------------------


def test_analyze_success_builds_request_and_parses(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    _patch_sdk(monkeypatch)
    client = ClaudeVisionClient(api_key="k", model="claude-test", max_tokens=123)
    resp = client.analyze("describe this", [_png])

    assert resp.ok
    assert resp.text == "hello world"
    assert resp.model == "claude-test"
    assert resp.input_tokens == 11
    assert resp.output_tokens == 7

    # Exactly one Anthropic instance was constructed and one create() call made.
    assert len(_FakeAnthropic.instances) == 1
    sdk = _FakeAnthropic.instances[0]
    assert sdk.api_key == "k"
    assert sdk.timeout == 300
    assert len(sdk.calls) == 1
    call = sdk.calls[0]
    assert call["model"] == "claude-test"
    assert call["max_tokens"] == 123
    content = call["messages"][0]["content"]
    # One image block (base64 PNG) + one trailing text block.
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    assert content[0]["source"]["type"] == "base64"
    assert content[0]["source"]["data"]  # non-empty base64
    assert content[-1] == {"type": "text", "text": "describe this"}


def test_analyze_reuses_client_across_calls(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    """The underlying Anthropic client is constructed lazily once, then reused."""
    _patch_sdk(monkeypatch)
    client = ClaudeVisionClient(api_key="k")
    client.analyze("a", [_png])
    client.analyze("b", [_png])
    assert len(_FakeAnthropic.instances) == 1  # not rebuilt on the 2nd call


def test_analyze_multiple_frames(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_sdk(monkeypatch)
    frames = []
    for i, ext in enumerate((".png", ".jpg", ".webp")):
        p = tmp_path / f"frame_{i}{ext}"
        p.write_bytes(b"data")
        frames.append(p)
    client = ClaudeVisionClient(api_key="k")
    resp = client.analyze("p", frames)
    assert resp.ok
    content = _FakeAnthropic.instances[0].calls[0]["messages"][0]["content"]
    media_types = [c["source"]["media_type"] for c in content if c["type"] == "image"]
    assert media_types == ["image/png", "image/jpeg", "image/webp"]


def test_analyze_no_usage_defaults_tokens_to_zero(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    _patch_sdk(monkeypatch)
    client = ClaudeVisionClient(api_key="k")
    # Build the client, then swap in a response with NO usage attribute.
    client.analyze("warmup", [_png])
    sdk = _FakeAnthropic.instances[0]
    sdk.response = _Response(content=[_Block("text only")], usage=None)
    resp = client.analyze("again", [_png])
    assert resp.ok
    assert resp.text == "text only"
    assert resp.input_tokens == 0
    assert resp.output_tokens == 0


def test_analyze_skips_blocks_without_text(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    """Blocks lacking a ``text`` attribute (e.g. tool-use) are filtered out."""
    _patch_sdk(monkeypatch)
    client = ClaudeVisionClient(api_key="k")
    client.analyze("warmup", [_png])
    sdk = _FakeAnthropic.instances[0]
    sdk.response = _Response(
        content=[_Block(None), _Block("kept"), _Block("")], usage=_Usage(1, 2)
    )
    resp = client.analyze("again", [_png])
    # _Block(None) has no .text; _Block("") is falsy -> only "kept" survives.
    assert resp.text == "kept"


# ---------------------------------------------------------------------------
# analyze — error paths
# ---------------------------------------------------------------------------


def test_analyze_frame_read_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_sdk(monkeypatch)
    missing = tmp_path / "does_not_exist.png"
    client = ClaudeVisionClient(api_key="k")
    resp = client.analyze("p", [missing])
    assert not resp.ok
    assert "read" in (resp.error or "")
    assert str(missing) in (resp.error or "")
    # No SDK call should have happened (we failed before constructing content).
    assert _FakeAnthropic.instances == []


def test_analyze_sdk_error_is_captured(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    _patch_sdk(monkeypatch)
    client = ClaudeVisionClient(api_key="k")
    # Warm up to get a handle on the fake, then make create() raise.
    client.analyze("warmup", [_png])
    _FakeAnthropic.instances[0].raise_on_create = RuntimeError("503 overloaded")
    resp = client.analyze("again", [_png])
    assert not resp.ok
    assert "anthropic: 503 overloaded" in (resp.error or "")


def test_analyze_response_parse_error_is_captured(
    monkeypatch: pytest.MonkeyPatch, _png: Path
) -> None:
    """If iterating response.content blows up, it is reported as a parse error."""
    _patch_sdk(monkeypatch)
    client = ClaudeVisionClient(api_key="k")
    client.analyze("warmup", [_png])
    sdk = _FakeAnthropic.instances[0]

    class _Boom:
        @property
        def content(self) -> list[Any]:
            raise ValueError("kaboom")

    sdk.response = _Boom()  # type: ignore[assignment]
    resp = client.analyze("again", [_png])
    assert not resp.ok
    assert "anthropic response parse" in (resp.error or "")


# ---------------------------------------------------------------------------
# _media_type_for
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a.png", "image/png"),
        ("a.PNG", "image/png"),
        ("a.jpg", "image/jpeg"),
        ("a.jpeg", "image/jpeg"),
        ("a.webp", "image/webp"),
        ("a.gif", "image/gif"),
        ("a.bmp", "image/png"),  # unknown extension falls back to PNG
        ("noext", "image/png"),
    ],
)
def test_media_type_for(name: str, expected: str) -> None:
    assert _media_type_for(Path(name)) == expected


def test_claude_response_ok_property() -> None:
    assert ClaudeResponse(text="x", model="m").ok is True
    assert ClaudeResponse(text="", model="m", error="boom").ok is False


def test_module_default_models() -> None:
    assert cc.DEFAULT_PANEL_MODEL == "claude-sonnet-4-6"
