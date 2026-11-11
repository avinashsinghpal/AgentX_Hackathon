from __future__ import annotations

import uuid
from typing import Any

from app.services.actions.providers.base import ActionProvider, ProviderOutcome

SUPPORTED_OUTCOMES = ("success", "failure", "timeout", "retryable_error", "duplicate")


class MockCourierProvider(ActionProvider):
    """Deterministic return-label generator and shipment tracking mock."""

    name = "mock_courier"

    def __init__(self, outcomes: dict[str, str] | None = None) -> None:
        self._outcomes: dict[str, str] = dict(outcomes or {})
        self._labels: dict[str, dict[str, Any]] = {}

    def configure_outcome(self, action_type: str, outcome: str) -> None:
        if outcome not in SUPPORTED_OUTCOMES:
            raise ValueError(f"Unsupported mock outcome: {outcome}")
        self._outcomes[action_type] = outcome

    def reset(self) -> None:
        self._outcomes.clear()
        self._labels.clear()

    def execute(
        self,
        action_type: str,
        idempotency_key: str,
        *,
        amount_minor: int | None,
        currency: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderOutcome:
        if action_type != "return_label":
            return ProviderOutcome(
                status="failed",
                error_code="UNSUPPORTED_ACTION",
                payload={"action_type": action_type},
            )

        existing = self._labels.get(idempotency_key)
        if existing is not None:
            return ProviderOutcome(
                status="duplicate",
                reference=existing["reference"],
                payload={**existing, "deduplicated": True},
            )

        configured = self._outcomes.get(action_type, "success")
        if configured in {"failure", "retryable_error"}:
            return ProviderOutcome(
                status="failed",
                error_code="COURIER_REJECTED" if configured == "failure" else "COURIER_UNAVAILABLE",
                payload={"reason": "return label could not be generated"},
                retryable=configured == "retryable_error",
            )

        label = {
            "reference": f"REV-DELHIVERY-{uuid.uuid4().hex[:6].upper()}",
            "courier": (metadata or {}).get("courier", "Delhivery"),
            "pickup_status": "manifested",
            "idempotency_key": idempotency_key,
        }
        self._labels[idempotency_key] = label

        if configured == "timeout":
            return ProviderOutcome(
                status="timeout",
                reference=None,
                payload={"idempotency_key": idempotency_key},
                error_code="COURIER_TIMEOUT",
                retryable=True,
            )

        return ProviderOutcome(status="succeeded", reference=label["reference"], payload=label)

    def verify(
        self,
        reference: str | None,
        *,
        amount_minor: int | None = None,
        currency: str | None = None,
    ) -> ProviderOutcome:
        if not reference:
            return ProviderOutcome(status="failed", error_code="MISSING_REFERENCE")
        for label in self._labels.values():
            if label["reference"] == reference:
                return ProviderOutcome(status="succeeded", reference=reference, payload=label)
        return ProviderOutcome(
            status="failed",
            error_code="REFERENCE_NOT_FOUND",
            reference=reference,
            payload={"reason": "courier has no record of this label"},
        )
