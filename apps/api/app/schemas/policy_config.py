"""Typed API contracts for the seller policy configuration workflow.

Structured input is accepted as a validated ``PolicySchema`` document: the
console never sends YAML it built by string interpolation, and the server never
accepts a field the schema does not know about.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.policy import PolicySchema


class PolicyConfigRequest(BaseModel):
    """Structured policy configuration from the seller console."""

    model_config = ConfigDict(extra="forbid")

    config: PolicySchema


class PolicyYamlRequest(BaseModel):
    """Raw YAML as edited by the seller (validation/preview)."""

    model_config = ConfigDict(extra="forbid")

    policy_yaml: str = Field(min_length=1, max_length=200_000)


class PolicyPublishRequest(BaseModel):
    """Explicit publication request.

    Exactly one source is supplied.  ``confirm`` must be ``true``: the API
    refuses to publish a policy version that the seller has not explicitly
    confirmed, and ``expected_active_version`` protects against publishing on top
    of a version that changed while the seller was editing.
    """

    model_config = ConfigDict(extra="forbid")

    config: PolicySchema | None = None
    policy_yaml: str | None = Field(default=None, max_length=200_000)
    confirm: bool = False
    expected_active_version: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def exactly_one_source(self) -> PolicyPublishRequest:
        has_config = self.config is not None
        has_yaml = self.policy_yaml is not None and self.policy_yaml.strip() != ""
        if has_config == has_yaml:
            raise ValueError("Provide exactly one of 'config' or 'policy_yaml'")
        return self


class PolicyLegacyPublishRequest(BaseModel):
    """Backward-compatible raw-YAML publication body (``POST /policies``)."""

    model_config = ConfigDict(extra="forbid")

    policy_yaml: str = Field(min_length=1, max_length=200_000)
    confirm: bool = False
    expected_active_version: int | None = Field(default=None, ge=0)


class PolicyMonetaryMinor(BaseModel):
    """Every monetary threshold in integer minor units (paise for INR)."""

    model_config = ConfigDict(extra="forbid")

    currency: str
    minor_unit_exponent: int
    refund_auto_approve_ceiling_minor: int
    refund_instant_without_return_threshold_minor: int
    delay_compensation_per_day_minor: int
    delay_compensation_max_minor: int
    damage_auto_replacement_max_minor: int
    damage_warehouse_inspection_threshold_minor: int
    fraud_high_value_order_threshold_minor: int


class PolicyDocumentResponse(BaseModel):
    """A policy version (active, historical or baseline) as served to the UI."""

    has_policy: bool
    valid: bool
    id: str | None = None
    version: int
    next_version: int
    currency: str
    policy_yaml: str
    config: PolicySchema | None = None
    parsed_rules: dict[str, Any] = Field(default_factory=dict)
    monetary_minor: PolicyMonetaryMinor | None = None
    activated_at: datetime | None = None
    created_at: datetime | None = None
    source: str | None = None
    content_sha256: str | None = None


class PolicyHistoryItem(BaseModel):
    id: str
    version: int
    is_active: bool
    currency: str
    created_at: datetime
    activated_at: datetime | None = None
    source: str | None = None
    content_sha256: str | None = None
    returns_window: int | None = None
    refund_ceiling: int | None = None
    refund_ceiling_minor: int | None = None


class PolicyConfigValidationResponse(BaseModel):
    valid: bool
    currency: str
    config: PolicySchema
    monetary_minor: PolicyMonetaryMinor


class PolicyPreviewResponse(BaseModel):
    valid: bool
    currency: str
    config: PolicySchema
    monetary_minor: PolicyMonetaryMinor
    policy_yaml: str
    warnings: list[str] = Field(default_factory=list)


class PolicyYamlValidationResponse(BaseModel):
    valid: bool
    error: str | None = None
    config: PolicySchema | None = None
    policy_yaml: str | None = None
    parsed: dict[str, Any] | None = None
    monetary_minor: PolicyMonetaryMinor | None = None


class PolicyPublishResponse(BaseModel):
    success: bool
    id: str
    version: int
    previous_version: int
    currency: str
    policy_yaml: str
    config: PolicySchema
    parsed_rules: dict[str, Any]
    monetary_minor: PolicyMonetaryMinor
    activated_at: datetime | None = None
    created_at: datetime | None = None
    source: str
    content_sha256: str


def monetary_minor_model(policy: PolicySchema) -> PolicyMonetaryMinor:
    return PolicyMonetaryMinor.model_validate(policy.monetary_minor())
