"""Structured buyer intake.

The LLM may classify and extract fields, but the result is validated against
strict Pydantic schemas.  Missing or ambiguous information produces a
clarifying question instead of a guessed value.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.services.llm.client import LLMClient, LLMMessage, get_llm_client


class IssueCategory(StrEnum):
    RETURN = "return"
    DAMAGED = "damaged"
    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    MISSING_ITEM = "missing_item"
    DELAY = "delay"
    CANCELLATION = "cancellation"
    WISMO = "wismo"


class DesiredRemedy(StrEnum):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    RETURN_LABEL = "return_label"
    TRACKING = "tracking"
    ESCALATION = "escalation"
    UNKNOWN = "unknown"


class BuyerIntake(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    issue_category: IssueCategory
    order_reference: str | None = Field(default=None, max_length=128)
    item: str | None = Field(default=None, max_length=256)
    desired_remedy: DesiredRemedy = DesiredRemedy.UNKNOWN
    confidence: float = Field(ge=0.0, le=1.0)
    clarifying_question: str | None = Field(default=None, max_length=500)


def parse_intake_response(text: str) -> BuyerIntake:
    stripped = text.strip()
    candidates = [stripped]
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match and match.group(0) != stripped:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            try:
                return BuyerIntake.model_validate(parsed)
            except Exception:
                continue
    raise ValueError("Unable to parse structured buyer intake response")


class IntakeService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or get_llm_client()

    async def classify(self, message: str) -> BuyerIntake:
        prompt = (
            "Classify the buyer complaint into strict JSON with keys: "
            "issue_category, order_reference, item, desired_remedy, confidence, "
            "clarifying_question. Allowed issue_category values: return, damaged, "
            "defective, wrong_item, missing_item, delay, cancellation, wismo. "
            "Allowed desired_remedy values: refund, replacement, return_label, "
            "tracking, escalation, unknown. confidence must be 0 to 1. If the "
            "complaint is ambiguous or missing an order reference, set "
            "clarifying_question to one clear question and lower confidence. "
            "Return JSON only."
        )
        messages = [
            LLMMessage(role="system", content=prompt),
            LLMMessage(role="user", content=message),
        ]
        response = await self.llm.generate_response(messages)
        return parse_intake_response(response.text or "")
