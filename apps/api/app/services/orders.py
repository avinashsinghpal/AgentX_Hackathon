"""Single writer for normalized order items and tracking events.

``order_items`` and ``tracking_events`` are authoritative.  The legacy JSON
columns on ``orders`` and ``shipments`` are kept as read-only snapshots so
existing API payloads and older consumers keep working.  Every write goes
through this module, so the two representations cannot silently diverge.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
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


def _legacy_money_to_minor(value: Any) -> int:
    """Convert an inferred legacy monetary value to integer minor units.

    Integers and integral Decimals are already minor units. Floats are major
    units. Strings are parsed as Decimals and follow the same rule.
    """
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(round(value * 100))
        except (TypeError, ValueError, OverflowError):
            return 0
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    if parsed == parsed.to_integral_value():
        return int(parsed)
    try:
        return int((parsed * 100).to_integral_value())
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return 0


def _explicit_minor_to_int(value: Any) -> int:
    """Coerce a value already expressed in minor units to an integer."""
    if isinstance(value, bool) or value is None:
        return 0
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    try:
        return int(parsed.to_integral_value(rounding=ROUND_HALF_EVEN))
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return 0


def item_price_minor_from_legacy(item: dict[str, Any]) -> int:
    """Best-effort minor-unit price for legacy JSON order lines.

    Explicit minor-unit fields always take precedence. Inferred legacy values
    use integer-minor/float-major conversion.
    """
    if not isinstance(item, dict):
        return 0

    if item.get("unit_price_minor") is not None:
        return _explicit_minor_to_int(item.get("unit_price_minor"))
    if item.get("total_price_minor") is not None:
        return _explicit_minor_to_int(item.get("total_price_minor"))

    unit_price = item.get("unit_price")
    if unit_price is not None and not isinstance(unit_price, bool):
        return _legacy_money_to_minor(unit_price)
    total_price = item.get("total_price")
    if total_price is not None and not isinstance(total_price, bool):
        return _legacy_money_to_minor(total_price)
    price = item.get("price")
    if price is not None and not isinstance(price, bool):
        return _legacy_money_to_minor(price)
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
