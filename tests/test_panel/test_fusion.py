"""Tests for the fusion rules that combine PersonaVerdicts into PanelVerdict."""

from __future__ import annotations

from slate.panel.fusion import fuse
from slate.panel.verdict import PersonaFlag, PersonaVerdict


def _persona(
    name: str,
    *,
    publish_ready: bool = True,
    flags: list[PersonaFlag] | None = None,
    error: str | None = None,
) -> PersonaVerdict:
    return PersonaVerdict(
        name=name,
        model="m",
        publish_ready=publish_ready,
        flags=flags or [],
        error=error,
    )


def test_all_pass_yields_publish_ready() -> None:
    personas = [_persona("a"), _persona("b"), _persona("c"), _persona("d")]
    fused = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    assert fused.publish_ready is True
    assert fused.fused_critical_flags == []
    assert fused.fused_high_flags == []
    assert fused.response_quality is not None
    assert fused.response_quality.tradeoffs
    assert any("response_quality" in item for item in fused.response_quality.unknowns)


def test_single_critical_blocks_publish() -> None:
    personas = [
        _persona("a"),
        _persona(
            "b",
            publish_ready=False,
            flags=[
                PersonaFlag(category="x", severity="critical", description="blocking")
            ],
        ),
        _persona("c"),
        _persona("d"),
    ]
    fused = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    assert fused.publish_ready is False
    assert len(fused.fused_critical_flags) == 1
    assert fused.response_quality is not None
    assert "Do not publish" in fused.response_quality.recommendation


def test_two_high_flags_from_same_persona_blocks_publish() -> None:
    personas = [
        _persona(
            "a",
            flags=[
                PersonaFlag(category="x", severity="high", description="1"),
                PersonaFlag(category="y", severity="high", description="2"),
            ],
        ),
        _persona("b"),
        _persona("c"),
        _persona("d"),
    ]
    fused = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    assert fused.publish_ready is False
    assert len(fused.fused_high_flags) == 2


def test_one_high_flag_does_not_block_publish() -> None:
    personas = [
        _persona(
            "a",
            flags=[
                PersonaFlag(category="x", severity="high", description="just one")
            ],
        ),
        _persona("b"),
        _persona("c"),
        _persona("d"),
    ]
    fused = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    assert fused.publish_ready is True
    assert len(fused.fused_high_flags) == 1


def test_errored_persona_does_not_contribute_vote() -> None:
    """An errored persona neither passes nor blocks — the engine surfaces
    INDETERMINATE at the EnhancedVerdict layer, not the fusion layer."""
    personas = [
        _persona("a", publish_ready=False, error="provider boom"),
        _persona("b"),
        _persona("c"),
        _persona("d"),
    ]
    fused = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    # b/c/d all passed; the errored a is ignored in vote counting.
    assert fused.publish_ready is True
    assert fused.response_quality is not None
    assert "Do not publish from this Panel result" in fused.response_quality.recommendation


def test_persona_publish_ready_false_without_critical_still_blocks() -> None:
    """A persona that returns publish_ready=false but with no critical flags
    still counts as a publish-block vote."""
    personas = [
        _persona("a", publish_ready=False, flags=[]),
        _persona("b"),
        _persona("c"),
        _persona("d"),
    ]
    fused = fuse(personas, slate_version="0.1.0", duration_seconds=1.0)
    assert fused.publish_ready is False
