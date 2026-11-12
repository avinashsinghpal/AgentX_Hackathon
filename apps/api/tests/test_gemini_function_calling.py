from __future__ import annotations

from typing import Any

import pytest

from app.services.agent.orchestrator import ResolutionOrchestrator
from app.services.llm.client import (
    GeminiLLMClient,
    LLMConfigurationError,
    LLMMessage,
    _to_gemini_schema,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.status_code = 200
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._responses = _FakeAsyncClient.RESPONSES

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *args: Any) -> bool:
        return False

    async def post(self, url: str, json: dict[str, Any] | None = None) -> _FakeResponse:
        if not self._responses:
            raise RuntimeError("No mocked Gemini response remaining")
        item = self._responses.pop(0)
        return item if isinstance(item, _FakeResponse) else _FakeResponse(item)


@pytest.mark.asyncio
async def test_gemini_multi_step_function_calling_feeds_results_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "lookup_order",
                                    "args": {"order_number": "ORD-1001"},
                                }
                            }
                        ]
                    }
                }
            ]
        },
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_tracking_events",
                                    "args": {"tracking_number": "TRK-1"},
                                }
                            }
                        ]
                    }
                }
            ]
        },
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_buyer_history",
                                    "args": {"buyer_id": "buyer-1"},
                                }
                            }
                        ]
                    }
                }
            ]
        },
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Investigation complete: order, tracking, and buyer history reviewed."}]
                    }
                }
            ]
        },
    ]
    _FakeAsyncClient.RESPONSES = responses
    monkeypatch.setattr("app.services.llm.client.httpx.AsyncClient", _FakeAsyncClient)

    client = GeminiLLMClient(api_key="test-key", model="gemini-test")
    calls: list[tuple[str, dict[str, Any]]] = []

    async def executor(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        calls.append((tool_name, arguments))
        return {"ok": True, "tool": tool_name}

    tools = [
        {"name": "lookup_order", "description": "lookup order", "parameters": {"type": "object"}},
        {"name": "get_tracking_events", "description": "tracking", "parameters": {"type": "object"}},
        {"name": "get_buyer_history", "description": "history", "parameters": {"type": "object"}},
    ]

    result = await client.generate_with_tools(
        [LLMMessage(role="user", content="Investigate case")],
        tools,
        executor,
        max_calls=6,
    )

    assert calls == [
        ("lookup_order", {"order_number": "ORD-1001"}),
        ("get_tracking_events", {"tracking_number": "TRK-1"}),
        ("get_buyer_history", {"buyer_id": "buyer-1"}),
    ]
    assert result == "Investigation complete: order, tracking, and buyer history reviewed."
    assert len(_FakeAsyncClient.RESPONSES) == 0


@pytest.mark.asyncio
async def test_gemini_function_call_budget_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"functionCall": {"name": "lookup_order", "args": {"order_number": "ORD-1"}}},
                            {"functionCall": {"name": "get_tracking_events", "args": {"tracking_number": "TRK-1"}}},
                        ]
                    }
                }
            ]
        },
        {
            "candidates": [
                {"content": {"parts": [{"text": "Budget exhausted; final answer."}]}}
            ]
        },
    ]
    _FakeAsyncClient.RESPONSES = responses
    monkeypatch.setattr("app.services.llm.client.httpx.AsyncClient", _FakeAsyncClient)

    client = GeminiLLMClient(api_key="test-key", model="gemini-test")
    calls: list[str] = []

    async def executor(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        calls.append(tool_name)
        return {"ok": True}

    tools = [
        {"name": "lookup_order", "description": "lookup order", "parameters": {"type": "object"}},
        {"name": "get_tracking_events", "description": "tracking", "parameters": {"type": "object"}},
    ]

    result = await client.generate_with_tools(
        [LLMMessage(role="user", content="Investigate")],
        tools,
        executor,
        max_calls=1,
    )

    assert calls == []
    assert result == "Budget exhausted; final answer."


@pytest.mark.asyncio
async def test_gemini_unknown_tool_is_handled_coherently(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"functionCall": {"name": "delete_everything", "args": {}}}
                        ]
                    }
                }
            ]
        },
        {
            "candidates": [
                {"content": {"parts": [{"text": "I cannot perform that action."}]}}
            ]
        },
    ]
    _FakeAsyncClient.RESPONSES = responses
    monkeypatch.setattr("app.services.llm.client.httpx.AsyncClient", _FakeAsyncClient)

    client = GeminiLLMClient(api_key="test-key", model="gemini-test")
    calls: list[str] = []

    async def executor(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        calls.append(tool_name)
        return {"ok": True}

    result = await client.generate_with_tools(
        [LLMMessage(role="user", content="Do something")],
        [{"name": "lookup_order", "description": "lookup", "parameters": {"type": "object"}}],
        executor,
        max_calls=2,
    )

    assert calls == []
    assert result == "I cannot perform that action."


def test_gemini_tool_schemas_use_provider_supported_fields() -> None:
    declarations = ResolutionOrchestrator().tool_declarations

    lookup_order = next(tool for tool in declarations if tool["name"] == "lookup_order")
    assert _to_gemini_schema(lookup_order["parameters"]) == {
        "type": "OBJECT",
        "properties": {"order_id": {"type": "STRING", "maxLength": 128}},
    }

    for tool in declarations:
        converted = _to_gemini_schema(tool["parameters"])
        assert "additionalProperties" not in converted
        assert converted["type"] == "OBJECT"


def test_gemini_tool_schema_rejects_unsupported_union_types() -> None:
    with pytest.raises(LLMConfigurationError, match="nullable single-type unions"):
        _to_gemini_schema(
            {
                "type": "object",
                "properties": {
                    "value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ]
                    }
                },
            }
        )
