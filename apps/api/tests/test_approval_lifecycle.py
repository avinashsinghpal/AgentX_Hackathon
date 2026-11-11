"""Approval lifecycle: authorization is not execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.case import ApprovalRequest, CaseMessage
from app.models.file_upload import FileUpload
from app.schemas.policy import PolicySchema, RefundsPolicy
from app.services.actions.registry import get_provider_registry
from app.services.approvals import (
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalStateError,
)
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


@pytest.fixture(autouse=True)
def reset_mock_providers():
    get_provider_registry().reset()
    yield
    get_provider_registry().reset()


def _pending_approval(db: Session, *, total_minor: int = 32000):
    seller = make_seller(db)
    buyer = make_buyer(db)
    make_policy(
        db,
        seller,
        PolicySchema(
            currency=seller.currency,
            refunds=RefundsPolicy(
                auto_approve_up_to=50,
                require_seller_approval_above=50,
            ),
        ),
    )
    order = make_order(db, seller, buyer, total_minor=total_minor)
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

    evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=True)
    assert evaluation.result.decision.value == "needs_approval"
    approval = ApprovalService().request_for_evaluation(
        db,
        case=case,
        evaluation=evaluation.result,
        evaluation_id=evaluation.record.id if evaluation.record else None,
    )
    return seller, order, case, approval


def test_approving_executes_and_verifies_the_action(db: Session) -> None:
    seller, order, case, approval = _pending_approval(db)
    db.refresh(case)
    assert case.status == "pending_approval"
    assert case.decision == "needs_approval"
    assert approval.requested_amount_minor == 32000

    outcome = ApprovalService().decide(
        db,
        approval_id=approval.id,
        seller=seller,
        decision="approved",
        seller_notes="Photo verified.",
    )

    db.refresh(case)
    db.refresh(order)
    assert outcome.executed is True, outcome.failure_reason
    assert outcome.approval.status == "approved"
    assert outcome.approval.decided_at is not None
    assert outcome.action is not None
    assert outcome.action.action.status == "succeeded"
    assert case.status == "resolved"
    assert case.decision == "executed"
    assert order.payment_status == "refunded"
    action = db.query(Action).filter(Action.case_id == case.id).one()
    assert action.approval_id == approval.id


def test_rejection_never_creates_or_executes_an_action(db: Session) -> None:
    seller, _order, case, approval = _pending_approval(db)

    outcome = ApprovalService().decide(
        db,
        approval_id=approval.id,
        seller=seller,
        decision="rejected",
        seller_notes="Damage photo does not match the reported item.",
    )

    db.refresh(case)
    assert outcome.executed is False
    assert outcome.approval.status == "rejected"
    assert case.status == "rejected"
    assert case.decision == "not_eligible"
    assert db.query(Action).filter(Action.case_id == case.id).count() == 0
    message = db.query(CaseMessage).filter(CaseMessage.case_id == case.id).one()
    assert message.decision_badge == "not_eligible"


def test_approval_cannot_be_decided_twice(db: Session) -> None:
    seller, _order, _case, approval = _pending_approval(db)
    service = ApprovalService()
    service.decide(db, approval_id=approval.id, seller=seller, decision="approved")

    with pytest.raises(ApprovalStateError):
        service.decide(db, approval_id=approval.id, seller=seller, decision="rejected")


def test_expired_approval_cannot_be_executed(db: Session) -> None:
    seller, _order, case, approval = _pending_approval(db)
    approval.expires_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()

    with pytest.raises(ApprovalStateError, match="expired"):
        ApprovalService().decide(db, approval_id=approval.id, seller=seller, decision="approved")

    db.refresh(approval)
    db.refresh(case)
    assert approval.status == "expired"
    assert db.query(Action).filter(Action.case_id == case.id).count() == 0


def test_another_seller_cannot_decide_the_approval(db: Session) -> None:
    _seller, _order, _case, approval = _pending_approval(db)
    intruder = make_seller(db)

    with pytest.raises(ApprovalNotFoundError):
        ApprovalService().decide(db, approval_id=approval.id, seller=intruder, decision="approved")


def test_repeated_escalation_reuses_the_pending_request(db: Session) -> None:
    _seller, _order, case, approval = _pending_approval(db)
    evaluation = PolicyEvaluationService().evaluate_case(db, case, persist=True)

    again = ApprovalService().request_for_evaluation(
        db,
        case=case,
        evaluation=evaluation.result,
        evaluation_id=evaluation.record.id if evaluation.record else None,
    )

    assert again.id == approval.id
    assert db.query(ApprovalRequest).filter(ApprovalRequest.case_id == case.id).count() == 1
