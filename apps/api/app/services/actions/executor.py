from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.action import Action
from app.services.actions.providers.base import ProviderOutcome
from app.services.actions.registry import ProviderRegistry, get_provider_registry
from app.services.actions.verification import ActionVerificationService
from app.services.audit import AuditLogService


@dataclass
class ExecutionOutcome:
    action: Action
    executed: bool
    verified: bool
    status: str
    reason: str | None = None
    provider_reference: str | None = None
    verification_attempt: int = 0


class ActionExecutor:
    """Executes a durable action and verifies the provider outcome.

    A database transaction is never held open across the provider call.  The
    pending action (including its unique idempotency key) is committed first, the
    provider is called outside the transaction, and the response plus
    verification are persisted afterwards.
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        verification: ActionVerificationService | None = None,
    ) -> None:
        self.registry = registry or get_provider_registry()
        self.verification = verification or ActionVerificationService()

    def execute(
        self,
        db: Session,
        action: Action,
        *,
        metadata: dict[str, Any] | None = None,
        actor_role: str = "agent",
        actor_id: str | None = None,
    ) -> ExecutionOutcome:
        if action.status == "succeeded":
            return ExecutionOutcome(
                action=action,
                executed=True,
                verified=True,
                status="succeeded",
                provider_reference=action.external_reference,
            )
        if action.status == "cancelled":
            return ExecutionOutcome(
                action=action,
                executed=False,
                verified=False,
                status="cancelled",
                reason="Action was cancelled before execution.",
            )

        try:
            provider = self.registry.provider_for(action.action_type)
        except ValueError as exc:
            action.status = "failed"
            action.failure_reason = str(exc)
            db.commit()
            AuditLogService.log_action(
                db=db,
                action="action.rejected",
                actor_role=actor_role,
                actor_id=actor_id,
                seller_id=action.seller_id,
                case_id=action.case_id,
                payload={"action_id": action.id, "reason": str(exc)},
            )
            return ExecutionOutcome(
                action=action,
                executed=False,
                verified=False,
                status="failed",
                reason=str(exc),
            )

        # Commit the intent and idempotency key before touching the provider.
        if action.status == "pending":
            action.status = "submitted"
            action.failure_reason = None
            db.commit()

        try:
            outcome = provider.execute(
                action.action_type,
                action.idempotency_key,
                amount_minor=action.amount_minor,
                currency=action.currency,
                metadata=metadata or {},
            )
        except Exception as exc:  # defensive: mock providers should not raise
            outcome = ProviderOutcome(
                status="failed",
                error_code="PROVIDER_EXCEPTION",
                payload={"error": type(exc).__name__},
                retryable=True,
            )

        if outcome.reference:
            action.external_reference = outcome.reference
        action.response_payload = dict(outcome.payload) | {
            "provider_status": outcome.status,
            "error_code": outcome.error_code,
            "retryable": outcome.retryable,
        }

        if outcome.status in {"succeeded", "duplicate"}:
            action.status = "verification_pending"
            action.failure_reason = None
        elif outcome.status == "timeout":
            # Unknown outcome: the operation may have happened.  Never report a
            # timeout as a failure, and never update order state here.
            action.status = "submitted"
            action.failure_reason = "provider_timeout"
        else:
            action.status = "failed" if not outcome.retryable else "submitted"
            action.failure_reason = outcome.error_code or "provider_error"

        db.commit()
        db.refresh(action)

        # A timeout with no reference cannot be verified yet; a retry with the
        # same idempotency key will discover the original provider operation.
        if outcome.status == "timeout" and not action.external_reference:
            AuditLogService.log_action(
                db=db,
                action="action.timeout",
                actor_role=actor_role,
                actor_id=actor_id,
                seller_id=action.seller_id,
                case_id=action.case_id,
                payload={
                    "action_id": action.id,
                    "action_type": action.action_type,
                    "amount_minor": action.amount_minor,
                    "idempotency_key": action.idempotency_key,
                },
            )
            return ExecutionOutcome(
                action=action,
                executed=False,
                verified=False,
                status="timeout",
                reason="Provider timed out; outcome is unknown and may be retried safely.",
                provider_reference=None,
            )

        if action.status not in {"verification_pending", "submitted"}:
            AuditLogService.log_action(
                db=db,
                action="action.failed",
                actor_role=actor_role,
                actor_id=actor_id,
                seller_id=action.seller_id,
                case_id=action.case_id,
                payload={
                    "action_id": action.id,
                    "action_type": action.action_type,
                    "amount_minor": action.amount_minor,
                    "error_code": action.failure_reason,
                },
            )
            return ExecutionOutcome(
                action=action,
                executed=False,
                verified=False,
                status="failed",
                reason=action.failure_reason,
                provider_reference=action.external_reference,
            )

        verification = self.verification.verify(db, action, provider, commit=True)
        db.refresh(action)

        if verification.verified:
            action.status = "succeeded"
            action.failure_reason = None
            action.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(action)
            return ExecutionOutcome(
                action=action,
                executed=True,
                verified=True,
                status="succeeded",
                provider_reference=action.external_reference,
                verification_attempt=verification.attempt,
            )

        # Verification failed: the action is not complete and no downstream
        # state may be marked successful.
        action.status = "failed"
        action.failure_reason = verification.reason or "verification_failed"
        db.commit()
        db.refresh(action)
        return ExecutionOutcome(
            action=action,
            executed=False,
            verified=False,
            status="failed",
            reason=action.failure_reason,
            provider_reference=action.external_reference,
            verification_attempt=verification.attempt,
        )
