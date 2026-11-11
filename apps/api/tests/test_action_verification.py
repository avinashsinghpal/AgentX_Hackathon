"""Verification tests: a provider response is never proof of execution."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.action import Action, ActionVerification
from app.models.case import Case
from app.models.file_upload import FileUpload
from app.models.order import Order
from app.schemas.policy import PolicySchema, RefundsPolicy
from app.services.actions.providers.base import ActionProvider, ProviderOutcome
from app.services.actions.providers.mock_payment import MockPaymentProvider
from app.services.actions.registry import ProviderRegistry
from app.services.actions.service import ActionService
from app.services.actions.verification import ActionVerificationService
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


class UnverifiableProvider(ActionProvider):
    """Accepts the request but cannot confirm the operation happened."""

    name = "unverifiable"

    def execute(
        self,
        action_type: str,
        idempotency_key: str,
        *,
        amount_minor: int | None,
        currency: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderOutcome:
        return ProviderOutcome(status="succeeded", reference="RFND-PHANTOM")

    def verify(
        self,
        reference: str | None,
        *,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> ProviderOutcome:
        return ProviderOutcome(
            status="failed",
            error_code="PROVIDER_NOT_FOUND",
            payload={"reference": reference},
        )


def _prepare_claim(db: Session) -> tuple[Order, Case]:
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
    return order, case


def test_unverified_provider_outcome_does_not_resolve_the_case(db: Session) -> None:
    order, case = _prepare_claim(db)
    evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=True)

    service = ActionService(registry=ProviderRegistry(payment_provider=UnverifiableProvider()))
    run = service.execute_for_case(db, case=case, order=order, evaluation=evaluation.result)

    db.refresh(case)
    db.refresh(order)
    action = db.query(Action).filter(Action.order_id == order.id).one()

    assert run.executed is False
    assert action.status == "failed"
    assert action.failure_reason == "PROVIDER_NOT_FOUND"
    assert action.external_reference == "RFND-PHANTOM"
    assert case.status != "resolved"
    assert case.decision != "executed"
    assert order.payment_status == "captured"

    attempts = db.query(ActionVerification).filter(ActionVerification.action_id == action.id).all()
    assert len(attempts) == 1
    assert attempts[0].verification_status == "failed"


def test_provider_rejection_is_recorded_without_resolving(db: Session) -> None:
    order, case = _prepare_claim(db)
    evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=True)

    payment = MockPaymentProvider()
    payment.configure_outcome("refund", "failure")
    service = ActionService(registry=ProviderRegistry(payment_provider=payment))
    run = service.execute_for_case(db, case=case, order=order, evaluation=evaluation.result)

    db.refresh(case)
    assert run.executed is False
    assert run.status == "failed"
    assert run.reason == "PROVIDER_REJECTED"
    assert case.status != "resolved"
    attempts = (
        db.query(ActionVerification).filter(ActionVerification.action_id == run.action.id).all()
    )
    assert attempts == []


def test_verification_records_every_attempt(db: Session) -> None:
    order, case = _prepare_claim(db)
    evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=True)

    payment = MockPaymentProvider()
    service = ActionService(registry=ProviderRegistry(payment_provider=payment))
    first = service.execute_for_case(db, case=case, order=order, evaluation=evaluation.result)
    assert first.executed is True

    # A second attempt is recorded even though the action already succeeded.
    verification = ActionVerificationService()
    outcome = verification.verify(db, first.action, payment)
    assert outcome.verified is True
    assert outcome.attempt == 2
    rows = (
        db.query(ActionVerification)
        .filter(ActionVerification.action_id == first.action.id)
        .order_by(ActionVerification.verification_attempt)
        .all()
    )
    assert [row.verification_status for row in rows] == ["verified", "verified"]
