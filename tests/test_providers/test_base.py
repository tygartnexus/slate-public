"""Tests for shared provider helpers — JSON parsing and base64 encoding."""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from slate.providers.base import encode_image_b64, parse_strict_json


def test_parse_clean_json() -> None:
    out = parse_strict_json('{"character_visible": true, "lighting_quality": 4}', "test")
    assert out["character_visible"] is True
    assert out["lighting_quality"] == 4


def test_parse_strips_markdown_fence() -> None:
    raw = "```json\n{\"character_visible\": true}\n```"
    out = parse_strict_json(raw, "test")
    assert out["character_visible"] is True


def test_parse_strips_prose() -> None:
    raw = 'Sure! Here is the JSON:\n{"character_visible": false}\nLet me know if...'
    out = parse_strict_json(raw, "test")
    assert out["character_visible"] is False


def test_parse_flattens_nested_categories() -> None:
    """Some models wrap signals under category headers — engine expects flat keys."""
    raw = """
    {
      "CORRECTNESS": {"character_visible": true},
      "WARDROBE": {"wardrobe_present": false}
    }
    """
    out = parse_strict_json(raw, "test")
    assert out["character_visible"] is True
    assert out["wardrobe_present"] is False


def test_parse_preserves_response_quality_object() -> None:
    raw = """
    {
      "CORRECTNESS": {"character_visible": true},
      "response_quality": {
        "facts": ["saw a character"],
        "assumptions": ["manifest is right"],
        "unknowns": ["unsampled frames"],
        "confidence_score": 0.7,
        "evidence": ["frame_0000.png"],
        "risks": ["partial occlusion"],
        "counterarguments": ["could be readable in motion"],
        "recommendation": "review the frame",
        "tradeoffs": ["more frames cost time"],
        "what_would_change_recommendation": ["full-sequence review"]
      }
    }
    """
    out = parse_strict_json(raw, "test")
    assert out["character_visible"] is True
    assert isinstance(out["response_quality"], dict)
    assert out["response_quality"]["confidence_score"] == 0.7


def test_parse_returns_error_for_garbage() -> None:
    out = parse_strict_json("this is not json at all", "test")
    assert "error" in out
    assert "raw" in out


def test_parse_returns_error_for_non_object_json() -> None:
    """Valid JSON that isn't an object (e.g. a top-level array) is rejected."""
    out = parse_strict_json("[1, 2, 3]", "test-model")
    assert out["error"] == "test-model did not return a JSON object"
    assert out["raw"] == "[1, 2, 3]"


def test_encode_image_b64_returns_ascii(tmp_path: Path) -> None:
    p = tmp_path / "tiny.png"
    Image.new("RGB", (4, 4), (255, 0, 0)).save(p, "PNG")
    encoded = encode_image_b64(p)
    assert isinstance(encoded, str)
    assert len(encoded) > 0
    # Standard base64 charset only.
    assert all(c.isalnum() or c in "+/=" for c in encoded)


def test_encode_image_b64_downscales_large(tmp_path: Path) -> None:
    """A frame larger than max_dim is downscaled so its longest side == max_dim."""
    p = tmp_path / "big.png"
    Image.new("RGB", (3000, 2000), (0, 128, 255)).save(p, "PNG")
    decoded = Image.open(io.BytesIO(base64.b64decode(encode_image_b64(p, max_dim=1024))))
    assert max(decoded.size) == 1024
    assert decoded.size == (1024, 683)  # aspect ratio preserved


def test_encode_image_b64_no_upscale_small(tmp_path: Path) -> None:
    """A frame already within max_dim keeps its native size."""
    p = tmp_path / "small.png"
    Image.new("RGB", (640, 480), (0, 0, 0)).save(p, "PNG")
    decoded = Image.open(io.BytesIO(base64.b64decode(encode_image_b64(p, max_dim=1024))))
    assert decoded.size == (640, 480)


def test_encode_image_b64_disabled_returns_raw(tmp_path: Path) -> None:
    """max_dim of None or 0 encodes the original bytes unchanged."""
    p = tmp_path / "raw.png"
    Image.new("RGB", (2048, 2048), (1, 2, 3)).save(p, "PNG")
    raw_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    assert encode_image_b64(p) == raw_b64
    assert encode_image_b64(p, max_dim=0) == raw_b64


def test_encode_image_b64_falls_back_when_resize_fails(tmp_path: Path) -> None:
    """Unreadable image bytes with downscaling on encode the raw bytes instead
    of failing — the resize path is strictly best-effort."""
    p = tmp_path / "corrupt.png"
    p.write_bytes(b"not a real image payload")
    expected = base64.b64encode(b"not a real image payload").decode("ascii")
    assert encode_image_b64(p, max_dim=512) == expected
