import re
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger

ZERO_EMOJI_SYSTEM_PROMPT = """You are SellerResolve's policy-aware autonomous resolution assistant.
STRICT OPERATIONAL RULES:
1. NEVER output emojis under any circumstances. Emojis are strictly banned.
2. Quote exact order references, amounts in INR, tracking numbers, and policy thresholds.
3. Ground all statements strictly in the facts and verification records provided.
4. Do not make policy decisions or promise exceptions outside the verified facts.
5. Maintain a professional, polite, and reassuring tone.
"""


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    finish_reason: str = "stop"


def sanitize_no_emoji(text: str) -> str:
    """Removes all unicode emojis and symbols from text."""
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff"
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f700-\U0001f77f"
        "\U0001f780-\U0001f7ff"
        "\U0001f800-\U0001f8ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001fa6f"
        "\U0001fa70-\U0001faff"
        "\u2600-\u26ff"
        "\u2700-\u27bf]"
    )
    return emoji_pattern.sub("", text).strip()


class LLMClient(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def stream_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        pass


class FakeLLMClient(LLMClient):
    """Deterministic offline mock LLM client for tests and predictable scenarios."""

    async def generate_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> LLMResponse:
        facts = messages[-1].content if messages else ""

        def field(label: str) -> str:
            match = re.search(rf"^- {re.escape(label)}: (.+)$", facts, re.MULTILINE)
            return match.group(1).strip() if match else ""

        order = field("Order") or "your order"
        amount = field("Order amount") or "the order amount"
        eligible = field("Eligible amount") or amount
        issue = (field("Issue category") or "claim").replace("_", " ")
        action = (field("Proposed action") or "resolution").replace("_", " ")
        reason = field("Deterministic reason")
        badge = field("Backend outcome badge")

        # Quote the deterministic decision supplied in the facts.  The mock must
        # never claim an action was executed when the backend is waiting for the
        # seller, nor invent a policy window or amount.
        if badge == "executed":
            if "damage" in issue or "replacement" in action:
                reply = (
                    f"We inspected the photographic evidence for order {order} and verified the "
                    f"transit damage claim. The {action} of {eligible} has been executed and "
                    "recorded in the audit trail."
                )
            elif "delay" in issue or "credit" in action:
                reply = (
                    f"We verified the transit delay for order {order}. A proactive {action} of "
                    f"{eligible} has been issued and recorded in the audit trail."
                )
            else:
                reply = (
                    f"We verified order {order} against the merchant policy. The {action} of "
                    f"{eligible} has been executed and recorded in the audit trail."
                )
        elif badge == "needs_approval":
            reply = (
                f"We reviewed order {order}. {reason} This {issue} request requires merchant "
                f"approval before {eligible} can be issued. No financial action has been "
                "executed yet; the merchant has been notified and the case is pending approval."
            )
        else:
            detail = f" {reason}" if reason else ""
            reply = (
                f"We reviewed order {order}.{detail} The {issue} request is not eligible for an "
                "automated resolution, and no financial action has been taken."
            )

        clean_text = sanitize_no_emoji(reply)
        return LLMResponse(text=clean_text)

    async def stream_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        res = await self.generate_response(messages, temperature)
        words = res.text.split(" ")
        for w in words:
            yield w + " "


class GeminiLLMClient(LLMClient):
    """Live LLM client using Gemini 2.5 Flash via REST API."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> LLMResponse:
        contents: list[dict[str, Any]] = []

        system_instruction = ZERO_EMOJI_SYSTEM_PROMPT
        for m in messages:
            if m.role == "system":
                system_instruction += "\n" + m.content
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    logger.error("Gemini API error: %s", res.text)
                    fallback = FakeLLMClient()
                    return await fallback.generate_response(messages, temperature)

                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return LLMResponse(text=sanitize_no_emoji(raw_text))
        except Exception as exc:
            logger.error("Exception calling Gemini: %s", exc)
            fallback = FakeLLMClient()
            return await fallback.generate_response(messages, temperature)

    async def stream_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        res = await self.generate_response(messages, temperature)
        words = res.text.split(" ")
        for w in words:
            yield w + " "


def get_llm_client() -> LLMClient:
    """Returns the appropriate LLMClient based on environment configuration."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    provider = getattr(settings, "LLM_PROVIDER", "fake")

    if provider == "gemini" and api_key and api_key.strip():
        return GeminiLLMClient(api_key=api_key.strip())

    return FakeLLMClient()
