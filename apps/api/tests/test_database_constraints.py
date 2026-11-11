"""Database-level integrity tests.

These assert that the constraints are enforced by the schema itself, not only by
service code, so a bug in a service cannot silently create duplicate orders,
cross-tenant cases, duplicated refunds or multiple active policies.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.audit import AuditChainState, AuditLog
from app.models.order_item import OrderItem
from app.models.policy_evaluation import PolicyEvaluation
from app.models.tracking_event import TrackingEvent
from app.schemas.policy import PolicySchema
from tests.factories import (
    make_buyer,
    make_case,
    make_order,
    make_policy,
    make_seller,
    make_shipment,
)


def test_order_number_is_unique_per_seller(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    make_order(db, seller, buyer, order_number="ORD-DUP-1")
    with pytest.raises(IntegrityError):
        make_order(db, seller, buyer, order_number="ORD-DUP-1")
    db.rollback()


def test_same_order_number_is_allowed_across_sellers(db: Session) -> None:
    buyer = make_buyer(db)
    first = make_seller(db)
    second = make_seller(db)
    make_order(db, first, buyer, order_number="ORD-SHARED")
    make_order(db, second, buyer, order_number="ORD-SHARED")
    db.flush()  # no error


def test_case_cannot_reference_another_sellers_order(db: Session) -> None:
    buyer = make_buyer(db)
    owner = make_seller(db)
    attacker = make_seller(db)
    order = make_order(db, owner, buyer)

    make_case(db, order).seller_id = attacker.id
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_seller_can_have_only_one_active_policy(db: Session) -> None:
    seller = make_seller(db)
    make_policy(db, seller, PolicySchema(currency="INR"), version=1, active=True)
    with pytest.raises(IntegrityError):
        make_policy(db, seller, PolicySchema(currency="INR"), version=2, active=True)
    db.rollback()


def test_policy_versions_are_unique_per_seller(db: Session) -> None:
    seller = make_seller(db)
    make_policy(db, seller, version=1, active=True)
    with pytest.raises(IntegrityError):
        make_policy(db, seller, version=1, active=False)
    db.rollback()


def test_action_idempotency_key_is_unique_per_seller(db: Session) -> None:
    seller = make_seller(db)
    for _ in range(2):
        db.add(
            Action(
                seller_id=seller.id,
                action_type="refund",
                idempotency_key="refund:same-key",
                status="pending",
                request_payload={},
                response_payload={},
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_order_item_quantity_must_be_positive(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    db.add(
        OrderItem(
            order_id=order.id,
            title="Bad line",
            quantity=0,
            unit_price_minor=100,
            returnable=True,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_tracking_provider_event_id_is_unique_per_shipment(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    shipment = make_shipment(db, order, status="in_transit", actual_delivery_days_ago=None)
    for _ in range(2):
        db.add(
            TrackingEvent(
                shipment_id=shipment.id,
                event_timestamp=datetime.now(UTC),
                status="in_transit",
                provider_event_id="evt-1",
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_audit_sequence_is_unique_per_chain(db: Session) -> None:
    seller = make_seller(db)
    for _ in range(2):
        db.add(
            AuditLog(
                seller_id=seller.id,
                chain_key=seller.id,
                sequence=1,
                actor_role="system",
                action="test.event",
                payload={},
                prev_hash="0" * 64,
                current_hash="1" * 64,
                timestamp=datetime.now(UTC),
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_policy_evaluations_are_append_only_rows(db: Session) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer)
    case = make_case(db, order)
    policy = make_policy(db, seller)
    for _ in range(2):
        db.add(
            PolicyEvaluation(
                case_id=case.id,
                seller_id=seller.id,
                order_id=order.id,
                seller_policy_id=policy.id,
                policy_version=1,
                decision="eligible",
                reason_code="RETURN_ELIGIBLE",
                explanation="test",
                evaluation_result={},
                evaluator_version="1.0.0",
            )
        )
    db.flush()
    rows = db.query(PolicyEvaluation).filter(PolicyEvaluation.case_id == case.id).all()
    assert len(rows) == 2


def test_audit_chain_state_is_unique_per_chain_key(db: Session) -> None:
    for _ in range(2):
        db.add(AuditChainState(chain_key="chain-1", last_hash="a" * 64, last_sequence=1))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
