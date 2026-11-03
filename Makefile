export PATH := $(HOME)/.local/bin:$(PATH)
SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs ps restart install test lint fmt health smoke clean docs build \
        backend-install backend-test backend-lint frontend-install frontend-test frontend-lint \
        migrate tenant seed worker demo screenshots sweep

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

fmt: ## Format and autofix
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && pnpm lint --fix

health: ## Print the readiness payload
	@curl -fsS http://localhost:8080/api/v1/health/ready | python3 -m json.tool

smoke: ## M0 acceptance checks against the running stack
	@bash scripts/smoke.sh

demo: smoke ## Demo entry point (grows through the milestones first)

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

worker: ## Available from M5
	@echo "target 'worker' lands in M5 (SATUSEHAT adapter)"

sweep: backend/.venv ## Remove expired uploads and release quota
	cd backend && uv run python -m app.files.sweep

screenshots: ## Available from M10
	@echo "screenshot harness lands in M10"

clean: ## Remove local caches (not containers or volumes)
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache frontend/.next