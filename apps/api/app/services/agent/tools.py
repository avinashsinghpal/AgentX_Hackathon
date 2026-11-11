"""Backward-compatible investigation tool façade.

The authoritative implementation now lives in the policy and action services.
This module keeps the historical ``ResolutionTools`` entry points working for
older callers while delegating all decisions and mutations to the new services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.order import Order
from app.models.shipment import Shipment
from app.services.orders import order_items_payload, tracking_events_payload
from app.services.policy.evaluator import PolicyEvaluationService
from app.services.policy.result import Decision
from app.services.resolution import ResolutionService


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


@dataclass
class PolicyEvaluationResult:
    """Legacy shape retained for compatibility."""

    eligible: bool
    decision: str  # "executed" | "needs_approval" | "not_eligible"
    action: str
    amount: float
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


_ACTION_BY_PROPOSED = {
    "refund": "instant_refund",
    "wallet_credit": "instant_refund",
    "return_label": "issue_return_label",
}

_BADGE_BY_DECISION = {
    Decision.ELIGIBLE: "executed",
    Decision.NEEDS_APPROVAL: "needs_approval",
    Decision.MANUAL_REVIEW: "needs_approval",
    Decision.NOT_ELIGIBLE: "not_eligible",
}


class ResolutionTools:
    @staticmethod
    def lookup_order(db: Session, order_id: str) -> dict[str, Any] | None:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        items = order_items_payload(order)
        return {
            "order_number": order.order_number,
            "order_date": order.order_date.isoformat(),
            "total_amount": order.total_amount / 100.0,
            "total_amount_minor": order.total_amount,
            "currency": order.currency,
            "order_status": order.order_status,
            "payment_status": order.payment_status,
            "payment_method": order.payment_method,
            "items_count": len(items),
            "items": items,
        }

    @staticmethod
    def lookup_shipment(db: Session, order_id: str) -> dict[str, Any] | None:
        shipment = (
            db.query(Shipment)
            .filter(Shipment.order_id == order_id)
            .order_by(Shipment.created_at.desc())
            .first()
        )
        if not shipment:
            return None
        return {
            "courier_partner": shipment.courier_partner,
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "dispatch_pincode": shipment.dispatch_pincode,
            "destination_pincode": shipment.destination_pincode,
            "promised_delivery_date": (
                shipment.promised_delivery_date.isoformat()
                if shipment.promised_delivery_date
                else None
            ),
            "actual_delivery_date": (
                shipment.actual_delivery_date.isoformat() if shipment.actual_delivery_date else None
            ),
            "tracking_events": tracking_events_payload(shipment),
        }

    @staticmethod
    def evaluate_policy_rules(
        db: Session,
        seller_id: str,
        order: Order,
        issue_category: str,
        evidence_count: int,
    ) -> PolicyEvaluationResult:
        """Deterministic evaluation through the shared engine (read-only)."""
        evaluation = PolicyEvaluationService().evaluate_order_category(
            db,
            order=order,
            seller_id=seller_id,
            buyer_id=order.buyer_id,
            issue_category=issue_category,
            evidence_count=evidence_count,
            persist=False,
        )
        result = evaluation.result
        return PolicyEvaluationResult(
            eligible=result.decision is Decision.ELIGIBLE,
            decision=_BADGE_BY_DECISION[result.decision],
            action=_ACTION_BY_PROPOSED.get(result.proposed_action, "reject")
            if result.decision in {Decision.ELIGIBLE, Decision.NEEDS_APPROVAL}
            else "reject",
            amount=result.eligible_amount_minor / 100.0,
            reason=result.reason,
            details={
                "reason_code": result.reason_code,
                "policy_version": result.policy_version,
                "checks": [check.model_dump(mode="json") for check in result.checks],
            },
        )

    @staticmethod
    def execute_and_verify_action(
        db: Session,
        case: Case,
        order: Order,
        evaluation: PolicyEvaluationResult | None = None,
    ) -> dict[str, Any]:
        """Run the authoritative resolution path for an existing case.

        The previously computed legacy evaluation is not trusted for amounts or
        authorization; the deterministic engine re-evaluates from the database.
        """
        service = ResolutionService()
        investigation = service.investigate(db, case.id)
        decision = service.decide(db, investigation)
        if decision.approval is not None:
            return {
                "status": "needs_approval",
                "approval_id": decision.approval.id,
                "verified": False,
            }
        if decision.action_run is not None and decision.action_run.executed:
            action = decision.action_run.action
            return {
                "status": "executed",
                "resolution_type": case.resolution_type,
                "amount": (action.amount_minor or 0) / 100.0,
                "amount_minor": action.amount_minor,
                "provider_reference": action.external_reference,
                "verified": True,
            }
        if decision.evaluation.decision is Decision.NOT_ELIGIBLE:
            return {
                "status": "not_eligible",
                "reason": decision.evaluation.reason,
                "verified": False,
            }
        return {
            "status": "failed",
            "reason": decision.action_run.reason if decision.action_run else "not executed",
            "verified": False,
        }
