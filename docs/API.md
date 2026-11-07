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

### `GET /seller/policies/active`
Retrieves currently published, active policy AST and raw YAML.

### `POST /seller/policies`
Validates and publishes a new seller policy version.
- **Request Body:**
  ```json
  {
    "policy_yaml": "returns:\n  window_days: 14\nrefunds:\n  auto_approve_max_amount: 50.00\n..."
  }
  ```

### `GET /seller/approvals`
List all pending human-in-the-loop escalations with case context and requested actions.

### `POST /seller/approvals/{id}/decide`
Submit decision for a pending escalation:
- **Request Body:**
  ```json
  {
    "decision": "approved",
    "seller_notes": "Damage photo verified. Authorized replacement."
  }
  ```

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

