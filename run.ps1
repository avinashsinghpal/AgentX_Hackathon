param (
    [Parameter(Position=0)]
    [string]$Target = "dev"
)

$ErrorActionPreference = "Stop"

switch ($Target) {
    "dev" {
        Write-Host "Starting SellerResolve development servers..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/api; .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000"
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/web; pnpm run dev -p 3000"
        Write-Host "API running at http://localhost:8000" -ForegroundColor Green
        Write-Host "Web running at http://localhost:3000" -ForegroundColor Green
    }
    "lint" {
        Write-Host "Running code quality checks..." -ForegroundColor Cyan
        node scripts/check-no-emoji.js
        node scripts/check-no-external-assets.js
        node scripts/check-legal-placeholders.js
        Write-Host "`nRunning frontend ESLint..." -ForegroundColor Cyan
        Set-Location apps/web; pnpm run lint; Set-Location ../..
        Write-Host "`nRunning backend Ruff..." -ForegroundColor Cyan
        Set-Location apps/api; .venv/Scripts/ruff.exe check .; Set-Location ../..
        Write-Host "`nRunning backend Mypy..." -ForegroundColor Cyan
        Set-Location apps/api; .venv/Scripts/mypy.exe app; Set-Location ../..
        Write-Host "`nAll lint checks passed cleanly!" -ForegroundColor Green
    }
    "test" {
        Write-Host "Running backend tests..." -ForegroundColor Cyan
        Set-Location apps/api
        .venv/Scripts/pytest.exe -v
        Set-Location ../..
    }
    "build" {
        Write-Host "Building web application..." -ForegroundColor Cyan
        node scripts/check-no-external-assets.js
        node scripts/check-no-emoji.js
        Set-Location apps/web; pnpm run build; Set-Location ../..
    }
    "seed" {
        Write-Host "Seeding demo records..." -ForegroundColor Cyan
        apps/api/.venv/Scripts/python.exe scripts/seed-demo-users.py
    }
    "db-up" {
        Write-Host "Starting PostgreSQL via docker compose..." -ForegroundColor Cyan
        docker compose up -d postgres
        docker compose ps postgres
    }
    "db-migrate" {
        Write-Host "Applying Alembic migrations..." -ForegroundColor Cyan
        Set-Location apps/api
        .venv/Scripts/python.exe -m alembic upgrade head
        .venv/Scripts/python.exe -m alembic current
        Set-Location ../..
    }
    "db-check" {
        Write-Host "Checking schema drift against the models..." -ForegroundColor Cyan
        Set-Location apps/api
        .venv/Scripts/python.exe -m alembic check
        Set-Location ../..
    }
    "e2e" {
        Write-Host "Running backend E2E scenario suite..." -ForegroundColor Cyan
        apps/api/.venv/Scripts/python.exe scripts/run-e2e-scenarios.py
    }
    "verify-llm" {
        Write-Host "Verifying LLM configuration..." -ForegroundColor Cyan
        Set-Location apps/api
        .venv/Scripts/python.exe -c "import asyncio; from app.services.llm.client import verify_llm_configuration; print(asyncio.run(verify_llm_configuration()))"
        Set-Location ../..
    }
    Default {
        Write-Host "Unknown target: $Target. Available targets: dev, lint, test, build, seed, e2e, verify-llm, db-up, db-migrate, db-check" -ForegroundColor Red
        Exit 1
    }
}

