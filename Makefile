# Hackathon Makefile — one entry point for the whole project.
# Usage: `make help`

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

COMPOSE      := docker compose
COMPOSE_DEV  := $(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml
COMPOSE_PROD := $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml

BACKEND_EXEC := $(COMPOSE_DEV) exec -T backend
FRONTEND_EXEC := $(COMPOSE_DEV) exec -T frontend

# ---------------------------------------------------------------- help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_%-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Setup

.PHONY: init
init: ## Copy .env.example to .env if missing
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env — edit it now."; else echo ".env already exists."; fi

.PHONY: install-backend
install-backend: ## Install backend deps locally (outside docker) with uv
	cd backend && uv sync --locked --extra dev

.PHONY: install-frontend
install-frontend: ## Install frontend deps locally (outside docker)
	cd frontend && npm install

.PHONY: install
install: install-backend install-frontend ## Install all deps locally

##@ Local dev (docker compose)

.PHONY: up
up: init ## Start full dev stack with hot-reload (detached)
	$(COMPOSE_DEV) up -d --build
	@echo ""
	@echo "  Backend:  http://localhost:8000/docs"
	@echo "  Frontend: http://localhost:5173"
	@echo ""

.PHONY: up-fg
up-fg: init ## Start full dev stack in the foreground (see logs)
	$(COMPOSE_DEV) up --build

.PHONY: down
down: ## Stop all services
	$(COMPOSE_DEV) down

.PHONY: restart
restart: down up ## Restart the dev stack

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE_DEV) logs -f --tail=100

.PHONY: logs-backend
logs-backend: ## Tail backend logs only
	$(COMPOSE_DEV) logs -f --tail=200 backend

.PHONY: logs-frontend
logs-frontend: ## Tail frontend logs only
	$(COMPOSE_DEV) logs -f --tail=200 frontend

.PHONY: ps
ps: ## List running containers
	$(COMPOSE_DEV) ps

.PHONY: shell-backend
shell-backend: ## Open a shell inside the backend container
	$(COMPOSE_DEV) exec backend bash

.PHONY: shell-frontend
shell-frontend: ## Open a shell inside the frontend container
	$(COMPOSE_DEV) exec frontend sh

.PHONY: shell-db
shell-db: ## Open psql inside the db container
	$(COMPOSE_DEV) exec db psql -U postgres -d app

##@ Prod-like

.PHONY: up-prod
up-prod: init ## Build and run the production-like stack
	$(COMPOSE_PROD) up -d --build
	@echo ""
	@echo "  Frontend (nginx): http://localhost:8080"
	@echo ""

.PHONY: down-prod
down-prod: ## Stop the production-like stack
	$(COMPOSE_PROD) down

##@ Build

.PHONY: build
build: ## Build all docker images (dev)
	$(COMPOSE_DEV) build

.PHONY: build-prod
build-prod: ## Build all docker images (prod)
	$(COMPOSE_PROD) build

.PHONY: build-backend
build-backend: ## Build backend image only
	$(COMPOSE_DEV) build backend

.PHONY: build-frontend
build-frontend: ## Build frontend image only
	$(COMPOSE_DEV) build frontend

##@ Tests

.PHONY: test
test: test-backend test-frontend ## Run ALL tests (backend + frontend)

.PHONY: test-backend
test-backend: ## Run backend unit tests in container
	$(COMPOSE_DEV) run --rm --no-deps backend pytest -q

.PHONY: test-backend-cov
test-backend-cov: ## Run backend tests with coverage report
	$(COMPOSE_DEV) run --rm --no-deps backend pytest --cov=app --cov-report=term-missing

.PHONY: test-backend-integration
test-backend-integration: ## Run backend integration tests (needs DB + Redis)
	$(COMPOSE_DEV) up -d db redis
	$(COMPOSE_DEV) run --rm backend pytest -m integration -q
	$(COMPOSE_DEV) down

.PHONY: test-frontend
test-frontend: ## Run frontend unit tests
	$(COMPOSE_DEV) run --rm --no-deps frontend npm test

##@ Database

# MSG is required for migrate-new: make migrate-new MSG="describe change"
MSG ?=

.PHONY: migrate
migrate: ## Apply all pending migrations (alembic upgrade head)
	$(COMPOSE_DEV) run --rm backend alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Roll back the last migration (alembic downgrade -1)
	$(COMPOSE_DEV) run --rm backend alembic downgrade -1

.PHONY: migrate-new
migrate-new: ## Generate a new migration: make migrate-new MSG="add users table"
	@[ -n "$(MSG)" ] || (echo "Error: MSG is required.  Usage: make migrate-new MSG=\"describe change\"" && false)
	$(COMPOSE_DEV) run --rm backend alembic revision --autogenerate -m "$(MSG)"

.PHONY: migrate-history
migrate-history: ## Show full migration history
	$(COMPOSE_DEV) run --rm backend alembic history --verbose

.PHONY: migrate-current
migrate-current: ## Show the current DB revision
	$(COMPOSE_DEV) run --rm backend alembic current

##@ Quality

.PHONY: lint
lint: lint-backend lint-frontend ## Lint all code

.PHONY: lint-backend
lint-backend: ## Ruff + mypy on backend
	$(COMPOSE_DEV) run --rm --no-deps backend bash -c "ruff check src tests && mypy src"

.PHONY: lint-frontend
lint-frontend: ## ESLint + tsc on frontend
	$(COMPOSE_DEV) run --rm --no-deps frontend sh -c "npm run typecheck && npm run lint || true"

.PHONY: format
format: format-backend format-frontend ## Auto-format all code

.PHONY: format-backend
format-backend: ## Ruff format backend code
	$(COMPOSE_DEV) run --rm --no-deps backend bash -c "ruff format src tests && ruff check --fix src tests"

.PHONY: format-frontend
format-frontend: ## Prettier format frontend code
	$(COMPOSE_DEV) run --rm --no-deps frontend npm run format

##@ Cleanup

.PHONY: clean
clean: ## Remove build artifacts and caches (local)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage backend/coverage.xml
	rm -rf frontend/dist frontend/.vite frontend/coverage

.PHONY: clean-docker
clean-docker: ## Stop stack and prune volumes (destroys DB data)
	$(COMPOSE_DEV) down -v
	$(COMPOSE_PROD) down -v

.PHONY: nuke
nuke: clean clean-docker ## Full reset: caches, volumes, everything

##@ Quick checks

.PHONY: check
check: lint test ## Run lint + tests (what CI should run)

.PHONY: smoke
smoke: ## Smoke-test a running stack
	@curl -fsS http://localhost:8000/healthz && echo " — backend OK"
	@curl -fsS http://localhost:8000/readyz && echo " — backend ready"
	@curl -fsS http://localhost:8000/api/v1/agents | head -c 200 && echo ""
