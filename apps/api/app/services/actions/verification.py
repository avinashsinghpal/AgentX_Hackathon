from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.action import Action, ActionVerification
from app.services.actions.providers.base import ActionProvider


@dataclass
class VerificationOutcome:
    verified: bool
    status: str
    reason: str | None
    reference: str | None
    attempt: int


class ActionVerificationService:
    """Records verification attempts and decides whether an action really happened."""

    METHOD = "provider_lookup"

    @staticmethod
    def record(
        db: Session,
        action: Action,
        *,
        status: str,
        method: str,
        reference: str | None,
        response: dict[str, Any] | None,
        verified_at: datetime | None = None,
        commit: bool = False,
    ) -> ActionVerification:
        attempt = (len(action.verifications) if action.verifications else 0) + 1
        record = ActionVerification(
            action_id=action.id,
            verification_status=status,
            verification_method=method,
            provider_reference=reference,
            provider_response=response or {},
            verification_attempt=attempt,
            verified_at=verified_at,
        )
        db.add(record)
        db.flush()
        if commit:
            db.commit()
        return record

    def verify(
        self,
        db: Session,
        action: Action,
        provider: ActionProvider,
        *,
        commit: bool = True,
    ) -> VerificationOutcome:
        attempt = (len(action.verifications) if action.verifications else 0) + 1

        if not action.external_reference:
            reason = "Action has no provider reference; execution cannot be verified."
            self.record(
                db,
                action,
                status="failed",
                method=self.METHOD,
                reference=None,
                response={"reason": reason},
                commit=commit,
            )
            return VerificationOutcome(
                verified=False,
                status="failed",
                reason=reason,
                reference=None,
                attempt=attempt,
            )

        outcome = provider.verify(
            action.external_reference,
            amount_minor=action.amount_minor,
            currency=action.currency,
        )

        if outcome.ok:
            self.record(
                db,
                action,
                status="verified",
                method=self.METHOD,
                reference=outcome.reference or action.external_reference,
                response=outcome.payload,
                verified_at=datetime.now(UTC),
                commit=commit,
            )
            return VerificationOutcome(
                verified=True,
                status="verified",
                reason=None,
                reference=outcome.reference or action.external_reference,
                attempt=attempt,
            )

        status = "timeout" if outcome.status == "timeout" else "failed"
        reason = outcome.error_code or "Provider could not confirm the operation."
        self.record(
            db,
            action,
            status=status,
            method=self.METHOD,
            reference=action.external_reference,
            response={**outcome.payload, "error_code": outcome.error_code},
            commit=commit,
        )
        return VerificationOutcome(
            verified=False,
            status=status,
            reason=reason,
            reference=action.external_reference,
            attempt=attempt,
        )
