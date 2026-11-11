from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.action import Action
from app.models.case import Case
from app.models.order import Order
from app.services.actions.executor import ActionExecutor
from app.services.actions.idempotency import build_idempotency_key, get_or_create_action
from app.services.actions.registry import ProviderRegistry
from app.services.audit import AuditLogService
from app.services.policy.exceptions import AuthorizationError
from app.services.policy.result import Decision, EvaluationResult

EXECUTABLE_ACTIONS = frozenset({"refund", "wallet_credit", "return_label"})

RESOLUTION_TYPE_BY_ACTION = {
    "refund": "refund",
    "wallet_credit": "wallet_credit",
    "return_label": "return_label",
}


@dataclass
class ActionRun:
    action: Action
    executed: bool
    verified: bool
    status: str
    reason: str | None = None
    already_completed: bool = False


class ActionService:
    """Authorization + durable execution for operational actions.

    Approval authorizes execution; only a verified provider outcome marks the
    case resolved and updates order/payment state.
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        executor: ActionExecutor | None = None,
    ) -> None:
        self.registry = registry
        self.executor = executor or ActionExecutor(registry=registry)

    # ------------------------------------------------------------- authorization
    @staticmethod
    def authorize(
        evaluation: EvaluationResult,
        *,
        approval_status: str | None = None,
        approval_action_type: str | None = None,
        approval_amount_minor: int | None = None,
    ) -> None:
        if approval_status is not None:
            if approval_status != "approved":
                raise AuthorizationError(
                    f"Action is not authorized: approval status is '{approval_status}'."
                )
            if approval_amount_minor is not None and approval_amount_minor != (
                evaluation.eligible_amount_minor
            ):
                raise AuthorizationError(
                    "Action is not authorized: the approved amount no longer matches the "
                    "evaluated amount."
                )
            if approval_action_type is not None and approval_action_type != (
                evaluation.proposed_action
            ):
                raise AuthorizationError(
                    "Action is not authorized: the approved action no longer matches the "
                    "policy evaluation."
                )
            return

        if evaluation.decision is not Decision.ELIGIBLE:
            raise AuthorizationError(
                f"Action is not authorized for policy decision '{evaluation.decision.value}'."
            )

    # ------------------------------------------------------------- case actions
    def execute_for_case(
        self,
        db: Session,
        *,
        case: Case,
        order: Order,
        evaluation: EvaluationResult,
        actor_role: str = "agent",
        actor_id: str | None = None,
        approval_status: str | None = None,
        approval_id: str | None = None,
        approval_action_type: str | None = None,
        approval_amount_minor: int | None = None,
        policy_evaluation_id: str | None = None,
    ) -> ActionRun:
        self.authorize(
            evaluation,
            approval_status=approval_status,
            approval_action_type=approval_action_type,
            approval_amount_minor=approval_amount_minor,
        )

        action_type = evaluation.proposed_action
        if action_type not in EXECUTABLE_ACTIONS:
            raise AuthorizationError(f"Unsupported action type '{action_type}'.")

        idempotency_key = build_idempotency_key(
            action_type,
            case.seller_id,
            case_id=case.id,
            order_id=order.id,
            amount_minor=evaluation.eligible_amount_minor,
            policy_version=evaluation.policy_version,
        )

        action, _created = get_or_create_action(
            db,
            seller_id=case.seller_id,
            action_type=action_type,
            idempotency_key=idempotency_key,
            case_id=case.id,
            order_id=order.id,
            amount_minor=evaluation.eligible_amount_minor,
            currency=evaluation.currency,
            request_payload={
                "policy_evaluation_id": policy_evaluation_id,
                "reason_code": evaluation.reason_code,
                "decision": evaluation.decision.value,
                "policy_version": evaluation.policy_version,
                "order_number": order.order_number,
            },
            initiated_by=actor_id or actor_role,
            approval_id=approval_id,
        )

        if action.status == "succeeded":
            return ActionRun(
                action=action,
                executed=True,
                verified=True,
                status="succeeded",
                already_completed=True,
            )

        outcome = self.executor.execute(
            db, action, actor_role=actor_role, actor_id=actor_id, metadata=metadata_for(order)
        )

        if outcome.verified:
            self._apply_success(
                db,
                action=outcome.action,
                case=case,
                order=order,
                evaluation=evaluation,
                actor_role=actor_role,
                actor_id=actor_id,
            )
            return ActionRun(
                action=outcome.action,
                executed=True,
                verified=True,
                status="succeeded",
            )

        case.outcome_details = {
            **(case.outcome_details or {}),
            "action_id": outcome.action.id,
            "action_type": action_type,
            "action_status": outcome.status,
            "failure_reason": outcome.reason,
            "policy_decision": evaluation.decision.value,
            "policy_version": evaluation.policy_version,
        }
        db.commit()

        return ActionRun(
            action=outcome.action,
            executed=False,
            verified=False,
            status=outcome.status,
            reason=outcome.reason,
        )

    # ------------------------------------------------------- delay compensation
    def execute_delay_compensation(
        self,
        db: Session,
        *,
        case: Case,
        order: Order,
        evaluation: EvaluationResult,
        extra_details: dict[str, Any] | None = None,
    ) -> ActionRun:
        self.authorize(evaluation)

        if evaluation.proposed_action != "wallet_credit":
            raise AuthorizationError(
                "Delay compensation must be evaluated as a wallet credit action."
            )

        idempotency_key = build_idempotency_key(
            "wallet_credit",
            order.seller_id,
            order_id=order.id,
            amount_minor=evaluation.eligible_amount_minor,
            policy_version=evaluation.policy_version,
        )

        action, _created = get_or_create_action(
            db,
            seller_id=order.seller_id,
            action_type="wallet_credit",
            idempotency_key=idempotency_key,
            case_id=case.id,
            order_id=order.id,
            amount_minor=evaluation.eligible_amount_minor,
            currency=evaluation.currency,
            request_payload={
                "reason_code": evaluation.reason_code,
                "policy_version": evaluation.policy_version,
                "order_number": order.order_number,
                "source": "proactive_delay_monitor",
            },
            initiated_by="system",
        )

        if action.status == "succeeded":
            return ActionRun(
                action=action,
                executed=True,
                verified=True,
                status="succeeded",
                already_completed=True,
            )

        outcome = self.executor.execute(
            db, action, actor_role="system", actor_id=None, metadata=metadata_for(order)
        )

        if outcome.verified:
            self._apply_success(
                db,
                action=outcome.action,
                case=case,
                order=order,
                evaluation=evaluation,
                actor_role="system",
                actor_id=None,
                resolution_type="delay_compensation",
                extra_details=extra_details,
            )
            return ActionRun(
                action=outcome.action,
                executed=True,
                verified=True,
                status="succeeded",
            )

        case.status = "investigating"
        case.outcome_details = {
            **(case.outcome_details or {}),
            "action_id": outcome.action.id,
            "action_status": outcome.status,
            "failure_reason": outcome.reason,
            "policy_decision": evaluation.decision.value,
        }
        db.commit()
        return ActionRun(
            action=outcome.action,
            executed=False,
            verified=False,
            status=outcome.status,
            reason=outcome.reason,
        )

    # ------------------------------------------------------------------ effects
    def _apply_success(
        self,
        db: Session,
        *,
        action: Action,
        case: Case,
        order: Order,
        evaluation: EvaluationResult,
        actor_role: str,
        actor_id: str | None,
        resolution_type: str | None = None,
        extra_details: dict[str, Any] | None = None,
    ) -> None:
        if case.status not in {"investigating", "pending_approval", "open"}:
            raise ValueError(
                f"Cannot apply a successful action to case in unexpected state "
                f"'{case.status}'."
            )
        now = datetime.now(UTC)
        amount_major = (action.amount_minor or 0) / 100.0

        details: dict[str, Any] = {
            "action_id": action.id,
            "action_type": action.action_type,
            "amount_minor": action.amount_minor,
            "amount": amount_major,
            "currency": action.currency,
            "provider_reference": action.external_reference,
            "policy_decision": evaluation.decision.value,
            "policy_version": evaluation.policy_version,
            "reason": evaluation.reason,
            "verified": True,
        }

        if action.action_type == "refund":
            if order.payment_method == "cod":
                order.payment_status = "refunded"
            elif (action.amount_minor or 0) >= order.total_amount:
                order.payment_status = "refunded"
            else:
                order.payment_status = "partially_refunded"
            details["payment_status"] = order.payment_status
            details["refunded_amount"] = amount_major
        elif action.action_type == "wallet_credit":
            details["wallet_credit_amount"] = amount_major
            details["wallet_credit_minor"] = action.amount_minor
            details["payment_status"] = order.payment_status
        elif action.action_type == "return_label":
            details["reverse_awb"] = action.external_reference
            details["courier"] = (action.response_payload or {}).get("courier", "Delhivery")
            details["pickup_status"] = (action.response_payload or {}).get(
                "pickup_status", "manifested"
            )

        if extra_details:
            details.update(extra_details)

        case.status = "resolved"
        case.decision = "executed"
        case.resolution_type = resolution_type or RESOLUTION_TYPE_BY_ACTION.get(
            action.action_type, action.action_type
        )
        case.outcome_details = details
        case.resolved_at = now

        AuditLogService.log_action(
            db=db,
            action="resolution.executed",
            actor_role=actor_role,
            actor_id=actor_id,
            seller_id=case.seller_id,
            case_id=case.id,
            payload={
                "action_id": action.id,
                "resolution_type": case.resolution_type,
                "order_number": order.order_number,
                "amount_minor": action.amount_minor,
                "currency": action.currency,
                "provider_reference": action.external_reference,
                "policy_version": evaluation.policy_version,
            },
            commit=False,
        )
        db.commit()
        db.refresh(case)
        db.refresh(action)


def metadata_for(order: Order) -> dict[str, Any]:
    return {
        "order_number": order.order_number,
        "payment_method": order.payment_method,
        "buyer_id": order.buyer_id,
        "courier": "Delhivery",
    }
