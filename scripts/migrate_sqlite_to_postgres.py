#!/usr/bin/env python3
"""Copy an existing SellerResolve SQLite database into PostgreSQL.

The schema itself is created by Alembic (``alembic upgrade head``); this script
only moves rows, preserving primary keys so foreign keys stay valid.  It refuses
to write into a non-empty target unless ``--truncate-target`` is passed.

Usage (from apps/api, with the PostgreSQL database already migrated):

    python ../../scripts/migrate_sqlite_to_postgres.py --sqlite ./sellerresolve.db
    python ../../scripts/migrate_sqlite_to_postgres.py --sqlite ./old.db \\
        --postgres postgresql+psycopg://user:pass@localhost:5432/sellerresolve

Exit codes: 0 success, 1 invalid input/target, 2 verification failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    MetaData,
    Table,
    create_engine,
    func,
    inspect,
    select,
)
from sqlalchemy.engine import Engine

# Reuse the single normalization rules the application uses for legacy JSON.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))
from app.services.orders import normalize_legacy_item  # noqa: E402

# Parent tables before children (foreign-key safe).
TABLE_ORDER = [
    "users",
    "buyers",
    "sellers",
    "seller_operations",
    "seller_policies",
    "orders",
    "order_items",
    "seller_customer_links",
    "shipments",
    "tracking_events",
    "cases",
    "policy_evaluations",
    "actions",
    "action_verifications",
    "approval_requests",
    "case_messages",
    "file_uploads",
    "audit_logs",
]

# Managed by Alembic, or rebuilt from the copied audit rows.
SKIPPED_TABLES = {"alembic_version", "audit_chain_state"}

BATCH_SIZE = 500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, help="Path to the source SQLite file")
    parser.add_argument(
        "--postgres",
        default=os.environ.get("DATABASE_URL"),
        help="Target PostgreSQL URL (defaults to $DATABASE_URL)",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete existing rows in the copied tables before inserting",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and report only")
    return parser.parse_args()


def convert_value(value: Any, column_type: Any) -> Any:
    """Normalize SQLite storage types for PostgreSQL."""
    if value is None:
        return None
    if isinstance(column_type, JSON):
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, (str, bytes)):
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return None
        return None
    if isinstance(column_type, DateTime):
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    if isinstance(column_type, Boolean):
        return bool(value)
    return value


def table_rows(
    engine: Engine, table: Table, columns: list[str] | None = None
) -> list[dict[str, Any]]:
    selection = [table.c[name] for name in columns] if columns else list(table.c)
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(select(*selection)).mappings()]


def assign_audit_chain(rows: list[dict[str, Any]]) -> None:
    """Populate chain_key/sequence for a legacy audit log that predates them.

    Sequence numbers follow timestamp order (the order the original global chain
    was written); the stored hashes and payloads are copied unchanged.
    """
    rows.sort(key=lambda row: (str(row.get("timestamp") or ""), str(row.get("id"))))
    sequence_by_chain: dict[str, int] = {}
    for row in rows:
        chain_key = row.get("seller_id") or "__global__"
        sequence = sequence_by_chain.get(str(chain_key), 0) + 1
        sequence_by_chain[str(chain_key)] = sequence
        row["chain_key"] = chain_key
        row["sequence"] = sequence


def rebuild_audit_chain(target: Engine, audit_logs: Table) -> int:
    """Recreate the per-chain head rows from the copied audit log."""
    with target.begin() as connection:
        rows = connection.execute(
            select(audit_logs.c.chain_key, audit_logs.c.sequence, audit_logs.c.current_hash)
            .order_by(audit_logs.c.chain_key, audit_logs.c.sequence)
        ).all()

        heads: dict[str, tuple[str, int]] = {}
        for chain_key, sequence, current_hash in rows:
            heads[str(chain_key)] = (str(current_hash), int(sequence))

        state = Table("audit_chain_state", audit_logs.metadata, autoload_with=target, extend_existing=True)
        now = datetime.now(UTC)
        for chain_key, (last_hash, last_sequence) in heads.items():
            connection.execute(
                state.insert().values(
                    id=_uuid(),
                    chain_key=chain_key,
                    last_hash=last_hash,
                    last_sequence=last_sequence,
                    created_at=now,
                    updated_at=now,
                )
            )
        return len(heads)


def _uuid() -> str:
    import uuid

    return str(uuid.uuid4())


def backfill_policy_metadata(target: Engine) -> None:
    """Derive publication metadata for copied legacy policy versions.

    Legacy rows do not have ``currency``/``content_sha256``/``source``.  The
    migration handles rows that existed before it ran; this covers rows copied
    afterwards from an old SQLite database.
    """
    metadata = MetaData()
    metadata.reflect(bind=target, only=["seller_policies"])
    policies = metadata.tables["seller_policies"]
    if "currency" not in policies.c:
        return

    with target.begin() as connection:
        rows = connection.execute(
            select(policies.c.id, policies.c.parsed_rules, policies.c.policy_yaml)
        ).mappings().all()
        for row in rows:
            rules = row["parsed_rules"]
            if isinstance(rules, str):
                try:
                    rules = json.loads(rules)
                except ValueError:
                    rules = {}
            if not isinstance(rules, dict):
                rules = {}
            currency = str(rules.get("currency") or "INR").strip().upper()[:3] or "INR"
            digest = hashlib.sha256(
                (row["policy_yaml"] or "").encode("utf-8")
            ).hexdigest()
            connection.execute(
                policies.update()
                .where(policies.c.id == row["id"])
                .values(currency=currency, content_sha256=digest, source="legacy")
            )


def backfill_normalized_rows(target: Engine) -> None:
    """Populate normalized tables for sources written before the refactor.

    A legacy SQLite database has no ``order_items``/``tracking_events`` tables,
    so the copied rows are normalized here from the legacy JSON snapshots using
    the application's own conversion rules.
    """
    metadata = MetaData()
    metadata.reflect(bind=target, only=["orders", "order_items", "shipments", "tracking_events"])
    orders = metadata.tables["orders"]
    order_items = metadata.tables["order_items"]
    shipments = metadata.tables["shipments"]
    tracking_events = metadata.tables["tracking_events"]

    inserted_items = 0
    with target.begin() as connection:
        order_rows = connection.execute(
            select(
                orders.c.id,
                orders.c["items"],
                orders.c.created_at,
                orders.c.updated_at,
            )
        ).mappings().all()
        for order in order_rows:
            has_rows = connection.execute(
                select(func.count()).select_from(order_items).where(
                    order_items.c.order_id == order["id"]
                )
            ).scalar_one()
            if has_rows:
                continue
            items = convert_value(order["items"], JSON())
            for index, raw in enumerate(items if isinstance(items, list) else []):
                if not isinstance(raw, dict):
                    continue
                normalized = normalize_legacy_item(raw, index)
                connection.execute(
                    order_items.insert().values(
                        id=_uuid(),
                        order_id=order["id"],
                        sku=normalized["sku"],
                        title=normalized["title"],
                        quantity=normalized["quantity"],
                        unit_price_minor=normalized["unit_price_minor"],
                        returnable=normalized["returnable"],
                        category=normalized["category"],
                        created_at=order["created_at"],
                        updated_at=order["updated_at"],
                    )
                )
                inserted_items += 1

    inserted_events = 0
    with target.begin() as connection:
        shipment_rows = connection.execute(
            select(
                shipments.c.id,
                shipments.c.tracking_events,
                shipments.c.created_at,
                shipments.c.updated_at,
            )
        ).mappings().all()
        for shipment in shipment_rows:
            has_rows = connection.execute(
                select(func.count()).select_from(tracking_events).where(
                    tracking_events.c.shipment_id == shipment["id"]
                )
            ).scalar_one()
            if has_rows:
                continue
            events = convert_value(shipment["tracking_events"], JSON())
            for raw in events if isinstance(events, list) else []:
                if not isinstance(raw, dict):
                    continue
                timestamp = convert_value(raw.get("timestamp"), DateTime())
                connection.execute(
                    tracking_events.insert().values(
                        id=_uuid(),
                        shipment_id=shipment["id"],
                        event_timestamp=timestamp or shipment["created_at"],
                        status=str(raw.get("status") or "unknown"),
                        location=raw.get("location"),
                        description=raw.get("description"),
                        provider_event_id=raw.get("provider_event_id"),
                        raw_payload=raw,
                        created_at=shipment["created_at"],
                        updated_at=shipment["updated_at"],
                    )
                )
                inserted_events += 1

    print(
        f"backfilled normalized rows: {inserted_items} order item(s), "
        f"{inserted_events} tracking event(s)"
    )


def main() -> int:
    args = parse_args()
    source_path = Path(args.sqlite).expanduser().resolve()
    if not source_path.exists():
        print(f"error: SQLite database not found: {source_path}", file=sys.stderr)
        return 1

    if not args.postgres:
        print("error: no target PostgreSQL URL (--postgres or DATABASE_URL)", file=sys.stderr)
        return 1
    if args.postgres.startswith("sqlite"):
        print("error: --postgres must point at PostgreSQL, not SQLite", file=sys.stderr)
        return 1

    source = create_engine(f"sqlite:///{source_path.as_posix()}")
    target = create_engine(args.postgres)

    source_tables = set(inspect(source).get_table_names())
    target_tables = set(inspect(target).get_table_names())

    missing_source = [name for name in TABLE_ORDER if name not in source_tables]
    missing_target = [
        name for name in [*TABLE_ORDER, *SKIPPED_TABLES] if name not in target_tables
    ]
    if missing_target:
        print(
            "error: target schema is not migrated; missing tables: "
            + ", ".join(sorted(missing_target))
            + ". Run 'alembic upgrade head' first.",
            file=sys.stderr,
        )
        return 1
    if missing_source:
        print(
            "warning: source database has no rows for: " + ", ".join(missing_source),
            file=sys.stderr,
        )

    metadata = MetaData()
    metadata.reflect(bind=target, only=TABLE_ORDER)
    tables = {name: metadata.tables[name] for name in TABLE_ORDER}

    source_columns = {
        name: {column["name"] for column in inspect(source).get_columns(name)}
        for name in TABLE_ORDER
        if name in source_tables
    }

    counts: dict[str, int] = {}
    existing: dict[str, int] = {}
    rows_by_table: dict[str, list[dict[str, Any]]] = {}
    columns_by_table: dict[str, list[str]] = {}
    for name, table in tables.items():
        if name in source_tables:
            column_names = [
                column.name for column in table.columns if column.name in source_columns[name]
            ]
            if name == "audit_logs":
                for required in ("chain_key", "sequence"):
                    if required not in source_columns[name]:
                        column_names.append(required)
            rows = table_rows(
                source,
                table,
                [column for column in column_names if column in source_columns[name]]
                or None,
            )
            if name == "audit_logs":
                assign_audit_chain(rows)
            columns_by_table[name] = column_names
            rows_by_table[name] = rows
            counts[name] = len(rows)
        else:
            counts[name] = 0
        with target.connect() as connection:
            existing[name] = connection.execute(
                select(func.count()).select_from(table)
            ).scalar_one()

    print("Planned copy (source -> target):")
    for name in TABLE_ORDER:
        print(f"  {name:<24} {counts[name]:>6} rows   target currently {existing[name]}")

    if args.dry_run:
        print("dry run: no rows written")
        return 0

    occupied = {name: count for name, count in existing.items() if count}
    if occupied and not args.truncate_target:
        print(
            "error: target tables are not empty: "
            + ", ".join(f"{name}={count}" for name, count in occupied.items())
            + ". Re-run with --truncate-target or use an empty database/schema.",
            file=sys.stderr,
        )
        return 1

    with target.begin() as connection:
        if args.truncate_target:
            for name in reversed(TABLE_ORDER):
                connection.execute(tables[name].delete())

    for name in TABLE_ORDER:
        if not counts[name]:
            continue
        table = tables[name]
        rows = rows_by_table[name]
        converted = [
            {
                column.name: convert_value(row.get(column.name), column.type)
                for column in table.columns
                if column.name in columns_by_table[name]
            }
            for row in rows
        ]
        with target.begin() as connection:
            for start in range(0, len(converted), BATCH_SIZE):
                connection.execute(
                    table.insert(), converted[start : start + BATCH_SIZE]
                )
        print(f"copied {name}: {len(converted)} rows")

    backfill_normalized_rows(target)
    backfill_policy_metadata(target)

    chains = rebuild_audit_chain(target, tables["audit_logs"])
    print(f"rebuilt {chains} audit chain head row(s)")

    failures = []
    for name, table in tables.items():
        with target.connect() as connection:
            target_count = connection.execute(
                select(func.count()).select_from(table)
            ).scalar_one()
        if name not in source_tables:
            # Normalized tables are backfilled from the legacy JSON snapshots.
            continue
        if target_count != counts[name]:
            failures.append(f"{name}: source={counts[name]} target={target_count}")
    if failures:
        print("error: row-count verification failed: " + "; ".join(failures), file=sys.stderr)
        return 2

    print("verification: row counts match for every table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
