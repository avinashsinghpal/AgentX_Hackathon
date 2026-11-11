"""Deterministic risk-evaluation result.

The risk engine is intentionally separate from the policy engine.  It reports
risk indicators only; it never produces eligibility, financial, approval or
action decisions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataSufficiency(StrEnum):
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


class RiskFlag(BaseModel):
    """One deterministic risk finding."""

    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["low", "medium", "high"]
    explanation: str


class RiskResult(BaseModel):
    """Validated, serialized risk-engine output."""

    model_config = ConfigDict(extra="forbid")

    risk_engine_version: str = "1.0.0"
    flags: list[RiskFlag] = Field(default_factory=list)
    data_sufficiency: DataSufficiency = DataSufficiency.SUFFICIENT
    evaluated_at: datetime
