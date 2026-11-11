"""Deterministic risk evaluation package."""

from app.services.risk.engine import RiskEngine
from app.services.risk.evaluator import RiskEvaluationService
from app.services.risk.result import (
    DataSufficiency,
    RiskFlag,
    RiskResult,
)
from app.services.risk.schemas import RiskEvaluationInput

# Compatibility aliases for callers that use alternate names.
RiskInput = RiskEvaluationInput
RiskEvaluationResult = RiskResult
RiskEvaluation = RiskResult

__all__ = [
    "DataSufficiency",
    "RiskEngine",
    "RiskEvaluation",
    "RiskEvaluationInput",
    "RiskEvaluationResult",
    "RiskEvaluationService",
    "RiskFlag",
    "RiskInput",
    "RiskResult",
]