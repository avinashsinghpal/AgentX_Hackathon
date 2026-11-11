"""Seller approval lifecycle.

Approval authorizes execution.  It does not prove that anything happened: the
linked action and its verification record are the evidence of execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.case import ApprovalRequest, Case, CaseMessage
from app.models.order import Order
from app.models.policy_evaluation import PolicyEvaluation
from app.models.seller import Seller
from app.services.actions.service import ActionRun, ActionService
from app.services.audit import AuditLogService
from app.services.policy.result import Decision, EvaluationResult

DEFAULT_APPROVAL_TTL_HOURS = 72


class ApprovalError(Exception):
    """Base class for approval lifecycle failures."""


class ApprovalNotFoundError(ApprovalError):
    pass


class ApprovalStateError(ApprovalError):
    pass


class StaleApprovalError(ApprovalStateError):
    pass


@dataclass
class ApprovalOutcome:
    approval: ApprovalRequest
    case: Case
    executed: bool
    action: ActionRun | None = None
    failure_reason: str | None = None


def resolve_requested_amount_minor(approval: ApprovalRequest, order: Order | None) -> int:
    """Amount for an approval, tolerating rows created before the migration.

    Legacy ``requested_action`` JSON used floats in major units; integer values
    were already minor units.  New rows always populate ``requested_amount_minor``.
    """
    if approval.requested_amount_minor is not None:
        return int(approval.requested_amount_minor)

    payload = approval.requested_action or {}
    if isinstance(payload.get("amount_minor"), int):
        return int(payload["amount_minor"])

    amount = payload.get("amount")
    if isinstance(amount, bool):
        amount = None
    if isinstance(amount, int):
        return amount
    if isinstance(amount, float):
        return int(round(amount * 100))
    if order is not None:
        return int(order.total_amount)
    return 0


def requested_action_type(approval: ApprovalRequest) -> str:
    payload = approval.requested_action or {}
    raw = str(payload.get("type") or payload.get("action") or "refund")
    mapping = {
        "issue_return_label": "return_label",
        "instant_refund": "refund",
        "escalate_for_approval": "refund",
    }
    return mapping.get(raw, raw if raw in {"refund", "wallet_credit", "return_label"} else "refund")


class ApprovalService:
    def __init__(self, action_service: ActionService | None = None) -> None:
        self.actions = action_service or ActionService()

    # ------------------------------------------------------------------ requests
    def request_for_evaluation(
        self,
        db: Session,
        *,
        case: Case,
        evaluation: EvaluationResult,
        evaluation_id: str | None = None,
        now: datetime | None = None,
        ttl_hours: int = DEFAULT_APPROVAL_TTL_HOURS,
    ) -> ApprovalRequest:
        requested_at = now or datetime.now(UTC)
        existing = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.case_id == case.id,
                ApprovalRequest.status == "pending",
                ApprovalRequest.requested_amount_minor == evaluation.eligible_amount_minor,
            )
            .order_by(ApprovalRequest.created_at.desc())
            .first()
        )
        if existing is not None:
            return existing

        amount_major = evaluation.eligible_amount_minor / 100.0
        approval = ApprovalRequest(
            case_id=case.id,
            seller_id=case.seller_id,
            policy_evaluation_id=evaluation_id,
            reason=evaluation.reason,
            auto_evaluation_summary={
                "decision": evaluation.decision.value,
                "reason_code": evaluation.reason_code,
                "policy_version": evaluation.policy_version,
                "eligible_amount_minor": evaluation.eligible_amount_minor,
                "currency": evaluation.currency,
                "checks": [check.model_dump(mode="json") for check in evaluation.checks],
            },
            requested_action={
                "type": evaluation.proposed_action,
                "action": evaluation.proposed_action,
                "amount": amount_major,
                "amount_minor": evaluation.eligible_amount_minor,
                "currency": evaluation.currency,
                "policy_version": evaluation.policy_version,
            },
            requested_amount_minor=evaluation.eligible_amount_minor,
            currency=evaluation.currency,
            status="pending",
            expires_at=requested_at + timedelta(hours=ttl_hours),
        )
        db.add(approval)

        case.status = "pending_approval"
        case.decision = "needs_approval"
        case.outcome_details = {
            "escalated": True,
            "reason": evaluation.reason,
            "policy_decision": evaluation.decision.value,
            "policy_version": evaluation.policy_version,
            "proposed_action": evaluation.proposed_action,
            "amount_minor": evaluation.eligible_amount_minor,
        }

        AuditLogService.log_action(
            db=db,
            action="approval.requested",
            actor_role="agent",
            actor_id=None,
            seller_id=case.seller_id,
            case_id=case.id,
            payload={
                "reason": evaluation.reason,
                "reason_code": evaluation.reason_code,
                "proposed_action": evaluation.proposed_action,
                "amount_minor": evaluation.eligible_amount_minor,
                "policy_version": evaluation.policy_version,
            },
            commit=False,
        )
        db.commit()
        db.refresh(approval)
        return approval

    def cancel(
        self,
        db: Session,
        approval: ApprovalRequest,
        *,
        reason: str,
        actor_role: str = "system",
        actor_id: str | None = None,
    ) -> None:
        approval.status = "cancelled"
        approval.decision_reason = reason
        approval.decided_at = datetime.now(UTC)
        AuditLogService.log_action(
            db=db,
            action="approval.cancelled",
            actor_role=actor_role,
            actor_id=actor_id,
            seller_id=approval.seller_id,
            case_id=approval.case_id,
            payload={"approval_id": approval.id, "reason": reason},
            commit=False,
        )
        db.commit()

    # ------------------------------------------------------------------ decision
    def decide(
        self,
        db: Session,
        *,
        approval_id: str,
        seller: Seller,
        decision: str,
        seller_notes: str | None = None,
        now: datetime | None = None,
    ) -> ApprovalOutcome:
        decided_at = now or datetime.now(UTC)
        approval = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.seller_id == seller.id,
            )
            .first()
        )
        if approval is None:
            raise ApprovalNotFoundError("Approval request not found.")

        if approval.status != "pending":
            raise ApprovalStateError(
                f"This request has already been decided ({approval.status})."
            )

        if approval.expires_at is not None:
            expires_at = approval.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if decided_at > expires_at:
                approval.status = "expired"
                approval.decision_reason = "Approval request expired before a decision was made."
                approval.decided_at = decided_at
                AuditLogService.log_action(
                    db=db,
                    action="approval.expired",
                    actor_role="seller",
                    actor_id=seller.user_id,
                    seller_id=seller.id,
                    case_id=approval.case_id,
                    payload={"approval_id": approval.id},
                    commit=False,
                )
                db.commit()
                raise ApprovalStateError("This approval request has expired.")

        case = db.query(Case).filter(Case.id == approval.case_id).first()
        if case is None:
            raise StaleApprovalError("The case behind this approval no longer exists.")

        if case.seller_id != seller.id:
            raise ApprovalNotFoundError("Approval request not found.")

        order = db.query(Order).filter(Order.id == case.order_id).first()
        if order is None or order.seller_id != case.seller_id:
            raise StaleApprovalError(
                "The case and order no longer agree on ownership; approval is stale."
            )

        evaluation_record = self._validate_freshness(db, approval, case, order)

        approval.seller_notes = seller_notes
        approval.decided_at = decided_at
        approval.approved_by = seller.user_id

        if decision == "rejected":
            approval.status = "rejected"
            approval.decision_reason = seller_notes or "Rejected by seller."
            case.status = "rejected"
            case.decision = "not_eligible"
            case.resolved_at = decided_at
            case.outcome_details = {
                "rejected": True,
                "reason": seller_notes or "Seller rejected the requested resolution.",
                "approval_id": approval.id,
            }

            message = f"Merchant Rejected Exception: {approval.reason}"
            if seller_notes:
                message += f"\nMerchant Note: {seller_notes}"
            db.add(
                CaseMessage(
                    case_id=case.id,
                    sender_role="seller",
                    message=message,
                    decision_badge="not_eligible",
                )
            )

            AuditLogService.log_action(
                db=db,
                action="approval.rejected",
                actor_role="seller",
                actor_id=seller.user_id,
                seller_id=seller.id,
                case_id=case.id,
                payload={"approval_id": approval.id, "seller_notes": seller_notes},
                commit=False,
            )
            db.commit()
            db.refresh(approval)
            return ApprovalOutcome(
                approval=approval, case=case, executed=False, failure_reason="rejected"
            )

        if decision != "approved":
            raise ApprovalStateError(f"Unsupported decision '{decision}'.")

        approval.status = "approved"
        approval.decision_reason = seller_notes or "Approved by seller."

        AuditLogService.log_action(
            db=db,
            action="approval.approved",
            actor_role="seller",
            actor_id=seller.user_id,
            seller_id=seller.id,
            case_id=case.id,
            payload={
                "approval_id": approval.id,
                "seller_notes": seller_notes,
                "requested_action": approval.requested_action,
            },
            commit=False,
        )
        db.commit()
        db.refresh(approval)

        # Authorization is complete; execution + verification follow.
        evaluation = self._authorized_evaluation(approval, case, order, evaluation_record)
        action_type = requested_action_type(approval)

        run = self.actions.execute_for_case(
            db,
            case=case,
            order=order,
            evaluation=evaluation,
            actor_role="seller",
            actor_id=seller.user_id,
            approval_status="approved",
            approval_id=approval.id,
            approval_action_type=action_type,
            approval_amount_minor=resolve_requested_amount_minor(approval, order),
            policy_evaluation_id=approval.policy_evaluation_id,
        )

        approval.action_id = run.action.id
        db.commit()
        db.refresh(approval)
        db.refresh(case)

        if run.executed:
            message = (
                f"Merchant Approved Exception: {approval.reason}\n"
                f"Executed and verified {action_type.replace('_', ' ')} of "
                f"{approval.currency or order.currency} "
                f"{resolve_requested_amount_minor(approval, order) / 100:.2f}."
            )
            db.add(
                CaseMessage(
                    case_id=case.id,
                    sender_role="seller",
                    message=message,
                    decision_badge="executed",
                )
            )
        else:
            case.status = "pending_approval"
            db.add(
                CaseMessage(
                    case_id=case.id,
                    sender_role="seller",
                    message=(
                        f"Merchant Approved Exception: {approval.reason}\n"
                        f"Execution could not be verified ({run.reason or run.status}). "
                        "The action was not completed and can be retried safely."
                    ),
                    decision_badge="needs_approval",
                )
            )
        db.commit()

        return ApprovalOutcome(
            approval=approval,
            case=case,
            executed=run.executed,
            action=run,
            failure_reason=None if run.executed else (run.reason or run.status),
        )

    # ------------------------------------------------------------------ helpers
    def _validate_freshness(
        self,
        db: Session,
        approval: ApprovalRequest,
        case: Case,
        order: Order,
    ) -> PolicyEvaluation | None:
        record: PolicyEvaluation | None = None

        if approval.policy_evaluation_id:
            record = (
                db.query(PolicyEvaluation)
                .filter(PolicyEvaluation.id == approval.policy_evaluation_id)
                .first()
            )
            if record is None:
                self.cancel(
                    db,
                    approval,
                    reason="The policy evaluation behind this approval no longer exists.",
                )
                raise StaleApprovalError(
                    "The policy evaluation behind this approval no longer exists."
                )

            latest = (
                db.query(PolicyEvaluation)
                .filter(PolicyEvaluation.case_id == case.id)
                .order_by(PolicyEvaluation.evaluated_at.desc())
                .first()
            )
            if latest is not None and latest.id != record.id:
                self.cancel(
                    db,
                    approval,
                    reason="The case was re-evaluated after this approval was requested.",
                )
                raise StaleApprovalError(
                    "The case was re-evaluated after this approval was requested; "
                    "the approval is stale."
                )

        amount_minor = resolve_requested_amount_minor(approval, order)
        if record is not None:
            record_result = self._result_from_record(record)
            if record_result is not None and record_result.eligible_amount_minor != amount_minor:
                self.cancel(
                    db,
                    approval,
                    reason="The requested amount changed after the approval was requested.",
                )
                raise StaleApprovalError(
                    "The requested amount changed after this approval was requested."
                )
            if record_result is not None and record_result.proposed_action != (
                requested_action_type(approval)
            ):
                self.cancel(
                    db,
                    approval,
                    reason="The proposed action changed after the approval was requested.",
                )
                raise StaleApprovalError(
                    "The proposed action changed after this approval was requested."
                )

        return record

    @staticmethod
    def _result_from_record(record: PolicyEvaluation) -> EvaluationResult | None:
        try:
            return EvaluationResult.model_validate(record.evaluation_result)
        except Exception:
            return None

    def _authorized_evaluation(
        self,
        approval: ApprovalRequest,
        case: Case,
        order: Order,
        record: PolicyEvaluation | None,
    ) -> EvaluationResult:
        if record is not None:
            base = self._result_from_record(record)
            if base is not None:
                return base.model_copy(
                    update={
                        "decision": Decision.ELIGIBLE,
                        "eligible_amount_minor": resolve_requested_amount_minor(approval, order),
                        "proposed_action": requested_action_type(approval),
                        "requires_approval": False,
                        "reason_code": "APPROVED_BY_SELLER",
                    }
                )

        return EvaluationResult(
            seller_id=case.seller_id,
            order_id=order.id,
            buyer_id=case.buyer_id,
            case_id=case.id,
            currency=approval.currency or order.currency,
            policy_id=None,
            policy_version=int((approval.requested_action or {}).get("policy_version") or 0),
            decision=Decision.ELIGIBLE,
            reason_code="APPROVED_BY_SELLER",
            reason=approval.reason,
            eligible_amount_minor=resolve_requested_amount_minor(approval, order),
            proposed_action=requested_action_type(approval),
            requires_approval=False,
            evaluated_at=datetime.now(UTC),
            checks=[],
            evaluator_version="approval-authorization",
        )

    @staticmethod
    def expire_stale(db: Session, now: datetime | None = None) -> int:
        """Expire pending approvals past their TTL.  Returns the number expired."""
        current = now or datetime.now(UTC)
        pending = db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").all()
        expired = 0
        for approval in pending:
            if approval.expires_at is None:
                continue
            expires_at = approval.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if current > expires_at:
                approval.status = "expired"
                approval.decision_reason = "Approval request expired before a decision was made."
                approval.decided_at = current
                expired += 1
        if expired:
            db.commit()
        return expired
