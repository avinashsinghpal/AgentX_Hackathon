# SellerResolve Operations Runbook

## 1. Quick Start (Development)

### Prerequisites
- Node.js 22+ with `pnpm`
- Python 3.12+ (or compatible 3.14+)

### Setup
```bash
# 1. Clone & environment
cp .env.example .env

# 2. Web dependencies
cd apps/web && pnpm install

# 3. Backend environment
cd apps/api
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/alembic upgrade head
```

### Running Locally
```powershell
# In PowerShell:
.\run.ps1 dev
# Or using make:
make dev
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Reference Template: `http://localhost:3001`

---

## 2. Quality Assurance Checks

```powershell
# Check for forbidden emojis:
node scripts/check-no-emoji.js

# Check for external asset host URLs:
node scripts/check-no-external-assets.js

# Check legal placeholders:
node scripts/check-legal-placeholders.js

# Frontend checks:
cd apps/web
pnpm run lint
pnpm run build

# Backend checks:
cd apps/api
.venv/Scripts/ruff.exe check .
.venv/Scripts/mypy.exe app
.venv/Scripts/python -m pytest tests -q
.venv/Scripts/python ../../scripts/run-e2e-scenarios.py
```

---

## 3. Database Operations (PostgreSQL)

### Start the database
```bash
docker compose up -d postgres
docker compose ps postgres          # must report (healthy)
docker port sellerresolve-postgres  # verify the host port mapping
```
If port 5432 is already taken by a local PostgreSQL install, change the compose
mapping to `"5433:5432"` and point `DATABASE_URL` at port 5433. Check what you are
actually connected to before running migrations:
```bash
cd apps/api
.venv/Scripts/python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### Apply migrations
```bash
cd apps/api
.venv/Scripts/alembic upgrade head
.venv/Scripts/alembic current
```
`alembic upgrade head` is the only supported way to create or change the schema.
`create_all` is used by tests only.

Verify the migrated schema matches the models (should print "No new upgrade
operations detected"):
```bash
.venv/Scripts/alembic check
```

### Roll back one revision
```bash
.venv/Scripts/alembic downgrade -1
```
The normalizer revision drops `order_items`, `tracking_events`,
`policy_evaluations`, `actions`, `action_verifications` and the audit-chain
metadata. Legacy JSON snapshots are preserved, but execution/evaluation history is
lost: take a backup first. Downgrading `c4b7e2d9a1f3` drops only the policy
publication metadata (currency/checksum/source/publisher); policy documents and
versions are untouched.

### Back up and restore
```bash
docker compose exec postgres pg_dump -U sellerresolve sellerresolve > backup.sql
docker compose exec -T postgres psql -U sellerresolve sellerresolve < backup.sql
```

### Copy an existing SQLite database
```bash
cd apps/api
# 1. migrate the empty PostgreSQL target
.venv/Scripts/alembic upgrade head
# 2. dry run, then copy
.venv/Scripts/python ../../scripts/migrate_sqlite_to_postgres.py --sqlite ./sellerresolve.db --dry-run
.venv/Scripts/python ../../scripts/migrate_sqlite_to_postgres.py --sqlite ./sellerresolve.db
```
The script refuses a non-empty target (use `--truncate-target` deliberately),
preserves primary keys, normalizes order items/tracking events from legacy JSON,
rebuilds `audit_chain_state`, and verifies row counts. It never creates the schema.

### Run the test suite against PostgreSQL
Create the schema once, then point the tests at it:
```bash
cd apps/api
.venv/Scripts/python -c "from sqlalchemy import create_engine, text; e=create_engine('postgresql+psycopg://sellerresolve:<POSTGRES_PASSWORD>@localhost:5432/sellerresolve', isolation_level='AUTOCOMMIT'); c=e.connect(); c.execute(text('CREATE SCHEMA IF NOT EXISTS sellerresolve_test')); c.commit()"

export TEST_DATABASE_URL="postgresql+psycopg://sellerresolve:<POSTGRES_PASSWORD>@localhost:5432/sellerresolve?options=-csearch_path%3Dsellerresolve_test"
.venv/Scripts/python -m pytest tests -q
```
The suite drops and recreates every table in that schema. Never point
`TEST_DATABASE_URL` at a database whose data you need.

### Inspect policy publications
Each seller must have at most one active version; every version is immutable.
```bash
docker compose exec postgres psql -U sellerresolve sellerresolve -c "\
SELECT seller_id, version, is_active, currency, source, content_sha256,
       activated_at
FROM seller_policies
ORDER BY seller_id, version DESC;"
```
If a seller reports that a policy change did not apply, confirm the new row is
`is_active` and that `policy_evaluations.seller_policy_id` references it. A
`409` from `POST /seller/policies/publish` means another version was published
while the console was open; reload the active policy and confirm again.

### Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'psycopg'` | `pip install "psycopg[binary]"` (already in `requirements.txt`). |
| `permission denied to create database` | The app role is not a superuser. Use a dedicated schema (above) or a pre-created database. |
| `Cannot enforce unique (seller_id, order_number)` | Duplicate order numbers exist; resolve them before migrating. The migration fails loudly rather than deleting data. |
| `Cannot enforce the case -> order seller constraint` | A case references another seller's order; fix the data before migrating. |
| Audit verification fails after a manual edit | Expected: the chain is tamper-evident. Restore from backup; do not rewrite hashes. |
| Policy publish returns `400 Explicit confirmation is required` | The console must send `"confirm": true` after the seller confirms the review dialog. |
| Policy preview/publish returns `400 ... does not match the store currency` | The document currency must equal the seller's store currency; amounts are never compared across currencies. |
| Policy validation returns `422` / `400` naming a field | The field is unknown, out of range or contradictory (for example both refund ceilings differ). The field path is in `error.details`. |
| Policy publish returns `409` | `expected_active_version` is stale. Reload and publish again; the new version is intentionally not created. |

---

## 4. Production Deployment via Docker
```bash
docker compose build
docker compose up -d
```


## Fake LLM end-to-end testing

1. Set `LLM_PROVIDER=fake` in `apps/api/.env`.
2. Start PostgreSQL and apply migrations (`run.ps1 db-up`, `run.ps1 db-migrate`).
3. Seed demo users (`run.ps1 seed`) and demo orders from the seller console.
4. Sign in with one of the seeded demo accounts:
   - Seller: `seller@store.com` / `Password123!`
   - Customer: `buyer@example.com` / `Password123!`
   - These accounts are available only in the database seeded by `run.ps1 seed`. A separate test schema or API instance may not contain them.
5. Create a buyer case or use a seeded order.
6. Submit a buyer message and verify the deterministic decision badge.
7. Inspect investigation telemetry and the audit chain for the case.
8. Confirm no external LLM credentials are required.

Fake-provider testing exercises deterministic policy, approval, action, verification and audit behavior. Real Gemini testing requires `LLM_PROVIDER=gemini` and `GEMINI_API_KEY`, and uses `verify-llm` to report provider/model/verification without exposing credentials.
