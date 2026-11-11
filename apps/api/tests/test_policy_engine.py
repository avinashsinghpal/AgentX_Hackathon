"""Deterministic policy-engine tests.

The engine is a pure function over trusted inputs: these tests do not touch the
database, the LLM or any provider, and they pin the exact boundary semantics
(documentation in docs/policy-schema.md).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.schemas.policy import (
    DamageClaimsPolicy,
    DelaysPolicy,
    FraudChecksPolicy,
    PolicySchema,
    RefundsPolicy,
    ReturnsPolicy,
    normalize_parsed_rules,
    policy_rules_dict,
)
from app.services.policy import PolicyEngine
from app.services.policy.result import Decision
from app.services.policy.schemas import (
    CaseInput,
    ItemInput,
    OrderInput,
    PolicyEvaluationInput,
    ShipmentInput,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
ENGINE = PolicyEngine()


def make_policy(
    *,
    currency: str = "INR",
    window_days: int = 14,
    ceiling: int = 5000,
    per_day: int = 1000,
    max_compensation: int = 3000,
    delay_threshold: int = 2,
    report_within_days: int = 2,
    require_photo: bool = True,
    max_refunds: int = 3,
) -> PolicySchema:
    return PolicySchema(
        currency=currency,
        returns=ReturnsPolicy(window_days=window_days),
        refunds=RefundsPolicy(
            auto_approve_up_to=ceiling,
            require_seller_approval_above=ceiling,
        ),
        delays=DelaysPolicy(
            notify_after_days_late=delay_threshold,
            compensation_per_day_late=per_day,
            max_delay_compensation=max_compensation,
        ),
        damage_claims=DamageClaimsPolicy(
            require_photo=require_photo,
            report_within_days=report_within_days,
        ),
        fraud_checks=FraudChecksPolicy(max_refunds_per_buyer_per_30_days=max_refunds),
    )


def make_inputs(
    *,
    policy: PolicySchema | None = None,
    category: str = "return",
    delivered_days_ago: int = 2,
    total_minor: int = 4500,
    order_currency: str | None = None,
    order_status: str = "delivered",
    seller_status: str = "active",
    evidence_count: int = 0,
    buyer_refund_count: int = 0,
    shipment: ShipmentInput | None | bool = True,
    items: tuple[ItemInput, ...] | None = None,
) -> PolicyEvaluationInput:
    document = policy or make_policy()
    if shipment is True:
        shipment = ShipmentInput(
            id="ship-1",
            status="delivered",
            promised_delivery_date=NOW - timedelta(days=delivered_days_ago + 3),
            actual_delivery_date=NOW - timedelta(days=delivered_days_ago),
        )
    return PolicyEvaluationInput(
        case=CaseInput(
            seller_id="seller-1",
            buyer_id="buyer-1",
            order_id="order-1",
            issue_category=category,
        ),
        order=OrderInput(
            id="order-1",
            seller_id="seller-1",
            buyer_id="buyer-1",
            order_number="ORD-TEST-1",
            currency=order_currency or document.currency,
            total_amount_minor=total_minor,
            payment_method="prepaid",
            payment_status="captured",
            order_status=order_status,
        ),
        seller_status=seller_status,
        policy=document,
        policy_id="policy-1",
        shipment=shipment if shipment is not True else None,
        items=items
        if items is not None
        else (
            ItemInput(
                reference_id="item-1",
                title="Test Item",
                quantity=1,
                unit_price_minor=total_minor,
            ),
        ),
        evidence_count=evidence_count,
        evidence_reference_ids=tuple(f"evidence-{i}" for i in range(evidence_count)),
        buyer_refund_count_30d=buyer_refund_count,
        now=NOW,
    )


def test_return_at_window_boundary_is_eligible() -> None:
    result = ENGINE.evaluate(make_inputs(policy=make_policy(window_days=14), delivered_days_ago=14))
    assert result.decision is Decision.ELIGIBLE


def test_return_one_day_past_window_is_rejected() -> None:
    result = ENGINE.evaluate(make_inputs(policy=make_policy(window_days=14), delivered_days_ago=15))
    assert result.decision is Decision.NOT_ELIGIBLE
    assert result.reason_code == "RETURN_WINDOW_EXPIRED"


def test_amount_at_approval_ceiling_is_auto_approved() -> None:
    result = ENGINE.evaluate(make_inputs(policy=make_policy(ceiling=50), total_minor=5000))
    assert result.decision is Decision.ELIGIBLE
    assert result.eligible_amount_minor == 5000


def test_amount_above_approval_ceiling_needs_approval() -> None:
    result = ENGINE.evaluate(make_inputs(policy=make_policy(ceiling=50), total_minor=5001))
    assert result.decision is Decision.NEEDS_APPROVAL
    assert result.reason_code == "APPROVAL_CEILING_EXCEEDED"
    assert result.eligible_amount_minor == 5001
    assert result.badge == "needs_approval"


def test_policy_decision_is_separate_from_action_outcome() -> None:
    # Only action execution may produce the "executed" badge; the engine itself
    # returns policy decisions and never claims execution.
    eligible = ENGINE.evaluate(make_inputs())
    pending = ENGINE.evaluate(make_inputs(total_minor=999999))
    rejected = ENGINE.evaluate(make_inputs(delivered_days_ago=90))
    assert {eligible.decision, pending.decision, rejected.decision} <= set(Decision)
    assert "executed" not in {d.value for d in Decision}


def test_fraud_limit_is_inclusive_at_the_configured_maximum() -> None:
    at_limit = ENGINE.evaluate(make_inputs(buyer_refund_count=3))
    over_limit = ENGINE.evaluate(make_inputs(buyer_refund_count=4))
    assert at_limit.decision is Decision.ELIGIBLE
    assert over_limit.decision is Decision.NEEDS_APPROVAL
    assert over_limit.reason_code == "FRAUD_LIMIT_EXCEEDED_ESCALATED"


def test_damage_claim_without_photo_is_rejected() -> None:
    result = ENGINE.evaluate(
        make_inputs(category="damaged", delivered_days_ago=1, evidence_count=0)
    )
    assert result.decision is Decision.NOT_ELIGIBLE
    assert result.reason_code == "MISSING_DAMAGE_PHOTO"


def test_damage_claim_with_photo_is_evaluated_normally() -> None:
    result = ENGINE.evaluate(
        make_inputs(category="damaged", delivered_days_ago=1, evidence_count=1)
    )
    assert result.decision is Decision.ELIGIBLE


def test_currency_mismatch_requires_manual_review() -> None:
    result = ENGINE.evaluate(
        make_inputs(policy=make_policy(currency="INR"), order_currency="USD")
    )
    assert result.decision is Decision.MANUAL_REVIEW
    assert result.reason_code == "CURRENCY_MISMATCH"
    assert result.badge == "needs_approval"


def test_suspended_seller_disables_automation() -> None:
    result = ENGINE.evaluate(make_inputs(seller_status="suspended"))
    assert result.decision is Decision.NOT_ELIGIBLE
    assert result.reason_code == "SELLER_SUSPENDED"


def test_delay_compensation_is_capped_by_policy_maximum() -> None:
    shipment = ShipmentInput(
        id="ship-2",
        status="in_transit",
        promised_delivery_date=NOW - timedelta(days=6),
        actual_delivery_date=None,
        tracking_event_count=2,
        latest_event_at=NOW - timedelta(days=1),
    )
    result = ENGINE.evaluate(
        make_inputs(
            category="delay",
            shipment=shipment,
            total_minor=11000,
            policy=make_policy(per_day=10, max_compensation=30),
        )
    )
    # 6 days late x 10.00 = 60.00, capped at 30.00 (= 3000 minor units).
    assert result.decision is Decision.ELIGIBLE
    assert result.eligible_amount_minor == 3000
    assert result.proposed_action == "wallet_credit"


def test_delay_without_configured_compensation_never_credits() -> None:
    shipment = ShipmentInput(
        id="ship-3",
        status="in_transit",
        promised_delivery_date=NOW - timedelta(days=6),
        actual_delivery_date=None,
        latest_event_at=NOW - timedelta(days=1),
    )
    result = ENGINE.evaluate(
        make_inputs(
            category="delay",
            shipment=shipment,
            policy=make_policy(per_day=0, max_compensation=0),
        )
    )
    assert result.decision is Decision.NOT_ELIGIBLE
    assert result.reason_code == "DELAY_COMPENSATION_NOT_CONFIGURED"
    assert result.eligible_amount_minor == 0


def test_delay_below_threshold_is_not_eligible() -> None:
    shipment = ShipmentInput(
        id="ship-4",
        status="in_transit",
        promised_delivery_date=NOW - timedelta(days=1),
        actual_delivery_date=None,
        latest_event_at=NOW - timedelta(hours=6),
    )
    result = ENGINE.evaluate(
        make_inputs(category="delay", shipment=shipment, policy=make_policy(delay_threshold=2))
    )
    assert result.decision is Decision.NOT_ELIGIBLE
    assert result.reason_code == "DELAY_THRESHOLD_NOT_MET"


def test_delay_without_promised_date_requires_manual_review() -> None:
    shipment = ShipmentInput(
        id="ship-5",
        status="in_transit",
        promised_delivery_date=None,
        actual_delivery_date=None,
        latest_event_at=NOW - timedelta(days=3),
    )
    result = ENGINE.evaluate(make_inputs(category="delay", shipment=shipment))
    assert result.decision is Decision.MANUAL_REVIEW
    assert result.reason_code == "SHIPMENT_DATA_MISSING"


def test_legacy_policy_keys_normalize_to_canonical_schema() -> None:
    legacy = {
        "returns": {"window_days": 10},
        "refunds": {"auto_approve_max_amount": 75},
        "delays": {"delay_threshold_days": 4},
        "damage_claims": {"photo_evidence_required": False},
        "fraud_checks": {"max_claims_per_buyer_90_days": 2},
    }
    policy = normalize_parsed_rules(legacy)
    assert policy is not None
    assert policy.refunds.auto_approve_up_to == 75
    assert policy.delays.notify_after_days_late == 4
    assert policy.damage_claims.require_photo is False
    assert policy.fraud_checks.max_refunds_per_buyer_per_30_days == 2
    # The projection re-emits the legacy keys the web client still reads.
    projected = policy_rules_dict(policy)
    assert projected["refunds"]["auto_approve_max_amount"] == 75
    assert projected["delays"]["delay_threshold_days"] == 4


def test_invalid_policy_document_requires_manual_review() -> None:
    inputs = make_inputs(policy=None)
    inputs = PolicyEvaluationInput(
        **{**inputs.__dict__, "policy": None, "policy_invalid": True}
    )
    result = ENGINE.evaluate(inputs)
    assert result.decision is Decision.MANUAL_REVIEW
    assert result.reason_code == "POLICY_INVALID"
