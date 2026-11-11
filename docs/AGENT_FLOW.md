# SellerResolve Agent Flow

## Buyer intake
- Entry: `app/services/agent/intake.py`
- Buyer messages are classified and linked to a seller-owned case.

## Authentication and ownership validation
- `app/api/deps.py`
- `app/services/resolution.py` (`investigate`) validates case/order/seller/buyer ownership.

## Investigation tools
- `app/services/agent/orchestrator.py`
- `app/services/agent/tools.py`
- Read-only tools gather order, shipment, tracking, buyer history, evidence and policy facts.

## Deterministic policy evaluation
- `app/services/policy/engine.py`
- `app/services/policy/evaluator.py`
- `app/services/policies.py`
- Eligibility, amounts, proposed actions and reason codes are deterministic.

## Risk evaluation
- `app/services/risk/evaluator.py`
- `app/services/risk/engine.py`
- Risk flags can require approval or manual review but cannot authorize or change policy amounts.

## Approval
- `app/services/approvals.py`
- Seller approval authorizes execution; stale approvals are cancelled.

## Action execution
- `app/services/actions/service.py`
- `app/services/actions/executor.py`
- `app/services/actions/providers/*`
- Idempotency keys and provider verification gate success.

## Verification
- `app/services/actions/service.py` (`_apply_success`)
- Case and order state change only after verified provider success.

## Audit logging
- `app/services/audit.py`
- Tamper-evident hash chain records all consequential actions.

## LLM responsibilities and restrictions
- `app/services/llm/client.py`
- `app/services/resolution.py`
- LLMs explain verified outcomes only. They never determine policy eligibility, financial amounts, or authorization.
