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
```

---

## 3. Production Deployment via Docker
```bash
docker compose build
docker compose up -d
```

