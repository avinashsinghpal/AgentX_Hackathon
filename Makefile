.PHONY: dev test lint build seed e2e checks db-up db-migrate db-check

dev:
	@echo "Starting development servers..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 dev

test:
	@echo "Running tests..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 test

lint:
	@echo "Running linters..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 lint

build:
	@echo "Building application..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 build

seed:
	@echo "Seeding demo data..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 seed

e2e:
	@echo "Running E2E tests..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 e2e

checks:
	@node scripts/check-no-emoji.js
	@node scripts/check-no-external-assets.js
	@node scripts/check-legal-placeholders.js

db-up:
	@echo "Starting PostgreSQL..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 db-up

db-migrate:
	@echo "Applying database migrations..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 db-migrate

db-check:
	@echo "Checking schema drift..."
	@powershell -ExecutionPolicy Bypass -File ./run.ps1 db-check
