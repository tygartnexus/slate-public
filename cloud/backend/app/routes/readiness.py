"""Operational readiness checks for deployment gates."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db

router = APIRouter(tags=["ops"])

CheckStatus = Literal["pass", "fail"]
OverallStatus = Literal["ready", "blocked"]


class ReadinessCheck(BaseModel):
    name: str
    status: CheckStatus
    detail: str


class ReadinessResponse(BaseModel):
    status: OverallStatus
    checks: list[ReadinessCheck]


REQUIRED_ENV_VARS = (
    "CLERK_JWT_PUBLIC_KEY",
)


@router.get("/ready", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)) -> ReadinessResponse:
    """Return deployment readiness without exposing secret values."""
    settings = get_settings()
    checks: list[ReadinessCheck] = []

    for name in REQUIRED_ENV_VARS:
        value = getattr(settings, name)
        checks.append(
            _check(
                name=name,
                ok=bool(value),
                pass_detail="configured",
                fail_detail="missing",
            )
        )

    checks.append(_database_check(db))

    overall: OverallStatus = (
        "ready" if all(check.status == "pass" for check in checks) else "blocked"
    )
    return ReadinessResponse(status=overall, checks=checks)


def _database_check(db: Session) -> ReadinessCheck:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return ReadinessCheck(
            name="database",
            status="fail",
            detail="query failed",
        )
    return ReadinessCheck(name="database", status="pass", detail="query ok")


def _check(
    *,
    name: str,
    ok: bool,
    pass_detail: str,
    fail_detail: str,
) -> ReadinessCheck:
    return ReadinessCheck(
        name=name,
        status="pass" if ok else "fail",
        detail=pass_detail if ok else fail_detail,
    )
