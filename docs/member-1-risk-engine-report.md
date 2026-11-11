# Member 1: Risk Engine Implementation and Policy Boundary Enforcement

## Existing Implementation Discovered

- Policy authority already lived in `app/services/policy/`, with:
  - `PolicyEngine` for deterministic eligibility, financial calculations, ceilings,
    refund/compensation limits and approval requirements.
  - `PolicyEvaluationService` for trusted DB loading and persistence.
  - `EvaluationResult` / `CheckResult` as the policy result contract.
- Seller-configured fraud threshold already existed as
  `FraudChecksPolicy.max_refunds_per_buyer_per_30_days`.
- Buyer refund history was already computed in
  `app/services/policy/evaluator.py::buyer_refund_count`.
- Order shipping addresses and buyer default shipping addresses were already
  stored as trusted JSON records.
- Evidence uploads were already associated with cases through `FileUpload`.
- Resolution orchestration already used `ResolutionService`, which consumes policy
  evaluation and executes/verifies actions.

No separate risk engine existed before this change.

## Files Changed

New risk package:

- `apps/api/app/services/risk/__init__.py`
- `apps/api/app/services/risk/result.py`
- `apps/api/app/services/risk/schemas.py`
- `apps/api/app/services/risk/engine.py`
- `apps/api/app/services/risk/evaluator.py`
- `apps/api/app/services/risk_engine.py` (compatibility shim)

Integration:

- `apps/api/app/services/resolution.py`
  - Added optional `risk_evaluation_service`.
  - Evaluates risk separately before policy evaluation.
  - Stores `risk_evaluation` on `DecisionOutcome` and `ResolutionOutcome`.
  - Records risk flags and data sufficiency in rejected-case outcome details.
  - Policy decision remains authoritative for eligibility, amounts and actions.

Tests:

- `apps/api/tests/test_risk_engine.py`

## Risk Checks Implemented

1. Refund frequency
   - Uses `max_refunds_per_buyer_per_30_days` from seller policy configuration.
   - Flags `HIGH_REFUND_FREQUENCY` only when the buyer count strictly exceeds the
     configured maximum.
   - No separate hardcoded threshold is introduced.

2. Claim frequency
   - Intentionally disabled.
   - The refund-frequency field is not reused for claim frequency.

3. Duplicate evidence
   - Detects exact SHA-256 matches between current evidence and evidence from
     previous claims.
   - Flag: `DUPLICATE_EVIDENCE`.
   - Treated as a risk indicator, not proof of fraud.

4. Address inconsistency
   - Compares trusted order shipping and buyer default shipping records.
   - Flags `ADDRESS_INCONSISTENCY` only when both records are available and a
     genuine conflicting field exists.

5. Missing customer history
   - Returns `insufficient_data` when no reliable history is available.
   - Does not classify the customer as high risk.

Removed from risk scope:

- Refund-value ratio calculations.
- High-value claim calculations.
- Any financial amount calculation.

## Risk Result Contract

Implemented `RiskResult`:

```json
{
  "risk_engine_version": "1.0.0",
  "flags": [
    {
      "code": "DUPLICATE_EVIDENCE",
      "severity": "high",
      "explanation": "Evidence hash matches a previous claim."
    }
  ],
  "data_sufficiency": "sufficient",
  "evaluated_at": "timestamp"
}
```

Properties:

- Pydantic model with `extra="forbid"`.
- Machine-readable flag codes.
- Explanation for every flag.
- Severity describes the finding, not the resolution.
- `data_sufficiency` supports `sufficient`, `partial` and `insufficient_data`.
- Includes risk engine version and evaluation timestamp.
- Contains no eligibility, financial, approval or action fields.

## Policy Boundary Enforcement

- `PolicyEngine` remains the sole authority for:
  - eligibility
  - financial calculations
  - refund and compensation limits
  - seller policy conditions
  - approval requirements derived from policy
- Risk flags do not override policy decisions.
- Risk flags do not deny claims or authorize financial actions.
- The existing orchestrator consumes both policy and risk results.
- Risk evaluation failures propagate instead of being silently ignored.

## Integration

- `ResolutionService` now constructs and uses `RiskEvaluationService`.
- Risk evaluation is performed separately from policy evaluation.
- Policy evaluation and persistence behavior are unchanged.
- Existing action authorization, execution, verification and audit mechanisms are
  preserved.
- No second orchestrator or duplicate policy engine was introduced.

## Tests Executed and Results

Risk unit tests:

- Command: `pytest tests/test_risk_engine.py -q`
- Result: `8 passed`

Full backend suite:

- Command: `pytest -q`
- Result: `110 passed, 4 skipped`

PostgreSQL-backed suite:

- Command: `TEST_DATABASE_URL=... pytest -q`
- Result: `114 passed`

Static checks:

- `ruff check .`: passed
- `mypy app`: passed, 83 source files

Risk tests cover:

- Refund frequency threshold boundaries.
- Claim frequency remaining disabled.
- Exact duplicate SHA-256 evidence detection.
- Address comparison with missing and conflicting data.
- Missing customer history and data sufficiency.
- Risk result serialization and forbidden-field contract.
- Risk engine absence of money/eligibility fields.

## Remaining Limitations or Decisions Requiring Human Approval

- Risk evaluation is advisory in the current integration: it does not escalate or
  deny claims by itself, preserving policy authority. A future decision is needed
  if high-risk flags should trigger approval escalation.
- Evidence hashing reads files from local storage during risk evaluation; missing
  files are skipped rather than failing the whole evaluation.
- Partial data sufficiency is supported by the contract but is not currently
  emitted by the engine; only sufficient/insufficient_data are used.
- No database schema changes were made. If durable risk history is required, a
  future migration and explicit approval would be needed.