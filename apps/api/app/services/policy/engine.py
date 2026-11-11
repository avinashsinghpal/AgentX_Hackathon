"""Deterministic policy engine.

Same validated inputs and same policy version always produce the same decision
and the same evaluation result.  The engine performs no I/O, issues no refunds,
and never consults an LLM.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.policy import guards
from app.services.policy.result import CheckResult, Decision, EvaluationResult
from app.services.policy.schemas import (
    DELIVERY_REQUIRED_CATEGORIES,
    VALID_ISSUE_CATEGORIES,
    PolicyEvaluationInput,
)


class PolicyEngine:
    EVALUATOR_VERSION = "1.0.0"

    def evaluate(self, inputs: PolicyEvaluationInput) -> EvaluationResult:
        now = guards.ensure_utc(inputs.now or datetime.now(UTC))
        checks: list[CheckResult] = []

        checks.append(guards.check_seller_status(inputs.seller_status))
        if not checks[-1].passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                checks[-1].reason_code or "SELLER_INACTIVE",
                "Automated resolution is unavailable because the seller account is not active.",
                amount_minor=0,
                action="reject",
            )

        ownership = guards.check_case_order_ownership(inputs.case, inputs.order)
        checks.append(ownership)
        if not ownership.passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "OWNERSHIP_MISMATCH",
                "This case, order and seller relationship is inconsistent.",
                amount_minor=0,
                action="reject",
            )

        buyer_check = guards.check_buyer_ownership(inputs.case, inputs.order)
        checks.append(buyer_check)
        if not buyer_check.passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "BUYER_OWNERSHIP_MISMATCH",
                "This case does not belong to the buyer on the order.",
                amount_minor=0,
                action="reject",
            )

        policy_check = guards.check_policy(
            present=inputs.policy is not None,
            invalid=inputs.policy_invalid,
        )
        checks.append(policy_check)
        if not policy_check.passed:
            decision = (
                Decision.MANUAL_REVIEW
                if policy_check.reason_code == "POLICY_INVALID"
                else Decision.NOT_ELIGIBLE
            )
            return self._result(
                inputs,
                now,
                checks,
                decision,
                policy_check.reason_code or "POLICY_MISSING",
                policy_check.detail or "No usable seller policy.",
                amount_minor=0,
                action="manual_review" if decision is Decision.MANUAL_REVIEW else "reject",
                requires_approval=decision is Decision.MANUAL_REVIEW,
            )

        assert inputs.policy is not None
        policy = inputs.policy

        category_check = guards.check_issue_category(
            inputs.case.issue_category, VALID_ISSUE_CATEGORIES
        )
        checks.append(category_check)
        if not category_check.passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "INVALID_CATEGORY",
                "The requested issue category is not supported by merchant policy.",
                amount_minor=0,
                action="reject",
            )

        duplicate_check = guards.check_duplicate_claim(inputs.duplicate_claim_exists)
        checks.append(duplicate_check)
        if not duplicate_check.passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "DUPLICATE_CLAIM",
                "A claim for this order and category is already being handled.",
                amount_minor=0,
                action="reject",
            )

        # Policy currency must agree with the order currency before any amount is
        # computed; mixing currencies would make the ceiling meaningless.
        if (policy.currency or "").upper() != (inputs.order.currency or "").upper():
            checks.append(
                CheckResult(
                    check="currency_match",
                    passed=False,
                    reason_code="CURRENCY_MISMATCH",
                    expected=policy.currency,
                    actual=inputs.order.currency,
                    detail="Policy currency does not match the order currency.",
                )
            )
            return self._result(
                inputs,
                now,
                checks,
                Decision.MANUAL_REVIEW,
                "CURRENCY_MISMATCH",
                "The active policy currency does not match the order currency.",
                amount_minor=0,
                action="manual_review",
                requires_approval=True,
            )

        if inputs.case.issue_category == "delay":
            return self._evaluate_delay(inputs, now, checks)

        return self._evaluate_claim(inputs, now, checks)

    # ------------------------------------------------------------------ claim
    def _evaluate_claim(
        self,
        inputs: PolicyEvaluationInput,
        now: datetime,
        checks: list[CheckResult],
    ) -> EvaluationResult:
        assert inputs.policy is not None
        policy = inputs.policy
        category = inputs.case.issue_category or ""
        order = inputs.order
        days_since_delivery: int | None = None

        if category in DELIVERY_REQUIRED_CATEGORIES:
            delivery_check = guards.check_delivery_data(inputs.shipment)
            checks.append(delivery_check)
            if not delivery_check.passed:
                return self._result(
                    inputs,
                    now,
                    checks,
                    Decision.MANUAL_REVIEW,
                    delivery_check.reason_code or "DELIVERY_DATE_UNKNOWN",
                    delivery_check.detail or "Delivery data is unavailable.",
                    amount_minor=0,
                    action="manual_review",
                    requires_approval=True,
                )

            assert inputs.shipment is not None
            delivery_date = (
                inputs.shipment.actual_delivery_date or inputs.shipment.latest_event_at
            )
            assert delivery_date is not None
            days_since_delivery = guards.days_between(now, delivery_date)

            if category == "damaged":
                damage_window = guards.check_damage_report_window(
                    days_since_delivery, policy.damage_claims.report_within_days
                )
                checks.append(damage_window)
                if not damage_window.passed:
                    return self._result(
                        inputs,
                        now,
                        checks,
                        Decision.NOT_ELIGIBLE,
                        "DAMAGE_CLAIM_WINDOW_EXPIRED",
                        (
                            f"Damage was reported {days_since_delivery} days after delivery, "
                            f"exceeding the {policy.damage_claims.report_within_days}-day damage "
                            "claim reporting window."
                        ),
                        amount_minor=0,
                        action="reject",
                    )

            window_check = guards.check_return_window(
                days_since_delivery, policy.returns.window_days
            )
            checks.append(window_check)
            if not window_check.passed:
                return self._result(
                    inputs,
                    now,
                    checks,
                    Decision.NOT_ELIGIBLE,
                    "RETURN_WINDOW_EXPIRED",
                    (
                        f"Order was delivered {days_since_delivery} days ago, exceeding the "
                        f"{policy.returns.window_days}-day merchant return policy window."
                    ),
                    amount_minor=0,
                    action="reject",
                )

        if category == "cancellation":
            if order.order_status in {"shipped", "delivered", "returned"}:
                checks.append(
                    CheckResult(
                        check="cancellation_window",
                        passed=False,
                        reason_code="CANCELLATION_WINDOW_CLOSED",
                        expected="placed",
                        actual=order.order_status,
                        detail="The order has already been fulfilled and can no longer be cancelled.",
                    )
                )
                return self._result(
                    inputs,
                    now,
                    checks,
                    Decision.NOT_ELIGIBLE,
                    "CANCELLATION_WINDOW_CLOSED",
                    "The order has already been fulfilled, so cancellation is no longer available.",
                    amount_minor=0,
                    action="reject",
                )

        items = inputs.items

        if category in DELIVERY_REQUIRED_CATEGORIES:
            returnable_check = guards.check_items_returnable(
                items, policy.returns.non_returnable_categories
            )
            checks.append(returnable_check)
            if not returnable_check.passed:
                return self._result(
                    inputs,
                    now,
                    checks,
                    Decision.NOT_ELIGIBLE,
                    "NON_RETURNABLE_ITEM",
                    "One or more items in this order are excluded from returns by merchant policy.",
                    amount_minor=0,
                    action="reject",
                )

            evidence_check = guards.check_evidence_requirement(
                category, policy.damage_claims.require_photo, inputs.evidence_count
            )
            checks.append(evidence_check)
            if not evidence_check.passed:
                return self._result(
                    inputs,
                    now,
                    checks,
                    Decision.NOT_ELIGIBLE,
                    "MISSING_DAMAGE_PHOTO",
                    (
                        "Merchant policy requires photographic evidence for transit defect and "
                        "damage claims. Please attach photos of the outer box and affected item."
                    ),
                    amount_minor=0,
                    action="reject",
                )

        eligible_amount_minor = order.total_amount_minor

        fraud_check = guards.check_buyer_refund_history(
            inputs.buyer_refund_count_30d,
            policy.fraud_checks.max_refunds_per_buyer_per_30_days,
            policy.fraud_checks.require_seller_approval_if_exceeded,
        )
        checks.append(fraud_check)
        if not fraud_check.passed:
            if policy.fraud_checks.require_seller_approval_if_exceeded:
                return self._result(
                    inputs,
                    now,
                    checks,
                    Decision.NEEDS_APPROVAL,
                    "FRAUD_LIMIT_EXCEEDED_ESCALATED",
                    (
                        f"Buyer has submitted {inputs.buyer_refund_count_30d} refunds in the last "
                        "30 days, which exceeds the merchant risk threshold. Seller review is required."
                    ),
                    amount_minor=eligible_amount_minor,
                    action=self._proposed_action(inputs),
                    requires_approval=True,
                )
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "FRAUD_LIMIT_EXCEEDED",
                "Buyer refund frequency exceeds the merchant risk limit.",
                amount_minor=0,
                action="reject",
            )

        ceiling_check = guards.check_approval_ceiling(
            eligible_amount_minor, policy.refunds.auto_approve_ceiling_minor
        )
        checks.append(ceiling_check)
        if not ceiling_check.passed:
            ceiling_major = eligible_amount_minor / 100.0
            ceiling_limit = policy.refunds.auto_approve_up_to
            return self._result(
                inputs,
                now,
                checks,
                Decision.NEEDS_APPROVAL,
                "APPROVAL_CEILING_EXCEEDED",
                (
                    f"Order value {inputs.order.currency} {ceiling_major:.2f} exceeds merchant "
                    f"automated approval ceiling of {inputs.order.currency} {ceiling_limit:.2f}. "
                    "Escalated to merchant for 1-click decision."
                ),
                amount_minor=eligible_amount_minor,
                action=self._proposed_action(inputs),
                requires_approval=True,
            )

        proposed_action = self._proposed_action(inputs)
        if proposed_action == "return_label":
            reason = (
                f"Order is within the {policy.returns.window_days}-day return window and the "
                f"refund amount is below the {inputs.order.currency} "
                f"{policy.refunds.auto_approve_up_to:.2f} automatic approval ceiling. "
                "A reverse pickup label can be issued automatically."
            )
            reason_code = "RETURN_ELIGIBLE"
        else:
            reason = (
                f"Claim qualifies for automatic settlement under {inputs.order.currency} "
                f"{policy.refunds.auto_approve_up_to:.2f} and the configured "
                f"{policy.returns.window_days}-day policy window."
            )
            reason_code = "REFUND_ELIGIBLE"

        cod_check = CheckResult(
            check="cod_refund_method",
            passed=True,
            actual=order.payment_method,
            detail=(
                "COD refund is settled as store credit per policy."
                if order.payment_method == "cod" and proposed_action == "wallet_credit"
                else "No COD restriction applies."
            ),
        )
        checks.append(cod_check)

        return self._result(
            inputs,
            now,
            checks,
            Decision.ELIGIBLE,
            reason_code,
            reason,
            amount_minor=eligible_amount_minor,
            action=proposed_action,
            requires_approval=False,
        )

    # ------------------------------------------------------------------ delay
    def _evaluate_delay(
        self,
        inputs: PolicyEvaluationInput,
        now: datetime,
        checks: list[CheckResult],
    ) -> EvaluationResult:
        assert inputs.policy is not None
        policy = inputs.policy
        shipment = inputs.shipment

        if shipment is None or shipment.promised_delivery_date is None:
            checks.append(
                CheckResult(
                    check="shipment_data",
                    passed=False,
                    reason_code="SHIPMENT_DATA_MISSING",
                    expected="promised_delivery_date",
                    actual=None,
                    detail="No promised delivery date is available; delay cannot be evaluated.",
                )
            )
            return self._result(
                inputs,
                now,
                checks,
                Decision.MANUAL_REVIEW,
                "SHIPMENT_DATA_MISSING",
                "Shipment tracking data is missing or stale; manual review is required.",
                amount_minor=0,
                action="manual_review",
                requires_approval=True,
            )

        if shipment.status == "delivered":
            checks.append(
                CheckResult(
                    check="shipment_status",
                    passed=False,
                    reason_code="SHIPMENT_ALREADY_DELIVERED",
                    expected="in_transit",
                    actual=shipment.status,
                    detail="The shipment has already been delivered.",
                )
            )
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "SHIPMENT_ALREADY_DELIVERED",
                "The shipment has already been delivered.",
                amount_minor=0,
                action="reject",
            )

        days_late = guards.days_between(now, shipment.promised_delivery_date)
        threshold_check = guards.check_delay_threshold(
            days_late, policy.delays.notify_after_days_late
        )
        checks.append(threshold_check)
        if not threshold_check.passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "DELAY_THRESHOLD_NOT_MET",
                (
                    f"Shipment is {days_late} day(s) late, below the merchant delay threshold of "
                    f"{policy.delays.notify_after_days_late} day(s)."
                ),
                amount_minor=0,
                action="reject",
            )

        per_day = policy.delays.compensation_per_day_minor
        maximum = policy.delays.max_compensation_minor
        compensation_minor = min(days_late * per_day, maximum) if per_day > 0 else 0

        if compensation_minor <= 0:
            checks.append(
                CheckResult(
                    check="delay_compensation",
                    passed=False,
                    reason_code="DELAY_COMPENSATION_NOT_CONFIGURED",
                    expected=">0",
                    actual=compensation_minor,
                    detail="The seller policy does not configure delay compensation.",
                )
            )
            return self._result(
                inputs,
                now,
                checks,
                Decision.NOT_ELIGIBLE,
                "DELAY_COMPENSATION_NOT_CONFIGURED",
                (
                    f"Shipment is {days_late} day(s) late, but the merchant policy does not "
                    "authorize automatic delay compensation."
                ),
                amount_minor=0,
                action="reject",
            )

        ceiling_check = guards.check_approval_ceiling(
            compensation_minor, policy.refunds.auto_approve_ceiling_minor
        )
        checks.append(ceiling_check)
        if not ceiling_check.passed:
            return self._result(
                inputs,
                now,
                checks,
                Decision.NEEDS_APPROVAL,
                "APPROVAL_CEILING_EXCEEDED",
                (
                    f"Delay compensation of {inputs.order.currency} {compensation_minor / 100:.2f} "
                    "exceeds the merchant automatic approval ceiling. Seller review is required."
                ),
                amount_minor=compensation_minor,
                action="wallet_credit",
                requires_approval=True,
            )

        checks.append(
            CheckResult(
                check="delay_compensation",
                passed=True,
                expected=f"<= {maximum}",
                actual=compensation_minor,
                detail=(
                    f"{days_late} day(s) late at {per_day} minor units per day, capped at "
                    f"{maximum} minor units."
                ),
            )
        )

        return self._result(
            inputs,
            now,
            checks,
            Decision.ELIGIBLE,
            "DELAY_COMPENSATION_ELIGIBLE",
            (
                f"Shipment is {days_late} day(s) past the promised delivery date. Merchant policy "
                f"authorizes {inputs.order.currency} {compensation_minor / 100:.2f} of wallet credit."
            ),
            amount_minor=compensation_minor,
            action="wallet_credit",
            requires_approval=False,
        )

    # ----------------------------------------------------------------- helpers
    def _proposed_action(self, inputs: PolicyEvaluationInput) -> str:
        assert inputs.policy is not None
        order = inputs.order
        category = inputs.case.issue_category or ""

        if order.payment_method == "cod":
            if (
                inputs.policy.refunds.cod_refund_method == "store_credit"
                or order.payment_status != "captured"
            ):
                return "wallet_credit"

        if category == "return":
            return "return_label"

        return "refund"

    def _result(
        self,
        inputs: PolicyEvaluationInput,
        now: datetime,
        checks: list[CheckResult],
        decision: Decision,
        reason_code: str,
        reason: str,
        *,
        amount_minor: int,
        action: str,
        requires_approval: bool | None = None,
    ) -> EvaluationResult:
        return EvaluationResult(
            seller_id=inputs.case.seller_id,
            order_id=inputs.order.id,
            buyer_id=inputs.case.buyer_id,
            case_id=inputs.case.id,
            currency=inputs.order.currency,
            policy_id=inputs.policy_id,
            policy_version=inputs.policy_version
            or (inputs.policy.version if inputs.policy else 0),
            decision=decision,
            reason_code=reason_code,
            reason=reason,
            eligible_amount_minor=amount_minor,
            proposed_action=action,
            requires_approval=(
                decision in {Decision.NEEDS_APPROVAL, Decision.MANUAL_REVIEW}
                if requires_approval is None
                else requires_approval
            ),
            evaluated_at=now,
            checks=checks,
            evidence_reference_ids=list(inputs.evidence_reference_ids),
            evaluator_version=inputs.evaluator_version,
            scenario="delay" if inputs.case.issue_category == "delay" else "case",
        )
