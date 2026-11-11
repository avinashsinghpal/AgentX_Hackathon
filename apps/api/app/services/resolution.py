"""Single resolution service used by every orchestrator path.

The non-streaming chat endpoint and the streaming endpoint call this same
service; policy evaluation, authorization and action execution are never
duplicated per transport.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.case import ApprovalRequest, Case, CaseMessage
from app.models.order import Order
from app.models.seller import Seller
from app.models.shipment import Shipment
from app.services.actions.service import ActionRun, ActionService
from app.services.approvals import ApprovalService
from app.services.audit import AuditLogService
from app.services.llm.client import LLMClient, LLMMessage, get_llm_client
from app.services.policy.evaluator import CaseEvaluation, PolicyEvaluationService
from app.services.policy.result import Decision, EvaluationResult


class ResolutionError(Exception):
    """Base class for resolution failures."""


class ResolutionCaseNotFoundError(ResolutionError):
    pass


class ResolutionOwnershipError(ResolutionError):
    pass


@dataclass
class Investigation:
    case: Case
    order: Order
    seller: Seller | None
    shipment: Shipment | None
    steps: list[dict[str, Any]]


@dataclass
class DecisionOutcome:
    evaluation: EvaluationResult
    evaluation_id: str | None
    badge: str
    approval: ApprovalRequest | None
    action_run: ActionRun | None
    steps: list[dict[str, Any]]


@dataclass
class ResolutionOutcome:
    case: Case
    order: Order
    evaluation: EvaluationResult
    evaluation_id: str | None
    badge: str
    approval: ApprovalRequest | None
    action_run: ActionRun | None
    steps: list[dict[str, Any]]
    explanation: str
    message: CaseMessage | None


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _money(amount_minor: int | None) -> str:
    return f"{(amount_minor or 0) / 100:.2f}"


class ResolutionService:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        evaluation_service: PolicyEvaluationService | None = None,
        action_service: ActionService | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.llm = llm_client or get_llm_client()
        self.evaluations = evaluation_service or PolicyEvaluationService()
        self.actions = action_service or ActionService()
        self.approvals = approval_service or ApprovalService(self.actions)

    # ---------------------------------------------------------------- investigate
    def investigate(self, db: Session, case_id: str) -> Investigation:
        case = db.query(Case).filter(Case.id == case_id).first()
        if case is None:
            raise ResolutionCaseNotFoundError(f"Case {case_id} not found")

        order = db.query(Order).filter(Order.id == case.order_id).first()
        if order is None:
            raise ResolutionCaseNotFoundError(f"Order {case.order_id} not found")

        if order.seller_id != case.seller_id:
            raise ResolutionOwnershipError(
                "The case and its order belong to different sellers; refusing to resolve."
            )
        if order.buyer_id is not None and order.buyer_id != case.buyer_id:
            raise ResolutionOwnershipError(
                "The case buyer does not match the order buyer; refusing to resolve."
            )

        seller = db.query(Seller).filter(Seller.id == case.seller_id).first()
        shipment = (
            db.query(Shipment)
            .filter(Shipment.order_id == order.id)
            .order_by(Shipment.created_at.desc())
            .first()
        )

        now_iso = datetime.now(UTC).isoformat()
        steps: list[dict[str, Any]] = [
            {
                "tool_name": "lookup_order",
                "tool_args": {"order_number": order.order_number},
                "outcome": (
                    f"Retrieved order {order.order_number}. Status: {order.order_status}, "
                    f"Payment: {order.payment_status}, Amount: {order.currency} "
                    f"{_money(order.total_amount)}"
                ),
                "timestamp": now_iso,
            },
            {
                "tool_name": "lookup_shipment",
                "tool_args": {"order_number": order.order_number},
                "outcome": (
                    f"Courier: {shipment.courier_partner}, Status: {shipment.status}"
                    if shipment
                    else "No shipment record is available for this order."
                ),
                "timestamp": now_iso,
            },
        ]

        return Investigation(case=case, order=order, seller=seller, shipment=shipment, steps=steps)

    # --------------------------------------------------------------------- decide
    def decide(
        self,
        db: Session,
        investigation: Investigation,
        *,
        now: datetime | None = None,
        actor_role: str = "agent",
        actor_id: str | None = None,
    ) -> DecisionOutcome:
        case = investigation.case
        order = investigation.order
        evaluated_at = now or datetime.now(UTC)

        evaluation: CaseEvaluation = self.evaluations.evaluate_case(
            db, case, now=evaluated_at, persist=True
        )
        result = evaluation.result
        record_id = evaluation.record.id if evaluation.record is not None else None

        steps: list[dict[str, Any]] = [
            {
                "tool_name": "evaluate_policy_rules",
                "tool_args": {
                    "category": case.issue_category,
                    "amount_minor": result.eligible_amount_minor,
                    "policy_version": result.policy_version,
                },
                "outcome": f"Decision: {result.decision.value.upper()}. {result.reason}",
                "timestamp": evaluated_at.isoformat(),
            }
        ]

        approval: ApprovalRequest | None = None
        action_run: ActionRun | None = None

        if result.decision is Decision.NOT_ELIGIBLE:
            case.status = "rejected"
            case.decision = "not_eligible"
            case.resolved_at = evaluated_at
            case.outcome_details = {
                "rejected": True,
                "reason": result.reason,
                "reason_code": result.reason_code,
                "policy_version": result.policy_version,
                "evaluation_id": record_id,
            }
            AuditLogService.log_action(
                db=db,
                action="resolution.rejected",
                actor_role=actor_role,
                actor_id=actor_id,
                seller_id=case.seller_id,
                case_id=case.id,
                payload={
                    "order_number": order.order_number,
                    "reason": result.reason,
                    "reason_code": result.reason_code,
                    "policy_version": result.policy_version,
                },
                commit=False,
            )
            db.commit()
            badge = "not_eligible"
            steps.append(
                {
                    "tool_name": "verify_action_outcome",
                    "tool_args": {"action": "none"},
                    "outcome": "No operational action was executed: the claim is not eligible.",
                    "timestamp": evaluated_at.isoformat(),
                }
            )

        elif result.decision in {Decision.NEEDS_APPROVAL, Decision.MANUAL_REVIEW}:
            approval = self.approvals.request_for_evaluation(
                db,
                case=case,
                evaluation=result,
                evaluation_id=record_id,
                now=evaluated_at,
            )
            badge = "needs_approval"
            steps.append(
                {
                    "tool_name": "verify_action_outcome",
                    "tool_args": {"action": result.proposed_action},
                    "outcome": (
                        "Escalated for seller approval. No financial action was executed; "
                        "execution requires an approved request and provider verification."
                    ),
                    "timestamp": evaluated_at.isoformat(),
                }
            )

        else:
            action_run = self.actions.execute_for_case(
                db,
                case=case,
                order=order,
                evaluation=result,
                actor_role=actor_role,
                actor_id=actor_id,
                policy_evaluation_id=record_id,
            )
            if action_run.executed:
                badge = "executed"
                steps.append(
                    {
                        "tool_name": "verify_action_outcome",
                        "tool_args": {"action": result.proposed_action},
                        "outcome": (
                            f"Action {result.proposed_action} executed and verified "
                            f"(provider reference {action_run.action.external_reference})."
                        ),
                        "timestamp": evaluated_at.isoformat(),
                    }
                )
            else:
                badge = "needs_approval"
                steps.append(
                    {
                        "tool_name": "verify_action_outcome",
                        "tool_args": {"action": result.proposed_action},
                        "outcome": (
                            f"Action {result.proposed_action} could not be verified "
                            f"({action_run.reason or action_run.status}). No financial action "
                            "was recorded as completed; it can be retried safely."
                        ),
                        "timestamp": evaluated_at.isoformat(),
                    }
                )

        db.refresh(case)
        return DecisionOutcome(
            evaluation=result,
            evaluation_id=record_id,
            badge=badge,
            approval=approval,
            action_run=action_run,
            steps=steps,
        )

    # -------------------------------------------------------------------- explain
    def build_messages(
        self,
        investigation: Investigation,
        decision: DecisionOutcome,
    ) -> list[LLMMessage]:
        case = investigation.case
        order = investigation.order
        result = decision.evaluation
        checks = "; ".join(
            f"{check.check}={check.passed}" + (f" ({check.reason_code})" if check.reason_code else "")
            for check in result.checks
        )

        facts = f"""
Verified facts (authoritative, produced by the deterministic backend):
- Order: {order.order_number}
- Order amount: {order.currency} {_money(order.total_amount)}
- Payment method: {order.payment_method}; payment status: {order.payment_status}
- Issue category: {case.issue_category}
- Seller status: {investigation.seller.status if investigation.seller else 'unknown'}
- Policy version: {result.policy_version}
- Policy decision: {result.decision.value}
- Reason code: {result.reason_code}
- Deterministic reason: {result.reason}
- Eligible amount: {order.currency} {_money(result.eligible_amount_minor)}
- Proposed action: {result.proposed_action}
- Backend outcome badge: {decision.badge}
- Checks: {checks}

Customer statement: "{case.customer_narrative}"

Write a clear, factual, reassuring response. Explain the exact outcome and next steps.
Never include emojis. Quote the exact amounts and only the facts above. Do not invent
policy exceptions, do not change the decision, and do not promise any amount that is not
listed here.
"""
        return [
            LLMMessage(role="system", content="Quote exact numbers. Zero emojis."),
            LLMMessage(role="user", content=facts),
        ]

    def fallback_explanation(
        self,
        investigation: Investigation,
        decision: DecisionOutcome,
    ) -> str:
        order = investigation.order
        result = decision.evaluation

        if decision.badge == "executed":
            return (
                f"We reviewed order {order.order_number}. {result.reason} "
                f"The {result.proposed_action.replace('_', ' ')} of {order.currency} "
                f"{_money(result.eligible_amount_minor)} has been executed and verified by our "
                "provider. The resolution is complete and recorded in the audit trail."
            )

        if decision.approval is not None:
            return (
                f"We reviewed order {order.order_number}. {result.reason} "
                f"This request requires merchant approval before any amount of {order.currency} "
                f"{_money(result.eligible_amount_minor)} can be issued. The request has been sent "
                "to the merchant; no financial action has been executed yet."
            )

        if decision.action_run is not None and not decision.action_run.executed:
            return (
                f"We reviewed order {order.order_number}. {result.reason} "
                "The operational action could not be verified, so no financial action was "
                "recorded as completed. It can be retried safely without duplicating a refund."
            )

        return (
            f"We reviewed order {order.order_number}. {result.reason} "
            "No financial action has been taken on this request."
        )

    async def explain(
        self,
        investigation: Investigation,
        decision: DecisionOutcome,
    ) -> str:
        messages = self.build_messages(investigation, decision)
        try:
            response = await self.llm.generate_response(messages)
            text = (response.text or "").strip()
            return text or self.fallback_explanation(investigation, decision)
        except Exception:
            # A generation failure must never roll back or alter the verified
            # policy decision or an already-completed action.
            return self.fallback_explanation(investigation, decision)

    # -------------------------------------------------------------------- resolve
    async def resolve_case(
        self,
        db: Session,
        case_id: str,
        *,
        now: datetime | None = None,
        actor_role: str = "agent",
        actor_id: str | None = None,
        persist_message: bool = True,
    ) -> ResolutionOutcome:
        investigation = self.investigate(db, case_id)
        decision = self.decide(
            db, investigation, now=now, actor_role=actor_role, actor_id=actor_id
        )
        explanation = await self.explain(investigation, decision)

        message: CaseMessage | None = None
        if persist_message:
            message = CaseMessage(
                case_id=investigation.case.id,
                sender_role="agent",
                message=explanation,
                tool_calls=investigation.steps + decision.steps,
                decision_badge=decision.badge,
            )
            db.add(message)
            db.commit()
            db.refresh(message)

        return ResolutionOutcome(
            case=investigation.case,
            order=investigation.order,
            evaluation=decision.evaluation,
            evaluation_id=decision.evaluation_id,
            badge=decision.badge,
            approval=decision.approval,
            action_run=decision.action_run,
            steps=investigation.steps + decision.steps,
            explanation=explanation,
            message=message,
        )

    async def stream_case(
        self,
        db: Session,
        case_id: str,
        *,
        now: datetime | None = None,
        actor_role: str = "agent",
        actor_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        investigation = self.investigate(db, case_id)
        for step in investigation.steps:
            yield {"event": "investigation_step", "data": step}

        decision = self.decide(
            db, investigation, now=now, actor_role=actor_role, actor_id=actor_id
        )

        yield {"event": "investigation_step", "data": decision.steps[0]}
        yield {"event": "decision_badge", "data": {"badge": decision.badge}}
        if len(decision.steps) > 1:
            yield {"event": "investigation_step", "data": decision.steps[1]}

        messages = self.build_messages(investigation, decision)
        full_text = ""
        try:
            async for token in self.llm.stream_response(messages):
                full_text += token
                yield {"event": "agent_token", "data": {"token": token}}
        except Exception:
            full_text = ""

        if not full_text.strip():
            fallback = self.fallback_explanation(investigation, decision)
            full_text = fallback
            for word in fallback.split(" "):
                yield {"event": "agent_token", "data": {"token": word + " "}}

        message = CaseMessage(
            case_id=investigation.case.id,
            sender_role="agent",
            message=full_text.strip(),
            tool_calls=investigation.steps + decision.steps,
            decision_badge=decision.badge,
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        yield {"event": "done", "data": {"message_id": message.id}}
