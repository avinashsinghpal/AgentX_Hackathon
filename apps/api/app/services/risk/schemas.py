"""Trusted inputs for the deterministic risk engine.

The risk engine performs no I/O and never consults policy decisions, financial
amounts or LLM output.  All values are supplied by the risk evaluation service.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RiskEvaluationInput(BaseModel):
    """Validated, trusted risk-evaluation input."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    seller_id: str | None = None
    buyer_id: str | None = None
    case_id: str | None = None
    order_id: str | None = None

    max_refunds_per_buyer_per_30_days: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "max_refunds_per_buyer_per_30_days",
            "refund_threshold",
            "max_refunds",
            "fraud_threshold",
            "max_refunds_per_buyer",
        ),
    )
    buyer_refund_count_30d: int = Field(
        default=0,
        validation_alias=AliasChoices(
            "buyer_refund_count_30d",
            "refund_count_30d",
            "buyer_refund_count",
            "refund_count",
        ),
    )

    current_evidence_hashes: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "current_evidence_hashes",
            "evidence_hashes",
            "evidence_sha256_hashes",
            "current_evidence_sha256",
        ),
    )
    previous_evidence_hashes: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices(
            "previous_evidence_hashes",
            "prior_evidence_hashes",
            "previous_evidence_sha256",
            "prior_evidence_sha256_hashes",
        ),
    )

    order_shipping_address: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "order_shipping_address",
            "shipping_address",
            "order_shipping",
            "trusted_order_shipping_address",
        ),
    )
    buyer_default_shipping_address: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "buyer_default_shipping_address",
            "default_shipping_address",
            "buyer_shipping_address",
            "buyer_default_address",
        ),
    )

    customer_history_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "customer_history_count",
            "history_count",
            "customer_history_records",
            "buyer_order_count",
            "prior_order_count",
            "history_records",
        ),
    )
    history_available: bool | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "history_available",
            "has_customer_history",
            "customer_history_available",
        ),
    )

    now: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("now", "evaluated_at"),
    )
