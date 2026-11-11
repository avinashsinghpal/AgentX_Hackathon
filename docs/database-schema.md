# SellerResolve Database Schema

PostgreSQL is the runtime database. SQLite remains supported for tests and
throwaway local runs. The schema is created exclusively by Alembic
(`alembic upgrade head`); the application never calls `create_all` outside tests.

## 1. Entity relationship diagram

```mermaid
erDiagram
    users ||--o| buyers : "buyer profile"
    users ||--o| sellers : "seller profile"
    sellers ||--|| seller_operations : "operations"
    sellers ||--o{ seller_policies : "versions"
    sellers ||--o{ orders : "sells"
    buyers ||--o{ orders : "places"
    orders ||--o{ order_items : "contains"
    orders ||--o{ shipments : "fulfilled by"
    shipments ||--o{ tracking_events : "history"
    orders ||--o{ cases : "claimed in"
    cases ||--o{ case_messages : "conversation"
    cases ||--o{ policy_evaluations : "evaluated by"
    cases ||--o{ approval_requests : "escalates"
    cases ||--o{ actions : "executes"
    seller_policies ||--o{ policy_evaluations : "policy version"
    policy_evaluations ||--o{ approval_requests : "evidence"
    approval_requests ||--o{ actions : "authorizes"
    actions ||--o{ action_verifications : "verified by"
    users ||--o{ file_uploads : "uploads"
    cases ||--o{ file_uploads : "evidence"
    sellers ||--o{ seller_customer_links : "invites"
    buyers ||--o{ seller_customer_links : "accepts"
    sellers ||--o{ audit_logs : "chained events"
    audit_chain_state ||--|| audit_logs : "chain head"

    orders {
        string id PK
        string seller_id FK
        string buyer_id FK
        string order_number
        int total_amount "minor units"
        string currency
        json items "legacy snapshot"
    }
    order_items {
        string id PK
        string order_id FK
        string sku
        string title
        int quantity
        int unit_price_minor
        bool returnable
        string category
    }
    shipments {
        string id PK
        string order_id FK
        string status
        datetime promised_delivery_date
        datetime actual_delivery_date
        json tracking_events "legacy snapshot"
    }
    tracking_events {
        string id PK
        string shipment_id FK
        datetime event_timestamp
        string status
        string provider_event_id
    }
    seller_policies {
        string id PK
        string seller_id FK
        int version "unique per seller"
        bool is_active "one active per seller"
        text policy_yaml "canonical YAML"
        json parsed_rules "validated snapshot"
        string currency "ISO-4217"
        string content_sha256
        string source "structured | yaml | legacy"
        string published_by_user_id FK
        datetime activated_at
    }
    cases {
        string id PK
        string seller_id FK
        string buyer_id FK
        string order_id FK
        string status
        string decision "UI badge"
        string issue_category
        string resolution_type
    }
    policy_evaluations {
        string id PK
        string case_id FK
        string seller_policy_id FK
        int policy_version
        string decision
        string reason_code
        json evaluation_result
        datetime evaluated_at
    }
    approval_requests {
        string id PK
        string case_id FK
        string seller_id FK
        string policy_evaluation_id FK
        string action_id
        int requested_amount_minor
        string status
        datetime expires_at
    }
    actions {
        string id PK
        string case_id FK
        string order_id FK
        string seller_id FK
        string action_type
        int amount_minor
        string status
        string idempotency_key
        string external_reference
        string approval_id
    }
    action_verifications {
        string id PK
        string action_id FK
        string verification_status
        int verification_attempt
        string provider_reference
        datetime verified_at
    }
    audit_logs {
        string id PK
        string seller_id
        string chain_key
        int sequence
        string prev_hash
        string current_hash
        json payload
    }
```

## 2. Authoritative data vs compatibility snapshots

| Concern | Authoritative | Compatibility projection |
| --- | --- | --- |
| Order lines | `order_items` | `orders.items` (read-only JSON snapshot) |
| Tracking history | `tracking_events` | `shipments.tracking_events` (read-only JSON snapshot) |
| Case evidence | `file_uploads.case_id` | `cases.evidence_urls` |
| Policy decision | `cases.decision` (UI badge) + `policy_evaluations` (audit log) | `cases.outcome_details` |
| Execution | `actions` + `action_verifications` | `cases.outcome_details`, order payment status |

`orders.items` and `shipments.tracking_events` are written **only** by
`app/services/orders.py` (`sync_order_items`, `sync_tracking_events`), which keeps
the snapshot consistent with the rows. Readers prefer the normalized rows and
fall back to the snapshot for data written before the refactor.

## 3. Integrity constraints

| Constraint | Purpose |
| --- | --- |
| `uq_orders_seller_order_number (seller_id, order_number)` | Order numbers are unique per tenant, not globally. |
| `uq_orders_id_seller_id (id, seller_id)` | Parent key for the composite case foreign key. |
| `fk_cases_seller_order (cases.seller_id, cases.order_id) -> orders(seller_id, id)` | A case can never point at another seller's order. |
| `uq_seller_policies_seller_version (seller_id, version)` | Policy versions are unambiguous. |
| `uq_seller_policies_one_active` (partial, `WHERE is_active`) | At most one active policy per seller. |
| `uq_actions_seller_idempotency (seller_id, idempotency_key)` | A retried operation cannot create a second action. |
| `uq_tracking_events_shipment_provider_event` (partial) | Provider events are unique per shipment when an id is present. |
| `ck_order_items_quantity_positive`, `ck_actions_amount_non_negative` | Amount/quantity sanity at the storage layer. |
| `uq_audit_logs_chain_sequence (chain_key, sequence)` | One audit sequence number per chain. |

Buyer/order consistency (`cases.buyer_id` matches `orders.buyer_id`) is enforced in
the policy evaluator (`BUYER_OWNERSHIP_MISMATCH`) rather than by a composite
foreign key, because orders may be unclaimed (`orders.buyer_id IS NULL`) before a
buyer links them.

## 4. Money and time

- All persisted amounts are integer **minor units** (`total_amount`,
  `unit_price_minor`, `amount_minor`, `requested_amount_minor`).
- Seller policy documents keep their documented **major-unit** values
  (`auto_approve_up_to: 500`) and an explicit `seller_policies.currency`; the
  engine converts exactly once at its boundary (`app.schemas.policy.to_minor_units`,
  `paise = rupees * 100`) and the API returns the derived `monetary_minor`
  snapshot for previews and reviews.
- A published policy row stores canonical YAML, the validated `parsed_rules`
  snapshot, the row `version`, `currency`, `content_sha256`, `source` and
  `published_by_user_id`. Content columns are immutable; only `is_active` may
  change when the next version is activated.
- All timestamps are timezone-aware UTC (`DateTime(timezone=True)`).

## 5. Audit chain

- Each seller has its own SHA-256 chain: `chain_key = seller_id`; legacy/global
  rows use `__global__`.
- `audit_chain_state` stores the head (`last_hash`, `last_sequence`) and is locked
  with `SELECT ... FOR UPDATE` while appending, which serializes concurrent writes
  per seller.
- Appends are part of the caller's transaction (`log_action(..., commit=False)`),
  so a failed business transaction does not leave a "successful" audit entry.
- Pre-existing rows keep their stored hashes and payloads; the migration only adds
  `chain_key`/`sequence` metadata and rebuilds `audit_chain_state`.

## 6. Migration history

| Revision | Purpose |
| --- | --- |
| `73fa33a3a744` | Baseline (users/audit log). Never rewritten. |
| `3d74bdde4fe4` | Core domain tables. Never rewritten. |
| `9a1f0b6c4d21` | Normalized order/tracking tables, policy evaluations, actions, verification, audit chain metadata, integrity constraints, backfills. |
| `c4b7e2d9a1f3` | Policy publication metadata: `currency`, `content_sha256`, `source`, `published_by_user_id`; backfills checksums and currency for existing versions. |

The incremental revisions are reversible. Downgrading `9a1f0b6c4d21` drops the
normalized/action tables (execution and evaluation history cannot be reconstructed)
but preserves the legacy JSON snapshots, so the pre-migration API shape still
works. Downgrading `c4b7e2d9a1f3` drops only publication metadata; policy documents
and versions are untouched.
