"""Idempotency tests for the action lifecycle.

A retry of the same business operation must never produce a second refund or
wallet credit, even when the first attempt lost its provider response.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.case import Case
from app.models.file_upload import FileUpload
from app.models.order import Order
from app.models.seller import Seller
from app.schemas.policy import PolicySchema, RefundsPolicy
from app.services.actions.providers.mock_payment import MockPaymentProvider
from app.services.actions.registry import ProviderRegistry
from app.services.actions.service import ActionService
from app.services.policy.evaluator import PolicyEvaluationService
from tests.factories import (
    make_buyer,
    make_case,
    make_order,
    make_policy,
    make_seller,
    make_shipment,
    unique,
)


def _prepare_claim(db: Session) -> tuple[Seller, Order, Case]:
    seller = make_seller(db)
    buyer = make_buyer(db)
    make_policy(
        db,
        seller,
        PolicySchema(
            currency=seller.currency,
            refunds=RefundsPolicy(
                auto_approve_up_to=500,
                require_seller_approval_above=500,
            ),
        ),
    )
    order = make_order(db, seller, buyer, total_minor=4500)
    make_shipment(db, order, status="delivered", actual_delivery_days_ago=1)
    case = make_case(db, order, category="damaged", evidence=["photo"])
    db.add(
        FileUpload(
            uploader_id=buyer.user_id,
            case_id=case.id,
            original_filename="damage.png",
            stored_filename=f"{unique('file')}.png",
            mime_type="image/png",
            file_size_bytes=128,
            storage_path="uploads/damage.png",
        )
    )
    db.flush()
    return seller, order, case


def _evaluate(db: Session, case: Case):
    return PolicyEvaluationService().evaluate_case(db, case, persist=True)


def test_repeated_execution_does_not_duplicate_the_refund(db: Session) -> None:
    _seller, order, case = _prepare_claim(db)
    evaluation = _evaluate(db, case)
    assert evaluation.result.proposed_action == "refund"

    payment = MockPaymentProvider()
    service = ActionService(registry=ProviderRegistry(payment_provider=payment))

    first = service.execute_for_case(
        db, case=case, order=order, evaluation=evaluation.result
    )
    assert first.executed is True
    assert first.action.status == "succeeded"
    assert first.action.external_reference

    second = service.execute_for_case(
        db, case=case, order=order, evaluation=evaluation.result
    )
    assert second.executed is True
    assert second.already_completed is True
    assert second.action.id == first.action.id

    actions = db.query(Action).filter(Action.order_id == order.id).all()
    assert len(actions) == 1
    assert len(payment._operations) == 1
    assert order.payment_status == "refunded"


def test_retry_after_provider_timeout_recovers_instead_of_paying_twice(
    db: Session,
) -> None:
    _seller, order, case = _prepare_claim(db)
    evaluation = _evaluate(db, case)

    payment = MockPaymentProvider()
    payment.configure_outcome("refund", "timeout")
    service = ActionService(registry=ProviderRegistry(payment_provider=payment))

    timed_out = service.execute_for_case(
        db, case=case, order=order, evaluation=evaluation.result
    )
    assert timed_out.executed is False
    assert timed_out.status == "timeout"
    assert timed_out.action.status == "submitted"
    assert timed_out.action.failure_reason == "provider_timeout"
    # The provider did record the operation; the response is what was lost.
    assert len(payment._operations) == 1

    payment.configure_outcome("refund", "success")
    retried = service.execute_for_case(
        db, case=case, order=order, evaluation=evaluation.result
    )
    assert retried.executed is True
    assert retried.action.status == "succeeded"
    assert retried.action.id == timed_out.action.id
    assert retried.action.response_payload.get("deduplicated") is True
    assert len(payment._operations) == 1
    assert db.query(Action).filter(Action.order_id == order.id).count() == 1


def test_idempotency_key_is_deterministic_for_the_same_evaluation(db: Session) -> None:
    _seller, order, case = _prepare_claim(db)
    evaluation = _evaluate(db, case)

    payment = MockPaymentProvider()
    service = ActionService(registry=ProviderRegistry(payment_provider=payment))
    first = service.execute_for_case(
        db, case=case, order=order, evaluation=evaluation.result
    )

    from app.services.actions.idempotency import build_idempotency_key

    expected = build_idempotency_key(
        "refund",
        case.seller_id,
        case_id=case.id,
        order_id=order.id,
        amount_minor=evaluation.result.eligible_amount_minor,
        policy_version=evaluation.result.policy_version,
    )
    assert first.action.idempotency_key == expected
