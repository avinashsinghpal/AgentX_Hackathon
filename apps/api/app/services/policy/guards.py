"""Individual deterministic policy guards.

Each guard is a pure function of trusted inputs and returns a CheckResult.  The
engine records every guard outcome, so a decision can be explained without any
LLM reasoning.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.policy.result import CheckResult
from app.services.policy.schemas import (
    CaseInput,
    ItemInput,
    OrderInput,
    ShipmentInput,
)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def days_between(now: datetime, earlier: datetime) -> int:
    """Whole days elapsed, using UTC-normalized values (0 for the same day)."""
    return max(0, int((ensure_utc(now) - ensure_utc(earlier)).total_seconds() // 86400))


def check_seller_status(status: str) -> CheckResult:
    normalized = (status or "").lower()
    if normalized == "suspended":
        return CheckResult(
            check="seller_status",
            passed=False,
            reason_code="SELLER_SUSPENDED",
            expected="active",
            actual=normalized,
            detail="The seller account is suspended; automated resolution is disabled.",
        )
    if normalized != "active":
        return CheckResult(
            check="seller_status",
            passed=False,
            reason_code="SELLER_INACTIVE",
            expected="active",
            actual=normalized,
            detail="The seller account is not active.",
        )
    return CheckResult(check="seller_status", passed=True, actual=normalized)


def check_case_order_ownership(case: CaseInput, order: OrderInput) -> CheckResult:
    if order.seller_id != case.seller_id:
        return CheckResult(
            check="case_order_seller",
            passed=False,
            reason_code="OWNERSHIP_MISMATCH",
            expected=case.seller_id,
            actual=order.seller_id,
            detail="The order does not belong to the seller that owns this case.",
        )
    if case.order_id != order.id:
        return CheckResult(
            check="case_order_seller",
            passed=False,
            reason_code="OWNERSHIP_MISMATCH",
            expected=order.id,
            actual=case.order_id,
            detail="The case does not reference this order.",
        )
    return CheckResult(check="case_order_seller", passed=True)


def check_buyer_ownership(case: CaseInput, order: OrderInput) -> CheckResult:
    if order.buyer_id is not None and order.buyer_id != case.buyer_id:
        return CheckResult(
            check="case_order_buyer",
            passed=False,
            reason_code="BUYER_OWNERSHIP_MISMATCH",
            expected=order.buyer_id,
            actual=case.buyer_id,
            detail="The case buyer does not match the order buyer.",
        )
    return CheckResult(check="case_order_buyer", passed=True)


def check_issue_category(category: str | None, valid_categories: frozenset[str]) -> CheckResult:
    if not category or category not in valid_categories:
        return CheckResult(
            check="issue_category",
            passed=False,
            reason_code="INVALID_CATEGORY",
            expected=sorted(valid_categories),
            actual=category,
            detail="The requested issue category is not supported by the policy engine.",
        )
    return CheckResult(check="issue_category", passed=True, actual=category)


def check_policy(present: bool, invalid: bool) -> CheckResult:
    if invalid:
        return CheckResult(
            check="policy_available",
            passed=False,
            reason_code="POLICY_INVALID",
            detail="The seller's stored policy could not be validated; manual review is required.",
        )
    if not present:
        return CheckResult(
            check="policy_available",
            passed=False,
            reason_code="POLICY_MISSING",
            detail="The seller has no active policy version to evaluate against.",
        )
    return CheckResult(check="policy_available", passed=True)


def check_duplicate_claim(exists: bool) -> CheckResult:
    if exists:
        return CheckResult(
            check="duplicate_claim",
            passed=False,
            reason_code="DUPLICATE_CLAIM",
            expected=False,
            actual=True,
            detail="Another claim for the same order and category is already in progress.",
        )
    return CheckResult(check="duplicate_claim", passed=True)


def check_delivery_data(shipment: ShipmentInput | None) -> CheckResult:
    if shipment is None:
        return CheckResult(
            check="delivery_data",
            passed=False,
            reason_code="SHIPMENT_DATA_MISSING",
            detail="No shipment record is available for this order.",
        )
    if shipment.actual_delivery_date is None and shipment.latest_event_at is None:
        return CheckResult(
            check="delivery_data",
            passed=False,
            reason_code="DELIVERY_DATE_UNKNOWN",
            detail="The delivery date cannot be established from the shipment record.",
        )
    return CheckResult(check="delivery_data", passed=True)


def check_return_window(days_since_delivery: int, window_days: int) -> CheckResult:
    passed = days_since_delivery <= window_days
    return CheckResult(
        check="return_window",
        passed=passed,
        reason_code=None if passed else "RETURN_WINDOW_EXPIRED",
        expected=window_days,
        actual=days_since_delivery,
        detail=(
            f"Delivered {days_since_delivery} day(s) ago; the return window is {window_days} day(s)."
        ),
    )


def check_damage_report_window(days_since_delivery: int, window_days: int) -> CheckResult:
    passed = days_since_delivery <= window_days
    return CheckResult(
        check="damage_report_window",
        passed=passed,
        reason_code=None if passed else "DAMAGE_CLAIM_WINDOW_EXPIRED",
        expected=window_days,
        actual=days_since_delivery,
        detail=(
            f"Damage reported {days_since_delivery} day(s) after delivery; the damage reporting "
            f"window is {window_days} day(s)."
        ),
    )


def check_items_returnable(
    items: tuple[ItemInput, ...], non_returnable_categories: list[str]
) -> CheckResult:
    blocked = sorted(
        {
            (item.category or "").strip().lower()
            for item in items
            if (item.category or "").strip().lower() in set(non_returnable_categories)
            or item.returnable is False
        }
    )
    return CheckResult(
        check="item_returnability",
        passed=not blocked,
        reason_code=None if not blocked else "NON_RETURNABLE_ITEM",
        expected=non_returnable_categories,
        actual=blocked,
        detail=(
            "All items are returnable."
            if not blocked
            else "One or more items are not returnable under the seller policy."
        ),
    )


def check_evidence_requirement(
    category: str | None, require_photo: bool, evidence_count: int
) -> CheckResult:
    required = category == "damaged" and require_photo
    passed = (not required) or evidence_count > 0
    return CheckResult(
        check="damage_evidence",
        passed=passed,
        reason_code=None if passed else "MISSING_DAMAGE_PHOTO",
        expected=1 if required else 0,
        actual=evidence_count,
        detail=(
            "Photographic evidence is required for damage claims."
            if required
            else "No photographic evidence is required for this category."
        ),
    )


def check_buyer_refund_history(
    refund_count_30d: int, maximum: int, escalate: bool
) -> CheckResult:
    passed = refund_count_30d <= maximum
    return CheckResult(
        check="buyer_refund_history",
        passed=passed,
        reason_code=None
        if passed
        else ("FRAUD_LIMIT_EXCEEDED_ESCALATED" if escalate else "FRAUD_LIMIT_EXCEEDED"),
        expected=maximum,
        actual=refund_count_30d,
        detail=(
            f"Buyer has {refund_count_30d} refund(s) in the last 30 days; "
            f"the configured maximum is {maximum}."
        ),
    )


def check_approval_ceiling(amount_minor: int, ceiling_minor: int) -> CheckResult:
    passed = amount_minor <= ceiling_minor
    return CheckResult(
        check="approval_ceiling",
        passed=passed,
        reason_code=None if passed else "APPROVAL_CEILING_EXCEEDED",
        expected=ceiling_minor,
        actual=amount_minor,
        detail=(
            f"Amount {amount_minor} minor units is within the automatic approval ceiling "
            f"of {ceiling_minor}."
            if passed
            else f"Amount {amount_minor} minor units exceeds the automatic approval ceiling "
            f"of {ceiling_minor}."
        ),
    )


def check_delay_threshold(days_late: int, threshold_days: int) -> CheckResult:
    passed = days_late >= threshold_days
    return CheckResult(
        check="delay_threshold",
        passed=passed,
        reason_code=None if passed else "DELAY_THRESHOLD_NOT_MET",
        expected=threshold_days,
        actual=days_late,
        detail=f"Shipment is {days_late} day(s) late against a {threshold_days}-day threshold.",
    )
