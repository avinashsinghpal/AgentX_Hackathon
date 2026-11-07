from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class ReturnsPolicy(BaseModel):
    window_days: int = Field(default=7, ge=0, le=90)
    non_returnable_categories: list[str] = Field(
        default_factory=lambda: ["innerwear", "perishables"]
    )

    @field_validator("non_returnable_categories")
    @classmethod
    def clean_categories(cls, v: list[str]) -> list[str]:
        return [cat.strip().lower() for cat in v if cat.strip()]


class RefundsPolicy(BaseModel):
    auto_approve_up_to: int = Field(default=500, ge=0, le=100000)
    require_seller_approval_above: int = Field(default=500, ge=0, le=100000)
    cod_refund_method: Literal["store_credit", "bank_transfer"] = Field(default="store_credit")

    @field_validator("require_seller_approval_above")
    @classmethod
    def validate_ceiling(cls, v: int, info: ValidationInfo) -> int:
        auto_up_to = info.data.get("auto_approve_up_to", 500) if info.data else 500
        if v < auto_up_to:
            raise ValueError(
                "require_seller_approval_above must be greater than or equal to auto_approve_up_to"
            )
        return v


class DelaysPolicy(BaseModel):
    notify_after_days_late: int = Field(default=2, ge=1, le=30)
    allow_return_if_late_days_at_least: int = Field(default=3, ge=1, le=30)


class DamageClaimsPolicy(BaseModel):
    require_photo: bool = Field(default=True)
    report_within_days: int = Field(default=2, ge=1, le=30)


class FraudChecksPolicy(BaseModel):
    max_refunds_per_buyer_per_30_days: int = Field(default=3, ge=1, le=20)
    require_seller_approval_if_exceeded: bool = Field(default=True)


class PolicySchema(BaseModel):
    version: int = Field(default=1, ge=1)
    currency: str = Field(default="INR", max_length=3)
    returns: ReturnsPolicy = Field(default_factory=ReturnsPolicy)
    refunds: RefundsPolicy = Field(default_factory=RefundsPolicy)
    delays: DelaysPolicy = Field(default_factory=DelaysPolicy)
    damage_claims: DamageClaimsPolicy = Field(default_factory=DamageClaimsPolicy)
    fraud_checks: FraudChecksPolicy = Field(default_factory=FraudChecksPolicy)

    model_config = ConfigDict(extra="forbid")


DEFAULT_POLICY_YAML = """version: 1
currency: INR

returns:
  window_days: 7
  non_returnable_categories:
    - innerwear
    - perishables

refunds:
  auto_approve_up_to: 500
  require_seller_approval_above: 500
  cod_refund_method: store_credit

delays:
  notify_after_days_late: 2
  allow_return_if_late_days_at_least: 3

damage_claims:
  require_photo: true
  report_within_days: 2

fraud_checks:
  max_refunds_per_buyer_per_30_days: 3
  require_seller_approval_if_exceeded: true
"""


def parse_and_validate_yaml(yaml_str: str) -> tuple[bool, PolicySchema | None, str | None]:
    """
    Parses and validates raw YAML against the deterministic PolicySchema.
    Returns (is_valid, parsed_policy, error_message).
    """
    try:
        raw_dict = yaml.safe_load(yaml_str)
        if not isinstance(raw_dict, dict):
            return False, None, "Policy YAML must evaluate to a dictionary object."
        policy = PolicySchema.model_validate(raw_dict)
        return True, policy, None
    except yaml.YAMLError as ye:
        return False, None, f"YAML Syntax Error: {ye}"
    except Exception as e:
        return False, None, f"Policy Validation Error: {e}"


def policy_to_yaml(policy: PolicySchema) -> str:
    """Converts a PolicySchema instance into formatted YAML string."""
    data = policy.model_dump()
    return yaml.dump(data, sort_keys=False, default_flow_style=False)
