"""Proactive delay monitor tests.

The monitor reuses the policy engine and action lifecycle: it may only create a
case, request approval or execute a verified credit, never mutate order state on
its own.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.case import ApprovalRequest, Case
from app.schemas.policy import DelaysPolicy, PolicySchema, RefundsPolicy
from app.services.monitor import run_delay_monitor_cycle
from tests.factories import (
    make_buyer,
    make_order,
    make_policy,
    make_seller,
    make_shipment,
)

NOW = datetime.now(UTC).replace(microsecond=0)


def _delayed_shipment(db: Session, *, per_day: int = 10, maximum: int = 50, ceiling: int = 500):
    seller = make_seller(db)
    buyer = make_buyer(db)
    make_policy(
        db,
        seller,
        PolicySchema(
            currency=seller.currency,
            refunds=RefundsPolicy(
                auto_approve_up_to=ceiling,
                require_seller_approval_above=ceiling,
            ),
            delays=DelaysPolicy(
                notify_after_days_late=5,
                compensation_per_day_late=per_day,
                max_delay_compensation=maximum,
            ),
        ),
    )
    order = make_order(
        db,
        seller,
        buyer,
        total_minor=11000,
        order_status="shipped",
        days_ago=8,
    )
    shipment = make_shipment(
        db,
        order,
        status="in_transit",
        promised_days_ago=6,
        actual_delivery_days_ago=None,
    )
    # Anchor the promise to the same clock the monitor is called with so
    # "days late" is deterministic (the factory uses the real clock).
    shipment.promised_delivery_date = NOW - timedelta(days=6)
    db.commit()
    return seller, order, shipment


def test_monitor_executes_a_verified_credit_once(db: Session) -> None:
    _seller, order, shipment = _delayed_shipment(db)

    remedies = run_delay_monitor_cycle(db, now=NOW)

    assert len(remedies) == 1
    assert remedies[0]["order_number"] == order.order_number
    assert remedies[0]["days_late"] == 6
    assert remedies[0]["compensation"] == 50.0

    case = db.query(Case).filter(Case.order_id == order.id).one()
    assert case.status == "resolved"
    assert case.decision == "executed"
    assert case.resolution_type == "delay_compensation"

    actions = db.query(Action).filter(Action.order_id == order.id).all()
    assert len(actions) == 1
    assert actions[0].action_type == "wallet_credit"
    assert actions[0].status == "succeeded"
    assert actions[0].amount_minor == 5000
    assert actions[0].external_reference


def test_second_cycle_does_not_duplicate_the_credit(db: Session) -> None:
    _seller, order, _shipment = _delayed_shipment(db)
    run_delay_monitor_cycle(db, now=NOW)

    repeated = run_delay_monitor_cycle(db, now=NOW + timedelta(minutes=1))

    assert repeated == []
    assert db.query(Action).filter(Action.order_id == order.id).count() == 1


def test_no_compensation_configured_creates_no_case(db: Session) -> None:
    _seller, order, _shipment = _delayed_shipment(db, per_day=0, maximum=0)

    remedies = run_delay_monitor_cycle(db, now=NOW)

    assert remedies == []
    assert db.query(Case).filter(Case.order_id == order.id).count() == 0
    assert db.query(Action).filter(Action.order_id == order.id).count() == 0


def test_compensation_above_ceiling_requires_approval(db: Session) -> None:
    _seller, order, _shipment = _delayed_shipment(
        db, per_day=100, maximum=1000, ceiling=500
    )

    remedies = run_delay_monitor_cycle(db, now=NOW)

    assert remedies == []
    case = db.query(Case).filter(Case.order_id == order.id).one()
    assert case.status == "pending_approval"
    assert case.decision == "needs_approval"
    approval = db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case.id).one()
    assert approval.status == "pending"
    assert approval.requested_amount_minor == 60000
    assert db.query(Action).filter(Action.order_id == order.id).count() == 0


def test_delivered_shipments_are_not_compensated(db: Session) -> None:
    _seller, order, shipment = _delayed_shipment(db)
    shipment.status = "delivered"
    shipment.actual_delivery_date = NOW - timedelta(days=1)
    db.commit()

    remedies = run_delay_monitor_cycle(db, now=NOW)

    assert remedies == []
    assert db.query(Action).filter(Action.order_id == order.id).count() == 0


def test_missing_promised_date_is_skipped_safely(db: Session) -> None:
    _seller, order, shipment = _delayed_shipment(db)
    shipment.promised_delivery_date = None
    db.commit()

    remedies = run_delay_monitor_cycle(db, now=NOW)

    assert remedies == []
    assert db.query(Case).filter(Case.order_id == order.id).count() == 0
