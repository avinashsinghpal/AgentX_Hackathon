from __future__ import annotations

from typing import Any

from app.services.actions.providers.base import ActionProvider, ProviderOutcome

SUPPORTED_OUTCOMES = ("success", "failure", "timeout", "retryable_error", "duplicate")


class MockPaymentProvider(ActionProvider):
    """Deterministic in-memory payment provider used by tests and the demo.

    Outcomes are configurable per action type so tests can exercise success,
    failure, timeout, retryable errors and duplicate requests.  Executed
    operations are retained, keyed by idempotency key, which lets a retry after
    a simulated timeout discover the original operation instead of paying twice.
    """

    name = "mock_payment"

    def __init__(self, outcomes: dict[str, str] | None = None) -> None:
        self._outcomes: dict[str, str] = dict(outcomes or {})
        self._operations: dict[str, dict[str, Any]] = {}
        self._sequence = 0

    # ----------------------------------------------------------- configuration
    def configure_outcome(self, action_type: str, outcome: str) -> None:
        if outcome not in SUPPORTED_OUTCOMES:
            raise ValueError(f"Unsupported mock outcome: {outcome}")
        self._outcomes[action_type] = outcome

    def reset(self) -> None:
        self._outcomes.clear()
        self._operations.clear()
        self._sequence = 0

    def operation_for_key(self, idempotency_key: str) -> dict[str, Any] | None:
        return self._operations.get(idempotency_key)

    # ---------------------------------------------------------------- provider
    def execute(
        self,
        action_type: str,
        idempotency_key: str,
        *,
        amount_minor: int | None,
        currency: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderOutcome:
        if action_type not in {"refund", "wallet_credit"}:
            return ProviderOutcome(
                status="failed",
                error_code="UNSUPPORTED_ACTION",
                payload={"action_type": action_type},
            )

        existing = self._operations.get(idempotency_key)
        if existing is not None:
            # Provider-side idempotency: the original operation is returned.
            return ProviderOutcome(
                status="duplicate",
                reference=existing["reference"],
                payload={**existing, "deduplicated": True},
            )

        configured = self._outcomes.get(action_type, "success")

        if configured == "failure":
            return ProviderOutcome(
                status="failed",
                error_code="PROVIDER_REJECTED",
                payload={"action_type": action_type, "reason": "provider rejected the operation"},
                retryable=False,
            )

        if configured == "retryable_error":
            return ProviderOutcome(
                status="failed",
                error_code="PROVIDER_UNAVAILABLE",
                payload={"action_type": action_type, "reason": "provider temporarily unavailable"},
                retryable=True,
            )

        # Both "success", "duplicate" and "timeout" perform the operation; a
        # timeout only loses the response.
        operation = self._record(action_type, idempotency_key, amount_minor, currency)

        if configured == "timeout":
            return ProviderOutcome(
                status="timeout",
                reference=None,
                payload={"idempotency_key": idempotency_key},
                error_code="PROVIDER_TIMEOUT",
                retryable=True,
            )

        return ProviderOutcome(
            status="succeeded",
            reference=operation["reference"],
            payload=operation,
        )

    def verify(
        self,
        reference: str | None,
        *,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> ProviderOutcome:
        if not reference:
            return ProviderOutcome(
                status="failed",
                error_code="MISSING_REFERENCE",
                payload={"reason": "no provider reference to verify"},
            )

        for operation in self._operations.values():
            if operation["reference"] != reference:
                continue

            if amount_minor is not None and operation["amount_minor"] != amount_minor:
                return ProviderOutcome(
                    status="failed",
                    error_code="AMOUNT_MISMATCH",
                    reference=reference,
                    payload={
                        "expected_amount_minor": amount_minor,
                        "provider_amount_minor": operation["amount_minor"],
                    },
                )
            if currency is not None and operation["currency"] != currency:
                return ProviderOutcome(
                    status="failed",
                    error_code="CURRENCY_MISMATCH",
                    reference=reference,
                    payload={"expected_currency": currency},
                )
            return ProviderOutcome(status="succeeded", reference=reference, payload=operation)

        return ProviderOutcome(
            status="failed",
            error_code="REFERENCE_NOT_FOUND",
            reference=reference,
            payload={"reason": "provider has no record of this reference"},
        )

    # ----------------------------------------------------------------- internal
    def _record(
        self,
        action_type: str,
        idempotency_key: str,
        amount_minor: int | None,
        currency: str | None,
    ) -> dict[str, Any]:
        self._sequence += 1
        prefix = "RFND" if action_type == "refund" else "CRDT"
        operation = {
            "reference": f"{prefix}-{self._sequence:06d}",
            "action_type": action_type,
            "amount_minor": amount_minor,
            "currency": currency,
            "status": "succeeded",
            "idempotency_key": idempotency_key,
        }
        self._operations[idempotency_key] = operation
        return operation
