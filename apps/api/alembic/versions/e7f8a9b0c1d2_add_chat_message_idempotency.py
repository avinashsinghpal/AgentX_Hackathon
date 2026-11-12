"""add chat message idempotency

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-11-12 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "case_messages",
        sa.Column("client_message_id", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_case_messages_client_request",
        "case_messages",
        ["case_id", "sender_role", "client_message_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_case_messages_client_request",
        "case_messages",
        type_="unique",
    )
    op.drop_column("case_messages", "client_message_id")
