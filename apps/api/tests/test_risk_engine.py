"""Deterministic risk-engine tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.services.risk import (
    DataSufficiency,
    RiskEngine,
    RiskEvaluationInput,
    RiskResult,
)


def test_refund_frequency_boundary() -> None:
    engine = RiskEngine()
    at_limit = engine.evaluate(
        RiskEvaluationInput(
            max_refunds_per_buyer_per_30_days=3,
            buyer_refund_count_30d=3,
        )
    )
    over_limit = engine.evaluate(
        RiskEvaluationInput(
            max_refunds_per_buyer_per_30_days=3,
            buyer_refund_count_30d=4,
        )
    )
    assert at_limit.flags == []
    assert [flag.code for flag in over_limit.flags] == ["HIGH_REFUND_FREQUENCY"]


def test_claim_frequency_remains_disabled() -> None:
    engine = RiskEngine()
    result = engine.evaluate(
        RiskEvaluationInput(
            max_refunds_per_buyer_per_30_days=1,
            buyer_refund_count_30d=100,
        )
    )
    assert "CLAIM_FREQUENCY" not in " ".join(flag.code for flag in result.flags)


def test_duplicate_evidence_exact_hash() -> None:
    engine = RiskEngine()
    result = engine.evaluate(
        RiskEvaluationInput(
            current_evidence_hashes=("abc123",),
            previous_evidence_hashes=("def456", "abc123"),
        )
    )
    assert [flag.code for flag in result.flags] == ["DUPLICATE_EVIDENCE"]
    assert result.flags[0].severity == "high"


def test_address_comparison_missing_and_conflicting() -> None:
    engine = RiskEngine()
    missing = engine.evaluate(
        RiskEvaluationInput(
            order_shipping_address={"city": "Delhi", "pincode": "110001"},
        )
    )
    conflicting = engine.evaluate(
        RiskEvaluationInput(
            order_shipping_address={"city": "Delhi", "pincode": "110001"},
            buyer_default_shipping_address={"city": "Mumbai", "pincode": "400001"},
        )
    )
    matching = engine.evaluate(
        RiskEvaluationInput(
            order_shipping_address={"city": "Delhi", "pincode": "110001"},
            buyer_default_shipping_address={"city": "Delhi", "pincode": "110001"},
        )
    )
    assert missing.flags == []
    assert [flag.code for flag in conflicting.flags] == ["ADDRESS_INCONSISTENCY"]
    assert matching.flags == []


def test_missing_customer_history_is_insufficient_data() -> None:
    engine = RiskEngine()
    result = engine.evaluate(RiskEvaluationInput(customer_history_count=0))
    assert result.data_sufficiency is DataSufficiency.INSUFFICIENT_DATA
    assert result.flags == []


def test_risk_result_forbidden_fields() -> None:
    result = RiskResult(
        risk_engine_version="1.0.0",
        flags=[],
        data_sufficiency="sufficient",
        evaluated_at=datetime.now(UTC),
    )
    dumped = result.model_dump(mode="json")
    assert set(dumped) == {
        "risk_engine_version",
        "flags",
        "data_sufficiency",
        "evaluated_at",
    }
    for forbidden in {
        "eligible",
        "not_eligible",
        "approval_required",
        "refund_amount",
        "execute_action",
        "manual_review_recommended",
    }:
        assert forbidden not in dumped

    with pytest.raises(ValidationError):
        RiskResult(
            risk_engine_version="1.0.0",
            flags=[],
            data_sufficiency="sufficient",
            evaluated_at=datetime.now(UTC),
            eligible=True,  # type: ignore[arg-type]
        )


def test_risk_engine_does_not_calculate_money_or_eligibility() -> None:
    engine = RiskEngine()
    result = engine.evaluate(
        RiskEvaluationInput(
            max_refunds_per_buyer_per_30_days=1,
            buyer_refund_count_30d=5,
        )
    )
    assert not hasattr(result, "eligible_amount_minor")
    assert not hasattr(result, "decision")


def test_risk_result_serializes_flags() -> None:
    engine = RiskEngine()
    result = engine.evaluate(
        RiskEvaluationInput(
            current_evidence_hashes=("hash",),
            previous_evidence_hashes=("hash",),
        )
    )
    dumped = result.model_dump(mode="json")
    assert dumped["flags"][0]["code"] == "DUPLICATE_EVIDENCE"
    assert dumped["flags"][0]["explanation"] == "Evidence hash matches a previous claim."
