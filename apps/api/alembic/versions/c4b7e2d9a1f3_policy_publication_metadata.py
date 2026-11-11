"""policy publication metadata (currency, checksum, source, publisher)

Revision ID: c4b7e2d9a1f3
Revises: 9a1f0b6c4d21
Create Date: 2026-11-10 00:00:00.000000

Adds the metadata a published policy version needs to be auditable: the explicit
currency of its monetary thresholds, a SHA-256 checksum of the canonical YAML,
the input source (structured form or edited YAML) and the publishing user.

Downgrade notes: the columns are dropped, so the checksum/source/publisher are
lost.  The policy documents, parsed rules and versions themselves are untouched.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "c4b7e2d9a1f3"
down_revision = "9a1f0b6c4d21"
branch_labels = None
depends_on = None


def _parse_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def upgrade() -> None:
    op.add_column(
        "seller_policies",
        sa.Column("currency", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "seller_policies",
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "seller_policies",
        sa.Column("source", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "seller_policies",
        sa.Column(
            "published_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_seller_policies_published_by_user_id",
        "seller_policies",
        ["published_by_user_id"],
    )

    bind = op.get_bind()
    rows = (
        bind.execute(sa.text("SELECT id, parsed_rules, policy_yaml FROM seller_policies"))
        .mappings()
        .all()
    )
    for row in rows:
        rules = _parse_json(row["parsed_rules"])
        currency = str(rules.get("currency") or "INR").strip().upper()[:3] or "INR"
        digest = hashlib.sha256((row["policy_yaml"] or "").encode("utf-8")).hexdigest()
        bind.execute(
            sa.text(
                "UPDATE seller_policies "
                "SET currency = :currency, content_sha256 = :digest, source = 'legacy' "
                "WHERE id = :id"
            ),
            {"currency": currency, "digest": digest, "id": row["id"]},
        )

    with op.batch_alter_table("seller_policies") as batch:
        batch.alter_column(
            "currency",
            existing_type=sa.String(length=3),
            nullable=False,
            server_default="INR",
        )


def downgrade() -> None:
    op.drop_index(
        "ix_seller_policies_published_by_user_id",
        table_name="seller_policies",
    )
    with op.batch_alter_table("seller_policies") as batch:
        batch.drop_column("published_by_user_id")
        batch.drop_column("source")
        batch.drop_column("content_sha256")
        batch.drop_column("currency")
