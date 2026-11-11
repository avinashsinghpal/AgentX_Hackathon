# Member 2: Agent Orchestration Implementation

## Files Changed

- `apps/api/app/services/resolution.py`
  - Added high-risk escalation in `ResolutionService.decide`.
  - Added risk flags and data sufficiency to approval-path outcome details.
  - Extended `build_messages` with risk flags, risk data sufficiency and conversation history.
  - Added optional `conversation_history`, `tool_executor` and `max_tool_calls` parameters to `explain`, `resolve_case` and `stream_case`.
  - Added JSON tool-request parsing helper for bounded multi-turn LLM tool calls.
- `apps/api/app/services/agent/orchestrator.py`
  - Extended `ResolutionOrchestrator` with conversation loading, a tool registry and safe tool execution.
  - Added multi-turn LLM tool loop support through `ResolutionService`.
  - Added backward-compatible aliases for common orchestrator method names.
- `apps/api/tests/test_risk_engine.py` (from Member 1 scope) remains unchanged and passing.

## Workflow Implemented

1. Conversation continuity
   - Loads existing `CaseMessage` records and includes recent turns in LLM context.
   - Buyer turns supplied to `process_case_resolution` are included without changing persistence ownership.

2. Multi-turn LLM tool calling
   - Supports strict JSON tool requests: `{"tool": "...", "arguments": {...}}`.
   - Enforces `MAX_TOOL_CALLS = 6`.
   - Tool observations are fed back to the LLM before final response.
   - Tool failures are returned as observations instead of crashing resolution.

3. Safe tool surface
   - `lookup_order`
   - `lookup_shipment`
   - `get_case`
   - `evaluate_policy_rules` (read-only, `persist=False`)
   - `evaluate_risk`
   - `get_conversation_history`
   - `resolve_case` (delegates to authoritative `ResolutionService`)
   - `escalate_to_human` (reuses existing approval service)

4. Structured policy and risk consumption
   - Policy decision remains authoritative for eligibility, amounts, limits and actions.
   - Risk flags are advisory and are now included in LLM context.
   - High-severity risk flags escalate an otherwise eligible case to seller approval.
   - Risk flags do not independently deny claims or execute financial actions.

5. Human escalation
   - Existing policy escalation paths remain active.
   - High-risk findings create or reuse a pending `ApprovalRequest`.
   - Approval authorization and execution remain separated.

6. Error handling and retries
   - LLM failures fall back to deterministic explanations.
   - Tool errors are captured and returned to the LLM.
   - Action execution remains idempotent through existing `ActionService`.

## Tests Executed and Results

- `pytest -q`: `110 passed, 4 skipped`
- PostgreSQL-backed `pytest -q`: `114 passed`
- E2E scenario suite: `4 of 4 scenarios passed`, audit hash chain valid
- `ruff check` on changed files: passed
- `mypy` on changed files: passed

## Remaining Limitations

- Tool calling depends on the LLM emitting the documented JSON shape; natural-language-only models simply produce a final answer.
- Streaming path includes conversation history but does not execute the multi-turn tool loop before token streaming.
- Risk flags are included in LLM context and rejected-case outcome details; broader persisted risk history would require future schema work.
- No new async database layer was introduced; services remain synchronous.