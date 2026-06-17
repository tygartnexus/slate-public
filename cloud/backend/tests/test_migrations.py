"""Migration smoke tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_head_with_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "slate_cloud_test.db"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "DATABASE_URL": f"sqlite:///{db_path.as_posix()}",
            "CLERK_JWT_PUBLIC_KEY": "test-key",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert db_path.exists()
