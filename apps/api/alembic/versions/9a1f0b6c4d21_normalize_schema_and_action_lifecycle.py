"""normalize order items, tracking events, policy evaluations and action lifecycle

Revision ID: 9a1f0b6c4d21
Revises: 3d74bdde4fe4
Create Date: 2026-11-10 00:00:00.000000

This is an incremental revision: the two earlier revisions are left untouched.
It introduces the normalized tables, the append-only policy evaluation log, the
action/verification lifecycle, audit chain metadata and the integrity
constraints, and backfills them from the legacy JSON documents.

Downgrade notes: dropping the new tables destroys action and policy-evaluation
history (it cannot be reconstructed from the JSON snapshots).  Legacy
``orders.items`` / ``shipments.tracking_events`` snapshots are preserved, so the
pre-migration API shape remains readable after a downgrade.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "9a1f0b6c4d21"
down_revision = "3d74bdde4fe4"
branch_labels = None
depends_on = None

GLOBAL_CHAIN_KEY = "__global__"


def _json_type() -> sa.types.TypeEngine[Any]:
    """JSONB on PostgreSQL, plain JSON elsewhere (matches ``app.db.types``)."""
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _mixin_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _parse_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _to_minor(value: Any) -> int:
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1")))
    except (InvalidOperation, TypeError, ValueError):
        return 0


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.now(UTC)
    else:
        parsed = datetime.now(UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------ tables
    op.create_table(
        "order_items",
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("returnable", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        *_mixin_columns(),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint(
            "unit_price_minor >= 0", name="ck_order_items_unit_price_non_negative"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_sku", "order_items", ["sku"])
    op.create_index(op.f("ix_order_items_id"), "order_items", ["id"])

    op.create_table(
        "tracking_events",
        sa.Column("shipment_id", sa.String(length=36), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider_event_id", sa.String(length=128), nullable=True),
        sa.Column("raw_payload", _json_type(), nullable=True),
        *_mixin_columns(),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tracking_events_shipment_timestamp",
        "tracking_events",
        ["shipment_id", "event_timestamp"],
    )
    op.create_index(
        "uq_tracking_events_shipment_provider_event",
        "tracking_events",
        ["shipment_id", "provider_event_id"],
        unique=True,
        postgresql_where=sa.text("provider_event_id IS NOT NULL"),
        sqlite_where=sa.text("provider_event_id IS NOT NULL"),
    )
    op.create_index(op.f("ix_tracking_events_id"), "tracking_events", ["id"])

    op.create_table(
        "policy_evaluations",
        sa.Column("case_id", sa.String(length=36), nullable=True),
        sa.Column("seller_id", sa.String(length=36), nullable=True),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("seller_policy_id", sa.String(length=36), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evaluation_result", _json_type(), nullable=False),
        sa.Column("evaluator_version", sa.String(length=32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        *_mixin_columns(),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["seller_policy_id"], ["seller_policies.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_evaluations_case_id", "policy_evaluations", ["case_id"])
    op.create_index(
        "ix_policy_evaluations_case_evaluated",
        "policy_evaluations",
        ["case_id", "evaluated_at"],
    )
    op.create_index(
        "ix_policy_evaluations_seller_policy_id", "policy_evaluations", ["seller_policy_id"]
    )
    op.create_index("ix_policy_evaluations_decision", "policy_evaluations", ["decision"])
    op.create_index(op.f("ix_policy_evaluations_id"), "policy_evaluations", ["id"])
    op.create_index(op.f("ix_policy_evaluations_seller_id"), "policy_evaluations", ["seller_id"])
    op.create_index(op.f("ix_policy_evaluations_order_id"), "policy_evaluations", ["order_id"])

    op.create_table(
        "actions",
        sa.Column("case_id", sa.String(length=36), nullable=True),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("seller_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("request_payload", _json_type(), nullable=False),
        sa.Column("response_payload", _json_type(), nullable=False),
        sa.Column("initiated_by", sa.String(length=64), nullable=True),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_mixin_columns(),
        sa.CheckConstraint(
            "amount_minor IS NULL OR amount_minor >= 0",
            name="ck_actions_amount_non_negative",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "seller_id", "idempotency_key", name="uq_actions_seller_idempotency"
        ),
    )
    op.create_index("ix_actions_case_id", "actions", ["case_id"])
    op.create_index("ix_actions_order_id", "actions", ["order_id"])
    op.create_index("ix_actions_status", "actions", ["status"])
    op.create_index("ix_actions_action_type", "actions", ["action_type"])
    op.create_index(op.f("ix_actions_id"), "actions", ["id"])
    op.create_index(op.f("ix_actions_approval_id"), "actions", ["approval_id"])

    op.create_table(
        "action_verifications",
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False),
        sa.Column("verification_method", sa.String(length=64), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("provider_response", _json_type(), nullable=False),
        sa.Column("verification_attempt", sa.Integer(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        *_mixin_columns(),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_verifications_action_id", "action_verifications", ["action_id"])
    op.create_index(
        "ix_action_verifications_status", "action_verifications", ["verification_status"]
    )
    op.create_index(op.f("ix_action_verifications_id"), "action_verifications", ["id"])

    op.create_table(
        "audit_chain_state",
        sa.Column("chain_key", sa.String(length=36), nullable=False),
        sa.Column("last_hash", sa.String(length=64), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        *_mixin_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_chain_state_chain_key", "audit_chain_state", ["chain_key"], unique=True
    )
    op.create_index(op.f("ix_audit_chain_state_id"), "audit_chain_state", ["id"])

    # ---------------------------------------------------------------- columns
    with op.batch_alter_table("audit_logs") as batch:
        batch.add_column(sa.Column("chain_key", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("sequence", sa.Integer(), nullable=True))
    op.create_index("ix_audit_logs_chain_key", "audit_logs", ["chain_key"])

    with op.batch_alter_table("approval_requests") as batch:
        batch.add_column(sa.Column("policy_evaluation_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("action_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("requested_amount_minor", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("currency", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("decision_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("approved_by", sa.String(length=36), nullable=True))
    op.create_index(
        "ix_approval_requests_policy_evaluation_id",
        "approval_requests",
        ["policy_evaluation_id"],
    )
    op.create_index("ix_approval_requests_action_id", "approval_requests", ["action_id"])
    op.create_foreign_key(
        "fk_approval_requests_policy_evaluation",
        "approval_requests",
        "policy_evaluations",
        ["policy_evaluation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_approval_requests_approved_by",
        "approval_requests",
        "users",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_approval_requests_seller_status",
        "approval_requests",
        ["seller_id", "status"],
    )

    # -------------------------------------------------------------- backfills
    _backfill_order_items(bind)
    _backfill_tracking_events(bind)
    _backfill_approval_amounts(bind)
    _backfill_audit_chain(bind)

    with op.batch_alter_table("audit_logs") as batch:
        batch.alter_column("chain_key", existing_type=sa.String(length=36), nullable=False)
        batch.alter_column("sequence", existing_type=sa.Integer(), nullable=False)

    # ----------------------------------------------------------- constraints
    duplicate_orders = bind.execute(
        sa.text(
            "SELECT seller_id, order_number, COUNT(*) AS n FROM orders "
            "GROUP BY seller_id, order_number HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicate_orders:
        detail = ", ".join(f"{row.order_number} (x{row.n})" for row in duplicate_orders)
        raise RuntimeError(
            "Cannot enforce unique (seller_id, order_number): duplicate order numbers "
            f"exist and must be resolved manually before migrating: {detail}"
        )

    op.create_unique_constraint(
        "uq_orders_seller_order_number", "orders", ["seller_id", "order_number"]
    )
    op.create_unique_constraint(
        "uq_orders_id_seller_id", "orders", ["id", "seller_id"]
    )

    # Collapse multiple active policies before enforcing "one active per seller".
    bind.execute(
        sa.text(
            "UPDATE seller_policies SET is_active = false "
            "WHERE is_active = true AND id NOT IN ("
            "  SELECT id FROM ("
            "    SELECT id, ROW_NUMBER() OVER ("
            "      PARTITION BY seller_id ORDER BY version DESC, created_at DESC"
            "    ) AS rn FROM seller_policies WHERE is_active = true"
            "  ) ranked WHERE rn = 1"
            ")"
        )
    )
    op.create_unique_constraint(
        "uq_seller_policies_seller_version",
        "seller_policies",
        ["seller_id", "version"],
    )
    op.create_index(
        "uq_seller_policies_one_active",
        "seller_policies",
        ["seller_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_seller_policies_seller_active", "seller_policies", ["seller_id", "is_active"]
    )

    cross_tenant_cases = bind.execute(
        sa.text(
            "SELECT c.id FROM cases c JOIN orders o ON o.id = c.order_id "
            "WHERE o.seller_id <> c.seller_id"
        )
    ).fetchall()
    if cross_tenant_cases:
        raise RuntimeError(
            "Cannot enforce the case -> order seller constraint: cases reference orders "
            "owned by another seller: "
            + ", ".join(str(row.id) for row in cross_tenant_cases)
        )
    op.create_foreign_key(
        "fk_cases_seller_order",
        "cases",
        "orders",
        ["seller_id", "order_id"],
        ["seller_id", "id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_cases_seller_order", "cases", ["seller_id", "order_id"])

    op.create_unique_constraint(
        "uq_audit_logs_chain_sequence", "audit_logs", ["chain_key", "sequence"]
    )


def _backfill_order_items(bind: sa.engine.Connection) -> None:
    rows = bind.execute(
        sa.text("SELECT id, items, created_at, updated_at FROM orders")
    ).mappings()
    for row in rows:
        items = _parse_json(row["items"], [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            quantity = int(item.get("quantity") or 1)
            if quantity <= 0:
                quantity = 1
            bind.execute(
                sa.text(
                    "INSERT INTO order_items "
                    "(id, order_id, sku, title, quantity, unit_price_minor, returnable, "
                    " category, created_at, updated_at) "
                    "VALUES (:id, :order_id, :sku, :title, :quantity, :unit_price_minor, "
                    " :returnable, :category, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "order_id": row["id"],
                    "sku": item.get("sku"),
                    "title": str(item.get("title") or item.get("name") or "Item"),
                    "quantity": quantity,
                    "unit_price_minor": _to_minor(
                        item.get("unit_price", item.get("price", 0))
                    ),
                    "returnable": bool(item.get("returnable", True)),
                    "category": item.get("category"),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
            )


def _backfill_tracking_events(bind: sa.engine.Connection) -> None:
    rows = bind.execute(
        sa.text("SELECT id, tracking_events, created_at, updated_at FROM shipments")
    ).mappings()
    for row in rows:
        events = _parse_json(row["tracking_events"], [])
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO tracking_events "
                    "(id, shipment_id, event_timestamp, status, location, description, "
                    " provider_event_id, raw_payload, created_at, updated_at) "
                    "VALUES (:id, :shipment_id, :event_timestamp, :status, :location, "
                    " :description, :provider_event_id, :raw_payload, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "shipment_id": row["id"],
                    "event_timestamp": _parse_timestamp(event.get("timestamp")),
                    "status": str(event.get("status") or "unknown"),
                    "location": event.get("location"),
                    "description": event.get("description"),
                    "provider_event_id": event.get("provider_event_id"),
                    "raw_payload": json.dumps(event),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
            )


def _backfill_approval_amounts(bind: sa.engine.Connection) -> None:
    rows = bind.execute(
        sa.text(
            "SELECT a.id, a.requested_action, o.currency AS order_currency "
            "FROM approval_requests a "
            "JOIN cases c ON c.id = a.case_id "
            "LEFT JOIN orders o ON o.id = c.order_id"
        )
    ).mappings()
    for row in rows:
        action = _parse_json(row["requested_action"], {})
        if not isinstance(action, dict):
            action = {}
        amount = action.get("amount")
        bind.execute(
            sa.text(
                "UPDATE approval_requests SET requested_amount_minor = :amount, "
                "currency = :currency WHERE id = :id"
            ),
            {
                "id": row["id"],
                "amount": _to_minor(amount) if amount is not None else None,
                "currency": action.get("currency") or row["order_currency"],
            },
        )


def _backfill_audit_chain(bind: sa.engine.Connection) -> None:
    rows = bind.execute(
        sa.text("SELECT id, seller_id, timestamp FROM audit_logs ORDER BY timestamp ASC, id ASC")
    ).mappings()

    sequence_by_chain: dict[str, int] = {}
    head_by_chain: dict[str, tuple[str, int]] = {}

    for row in rows:
        chain_key = row["seller_id"] or GLOBAL_CHAIN_KEY
        sequence = sequence_by_chain.get(chain_key, 0) + 1
        sequence_by_chain[chain_key] = sequence
        bind.execute(
            sa.text("UPDATE audit_logs SET chain_key = :chain_key, sequence = :sequence WHERE id = :id"),
            {"chain_key": chain_key, "sequence": sequence, "id": row["id"]},
        )
        head_by_chain[chain_key] = ("", sequence)

    now = datetime.now(UTC)
    for chain_key, (_, sequence) in head_by_chain.items():
        last_hash = bind.execute(
            sa.text(
                "SELECT current_hash FROM audit_logs "
                "WHERE chain_key = :chain_key ORDER BY sequence DESC LIMIT 1"
            ),
            {"chain_key": chain_key},
        ).scalar_one()
        bind.execute(
            sa.text(
                "INSERT INTO audit_chain_state "
                "(id, chain_key, last_hash, last_sequence, created_at, updated_at) "
                "VALUES (:id, :chain_key, :last_hash, :last_sequence, :created_at, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "chain_key": chain_key,
                "last_hash": last_hash,
                "last_sequence": sequence,
                "created_at": now,
                "now": now,
            },
        )


def downgrade() -> None:
    op.drop_constraint("uq_audit_logs_chain_sequence", "audit_logs", type_="unique")
    op.drop_index("ix_cases_seller_order", table_name="cases")
    op.drop_constraint("fk_cases_seller_order", "cases", type_="foreignkey")
    op.drop_index("ix_seller_policies_seller_active", table_name="seller_policies")
    op.drop_index("uq_seller_policies_one_active", table_name="seller_policies")
    op.drop_constraint(
        "uq_seller_policies_seller_version", "seller_policies", type_="unique"
    )
    op.drop_constraint("uq_orders_id_seller_id", "orders", type_="unique")
    op.drop_constraint("uq_orders_seller_order_number", "orders", type_="unique")

    op.drop_index("ix_approval_requests_seller_status", table_name="approval_requests")
    op.drop_constraint(
        "fk_approval_requests_approved_by", "approval_requests", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_approval_requests_policy_evaluation", "approval_requests", type_="foreignkey"
    )
    op.drop_index("ix_approval_requests_action_id", table_name="approval_requests")
    op.drop_index(
        "ix_approval_requests_policy_evaluation_id", table_name="approval_requests"
    )
    with op.batch_alter_table("approval_requests") as batch:
        batch.drop_column("approved_by")
        batch.drop_column("expires_at")
        batch.drop_column("decision_reason")
        batch.drop_column("currency")
        batch.drop_column("requested_amount_minor")
        batch.drop_column("action_id")
        batch.drop_column("policy_evaluation_id")

    op.drop_index("ix_audit_logs_chain_key", table_name="audit_logs")
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_column("sequence")
        batch.drop_column("chain_key")

    op.drop_table("audit_chain_state")
    op.drop_table("action_verifications")
    op.drop_table("actions")
    op.drop_table("policy_evaluations")
    op.drop_table("tracking_events")
    op.drop_table("order_items")
