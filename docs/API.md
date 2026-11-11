# SellerResolve REST API Specification

**Project:** SellerResolve (Team "Break The Bug", AgentX Hackathon 2026, PS-04)  
**Version:** 0.1.0  
**Base URL:** `http://localhost:8000/api/v1` (Proxied in Next.js via `/api/v1/*`)  
**Standard Envelope:** All errors return `{ "error": { "code": string, "message": string, "details": any }, "request_id": string }`.

---

## 1. Authentication & Identity (`/auth`)

### `POST /auth/register`
Register a new seller or buyer account.
- **Request Body:**
  ```json
  {
    "email": "seller@store.com",
    "password": "SecurePassword123!",
    "full_name": "Store Administrator",
    "role": "seller",
    "store_name": "Apex Electronics",
    "store_url": "https://apex.com"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "user": {
      "id": "usr-123",
      "email": "seller@store.com",
      "full_name": "Store Administrator",
      "role": "seller"
    },
    "token": "signed-session-token"
  }
  ```
- **Cookies:** Sets HttpOnly, SameSite=Lax session cookie `sr_session`.

### `POST /auth/login`
Authenticate existing user.
- **Request Body:**
  ```json
  {
    "email": "seller@store.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK):** User payload + session cookie.

### `POST /auth/logout`
Terminates current session and clears cookies.

### `GET /auth/me`
Fetches authenticated user identity and role from session context.

---

## 2. Seller Console Endpoints (`/seller`)

### `GET /seller/onboarding/status`
Returns 4-step onboarding status:
- `connect_store` (completed/pending)
- `configure_operations` (completed/pending)
- `define_policies` (completed/pending)
- `review_and_activate` (completed/pending)

### `POST /seller/onboarding/step`
Updates completion status for a given onboarding step.

### `POST /seller/onboarding/activate`
Activates merchant account for autonomous operations once all steps are completed.

### `GET /seller/operations` & `PUT /seller/operations`
Fetch and update operational parameters:
- `fulfillment_sla_hours`: int (e.g. 24)
- `default_carrier`: string (e.g. "BlueDart")
- `serviceable_pincodes`: list[string]
- `warehouse_address`: object

### Seller policy configuration

Policies are edited in the Seller Console as a structured document, validated by
`PolicySchema`, rendered into canonical YAML by the backend, and published as an
immutable per-seller version. Monetary inputs are integer rupees with an explicit
`currency`; the server converts them exactly once into integer paise
(`paise = rupees * 100`) and returns the minor-unit snapshot as `monetary_minor`.
See [Policy Engine Schema](policy-schema.md) for every field and invariant.

All endpoints require a seller session and are scoped to the authenticated
seller. Errors use the standard envelope: `{"error": {"code", "message", "request_id", "details?"}}`.

### `GET /seller/policies/active`
Returns the active policy, or a baseline template when nothing is published.

```json
{
  "has_policy": true,
  "valid": true,
  "id": "...",
  "version": 2,
  "next_version": 3,
  "currency": "INR",
  "policy_yaml": "version: 2\ncurrency: INR\n...",
  "config": { "version": 2, "currency": "INR", "returns": {}, "refunds": {}, "delays": {}, "damage_claims": {}, "fraud_checks": {} },
  "parsed_rules": { "version": 2, "currency": "INR", "returns": {} },
  "monetary_minor": { "currency": "INR", "minor_unit_exponent": 2, "refund_auto_approve_ceiling_minor": 200000, "...": "..." },
  "activated_at": "2026-11-10T10:00:00Z",
  "created_at": "2026-11-10T10:00:00Z",
  "source": "structured",
  "content_sha256": "..."
}
```

### `GET /seller/policies/history`
Lists every version, newest first, with currency, publication/activation times,
source, checksum, return window and refund ceiling (major and minor units).

### `GET /seller/policies/versions/{version}`
Returns one immutable version as the same document shape as `/active`. Another
seller's version returns `404`.

### `POST /seller/policies/validate-config`
Validates structured JSON against `PolicySchema`. Unknown, missing or
contradictory fields return `422` with field paths in `error.details`.

```json
{ "config": { "version": 1, "currency": "INR", "returns": {}, "refunds": {}, "delays": {}, "damage_claims": {}, "fraud_checks": {} } }
```

### `POST /seller/policies/preview`
Validates the structured config and returns the canonical YAML without
publishing, plus `monetary_minor` and non-blocking `warnings`. A policy whose
currency differs from the store currency, or whose two approval ceilings
disagree, returns `400`.

```json
{ "config": { "version": 1, "currency": "INR", "returns": {}, "refunds": {}, "delays": {}, "damage_claims": {}, "fraud_checks": {} } }
```

### `POST /seller/policies/validate`
Validates manually edited YAML with the same schema. Invalid input returns
`200 { "valid": false, "error": "..." }`; valid input returns the canonical YAML,
normalized `config` and `monetary_minor`.

```json
{ "policy_yaml": "version: 1\ncurrency: INR\nreturns:\n  window_days: 14\n..." }
```

### `POST /seller/policies/publish`
Publishes a new immutable version. Exactly one of `config` or `policy_yaml` is
required, and `confirm` must be `true`; otherwise the request is rejected.
`expected_active_version` (`0` when no policy exists) rejects a stale edit with
`409` instead of publishing on top of someone else's change.

```json
{
  "config": { "version": 1, "currency": "INR", "returns": {}, "refunds": {}, "delays": {}, "damage_claims": {}, "fraud_checks": {} },
  "confirm": true,
  "expected_active_version": 2
}
```

Response (`201`): `success`, `id`, `version`, `previous_version`, `currency`,
`policy_yaml`, `config`, `parsed_rules`, `monetary_minor`, `activated_at`,
`source` and `content_sha256`.

### `POST /seller/policies` (deprecated)
Backward-compatible raw-YAML publication. Body requires `policy_yaml` and
`confirm: true`; it delegates to the same publication service as `/publish`.

### `GET /seller/approvals`
List pending human-in-the-loop escalations with case context and requested actions.
Each item includes `requested_amount_minor`, `currency`, `policy_evaluation_id`,
`expires_at`, the case summary and the order line items.

### `POST /seller/approvals/{id}/decide`
Submit a decision for a pending escalation:
- **Request Body:**
  ```json
  {
    "decision": "approved",
    "seller_notes": "Damage photo verified. Authorized replacement."
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "approval_id": "…",
    "status": "approved",
    "executed": true,
    "action_id": "…",
    "failure_reason": null,
    "case_status": "resolved",
    "case_decision": "executed"
  }
  ```
  Approval authorizes execution; it is not proof of execution. `executed` is only
  `true` after the provider operation was verified. A verified failure returns
  `executed: false` with `failure_reason` and leaves the case unresolved. Repeated
  decisions return HTTP 400, expired requests are marked `expired`, and another
  seller's request returns HTTP 404.

### `GET /seller/customers/invites` & `POST /seller/customers/invites`
List and generate customer invitation tokens for store onboarding.

### `POST /seller/demo-seed`
Seeds test orders (`ORD-1001` through `ORD-1004`) for hackathon scenario evaluation.

### `GET /seller/audit`
Paginated audit trail records with before/after state diffs and hash chain links.

### `GET /seller/audit/verify`
Mathematically verifies SHA-256 hash chaining across all audit events for the merchant.
- **Response (200 OK):**
  ```json
  {
    "is_valid": true,
    "total_records": 12,
    "tampered_at": null
  }
  ```

### `GET /seller/audit/export`
Streams raw CSV export of all cryptographic audit log events.

---

## 3. Buyer Portal Endpoints (`/buyer`)

### `GET /sellers/directory`
Public directory of active, registered sellers.

### `GET /invites/{token}` & `POST /invites/{token}/accept`
Validate and accept merchant store invites.

### `GET /buyer/orders`
List orders belonging to the authenticated buyer across connected sellers.

### `POST /buyer/orders/link`
Manually link an unassociated order to the buyer profile via order number and billing phone/email.

### `POST /buyer/cases`
File a new complaint or claim against an order.
- **Request Body:**
  ```json
  {
    "order_id": "ord-1001",
    "issue_category": "return",
    "customer_narrative": "Package unopened, requesting return label.",
    "evidence_urls": []
  }
  ```

### `GET /buyer/cases`
List all complaints raised by the authenticated buyer.

### `GET /buyer/cases/{case_id}`
Returns full Resolution Room details: case status, order record, shipment status, messages, tool call traces, and decision badge.

---

## 4. Autonomous Agent Chat Endpoints

### `POST /buyer/cases/{case_id}/chat`
Sends a customer conversational turn to the autonomous resolution engine.
- **Request Body:**
  ```json
  {
    "message": "I would like to return the wireless earbuds."
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "id": "msg-99",
    "sender_role": "agent",
    "message": "I have investigated your order record and verified that your purchase was delivered 5 days ago...",
    "decision_badge": "executed",
    "tool_calls": [
      {
        "tool_name": "lookup_order",
        "tool_args": { "order_number": "ORD-1001" },
        "outcome": "Retrieved order status: delivered, Amount: $45.00",
        "timestamp": "2026-11-07T13:30:00Z"
      },
      {
        "tool_name": "evaluate_policy_rules",
        "tool_args": { "category": "return" },
        "outcome": "Eligible: within 14-day window and under $50 ceiling",
        "timestamp": "2026-11-07T13:30:01Z"
      },
      {
        "tool_name": "verify_action_outcome",
        "tool_args": { "action": "approve_return" },
        "outcome": "Return label RET-99214 generated",
        "timestamp": "2026-11-07T13:30:02Z"
      }
    ],
    "created_at": "2026-11-07T13:30:02Z"
  }
  ```

### `GET /buyer/cases/{case_id}/chat/stream`
Server-Sent Events (SSE) stream delivering real-time agent investigation tokens and lifecycle state events.

---

## 5. File Uploads (`/uploads`)

### `POST /uploads`
Multipart upload (image/PDF evidence). If `case_id` is supplied, the caller must
own that case (buyer of the case or its seller); otherwise the API returns 403.
Downloads are authorized the same way: uploader, case buyer or case seller only.
Upload photographic evidence for damage claims.
- **Validation:** Enforces 5MB size limit and validates magic byte signatures (`image/jpeg`, `image/png`, `image/webp`).
- **Response (200 OK):**
  ```json
  {
    "file_url": "/uploads/proof-99.png",
    "filename": "proof-99.png",
    "mime_type": "image/png",
    "size_bytes": 1048576
  }
  ```

