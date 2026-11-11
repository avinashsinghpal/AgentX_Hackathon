from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Decision(StrEnum):
    ELIGIBLE = "eligible"
    NEEDS_APPROVAL = "needs_approval"
    NOT_ELIGIBLE = "not_eligible"
    MANUAL_REVIEW = "manual_review"


# Frontend/API badge contract.  ``executed`` is an action outcome, never a
# policy decision: the policy engine only ever returns the decisions above.
DECISION_TO_BADGE: dict[Decision, str] = {
    Decision.ELIGIBLE: "executed",
    Decision.NEEDS_APPROVAL: "needs_approval",
    Decision.MANUAL_REVIEW: "needs_approval",
    Decision.NOT_ELIGIBLE: "not_eligible",
}


class CheckResult(BaseModel):
    """One deterministic policy guard outcome."""

    model_config = ConfigDict(extra="forbid")

    check: str
    passed: bool
    reason_code: str | None = None
    expected: Any = None
    actual: Any = None
    detail: str | None = None


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seller_id: str
    order_id: str
    buyer_id: str | None = None
    case_id: str | None = None
    currency: str
    policy_id: str | None = None
    policy_version: int
    decision: Decision
    reason_code: str
    reason: str
    eligible_amount_minor: int = Field(default=0, ge=0)
    proposed_action: str = "reject"
    requires_approval: bool
    evaluated_at: datetime
    checks: list[CheckResult] = Field(default_factory=list)
    evidence_reference_ids: list[str] = Field(default_factory=list)
    evaluator_version: str
    scenario: str = "case"

    @property
    def badge(self) -> str:
        return DECISION_TO_BADGE[self.decision]
