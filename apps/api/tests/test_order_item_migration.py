"""Order-item normalization tests.

``order_items`` is authoritative, the legacy ``orders.items`` JSON is a snapshot,
and readers fall back to the snapshot for rows written before the migration.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.order_item import OrderItem
from app.services.orders import (
    item_price_minor_from_legacy,
    order_items_payload,
    sync_order_items,
)
from tests.factories import make_buyer, make_order, make_seller


def test_legacy_integer_prices_are_already_minor_units() -> None:
    assert item_price_minor_from_legacy({"unit_price": 4500}) == 4500


def test_legacy_float_prices_are_major_units() -> None:
    assert item_price_minor_from_legacy({"unit_price": 45.0}) == 4500
    assert item_price_minor_from_legacy({"total_price": 89.5}) == 8950


def test_sync_replaces_rows_without_duplicating(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(
        db,
        seller,
        buyer,
        items=[
            {"sku": "A", "title": "Alpha", "quantity": 2, "unit_price": 10.0},
            {"sku": "B", "title": "Beta", "quantity": 1, "unit_price": 5.0},
        ],
    )

    sync_order_items(db, order, order.items)
    sync_order_items(db, order, order.items)

    rows = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    assert len(rows) == 2
    assert {row.sku for row in rows} == {"A", "B"}
    assert sum(row.unit_price_minor * row.quantity for row in rows) == 2500


def test_normalized_rows_are_preferred_over_the_json_snapshot(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(
        db,
        seller,
        buyer,
        items=[{"sku": "A", "title": "Alpha", "quantity": 1, "unit_price": 10.0}],
    )
    sync_order_items(db, order, order.items)

    # A stale snapshot must not win over the authoritative rows.
    order.items = [
        {"sku": "STALE", "title": "Stale", "quantity": 1, "unit_price": 999.0}
    ]
    db.flush()
    payload = order_items_payload(order)
    assert payload[0]["sku"] == "A"
    assert payload[0]["unit_price_minor"] == 1000


def test_reader_falls_back_to_json_when_no_normalized_rows_exist(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(
        db,
        seller,
        buyer,
        items=[{"sku": "LEGACY", "title": "Old line", "quantity": 1, "unit_price": 45.0}],
    )
    assert db.query(OrderItem).filter(OrderItem.order_id == order.id).count() == 0

    payload = order_items_payload(order)
    assert payload[0]["sku"] == "LEGACY"
    assert payload[0]["unit_price"] == 45.0
    assert payload[0]["unit_price_minor"] == 4500


def test_snapshot_keeps_the_legacy_api_shape(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer, items=[])
    rows = sync_order_items(
        db,
        order,
        [{"sku": "A", "title": "Alpha", "quantity": 3, "unit_price": 12.5}],
    )

    snapshot = order.items
    assert isinstance(snapshot, list)
    assert snapshot[0]["item_id"] == rows[0].id
    assert snapshot[0]["unit_price"] == 12.5
    assert snapshot[0]["total_price"] == 37.5
    assert snapshot[0]["quantity"] == 3
