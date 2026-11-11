"""add case workflow state

Revision ID: d5e6f7a8b9c0
Revises: c4b7e2d9a1f3
Create Date: 2026-11-11 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d5e6f7a8b9c0"
down_revision = "c4b7e2d9a1f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cases") as batch:
        batch.add_column(
            sa.Column(
                "workflow_state",
                sa.String(length=32),
                nullable=False,
                server_default="intake",
            )
        )
    op.create_index("ix_cases_workflow_state", "cases", ["workflow_state"])


def downgrade() -> None:
    op.drop_index("ix_cases_workflow_state", table_name="cases")
    with op.batch_alter_table("cases") as batch:
        batch.drop_column("workflow_state")
