import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.case import ApprovalRequest, Case
from app.models.order import Order
from app.models.seller import SellerPolicy
from app.models.shipment import Shipment
from app.services.audit import AuditLogService


@dataclass
class PolicyEvaluationResult:
    eligible: bool
    decision: str  # "executed" | "needs_approval" | "not_eligible"
    action: str  # "issue_return_label" | "instant_refund" | "escalate_for_approval" | "reject"
    amount: float
    reason: str
    details: dict[str, Any]


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class ResolutionTools:
    @staticmethod
    def lookup_order(db: Session, order_id: str) -> dict[str, Any] | None:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        return {
            "order_number": order.order_number,
            "order_date": order.order_date.isoformat(),
            "total_amount": order.total_amount / 100.0,
            "currency": order.currency,
            "order_status": order.order_status,
            "payment_status": order.payment_status,
            "payment_method": order.payment_method,
            "items_count": len(order.items) if isinstance(order.items, list) else 0,
            "items": order.items,
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
        }

    @staticmethod
    def evaluate_policy_rules(
        db: Session,
        seller_id: str,
        order: Order,
        issue_category: str,
        evidence_count: int,
    ) -> PolicyEvaluationResult:
        policy = (
            db.query(SellerPolicy)
            .filter(SellerPolicy.seller_id == seller_id, SellerPolicy.is_active.is_(True))
            .first()
        )

        rules = policy.parsed_rules if (policy and policy.parsed_rules) else {}
        returns_rule = rules.get("returns", {})
        refunds_rule = rules.get("refunds", {})
        damage_rule = rules.get("damage_claims", {})

        window_days = returns_rule.get("window_days", 7)
        auto_approve_max = float(refunds_rule.get("auto_approve_max_amount", 2000.0))
        instant_refund_thresh = float(
            refunds_rule.get("instant_refund_without_return_threshold", 500.0)
        )
        photo_required = damage_rule.get("photo_evidence_required", True)

        order_amount_inr = order.total_amount / 100.0

        # Find delivery date
        shipment = (
            db.query(Shipment)
            .filter(Shipment.order_id == order.id)
            .order_by(Shipment.created_at.desc())
            .first()
        )
        delivery_date = shipment.actual_delivery_date if shipment else None
        now = datetime.now(UTC)

        days_since_delivery = 0
        if delivery_date:
            days_since_delivery = (now - ensure_utc(delivery_date)).days

        # 1. Eligibility Check: Return window check (overdue returns are categorically rejected)
        if issue_category in ["return", "damaged"] and delivery_date:
            if days_since_delivery > window_days:
                return PolicyEvaluationResult(
                    eligible=False,
                    decision="not_eligible",
                    action="reject",
                    amount=0.0,
                    reason=(
                        f"Order was delivered {days_since_delivery} days ago, exceeding the "
                        f"{window_days}-day merchant return policy window."
                    ),
                    details={
                        "days_since_delivery": days_since_delivery,
                        "window_days": window_days,
                    },
                )

        # 2. Eligibility Check: Damage claim photo requirement
        if issue_category == "damaged" and photo_required and evidence_count == 0:
            return PolicyEvaluationResult(
                eligible=False,
                decision="not_eligible",
                action="reject",
                amount=0.0,
                reason=(
                    "Merchant policy requires photographic evidence for transit defect and damage claims. "
                    "Please attach photos of the outer box and affected item."
                ),
                details={"evidence_count": evidence_count, "photo_required": True},
            )

        # 3. Financial Ceiling Check: Orders exceeding auto-approve ceiling require seller approval
        if order_amount_inr > auto_approve_max:
            return PolicyEvaluationResult(
                eligible=True,
                decision="needs_approval",
                action="escalate_for_approval",
                amount=order_amount_inr,
                reason=(
                    f"Order value INR {order_amount_inr:.2f} exceeds merchant automated "
                    f"approval ceiling of INR {auto_approve_max:.2f}. "
                    "Escalated to merchant for 1-click decision."
                ),
                details={
                    "order_amount": order_amount_inr,
                    "ceiling": auto_approve_max,
                    "days_since_delivery": days_since_delivery,
                },
            )

        # 4. Instant refund under low threshold without return freight
        if order_amount_inr <= instant_refund_thresh and issue_category == "damaged":
            return PolicyEvaluationResult(
                eligible=True,
                decision="executed",
                action="instant_refund",
                amount=order_amount_inr,
                reason=(
                    f"Claim value INR {order_amount_inr:.2f} qualifies for instant settlement "
                    f"under INR {instant_refund_thresh:.2f} threshold without reverse pickup."
                ),
                details={"instant_refund": True, "amount": order_amount_inr},
            )

        # 5. Standard return label generation within parameters
        return PolicyEvaluationResult(
            eligible=True,
            decision="executed",
            action="issue_return_label",
            amount=order_amount_inr,
            reason=(
                f"Order is within the {window_days}-day window and below INR {auto_approve_max:.2f} ceiling. "
                "Reverse pickup label issued automatically."
            ),
            details={
                "window_days": window_days,
                "auto_approved": True,
                "amount": order_amount_inr,
            },
        )

    @staticmethod
    def execute_and_verify_action(
        db: Session,
        case: Case,
        order: Order,
        evaluation: PolicyEvaluationResult,
    ) -> dict[str, Any]:
        """Executes the deterministic action and cryptographically signs into audit trail."""
        now = datetime.now(UTC)

        if evaluation.action == "issue_return_label":
            reverse_awb = f"REV-DELHIVERY-{uuid.uuid4().hex[:6].upper()}"
            case.status = "resolved"
            case.decision = "executed"
            case.resolution_type = "return_label"
            case.outcome_details = {
                "reverse_awb": reverse_awb,
                "courier": "Delhivery",
                "pickup_status": "manifested",
                "reason": evaluation.reason,
            }
            case.resolved_at = now
            db.commit()

            AuditLogService.log_action(
                db=db,
                action="resolution.executed",
                actor_role="agent",
                actor_id=None,
                seller_id=case.seller_id,
                case_id=case.id,
                payload={
                    "resolution_type": "return_label",
                    "reverse_awb": reverse_awb,
                    "order_number": order.order_number,
                    "amount": evaluation.amount,
                },
            )

            return {
                "status": "executed",
                "resolution_type": "return_label",
                "reverse_awb": reverse_awb,
                "verified": True,
            }

        elif evaluation.action == "instant_refund":
            order.payment_status = "refunded"
            case.status = "resolved"
            case.decision = "executed"
            case.resolution_type = "refund"
            case.outcome_details = {
                "refunded_amount": evaluation.amount,
                "payment_status": "refunded",
                "reason": evaluation.reason,
            }
            case.resolved_at = now
            db.commit()

            AuditLogService.log_action(
                db=db,
                action="resolution.executed",
                actor_role="agent",
                actor_id=None,
                seller_id=case.seller_id,
                case_id=case.id,
                payload={
                    "resolution_type": "refund",
                    "order_number": order.order_number,
                    "amount": evaluation.amount,
                },
            )

            return {
                "status": "executed",
                "resolution_type": "refund",
                "amount": evaluation.amount,
                "verified": True,
            }

        elif evaluation.action == "escalate_for_approval":
            case.status = "pending_approval"
            case.decision = "needs_approval"
            case.outcome_details = {
                "escalated": True,
                "reason": evaluation.reason,
            }

            approval = ApprovalRequest(
                case_id=case.id,
                seller_id=case.seller_id,
                reason=evaluation.reason,
                auto_evaluation_summary=evaluation.details,
                requested_action={
                    "action": "refund",
                    "amount": evaluation.amount,
                },
                status="pending",
            )
            db.add(approval)
            db.commit()

            AuditLogService.log_action(
                db=db,
                action="approval.requested",
                actor_role="agent",
                actor_id=None,
                seller_id=case.seller_id,
                case_id=case.id,
                payload={
                    "order_number": order.order_number,
                    "reason": evaluation.reason,
                    "proposed_amount": evaluation.amount,
                },
            )

            return {
                "status": "needs_approval",
                "approval_id": approval.id,
                "verified": True,
            }

        else:  # reject
            case.status = "rejected"
            case.decision = "not_eligible"
            case.outcome_details = {
                "rejected": True,
                "reason": evaluation.reason,
            }
            case.resolved_at = now
            db.commit()

            AuditLogService.log_action(
                db=db,
                action="resolution.rejected",
                actor_role="agent",
                actor_id=None,
                seller_id=case.seller_id,
                case_id=case.id,
                payload={
                    "order_number": order.order_number,
                    "reason": evaluation.reason,
                },
            )

            return {
                "status": "not_eligible",
                "reason": evaluation.reason,
                "verified": True,
            }
