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
    @property
    def provider_name(self) -> str:
        return "unknown"

    @property
    def model_name(self) -> str:
        return ""

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

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake"

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

    async def generate_with_tools(
        self,
        messages: list[LLMMessage],
        tool_declarations: list[dict[str, Any]],
        tool_executor: Any,
        max_calls: int,
        temperature: float = 0.1,
    ) -> str:
        """Run a deterministic investigation-tool workflow for offline tests."""
        budget = max(0, int(max_calls or 0))
        available = {
            str(tool.get("name")) for tool in tool_declarations if tool.get("name")
        }
        preferred = [
            "lookup_order",
            "lookup_shipment",
            "get_tracking_events",
            "get_buyer_history",
            "get_evidence_summary",
            "get_policy_summary",
        ]
        sequence = [name for name in preferred if name in available]
        used = 0
        for name in sequence:
            if used >= budget:
                break
            try:
                await tool_executor(name, {})
            except Exception:
                pass
            used += 1

        return (
            "Investigation complete: order, tracking, buyer history and evidence reviewed "
            "using deterministic offline tools."
        )

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

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.model

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
                    raise LLMProviderError(f"Gemini request failed with HTTP {res.status_code}")

                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return LLMResponse(text=sanitize_no_emoji(raw_text))
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error("Exception calling Gemini: %s", exc)
            raise LLMProviderError("Gemini request failed") from exc

    async def stream_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        contents: list[dict[str, Any]] = []
        system_instruction = ZERO_EMOJI_SYSTEM_PROMPT
        for message in messages:
            if message.role == "system":
                system_instruction += "\n" + message.content
            else:
                role = "user" if message.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": message.content}]})

        url = (
            f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024},
        }
        try:
            import json

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        raise LLMProviderError(
                            f"Gemini stream failed with HTTP {response.status_code}"
                        )
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if not data_str or data_str == "[DONE]":
                            continue
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        candidates = data.get("candidates") or []
                        if not candidates:
                            continue
                        content = candidates[0].get("content") or {}
                        for part in content.get("parts") or []:
                            text = part.get("text")
                            if text:
                                yield sanitize_no_emoji(text)
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError("Gemini streaming failed") from exc

    async def generate_with_tools(
        self,
        messages: list[LLMMessage],
        tool_declarations: list[dict[str, Any]],
        tool_executor: Any,
        max_calls: int,
        temperature: float = 0.1,
    ) -> str:
        """Run a native Gemini function-calling loop and return final text."""
        budget = max(0, int(max_calls or 0))
        system_instruction = ZERO_EMOJI_SYSTEM_PROMPT
        contents: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system_instruction += "\n" + message.content
            else:
                role = "user" if message.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": message.content}]})

        allowed_tools = {
            str(tool.get("name")): tool for tool in tool_declarations if tool.get("name")
        }
        declarations = []
        for tool in tool_declarations:
            name = tool.get("name")
            if not name:
                continue
            declarations.append(
                {
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                }
            )

        if budget == 0:
            response = await self.generate_response(messages, temperature)
            return response.text

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        used_calls = 0

        async def final_response(retry: bool = False) -> str:
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024},
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code != 200:
                        raise LLMProviderError(f"Gemini request failed with HTTP {res.status_code}")
                    data = res.json()
            except LLMProviderError:
                raise
            except Exception as exc:
                raise LLMProviderError("Gemini request failed") from exc
            candidate = (data.get("candidates") or [{}])[0]
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            text_parts = [
                part.get("text", "")
                for part in parts
                if isinstance(part, dict) and part.get("text")
            ]
            text = sanitize_no_emoji("".join(text_parts).strip())
            function_calls = [
                part.get("functionCall")
                for part in parts
                if isinstance(part, dict) and part.get("functionCall")
            ]
            if function_calls and not text and not retry:
                contents.append({"role": "model", "parts": parts})
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": (
                                    "Respond with a concise final answer in plain text. "
                                    "Do not call any tools."
                                )
                            }
                        ],
                    }
                )
                return await final_response(retry=True)
            return text

        while used_calls < budget:
            payload: dict[str, Any] = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024},
            }
            if declarations:
                payload["tools"] = [{"functionDeclarations": declarations}]

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code != 200:
                        raise LLMProviderError(f"Gemini request failed with HTTP {res.status_code}")
                    data = res.json()
            except LLMProviderError:
                raise
            except Exception as exc:
                raise LLMProviderError("Gemini request failed") from exc

            candidate = (data.get("candidates") or [{}])[0]
            content = candidate.get("content") or {}
            parts = content.get("parts") or []
            function_calls = [
                part.get("functionCall")
                for part in parts
                if isinstance(part, dict) and part.get("functionCall")
            ]

            if not function_calls:
                text_parts = [
                    part.get("text", "")
                    for part in parts
                    if isinstance(part, dict) and part.get("text")
                ]
                return sanitize_no_emoji("".join(text_parts).strip())

            # Preserve the original model turn, including thought signatures.
            contents.append({"role": "model", "parts": parts})

            remaining = budget - used_calls
            over_budget = len(function_calls) > remaining
            response_parts: list[dict[str, Any]] = []
            for function_call in function_calls:
                function_call = function_call or {}
                tool_name = str(function_call.get("name") or "")
                arguments = function_call.get("args") or {}
                if not isinstance(arguments, dict):
                    arguments = {}

                if over_budget:
                    observation: Any = {"error": "Tool call budget exceeded"}
                elif tool_name not in allowed_tools:
                    observation = {"error": "Unknown or unauthorized tool"}
                else:
                    try:
                        observation = await tool_executor(tool_name, arguments)
                    except Exception:
                        observation = {"error": "Tool execution failed"}

                response_parts.append(
                    {
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"result": observation},
                        }
                    }
                )

            contents.append({"role": "user", "parts": response_parts})
            if over_budget:
                used_calls = budget
            else:
                used_calls += min(len(function_calls), remaining)

        return await final_response()


class LLMProviderError(RuntimeError):
    """Raised when a configured LLM provider request fails."""


class LLMConfigurationError(RuntimeError):
    """Raised when a requested LLM provider is missing required configuration."""


class AnthropicLLMClient(LLMClient):
    """Live LLM client using Anthropic Claude via the official SDK."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self.model

    async def generate_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> LLMResponse:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            system_parts: list[str] = [ZERO_EMOJI_SYSTEM_PROMPT]
            converted: list[dict[str, Any]] = []
            for message in messages:
                if message.role == "system":
                    system_parts.append(message.content)
                else:
                    role = "user" if message.role == "user" else "assistant"
                    converted.append({"role": role, "content": message.content})

            response = await client.messages.create(
                model=self.model,
                max_tokens=1024,
                system="\n".join(part for part in system_parts if part),
                messages=converted or [{"role": "user", "content": ""}],  # type: ignore[arg-type]
            )
            raw_text = ""
            for block in getattr(response, "content", []) or []:
                if getattr(block, "type", None) == "text":
                    raw_text += getattr(block, "text", "")
            return LLMResponse(text=sanitize_no_emoji(raw_text))
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.error("Exception calling Anthropic: %s", exc)
            raise LLMProviderError("Anthropic request failed") from exc

    async def stream_response(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        res = await self.generate_response(messages, temperature)
        words = res.text.split(" ")
        for word in words:
            yield word + " "


async def verify_llm_configuration() -> dict[str, Any]:
    """Make a minimal provider request and report non-secret diagnostics."""
    client = get_llm_client()
    response = await client.generate_response(
        [LLMMessage(role="user", content="Reply with OK only.")]
    )
    return {
        "provider": client.provider_name,
        "model": client.model_name,
        "verified": bool((response.text or "").strip()),
    }


def get_llm_client() -> LLMClient:
    """Returns the appropriate LLMClient based on environment configuration.

    A provider that requires credentials raises ``LLMConfigurationError`` when
    those credentials are absent, so missing configuration is reported clearly
    instead of silently falling back to the mock client.
    """
    provider = str(getattr(settings, "LLM_PROVIDER", "fake") or "fake").strip().lower()
    model = str(getattr(settings, "LLM_MODEL", "") or "").strip()

    if provider in {"fake", "mock", "offline"}:
        return FakeLLMClient()

    if provider == "gemini":
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key or not str(api_key).strip():
            raise LLMConfigurationError(
                "LLM_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not configured. "
                "Set GEMINI_API_KEY in apps/api/.env or set LLM_PROVIDER=fake."
            )
        if model and not model.lower().startswith("gemini"):
            raise LLMConfigurationError(
                "A Claude model ID cannot be used with the Gemini provider. "
                "Set LLM_MODEL to a Gemini model or leave it empty."
            )
        return GeminiLLMClient(
            api_key=str(api_key).strip(),
            model=model or "gemini-2.5-flash",
        )

    if provider in {"anthropic", "claude"}:
        api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
        if not api_key or not str(api_key).strip():
            raise LLMConfigurationError(
                "LLM_PROVIDER is set to 'anthropic' but ANTHROPIC_API_KEY is not configured. "
                "Set ANTHROPIC_API_KEY in apps/api/.env or set LLM_PROVIDER=fake."
            )
        if model and not model.lower().startswith("claude"):
            raise LLMConfigurationError(
                "An Anthropic provider requires a Claude model ID. "
                "Set LLM_MODEL to a Claude model or leave it empty."
            )
        return AnthropicLLMClient(
            api_key=str(api_key).strip(),
            model=model or "claude-3-5-sonnet-20241022",
        )

    raise LLMConfigurationError(
        f"Unsupported LLM_PROVIDER {provider!r}. Use 'fake', 'gemini', or 'anthropic'."
    )
