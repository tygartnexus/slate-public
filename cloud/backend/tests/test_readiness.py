"""Operational readiness endpoint tests."""

from __future__ import annotations

from tests.conftest import Ctx


def _checks_by_name(body: dict) -> dict[str, dict]:
    return {check["name"]: check for check in body["checks"]}


def test_ready_endpoint_passes_with_test_configuration(ctx: Ctx) -> None:
    resp = ctx.client.get("/ready")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"

    checks = _checks_by_name(body)
    assert checks["CLERK_JWT_PUBLIC_KEY"]["status"] == "pass"
    assert checks["database"]["status"] == "pass"
    assert "STRIPE_API_KEY" not in checks
    assert "issuer_private_key_file" not in checks


def test_ready_endpoint_blocks_when_required_env_missing(ctx: Ctx, monkeypatch) -> None:
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", "")

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        resp = ctx.client.get("/ready")
    finally:
        get_settings.cache_clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "blocked"
    assert _checks_by_name(body)["CLERK_JWT_PUBLIC_KEY"] == {
        "name": "CLERK_JWT_PUBLIC_KEY",
        "status": "fail",
        "detail": "missing",
    }
