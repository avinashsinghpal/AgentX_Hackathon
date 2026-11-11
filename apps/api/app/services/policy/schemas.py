"""Trusted, structured inputs for the deterministic policy engine.

Every value here is loaded from the database (or is the policy document itself).
Nothing in this module is populated from LLM output or from client-supplied
financial values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.policy import PolicySchema

DELIVERY_REQUIRED_CATEGORIES = frozenset(
    {"return", "damaged", "defective", "wrong_item", "missing_item"}
)
VALID_ISSUE_CATEGORIES = DELIVERY_REQUIRED_CATEGORIES | {"delay", "cancellation"}


@dataclass(frozen=True)
class CaseInput:
    seller_id: str
    buyer_id: str
    order_id: str
    issue_category: str | None
    id: str | None = None
    case_number: str | None = None


@dataclass(frozen=True)
class OrderInput:
    id: str
    seller_id: str
    buyer_id: str | None
    order_number: str
    currency: str
    total_amount_minor: int
    payment_method: str
    payment_status: str
    order_status: str
    original_delivery_date: datetime | None = None


@dataclass(frozen=True)
class ItemInput:
    reference_id: str
    title: str
    quantity: int
    unit_price_minor: int
    returnable: bool = True
    category: str | None = None
    sku: str | None = None


@dataclass(frozen=True)
class ShipmentInput:
    """Snapshot of the latest shipment plus its normalized tracking history."""

    id: str
    status: str
    promising_available: bool = True
    promised_delivery_date: datetime | None = None
    actual_delivery_date: datetime | None = None
    tracking_event_count: int = 0
    latest_event_at: datetime | None = None
    courier_partner: str | None = None
    tracking_number: str | None = None


@dataclass(frozen=True)
class PolicyEvaluationInput:
    case: CaseInput
    order: OrderInput
    seller_status: str
    policy: PolicySchema | None
    policy_id: str | None
    # Monotonic version of the stored SellerPolicy row.  The document's own
    # `version` field is informational; the row version is what makes an
    # evaluation traceable to the exact published policy.
    policy_version: int | None = None
    policy_invalid: bool = False
    shipment: ShipmentInput | None = None
    items: tuple[ItemInput, ...] = field(default_factory=tuple)
    evidence_count: int = 0
    evidence_reference_ids: tuple[str, ...] = field(default_factory=tuple)
    buyer_refund_count_30d: int = 0
    duplicate_claim_exists: bool = False
    now: datetime | None = None
    evaluator_version: str = "1.0.0"
