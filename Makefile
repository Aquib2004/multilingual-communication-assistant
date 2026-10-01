# Multilingual Communication Assistant - developer helper targets.
# Run `make help` to list everything.

.DEFAULT_GOAL := help
SHELL := bash
BACKEND := backend
FRONTEND := frontend

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
        lint format format-check typecheck test test-backend test-frontend \
        up down logs db-shell clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# --- Setup -------------------------------------------------------------------

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	cd $(BACKEND) && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	cd $(FRONTEND) && npm install

# --- Development -------------------------------------------------------------

dev: dev-backend dev-frontend ## Run backend and frontend together

dev-backend: ## Run FastAPI with reload
	cd $(BACKEND) && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Run Vite dev server
	cd $(FRONTEND) && npm run dev

# --- Quality -----------------------------------------------------------------

lint: ## Lint backend and frontend
	cd $(BACKEND) && ruff check app tests
	cd $(BACKEND) && mypy app
	cd $(FRONTEND) && npm run lint

format: ## Format all code
	cd $(BACKEND) && black app tests
	cd $(BACKEND) && ruff check --fix app tests
	cd $(FRONTEND) && npm run format

format-check: ## Verify formatting without writing
	cd $(BACKEND) && black --check app tests
	cd $(BACKEND) && ruff check app tests
	cd $(FRONTEND) && npm run format:check

typecheck: ## Type check backend and frontend
	cd $(BACKEND) && mypy app
	cd $(FRONTEND) && npx tsc --noEmit

test: test-backend test-frontend ## Run all tests

test-backend: ## Run pytest
	cd $(BACKEND) && pytest -q

test-frontend: ## Run vitest
	cd $(FRONTEND) && npm run test

# --- Docker ------------------------------------------------------------------

up: ## Build and start the full stack
	docker compose up --build

down: ## Stop the full stack
	docker compose down

logs: ## Tail container logs
	docker compose logs -f

db-shell: ## Open a psql shell
	docker compose exec postgres psql -U postgres -d multilingual_assistant

# --- Cleanup -----------------------------------------------------------------

clean: ## Remove caches and build artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.mypy_cache $(BACKEND)/.ruff_cache
	rm -rf $(FRONTEND)/node_modules $(FRONTEND)/dist $(FRONTEND)/coverage
