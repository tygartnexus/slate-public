"""Backend test harness.

Strategy:
* In-memory SQLite (StaticPool) instead of Postgres — no Docker needed.
* Dependency overrides for ``get_db`` (test session) and ``current_account``
  (a seeded test account — bypasses Clerk JWT verification).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@dataclass
class Ctx:
    client: TestClient
    account_id: str


@pytest.fixture
def ctx(tmp_path, monkeypatch) -> Ctx:
    _ = tmp_path

    # 1. Env → settings (clear the lru_cache so they take effect).
    monkeypatch.setenv("CLERK_JWT_PUBLIC_KEY", "test-clerk-public-key")

    from app.config import get_settings

    get_settings.cache_clear()

    # 2. In-memory SQLite shared across connections. Import the models module
    #    BEFORE create_all so every table is registered on Base.metadata.
    from app.db import Base, get_db
    from app.models import Account  # noqa: F401 — registers tables on Base.metadata

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, future=True)

    # 3. Seed one account.

    seed = TestSession()
    account = Account(clerk_user_id="clerk_test_user", email="test@example.com")
    seed.add(account)
    seed.commit()
    account_id = account.id
    seed.close()

    # 4. Dependency overrides.
    from app.auth.clerk import current_account
    from app.main import app

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    def override_current_account(db: Session = Depends(get_db)) -> Account:
        return db.query(Account).filter(Account.id == account_id).one()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_account] = override_current_account

    client = TestClient(app)
    try:
        yield Ctx(client=client, account_id=account_id)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
