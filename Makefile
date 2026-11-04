export PATH := $(HOME)/.local/bin:$(PATH)
SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs ps restart install test lint fmt health smoke clean docs build \
        backend-install backend-test backend-lint frontend-install frontend-test frontend-lint \
        migrate tenant seed worker demo screenshots sweep integration-demo worker-once \
        retention restore-drill rewrap-secrets docs-api screenshots-check

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

up: build ## Build and start the whole stack
	$(COMPOSE) up -d

build: ## Build images sequentially (safe on a 4 GB Docker VM)
	COMPOSE_PARALLEL_LIMIT=1 $(COMPOSE) build

down: ## Stop the stack (volumes kept)
	$(COMPOSE) down

logs: ## Follow logs
	$(COMPOSE) logs -f --tail=100

ps: ## Show container status
	$(COMPOSE) ps

restart: ## Restart app containers
	$(COMPOSE) restart backend frontend caddy

install: backend-install frontend-install ## Install local dev dependencies

backend-install: backend/.venv
backend/.venv: backend/pyproject.toml backend/uv.lock
	cd backend && uv sync

frontend-install: frontend/node_modules
frontend/node_modules: frontend/package.json frontend/pnpm-lock.yaml
	cd frontend && pnpm install --frozen-lockfile

test: backend-test frontend-test ## Run unit checks (no services needed)

test-integration: backend-test-integration ## Tenancy tests against a running stack

backend-test: backend/.venv
	cd backend && uv run pytest -q

backend-test-integration: backend/.venv
	cd backend && uv run pytest -q -m integration

backend-lint: backend/.venv
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd backend && uv run python scripts/check_tenant_safety.py

frontend-test: frontend/node_modules
	cd frontend && pnpm lint && pnpm typecheck

frontend-lint: frontend-test

lint: backend-lint frontend-test ## Lint and typecheck everything

docs-api: backend/.venv ## Regenerate docs/api.md from OpenAPI
	cd backend && uv run python scripts/generate_api_docs.py

fmt: ## Format and autofix
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && pnpm lint --fix

health: ## Print the readiness payload
	@curl -fsS http://localhost:8080/api/v1/health/ready | python3 -m json.tool

smoke: ## M0 acceptance checks against the running stack
	@bash scripts/smoke.sh

demo: ## End-to-end demo; prints [ok]/[fail] per claim
	bash scripts/demo.sh

migrate: backend/.venv ## Apply the public schema (Alembic)
	cd backend && uv run alembic upgrade head

migrate-tenants: backend/.venv ## Apply pending tenant migrations
	cd backend && uv run python -m app.cli migrate-tenants

tenant: backend/.venv ## make tenant NAME=slug OWNER=email [TITLE="Display Name"]
	@test -n "$(NAME)" || (echo "NAME is required"; exit 1)
	@test -n "$(OWNER)" || (echo "OWNER is required"; exit 1)
	cd backend && uv run python -m app.cli tenant --slug "$(NAME)" --name "$(or $(TITLE),$(NAME))" --owner "$(OWNER)"

seed: backend/.venv ## Provision the two demo tenants
	cd backend && uv run python -m scripts.seed

worker: ## Run the SATUSEHAT outbox worker (Compose network)
	$(COMPOSE) up worker

worker-once: ## Drain one worker pass (demo/tests)
	$(COMPOSE) run --rm -T worker python -m app.integrations.satusehat.worker --once

integration-demo: backend/.venv ## Credentials -> test -> sync -> job result table
	cd backend && uv run python -m app.cli migrate-tenants
	cd backend && uv run python -m scripts.integration_demo

sweep: backend/.venv ## Remove expired uploads and release quota
	cd backend && uv run python -m app.files.sweep

retention: backend/.venv ## Delete expired audit rows, leads, and auth tokens
	cd backend && uv run python -m app.cli retention

restore-drill: ## Restore one tenant schema into a scratch schema and compare (TENANT=acme)
	@test -n "$(TENANT)" || (echo "TENANT is required"; exit 1)
	bash scripts/restore_drill.sh "$(TENANT)"

rewrap-secrets: backend/.venv ## Re-encrypt integration secrets (OLD_KEY=previous passphrase)
	@test -n "$(OLD_KEY)" || (echo "OLD_KEY is required"; exit 1)
	cd backend && uv run python -m app.cli rewrap-secrets --old-key "$(OLD_KEY)"

screenshots: ## Capture docs/screenshots from a seeded running stack
	cd tools/screenshots && uv run --with playwright --with pillow python capture.py $(ARGS)

screenshots-check: ## Regenerate into a temp dir (manual/weekly check)
	cd tools/screenshots && uv run --with playwright --with pillow python capture.py --check

clean: ## Remove local caches (not containers or volumes)
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache frontend/.next