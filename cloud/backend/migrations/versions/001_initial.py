"""initial accounts/verdicts tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-05-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("clerk_user_id", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_accounts_clerk_user_id", "accounts", ["clerk_user_id"])
    op.create_index("ix_accounts_email", "accounts", ["email"])

    op.create_table(
        "verdicts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("account_id", sa.String(32), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("shot_id", sa.String(255), nullable=False),
        sa.Column("final_status", sa.String(32), nullable=False),
        sa.Column("has_panel_review", sa.Boolean, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verdicts_account_id", "verdicts", ["account_id"])
    op.create_index("ix_verdicts_shot_id", "verdicts", ["shot_id"])
    op.create_index("ix_verdicts_final_status", "verdicts", ["final_status"])
    op.create_index("ix_verdicts_submitted_at", "verdicts", ["submitted_at"])
    op.create_index(
        "ix_verdicts_account_submitted",
        "verdicts",
        ["account_id", sa.text("submitted_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("verdicts")
    op.drop_table("accounts")
