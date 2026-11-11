"""Strict Pydantic schemas for orchestrator tool calls.

These schemas validate tool arguments before execution and describe the
structured results returned to the LLM.  Unknown fields are rejected.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LookupOrderArgs(StrictModel):
    order_id: str | None = Field(default=None, max_length=128)


class LookupShipmentArgs(StrictModel):
    order_id: str | None = Field(default=None, max_length=128)


class GetCaseArgs(StrictModel):
    pass


class EvaluatePolicyArgs(StrictModel):
    pass


class EvaluateRiskArgs(StrictModel):
    pass


class GetConversationHistoryArgs(StrictModel):
    limit: int = Field(default=20, ge=1, le=100)


class ResolveCaseArgs(StrictModel):
    pass


class EscalateToHumanArgs(StrictModel):
    reason: str | None = Field(default=None, max_length=2000)


class GetTrackingEventsArgs(StrictModel):
    pass


class GetBuyerHistoryArgs(StrictModel):
    limit: int = Field(default=20, ge=1, le=100)


class GetEvidenceSummaryArgs(StrictModel):
    pass


class GetPolicySummaryArgs(StrictModel):
    pass


class ToolErrorResult(BaseModel):
    error: str
    tool: str | None = None


class ToolSuccessResult(BaseModel):
    result: dict[str, Any]


TOOL_INPUT_SCHEMAS: dict[str, type[StrictModel]] = {
    "lookup_order": LookupOrderArgs,
    "lookup_shipment": LookupShipmentArgs,
    "get_case": GetCaseArgs,
    "evaluate_policy_rules": EvaluatePolicyArgs,
    "evaluate_risk": EvaluateRiskArgs,
    "get_conversation_history": GetConversationHistoryArgs,
    "resolve_case": ResolveCaseArgs,
    "escalate_to_human": EscalateToHumanArgs,
    "get_tracking_events": GetTrackingEventsArgs,
    "get_buyer_history": GetBuyerHistoryArgs,
    "get_evidence_summary": GetEvidenceSummaryArgs,
    "get_policy_summary": GetPolicySummaryArgs,
}


def validate_tool_arguments(tool_name: str, arguments: Any) -> dict[str, Any]:
    if tool_name not in TOOL_INPUT_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}")
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object")
    try:
        model = TOOL_INPUT_SCHEMAS[tool_name].model_validate(arguments)
    except Exception as exc:
        raise ValueError(f"Invalid arguments for {tool_name}: {exc}") from exc
    return model.model_dump(exclude_none=True)
