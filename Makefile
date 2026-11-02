export PATH := $(HOME)/.local/bin:$(PATH)
SHELL := /bin/bash
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs ps restart install test lint fmt health smoke clean docs \
        backend-install backend-test backend-lint frontend-install frontend-test frontend-lint \
        migrate tenant seed worker demo screenshots

help: ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

up: ## Build and start the whole stack
	$(COMPOSE) up -d --build

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

test: backend-test frontend-test ## Run all local checks

backend-test: backend/.venv
	cd backend && uv run pytest -q

backend-lint: backend/.venv
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app

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

migrate tenant seed worker: ## Available from M1
	@echo "target '$@' lands in M1 (tenancy foundation)"

screenshots: ## Available from M10
	@echo "screenshot harness lands in M10"

clean: ## Remove local caches (not containers or volumes)
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache frontend/.next