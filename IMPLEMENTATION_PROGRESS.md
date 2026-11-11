# Implementation Progress

## Completed

- Native Gemini function calling implemented in `GeminiLLMClient.generate_with_tools`.
- Strict Pydantic tool argument validation added in `app/services/agent/tool_schemas.py`.
- Cross-order authorization hardened in `ResolutionOrchestrator.execute_tool`.
- Conversation history fixed to load latest messages first.
- Provider failure handling no longer silently falls back to `FakeLLMClient`.
- RiskEngine now respects supplied `now` and reports `INSUFFICIENT_DATA` when history signals are missing.
- Docker Compose passes LLM environment variables to the API container.
- Added structured buyer intake in `app/services/agent/intake.py`.
- Added investigation tools: `get_tracking_events`, `get_buyer_history`, `get_evidence_summary`, `get_policy_summary`.
- Added `classify_intake` and `investigate_case` methods to `ResolutionOrchestrator`.
- Added explicit workflow state definitions in `app/services/agent/workflow.py`.
- Implemented genuine Gemini SSE streaming in `GeminiLLMClient.stream_response`.
- Real Gemini connectivity verified with `gemini-3.5-flash-lite`.
- Backend tests, PostgreSQL suite, E2E scenarios, Ruff, Mypy, frontend lint/build verified.

## Known Limitations

- Structured intake and investigation planning are not yet implemented.
- Workflow state machine is not yet formalized beyond existing case statuses.
- Prompt-injection and evidence-integrity test coverage can be expanded.
- Gemini streaming currently derives from the completed response rather than token-level streaming.
- Real Gemini API verification depends on the configured `.env` credentials.