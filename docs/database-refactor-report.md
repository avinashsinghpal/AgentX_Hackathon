# Database and Action-Lifecycle Refactor: Final Report

Date: 2026-11-10

## 1. What was implemented

| Area | Status | Evidence |
| --- | --- | --- |
| PostgreSQL as runtime database | Implemented and verified | `DATABASE_URL` defaults to `postgresql+psycopg://…`; Alembic `upgrade head`, `downgrade base`, `upgrade head` and `alembic check` all pass on PostgreSQL 18.6. |
| Docker PostgreSQL service | Implemented, not exercised on this host | `docker-compose.yml` defines `postgres:17` with a healthcheck and named volume. The host's port 5432 is occupied by a native PostgreSQL server, so verification ran against that server (see Limitations). |
| Normalized order items | Implemented and verified | `order_items` table + `app/services/orders.py` sync writer; API payloads unchanged (legacy shape with both major and minor prices). Migration backfills rows from `orders.items`. |
| Normalized tracking events | Implemented and verified | `tracking_events` table, ordered by timestamp, optional unique provider event id; readers fall back to the legacy snapshot. |
| Deterministic policy decision separated from outcome | Implemented and verified | `app/services/policy` returns only `eligible / needs_approval / not_eligible / manual_review`; `executed` is set only after action verification. 16 unit tests pin boundaries. |
| Append-only policy evaluations | Implemented and verified | `policy_evaluations` stores the stored policy row version, all guard results and inputs snapshot; re-evaluating appends, never updates. |
| Approval lifecycle | Implemented and verified | Request / approve / reject / expire, single-use, expiry, cross-seller 404, staleness checks; approval executes and verifies through `ActionService`. |
| Action idempotency | Implemented and verified | Unique `(seller_id, idempotency_key)`, deterministic key, provider-side deduplication. Tests cover repeat execution and retry after timeout with exactly one provider operation. |
| Action verification | Implemented and verified | `actions` + `action_verifications`; a provider response never resolves a case. Unverifiable success leaves the action failed and the case unresolved. |
| Proactive delay monitor | Implemented and verified | Uses the policy engine and action service with an injectable clock; compensation capped by policy, approvals when above the ceiling, no duplicate credit across cycles. |
| Audit hash chain | Implemented and verified | Per-seller chains (`chain_key`, `sequence`), head table locked with `SELECT … FOR UPDATE`, transactional appends; CSV header preserved. |
| Cross-tenant integrity | Implemented and verified | Unique order number per seller, composite `cases(seller_id, order_id) -> orders(seller_id, id)` FK, single active policy index, evidence access scoped to uploader/case buyer/case seller. |
| Seller policy configuration workflow | Implemented and verified | Typed JSON form -> `PolicySchema` -> canonical YAML preview -> optional YAML edit -> explicit confirmation -> immutable version. `PolicyConfigurationService` owns validation, YAML rendering, activation and persistence; endpoints are thin. 8 dedicated tests cover JSON/YAML conversion, invalid input, publication, stale-version conflict, immutability, seller isolation and active-version evaluation. |
| Policy publication metadata | Implemented and verified | Revision `c4b7e2d9a1f3` adds `currency`, `content_sha256`, `source`, `published_by_user_id` with backfill; `alembic check` is clean. ORM guard rejects edits to a published document. |
| Migration tooling | Implemented and verified | New revisions `9a1f0b6c4d21` (normalization) and `c4b7e2d9a1f3` (policy metadata); `scripts/migrate_sqlite_to_postgres.py` copies a legacy SQLite DB, backfills normalized rows and policy metadata, rebuilds the audit head and verifies counts. |
| Documentation | Implemented | `docs/database-schema.md`, `docs/database-refactor-plan.md`, updated `docs/architecture.md`, `docs/API.md`, `docs/policy-schema.md`, `docs/runbook.md`, `README.md`, `.env.example`, `Makefile`, `run.ps1`. |

## 2. Verification actually performed

- `ruff check .` — clean.
- `mypy app` — clean (77 source files).
- `pytest` on SQLite in-memory — **102 passed, 4 skipped** (the 4 skips are the
  PostgreSQL-only schema assertions).
- `pytest` with `TEST_DATABASE_URL` pointing at a dedicated PostgreSQL schema —
  **106 passed** (no skips), including JSONB, composite foreign key, partial unique
  index, audit column and policy publication metadata assertions.
- `ruff check ../../scripts` — clean (the E2E and migration scripts).
- Web: `tsc --noEmit` clean and `next build` succeeds (all routes, including
  `/seller/policies`, compile and prerender).
- `scripts/run-e2e-scenarios.py` — all 4 canonical scenarios plus cryptographic
  audit integrity pass. Scenario 3 now goes through real approval execution
  (`refund` reference recorded, case resolved as `executed`), and scenario 4
  asserts a single verified wallet credit and that a second monitor cycle creates
  no duplicate.
- Alembic on PostgreSQL: `upgrade head`, `downgrade -1`, `upgrade head`, then
  `alembic check` → "No new upgrade operations detected". The earlier full
  `downgrade base` / `upgrade head` round-trip was also exercised.
- Legacy data migration: the repository's pre-refactor `apps/api/sellerresolve.db`
  was copied into a scratch PostgreSQL schema — 5 users, 2 sellers, 8 orders,
  8 backfilled order items, 9 audit rows recopied, 2 audit chain heads rebuilt;
  both copied policy versions received currency `INR`, source `legacy` and a
  64-character checksum. Row counts were verified and both seller chains verified
  cryptographically. The scratch schema was dropped afterwards.
- Seller/buyer flow tests still pass unchanged in behaviour; only the legacy
  `POST /seller/policies` test payloads gained the now-required `confirm: true`.
  The UI badge, approval and `parsed_rules` read contracts are preserved.

## 3. Limitations and honest gaps

1. **Docker PostgreSQL 17 was not the verified server.** The container
   `sellerresolve-postgres` is running and healthy but has no published host port
   in this environment, and the application role is not allowed to create
   databases. All PostgreSQL verification therefore ran against the native
   PostgreSQL 18.6 server listening on `localhost:5432`, using a dedicated
   `sellerresolve_test` schema instead of a separate database. The compose file
   itself was not re-created during verification.
2. **No real provider integrations.** Payment and courier providers remain
   deterministic mocks, as required. Idempotency and verification are proven
   against those mocks, not against a live vendor API.
3. **Concurrency is reasoned and constraint-backed, not stress-tested.** Audit
   head locking and unique idempotency keys are correct by construction, but no
   multi-process load test was run.
4. **SQLite is a supported test/runtime fallback, but Alembic was not executed
   against SQLite.** Tests build SQLite schema via `create_all`; the migration is
   written with batch mode for SQLite but only PostgreSQL was exercised.
5. **Policy documents are major-unit by contract.** This is deliberate (the UI
   says "auto approve up to 500"). The server converts exactly once
   (`paise = rupees * 100`), returns a `monetary_minor` snapshot, and stores the
   explicit currency; any new code persisting policy money must use the same
   boundary helpers rather than dividing minor units itself.
6. **The policy console was type-checked and built, not visually exercised.**
   `tsc --noEmit` and `next build` pass, and the API workflow is covered by
   request-level tests, but no browser session was run to click through the form,
   YAML editor and confirmation dialog. Layout and interaction polish should be
   checked in a running console.
7. **Publication concurrency is lock-backed but not load-tested.** Version
   allocation uses a seller row lock plus the unique/partial indexes; a two-process
   stress test was not run.

## 4. How to reproduce

```bash
cd apps/api
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m mypy app
.venv/Scripts/python ../../scripts/run-e2e-scenarios.py
DATABASE_URL="postgresql+psycopg://…" .venv/Scripts/python -m alembic upgrade head
DATABASE_URL="postgresql+psycopg://…" .venv/Scripts/python -m alembic check

cd ../web
node node_modules/typescript/bin/tsc --noEmit
node node_modules/next/dist/bin/next build
```
