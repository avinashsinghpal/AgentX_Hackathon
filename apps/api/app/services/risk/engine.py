"""Deterministic risk engine.

Risk evaluation is intentionally separate from policy evaluation.  The engine
returns risk indicators only; it never calculates money, eligibility, approval
requirements or actions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.services.risk.result import (
    DataSufficiency,
    RiskFlag,
    RiskResult,
)
from app.services.risk.schemas import RiskEvaluationInput

ADDRESS_FIELDS = (
    "street",
    "address_line1",
    "line1",
    "address",
    "city",
    "state",
    "province",
    "pincode",
    "postal_code",
    "zip",
    "zip_code",
    "country",
)

ADDRESS_ALIASES = {
    "address_line1": "street",
    "line1": "street",
    "address": "street",
    "province": "state",
    "pincode": "postal_code",
    "zip": "postal_code",
    "zip_code": "postal_code",
}


class RiskEngine:
    """Pure, deterministic risk indicator engine."""

    RISK_ENGINE_VERSION = "1.0.0"

    def evaluate(self, inputs: Any = None, **kwargs: Any) -> RiskResult:
        """Evaluate trusted risk inputs.

        ``inputs`` may be a ``RiskEvaluationInput``, a mapping, or any object
        exposing the relevant attributes.  Keyword arguments are also accepted
        so callers can use the engine without constructing the input model.
        """

        if inputs is None:
            inputs = RiskEvaluationInput(**kwargs)
        elif isinstance(inputs, dict):
            inputs = RiskEvaluationInput(**inputs, **kwargs)
        elif not isinstance(inputs, RiskEvaluationInput):
            try:
                values = {
                    key: value for key, value in vars(inputs).items() if not key.startswith("_")
                }
            except TypeError:
                values = {}
            inputs = RiskEvaluationInput(**values, **kwargs)

        evaluated_at = inputs.now if getattr(inputs, "now", None) is not None else datetime.now(UTC)
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=UTC)
        flags: list[RiskFlag] = []

        # 1. Refund frequency.  The threshold comes from the seller policy's
        # fraud_checks configuration; it is never hardcoded here.
        threshold = inputs.max_refunds_per_buyer_per_30_days
        refund_count = inputs.buyer_refund_count_30d
        if threshold is not None and refund_count > threshold:
            flags.append(
                RiskFlag(
                    code="HIGH_REFUND_FREQUENCY",
                    severity="high",
                    explanation=(
                        f"Buyer has {refund_count} successful refunds in the last 30 days, "
                        f"exceeding the configured maximum of {threshold}."
                    ),
                )
            )

        # 2. Claim frequency is intentionally disabled until a dedicated,
        # seller-configurable threshold exists.  The refund-frequency field is
        # never reused for it.

        # 3. Duplicate evidence: exact SHA-256 matches are risk indicators, not
        # proof of fraud.
        current_hashes = {
            str(value).strip().lower()
            for value in inputs.current_evidence_hashes
            if str(value).strip()
        }
        previous_hashes = {
            str(value).strip().lower()
            for value in inputs.previous_evidence_hashes
            if str(value).strip()
        }
        if current_hashes and current_hashes & previous_hashes:
            flags.append(
                RiskFlag(
                    code="DUPLICATE_EVIDENCE",
                    severity="high",
                    explanation="Evidence hash matches a previous claim.",
                )
            )

        # 4. Address inconsistency: only flag a genuine conflict when both
        # trusted records are available.
        order_address = _canonical_address(inputs.order_shipping_address)
        buyer_address = _canonical_address(inputs.buyer_default_shipping_address)
        if order_address is not None and buyer_address is not None:
            common_fields = set(order_address) & set(buyer_address)
            if common_fields and any(
                order_address[field] != buyer_address[field] for field in common_fields
            ):
                flags.append(
                    RiskFlag(
                        code="ADDRESS_INCONSISTENCY",
                        severity="medium",
                        explanation="Trusted order shipping and buyer default shipping records conflict.",
                    )
                )

        # 5. Missing customer history: report insufficient data without
        # automatically classifying the customer as high risk.
        data_sufficiency = _data_sufficiency(inputs)

        return RiskResult(
            risk_engine_version=self.RISK_ENGINE_VERSION,
            flags=flags,
            data_sufficiency=data_sufficiency,
            evaluated_at=evaluated_at,
        )

    # Backwards/alternative method names for compatibility with callers.
    def evaluate_risk(self, *args: Any, **kwargs: Any) -> RiskResult:
        return self.evaluate(*args, **kwargs)

    def run(self, *args: Any, **kwargs: Any) -> RiskResult:
        return self.evaluate(*args, **kwargs)

    def assess(self, *args: Any, **kwargs: Any) -> RiskResult:
        return self.evaluate(*args, **kwargs)


def _canonical_address(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    canonical: dict[str, str] = {}
    for key, raw in value.items():
        if raw is None:
            continue
        text = str(raw).strip().lower()
        if not text:
            continue
        normalized_key = ADDRESS_ALIASES.get(str(key).strip().lower(), str(key).strip().lower())
        if normalized_key in ADDRESS_FIELDS:
            canonical[normalized_key] = text
    return canonical or None


def _data_sufficiency(inputs: RiskEvaluationInput) -> DataSufficiency:
    history_count = inputs.customer_history_count
    if history_count is None and inputs.history_available is not None:
        history_count = 1 if inputs.history_available else 0

    if history_count is None:
        # No reliable history signal was supplied; do not claim sufficiency.
        return DataSufficiency.INSUFFICIENT_DATA

    if history_count <= 0:
        return DataSufficiency.INSUFFICIENT_DATA

    return DataSufficiency.SUFFICIENT
