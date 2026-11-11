"""Single writer for normalized order items and tracking events.

``order_items`` and ``tracking_events`` are authoritative.  The legacy JSON
columns on ``orders`` and ``shipments`` are kept as read-only snapshots so
existing API payloads and older consumers keep working.  Every write goes
through this module, so the two representations cannot silently diverge.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.tracking_event import TrackingEvent


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def item_price_minor_from_legacy(item: dict[str, Any]) -> int:
    """Best-effort minor-unit price for legacy JSON order lines.

    New writes always use ``unit_price_minor``.  Legacy data used either integer
    minor units (demo seed) or float major units (older fixtures); integers are
    treated as minor units and floats as major units.
    """
    if isinstance(item.get("unit_price_minor"), int):
        return int(item["unit_price_minor"])
    unit_price = item.get("unit_price")
    if isinstance(unit_price, bool):
        unit_price = None
    if isinstance(unit_price, int):
        return unit_price
    if isinstance(unit_price, float):
        return int(round(unit_price * 100))
    total_price = item.get("total_price")
    if isinstance(total_price, int):
        return total_price
    if isinstance(total_price, float):
        return int(round(total_price * 100))
    return 0


def normalize_legacy_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    quantity = max(1, _to_int(item.get("quantity"), 1))
    unit_price_minor = item_price_minor_from_legacy(item)
    return {
        "reference_id": str(item.get("item_id") or item.get("id") or f"legacy-{index}"),
        "sku": item.get("sku"),
        "title": str(item.get("title") or item.get("name") or "Item"),
        "quantity": quantity,
        "unit_price_minor": max(0, unit_price_minor),
        "returnable": bool(item.get("returnable", True)),
        "category": item.get("category"),
    }


def legacy_payload_from_normalized(row: OrderItem | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, OrderItem):
        return row.to_legacy_dict()
    unit_price_minor = max(0, _to_int(row.get("unit_price_minor"), 0))
    quantity = max(1, _to_int(row.get("quantity"), 1))
    unit_price = unit_price_minor / 100.0
    return {
        "item_id": row.get("reference_id"),
        "sku": row.get("sku"),
        "title": row.get("title", "Item"),
        "quantity": quantity,
        "unit_price": unit_price,
        "unit_price_minor": unit_price_minor,
        "total_price": unit_price * quantity,
        "total_price_minor": unit_price_minor * quantity,
        "returnable": bool(row.get("returnable", True)),
        "category": row.get("category"),
    }


def sync_order_items(
    db: Session,
    order: Order,
    items: list[dict[str, Any]] | None,
    *,
    commit: bool = False,
) -> list[OrderItem]:
    """Replace an order's normalized lines and refresh the legacy snapshot."""
    normalized = [normalize_legacy_item(item, index) for index, item in enumerate(items or [])]

    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete(synchronize_session=False)
    db.flush()

    rows = [
        OrderItem(
            order_id=order.id,
            sku=item["sku"],
            title=item["title"],
            quantity=item["quantity"],
            unit_price_minor=item["unit_price_minor"],
            returnable=item["returnable"],
            category=item["category"],
        )
        for item in normalized
    ]
    db.add_all(rows)
    db.flush()

    order.items = [legacy_payload_from_normalized(row) for row in rows]
    if commit:
        db.commit()
    return rows


def order_items_payload(order: Order) -> list[dict[str, Any]]:
    """Legacy API shape for order lines, preferring normalized rows."""
    rows = list(order.order_items) if order.order_items else []
    if rows:
        return [row.to_legacy_dict() for row in rows]
    legacy = order.items if isinstance(order.items, list) else []
    return [
        legacy_payload_from_normalized(normalize_legacy_item(item, index))
        for index, item in enumerate(legacy)
    ]


def _parse_event_timestamp(value: Any, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = fallback
    else:
        parsed = fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def sync_tracking_events(
    db: Session,
    shipment: Shipment,
    events: list[dict[str, Any]] | None,
    *,
    commit: bool = False,
) -> list[TrackingEvent]:
    """Replace a shipment's normalized tracking history and legacy snapshot."""
    fallback = shipment.created_at or datetime.now(UTC)
    if fallback.tzinfo is None:
        fallback = fallback.replace(tzinfo=UTC)

    db.query(TrackingEvent).filter(TrackingEvent.shipment_id == shipment.id).delete(
        synchronize_session=False
    )
    db.flush()

    rows = []
    for raw in events or []:
        rows.append(
            TrackingEvent(
                shipment_id=shipment.id,
                event_timestamp=_parse_event_timestamp(raw.get("timestamp"), fallback),
                status=str(raw.get("status") or "unknown"),
                location=raw.get("location"),
                description=raw.get("description"),
                provider_event_id=raw.get("provider_event_id") or raw.get("event_id"),
                raw_payload=raw.get("raw_payload"),
            )
        )
    rows.sort(key=lambda row: row.event_timestamp)
    db.add_all(rows)
    db.flush()

    shipment.tracking_events = [row.to_legacy_dict() for row in rows]
    if commit:
        db.commit()
    return rows


def tracking_events_payload(shipment: Shipment) -> list[dict[str, Any]]:
    rows = list(shipment.tracking_event_rows) if shipment.tracking_event_rows else []
    if rows:
        return [row.to_legacy_dict() for row in rows]
    legacy = shipment.tracking_events if isinstance(shipment.tracking_events, list) else []
    return [dict(event) for event in legacy]
