"""Canonical seller policy document.

The document a seller publishes is expressed in **major units** of an explicit
ISO-4217 ``currency`` ("INR 500").  It is validated strictly here, converted to
canonical YAML, and persisted verbatim with the parser snapshot.

Every calculation inside the platform uses **integer minor units** instead:
``paise = rupees * 100`` (factor ``MAJOR_UNITS_PER_CURRENCY_UNIT``).  The
conversion happens exactly once, in the ``*_minor`` accessors below, and the
derived values are exposed by ``PolicySchema.monetary_minor()`` so callers never
have to re-derive the unit convention.
"""

from __future__ import annotations

import re
from typing import Any, Literal

import yaml
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.core.logging import logger

#: Minor units per major unit for the supported two-decimal currencies (INR).
MAJOR_UNITS_PER_CURRENCY_UNIT = 100

CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
MINOR_UNIT_EXPONENT = 2


def to_minor_units(amount_major: int) -> int:
    """Convert an integer major-unit amount (rupees) into integer paise."""
    return int(amount_major) * MAJOR_UNITS_PER_CURRENCY_UNIT


def from_minor_units(amount_minor: int) -> int:
    """Whole major units for display.  Never used for arithmetic."""
    return int(amount_minor) // MAJOR_UNITS_PER_CURRENCY_UNIT


class ReturnsPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    window_days: int = Field(default=7, ge=0, le=90)
    non_returnable_categories: list[str] = Field(
        default_factory=lambda: ["innerwear", "perishables"]
    )
    eligible_categories: list[str] | None = None
    return_shipping_paid_by: Literal["seller", "buyer"] = Field(default="seller")
    auto_generate_shipping_label: bool = Field(default=True)
    require_original_packaging: bool = Field(default=False)

    @field_validator("non_returnable_categories")
    @classmethod
    def clean_categories(cls, v: list[str]) -> list[str]:
        return [cat.strip().lower() for cat in v if cat and cat.strip()]

    @field_validator("eligible_categories")
    @classmethod
    def clean_eligible_categories(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [cat.strip().lower() for cat in v if cat and cat.strip()]


class RefundsPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    auto_approve_up_to: int = Field(
        default=500,
        ge=0,
        le=100000,
        validation_alias=AliasChoices("auto_approve_up_to", "auto_approve_max_amount"),
    )
    require_seller_approval_above: int = Field(default=500, ge=0, le=100000)
    cod_refund_method: Literal["store_credit", "bank_transfer"] = Field(default="store_credit")
    instant_refund_without_return_threshold: int = Field(default=500, ge=0, le=100000)
    restocking_fee_percentage: int = Field(default=0, ge=0, le=100)
    processing_sla_days: int = Field(default=2, ge=0, le=30)

    @model_validator(mode="before")
    @classmethod
    def resolve_approval_ceiling(cls, data: Any) -> Any:
        """Keep the two ceiling fields coherent.

        ``auto_approve_up_to`` is the autonomous ceiling; the engine escalates
        strictly above it.  ``require_seller_approval_above`` expresses the same
        boundary and is therefore inherited from the autonomous ceiling when the
        document only supplies one of the two (or the legacy alias).  Supplying
        both with different values is a contradiction and is rejected instead of
        silently picking one.
        """
        if not isinstance(data, dict):
            return data

        auto: Any = None
        if data.get("auto_approve_up_to") is not None:
            auto = data["auto_approve_up_to"]
        alias = data.get("auto_approve_max_amount")
        if alias is not None:
            if auto is not None and alias != auto:
                raise ValueError(
                    "refunds.auto_approve_up_to and refunds.auto_approve_max_amount "
                    "are the same field and disagree"
                )
            if auto is None:
                auto = alias

        approval = data.get("require_seller_approval_above")
        if auto is None and approval is None:
            return data
        if auto is None:
            auto = approval
        if approval is None:
            approval = auto
        if auto != approval:
            raise ValueError(
                "refunds.require_seller_approval_above must equal refunds.auto_approve_up_to"
            )
        cleaned = {key: value for key, value in data.items() if key != "auto_approve_max_amount"}
        return {
            **cleaned,
            "auto_approve_up_to": auto,
            "require_seller_approval_above": auto,
        }

    @field_validator("require_seller_approval_above")
    @classmethod
    def validate_ceiling(cls, v: int, info: ValidationInfo) -> int:
        auto_up_to = info.data.get("auto_approve_up_to", 500) if info.data else 500
        if v != auto_up_to:
            raise ValueError("require_seller_approval_above must equal auto_approve_up_to")
        return v

    @property
    def auto_approve_ceiling_minor(self) -> int:
        return to_minor_units(self.auto_approve_up_to)

    @property
    def seller_approval_ceiling_minor(self) -> int:
        return to_minor_units(self.require_seller_approval_above)

    @property
    def instant_refund_threshold_minor(self) -> int:
        return to_minor_units(self.instant_refund_without_return_threshold)


class DelaysPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    notify_after_days_late: int = Field(
        default=2,
        ge=1,
        le=30,
        validation_alias=AliasChoices(
            "notify_after_days_late", "delay_threshold_days", "auto_credit_after_days"
        ),
    )
    allow_return_if_late_days_at_least: int = Field(default=3, ge=1, le=30)
    compensation_per_day_late: int = Field(default=0, ge=0, le=100000)
    max_delay_compensation: int = Field(default=0, ge=0, le=100000)

    @property
    def compensation_per_day_minor(self) -> int:
        return to_minor_units(self.compensation_per_day_late)

    @property
    def max_compensation_minor(self) -> int:
        return to_minor_units(self.max_delay_compensation)


class DamageClaimsPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    require_photo: bool = Field(
        default=True,
        validation_alias=AliasChoices("require_photo", "photo_evidence_required"),
    )
    report_within_days: int = Field(default=2, ge=1, le=30)
    auto_replacement_under_amount: int = Field(default=1500, ge=0, le=100000)
    require_warehouse_inspection_above: int = Field(default=5000, ge=0, le=100000)

    @property
    def auto_replacement_under_minor(self) -> int:
        return to_minor_units(self.auto_replacement_under_amount)

    @property
    def warehouse_inspection_threshold_minor(self) -> int:
        return to_minor_units(self.require_warehouse_inspection_above)


class FraudChecksPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def warn_legacy_claim_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "max_claims_per_buyer_90_days" in data:
            logger.warning(
                "Legacy policy key 'max_claims_per_buyer_90_days' was supplied; "
                "it is treated as a 30-day refund limit, not a 90-day claim limit."
            )
        return data

    max_refunds_per_buyer_per_30_days: int = Field(
        default=3,
        ge=1,
        le=20,
        validation_alias=AliasChoices(
            "max_refunds_per_buyer_per_30_days", "max_claims_per_buyer_90_days"
        ),
    )
    require_seller_approval_if_exceeded: bool = Field(default=True)
    require_manual_review_for_high_value: bool = Field(default=False)
    high_value_order_threshold: int = Field(default=5000, ge=0, le=1000000)
    block_suspicious_addresses: bool = Field(default=False)

    @property
    def high_value_order_threshold_minor(self) -> int:
        return to_minor_units(self.high_value_order_threshold)


class PolicySchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: int = Field(default=1, ge=1)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    returns: ReturnsPolicy = Field(default_factory=ReturnsPolicy)
    refunds: RefundsPolicy = Field(default_factory=RefundsPolicy)
    delays: DelaysPolicy = Field(default_factory=DelaysPolicy)
    damage_claims: DamageClaimsPolicy = Field(default_factory=DamageClaimsPolicy)
    fraud_checks: FraudChecksPolicy = Field(default_factory=FraudChecksPolicy)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        value = v.strip().upper()
        if not CURRENCY_PATTERN.match(value):
            raise ValueError("currency must be a three-letter ISO-4217 code such as INR")
        return value

    def monetary_minor(self) -> dict[str, int | str]:
        """Authoritative minor-unit snapshot of every monetary threshold.

        ``paise = rupees * 100``.  This is what the API returns for previews and
        what the engine relies on, so the unit convention is explicit at the
        boundary rather than implied by a bare number.
        """
        return {
            "currency": self.currency,
            "minor_unit_exponent": MINOR_UNIT_EXPONENT,
            "refund_auto_approve_ceiling_minor": self.refunds.auto_approve_ceiling_minor,
            "refund_instant_without_return_threshold_minor": (
                self.refunds.instant_refund_threshold_minor
            ),
            "delay_compensation_per_day_minor": self.delays.compensation_per_day_minor,
            "delay_compensation_max_minor": self.delays.max_compensation_minor,
            "damage_auto_replacement_max_minor": (self.damage_claims.auto_replacement_under_minor),
            "damage_warehouse_inspection_threshold_minor": (
                self.damage_claims.warehouse_inspection_threshold_minor
            ),
            "fraud_high_value_order_threshold_minor": (
                self.fraud_checks.high_value_order_threshold_minor
            ),
        }


def default_policy(currency: str = "INR") -> PolicySchema:
    """Baseline policy shown to sellers that have not published one yet."""
    return PolicySchema(currency=currency)


def policy_to_yaml(policy: PolicySchema) -> str:
    """Render a validated policy as canonical (deterministic) YAML."""
    data = policy.model_dump(mode="json")
    return yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=1000,
    )


DEFAULT_POLICY_YAML = policy_to_yaml(default_policy())


def _format_validation_error(error: ValidationError) -> str:
    parts: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ()))
        message = item.get("msg", "invalid value")
        parts.append(f"{location}: {message}" if location else str(message))
    return "; ".join(parts)


def parse_and_validate_yaml(yaml_str: str) -> tuple[bool, PolicySchema | None, str | None]:
    """Parse and validate raw YAML against the deterministic ``PolicySchema``.

    Returns ``(is_valid, parsed_policy, error_message)``.  Unknown keys are
    rejected rather than discarded, and error messages name the offending field
    so the console can point at it.
    """
    try:
        raw_dict = yaml.safe_load(yaml_str or "")
        if not isinstance(raw_dict, dict):
            return False, None, "Policy YAML must evaluate to a dictionary object."
        policy = PolicySchema.model_validate(raw_dict)
        return True, policy, None
    except yaml.YAMLError as exc:
        return False, None, f"YAML Syntax Error: {exc}"
    except ValidationError as exc:
        return False, None, f"Policy Validation Error: {_format_validation_error(exc)}"
    except Exception as exc:  # pragma: no cover - defensive
        return False, None, f"Policy Validation Error: {exc}"


def normalize_parsed_rules(rules: dict[str, Any] | None) -> PolicySchema | None:
    """Validate a persisted ``parsed_rules`` document.

    Older rows were written without full validation; this normalizes them into
    the canonical schema, returning ``None`` when the stored document is not a
    valid policy.  A derived ``monetary`` block (if present) is ignored because
    it is not part of the document schema.
    """
    if not rules:
        return None
    candidate = {key: value for key, value in rules.items() if key != "monetary"}
    try:
        return PolicySchema.model_validate(candidate)
    except Exception:
        return None


def policy_rules_dict(policy: PolicySchema) -> dict[str, Any]:
    """Canonical parsed rules plus legacy keys existing UI pages still read."""
    data = policy.model_dump(mode="json")
    data["refunds"]["auto_approve_max_amount"] = data["refunds"]["auto_approve_up_to"]
    data["delays"]["delay_threshold_days"] = data["delays"]["notify_after_days_late"]
    data["damage_claims"]["photo_evidence_required"] = data["damage_claims"]["require_photo"]
    data["fraud_checks"]["max_claims_per_buyer_90_days"] = data["fraud_checks"][
        "max_refunds_per_buyer_per_30_days"
    ]
    return data
