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
        Set-Location apps/api
        .venv/Scripts/python.exe -m app.db.seed
        Set-Location ../..
    }
    "e2e" {
        Write-Host "Running Playwright E2E test suite..." -ForegroundColor Cyan
        Set-Location apps/web
        pnpm exec playwright test
        Set-Location ../..
    }
    Default {
        Write-Host "Unknown target: $Target. Available targets: dev, lint, test, build, seed, e2e" -ForegroundColor Red
        Exit 1
    }
}

