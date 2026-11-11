"""Policy versioning and append-only evaluation history."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.policy_evaluation import PolicyEvaluation
from app.schemas.policy import PolicySchema, ReturnsPolicy
from app.services.policy.evaluator import PolicyEvaluationService
from tests.factories import (
    make_buyer,
    make_case,
    make_order,
    make_policy,
    make_seller,
    make_shipment,
)


def test_new_policy_version_changes_the_decision_and_keeps_history(
    db: Session,
) -> None:
    seller = make_seller(db)
    buyer = make_buyer(db)
    order = make_order(db, seller, buyer, total_minor=4500)
    make_shipment(db, order, status="delivered", actual_delivery_days_ago=5)
    case = make_case(db, order, category="return")

    first_policy = make_policy(
        db,
        seller,
        PolicySchema(currency=seller.currency, returns=ReturnsPolicy(window_days=14)),
        version=1,
        active=True,
    )
    service = PolicyEvaluationService()
    first = service.evaluate_case(db, case, persist=True)
    assert first.result.decision.value == "eligible"
    assert first.result.policy_version == 1

    first_policy.is_active = False
    db.flush()
    make_policy(
        db,
        seller,
        PolicySchema(currency=seller.currency, returns=ReturnsPolicy(window_days=3)),
        version=2,
        active=True,
    )

    second = service.evaluate_case(db, case, persist=True)
    assert second.result.decision.value == "not_eligible"
    assert second.result.reason_code == "RETURN_WINDOW_EXPIRED"
    assert second.result.policy_version == 2

    records = (
        db.query(PolicyEvaluation)
        .filter(PolicyEvaluation.case_id == case.id)
        .order_by(PolicyEvaluation.evaluated_at.asc())
        .all()
    )
    assert [record.policy_version for record in records] == [1, 2]
    assert [record.decision for record in records] == ["eligible", "not_eligible"]
    # The first evaluation is untouched: history is append-only.
    assert records[0].evaluation_result["decision"] == "eligible"
    assert records[0].evaluation_result["policy_version"] == 1
