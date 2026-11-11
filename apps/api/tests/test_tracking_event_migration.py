"""Tracking-event normalization tests.

``tracking_events`` is authoritative; ``shipments.tracking_events`` remains as a
read-only legacy snapshot maintained by the sync writer.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tracking_event import TrackingEvent
from app.services.orders import sync_tracking_events, tracking_events_payload
from tests.factories import (
    make_buyer,
    make_order,
    make_seller,
    make_shipment,
)


def _events() -> list[dict[str, object]]:
    return [
        {
            "status": "in_transit",
            "timestamp": "2026-11-01T10:00:00Z",
            "location": "Delhi Hub",
            "description": "Picked up",
            "provider_event_id": "evt-1",
        },
        {
            "status": "delivered",
            "timestamp": "2026-11-03T16:30:00+00:00",
            "location": "Springfield",
            "description": "Delivered",
            "event_id": "evt-2",
        },
    ]


def test_sync_creates_sorted_normalized_events(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    shipment = make_shipment(db, order, status="delivered")

    rows = sync_tracking_events(db, shipment, _events())

    assert [row.status for row in rows] == ["in_transit", "delivered"]
    assert [row.provider_event_id for row in rows] == ["evt-1", "evt-2"]
    assert rows[0].event_timestamp < rows[1].event_timestamp
    assert db.query(TrackingEvent).filter(TrackingEvent.shipment_id == shipment.id).count() == 2


def test_sync_is_idempotent_and_refreshes_the_snapshot(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    shipment = make_shipment(db, order, status="in_transit")

    sync_tracking_events(db, shipment, _events())
    sync_tracking_events(db, shipment, _events())

    assert db.query(TrackingEvent).filter(TrackingEvent.shipment_id == shipment.id).count() == 2
    assert len(shipment.tracking_events) == 2
    assert shipment.tracking_events[1]["status"] == "delivered"


def test_reader_falls_back_to_the_legacy_snapshot(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    shipment = make_shipment(
        db,
        order,
        status="in_transit",
        tracking_events=[
            {
                "status": "in_transit",
                "timestamp": "2026-11-01T10:00:00+00:00",
                "location": "Hub",
                "description": "In transit",
            }
        ],
    )

    payload = tracking_events_payload(shipment)
    assert len(payload) == 1
    assert payload[0]["status"] == "in_transit"


def test_reader_prefers_normalized_events(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    shipment = make_shipment(db, order, status="in_transit")
    sync_tracking_events(db, shipment, _events())

    shipment.tracking_events = [{"status": "stale", "timestamp": "2020-01-01T00:00:00+00:00"}]
    db.flush()

    payload = tracking_events_payload(shipment)
    assert [event["status"] for event in payload] == ["in_transit", "delivered"]
