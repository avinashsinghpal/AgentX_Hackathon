# SellerResolve Policy Engine Schema

## 1. Overview

Seller policies are authored in the Seller Console as a structured form, submitted
as typed JSON, validated against a Pydantic v2 schema, and rendered into canonical
YAML. A seller may optionally edit that YAML directly; the same schema validates
both paths. Publication creates an immutable version, and
`app/services/policy/engine.py` evaluates claims deterministically against exactly
the active version. No LLM output is accepted as an input to a decision.

Every evaluation is appended to `policy_evaluations` (append-only) with the stored
policy row id, the row version and every guard result. A case keeps the current UI
badge in `cases.decision`; the evaluation log is the audit trail behind it.

## 2. Canonical schema

```yaml
version: 1
currency: INR

returns:
  window_days: 7                            # days after delivery (inclusive)
  non_returnable_categories: [innerwear, perishables]
  eligible_categories: null                 # null = all categories
  return_shipping_paid_by: seller           # seller | buyer
  auto_generate_shipping_label: true
  require_original_packaging: false

refunds:
  auto_approve_up_to: 500                   # major units (INR)
  require_seller_approval_above: 500        # same boundary; must equal the above
  cod_refund_method: store_credit           # store_credit | bank_transfer
  instant_refund_without_return_threshold: 500
  restocking_fee_percentage: 0
  processing_sla_days: 2

delays:
  notify_after_days_late: 2                 # minimum days late to act
  allow_return_if_late_days_at_least: 3
  compensation_per_day_late: 0              # major units; 0 disables compensation
  max_delay_compensation: 0                 # major units cap

damage_claims:
  require_photo: true
  report_within_days: 2
  auto_replacement_under_amount: 1500
  require_warehouse_inspection_above: 5000

fraud_checks:
  max_refunds_per_buyer_per_30_days: 3
  require_seller_approval_if_exceeded: true
  require_manual_review_for_high_value: false
  high_value_order_threshold: 5000
  block_suspicious_addresses: false
```

`currency` is a three-letter ISO-4217 code and is normalized to uppercase. A
policy can only be published for the seller's store currency; a mismatched
currency is rejected rather than compared against order amounts.

`refunds.auto_approve_up_to` is the autonomous ceiling. The engine escalates
strictly above it. `refunds.require_seller_approval_above` expresses the same
decision boundary: it is inherited from the autonomous ceiling when omitted, and
publication rejects a document where the two disagree, so neither value can be
silently ignored.

## 3. Money units (rupees to paise)

The seller-facing document, the structured JSON API and the YAML editor all use
**integer major units** (`500` means INR 500). Amounts are never fractional: the
schema rejects a float with a fractional part instead of truncating it.

Internally every calculation, stored request amount and approval amount uses
**integer minor units** (paise):

```
paise = rupees * 100
```

- The conversion lives in exactly one place:
  `app.schemas.policy.to_minor_units` (factor
  `MAJOR_UNITS_PER_CURRENCY_UNIT = 100`).
- The engine reads `auto_approve_ceiling_minor`, `compensation_per_day_minor`,
  `max_compensation_minor`, and the other `*_minor` accessors; it never compares a
  major-unit threshold with a minor-unit order total.
- `PolicySchema.monetary_minor()` produces the complete minor-unit snapshot
  (`currency`, `minor_unit_exponent`, refund/delay/damage/fraud thresholds), which
  the preview, validation and active-policy endpoints return as `monetary_minor`.
- Example: a ₹2,000 ceiling is `200000` paise; a ₹50/day delay credit capped at
  ₹250 is `5000` and `25000` paise respectively.
- The seller UI displays rupees; it does not compute minor units. The server
  performs the conversion and the review dialog shows both values
  (`₹2,000` / `200,000 paise`).

## 4. Persistence and publication invariants

`POST /api/v1/seller/policies/publish` creates a new `seller_policies` row:

| Column | Meaning |
| --- | --- |
| `version` | Monotonic per-seller version, allocated under a seller row lock. |
| `policy_yaml` | Canonical YAML rendered from the validated document (`document.version` equals the row version). |
| `parsed_rules` | Canonical validated document snapshot (no legacy aliases). |
| `currency` | Explicit currency of every threshold. |
| `content_sha256` | SHA-256 of the canonical YAML, so a version can be verified. |
| `source` | `structured` (form) or `yaml` (direct edit). |
| `published_by_user_id` | Publishing seller user. |
| `activated_at` / `created_at` | Activation and publication timestamps. |
| `is_active` | Exactly one active row per seller (partial unique index). |

Additional invariants:

- A published version is immutable. An ORM guard rejects changes to its content
  fields; only `is_active` may be flipped, which happens atomically when the next
  version is published.
- Publication requires explicit confirmation (`"confirm": true`). Missing
  confirmation is a `400`, not a silent publish.
- The request may include `expected_active_version` (0 when none). If another
  version was published in the meantime, the API returns `409` so the seller can
  reload instead of overwriting intent.
- The previous active row is deactivated and the new row activated in one
  transaction together with the `policy.published` audit entry. A failure leaves
  the previous policy active.
- The engine loads the active row ordered by version and records its `id` and
  `version` in `policy_evaluations`, so every decision is traceable to the exact
  version that produced it.

## 5. Seller workflow

1. `GET /seller/policies/active` returns the active document, its canonical YAML,
   the structured `config`, `monetary_minor`, activation metadata and the next
   version.
2. The seller edits the structured form. The client holds the complete document,
   so fields without a dedicated input are preserved rather than dropped.
3. `POST /seller/policies/validate-config` validates the typed JSON against
   `PolicySchema` (unknown or contradictory fields produce a `422` with field
   paths).
4. `POST /seller/policies/preview` returns canonical YAML, the normalized config,
   the minor-unit snapshot and non-blocking warnings.
5. Optionally, the seller edits the YAML. `POST /seller/policies/validate` runs
   the same `parse_and_validate_yaml` validation and returns the canonical form.
6. The seller opens the review dialog, which shows the canonical YAML and the
   minor-unit thresholds, and explicitly confirms publication.
7. `POST /seller/policies/publish` creates the new immutable version.

Natural-language policy generation is deliberately out of the mandatory scope. If
it is added later it may only produce a draft, which must pass the same
deterministic validation and explicit confirmation before publication.

## 6. API contracts

| Method & path | Body | Result |
| --- | --- | --- |
| `GET /seller/policies/active` | — | Active (or baseline) document; `has_policy`, `valid`, `version`, `next_version`, `config`, `policy_yaml`, `parsed_rules`, `monetary_minor`, `activated_at`, `source`, `content_sha256`. |
| `GET /seller/policies/history` | — | Versions newest first with currency, timestamps, source, checksum, return window and refund ceiling. |
| `GET /seller/policies/versions/{version}` | — | One immutable version, scoped to the authenticated seller (`404` otherwise). |
| `POST /seller/policies/validate-config` | `{"config": PolicySchema}` | Normalized config and `monetary_minor`; `422` on schema errors. |
| `POST /seller/policies/preview` | `{"config": PolicySchema}` | Canonical `policy_yaml`, config, `monetary_minor`, warnings; `400` for publication-level contradictions. |
| `POST /seller/policies/validate` | `{"policy_yaml": "..."}` | `valid`, `error`, canonical `policy_yaml`, `config`, `monetary_minor`. |
| `POST /seller/policies/publish` | `{"config": ...}` or `{"policy_yaml": "..."}` plus `confirm: true` and optional `expected_active_version` | New version metadata; `400` unconfirmed/invalid, `409` stale version. |
| `POST /seller/policies` | Legacy raw YAML plus `confirm: true` | Deprecated alias of `/publish`; still requires confirmation. |

## 7. Legacy key aliases

Documents written before the canonical field names are still readable. The
validator accepts these aliases and normalizes them into the canonical fields;
new publications store canonical keys only. The Seller Console sends canonical
keys.

| Canonical | Accepted legacy alias |
| --- | --- |
| `refunds.auto_approve_up_to` | `refunds.auto_approve_max_amount` |
| `delays.notify_after_days_late` | `delays.delay_threshold_days`, `delays.auto_credit_after_days` |
| `damage_claims.require_photo` | `damage_claims.photo_evidence_required` |
| `fraud_checks.max_refunds_per_buyer_per_30_days` | `fraud_checks.max_claims_per_buyer_90_days` |

The last alias is a legacy key name only: both map to the same 30-day refund
frequency window the engine actually computes. The console labels the field
"Max refunds per buyer (30 days)" so the name matches the behavior.

Unknown keys are rejected (`extra="forbid"`) rather than discarded. A stored
policy that no longer validates is treated as `POLICY_INVALID` and routed to
manual review rather than silently falling back to defaults.

## 8. Boundary semantics (pinned by tests)

| Rule | Semantics |
| --- | --- |
| Return window | `days_since_delivery <= window_days` is eligible; one day over is `RETURN_WINDOW_EXPIRED`. Exactly at the limit is inside the window. |
| Approval ceiling | `amount_minor <= auto_approve_ceiling_minor` is auto-approved; one minor unit over requires approval. |
| Fraud limit | At most `max_refunds_per_buyer_per_30_days` is allowed; only a count strictly greater escalates. |
| Delay threshold | `days_late >= notify_after_days_late`; below it is `DELAY_THRESHOLD_NOT_MET`. |
| Delay compensation | `min(days_late * per_day, max)`; if the configured maximum is 0, no compensation is authorized (`DELAY_COMPENSATION_NOT_CONFIGURED`). |
| Damage evidence | Photo evidence is required for `damaged` when `require_photo`; missing evidence is `MISSING_DAMAGE_PHOTO`. |
| Currency | Policy currency must equal the store/order currency, otherwise `CURRENCY_MISMATCH` (manual review) or publication rejection. |

## 9. Decisions vs UI badges

| Policy decision | Meaning | UI badge |
| --- | --- | --- |
| `eligible` | Deterministic policy permits an automated action. | `executed` only after verified execution |
| `needs_approval` | A seller decision is required before acting. | `needs_approval` |
| `manual_review` | Inputs are missing/ambiguous (currency, tracking, invalid policy). | `needs_approval` |
| `not_eligible` | Policy forbids the claim. | `not_eligible` |

The engine never returns `executed`. Without approval, `needs_approval` creates an
approval request; approving it authorizes execution, and only a verified provider
outcome sets `cases.decision = executed`.

## 10. Evaluation order

1. Seller status (`active` required).
2. Case/order/buyer ownership and issue category.
3. Duplicate-claim and policy-availability checks.
4. Currency match.
5. Delivery data (for return, damage, defective, wrong/missing item).
6. Return window and damage reporting window.
7. Item returnability.
8. Evidence requirements.
9. Buyer refund-frequency risk.
10. Monetary approval ceiling (and delay compensation for `delay`).
11. Proposed action (`refund`, `wallet_credit`, `return_label`, `reject`,
    `manual_review`).
