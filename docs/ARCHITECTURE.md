# Architecture

## System diagram

```
            ┌──────────────┐
            │   Browser    │
            └──────┬───────┘
                   │ HTTPS
                   ▼
          ┌────────────────┐
          │ frontend (SPA) │   dev: Vite @ :5173
          │ React + Vite   │   prod: nginx @ :80 (proxies /api)
          └────────┬───────┘
                   │ /api/*
                   ▼
          ┌────────────────┐
          │  backend :8000 │   FastAPI + Uvicorn
          │  Agents / API  │
          └───┬────────┬───┘
              │        │
              ▼        ▼
        ┌────────┐  ┌────────┐
        │Postgres│  │ Redis  │
        │  :5432 │  │ :6379  │
        └────────┘  └────────┘
```

Two Docker networks:

- `backend_net`: backend ↔ db ↔ redis. Not exposed to the frontend.
- `frontend_net`: frontend ↔ backend. No direct DB access from the browser.

## Services

### backend

- **FastAPI** app factory in `backend/src/app/main.py`.
- **Lifespan** hook configures logging and (in a real app) opens DB/Redis pools.
- **Routers**: `/healthz`, `/readyz`, `/api/v1/agents/*`.
- **Settings** via `pydantic-settings` reading env vars (`backend/src/app/config.py`).
- **Structured logging** with `structlog`, JSON to stdout.
- **Agents** live under `backend/src/app/agents/`. A registry (`registry.py`) holds
  instances; the router dispatches by name.

### frontend

- **Vite + React + TypeScript**, strict mode.
- **API client** in `frontend/src/api/client.ts` — typed wrapper over `fetch`.
- Dev server proxies `/api/*` to the backend (see `vite.config.ts`).
- Prod build is static assets served by nginx, which also proxies `/api/*`.

### db (Postgres 16)

- Init script at `infra/postgres/init.sql` bootstraps extensions and a sample table.
- Real schema changes should go through **Alembic** migrations (not yet wired —
  add when you have your first model).
- Data persisted in the named volume `postgres_data`.

### redis (Redis 7)

- For caching, rate limiting, and ephemeral queues.
- AOF persistence enabled (`--appendonly yes`).
- Data in volume `redis_data`.

## Configuration

All configuration is via environment variables, loaded by `Settings` in
`backend/src/app/config.py`. Locally, a `.env` file provides defaults; in
production, inject via your deployment platform.

Never read env vars directly in application code — always go through `Settings`.

## Agent architecture

```
                    POST /api/v1/agents/<name>/invoke
                               │
                               ▼
                    ┌──────────────────┐
                    │  api/agents.py   │  validate, look up in registry
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ agents/registry  │  dict[str, Agent]
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Agent.run()     │  subclass decides how to respond
                    └──────────────────┘
```

Minimal `Agent` protocol: one async `run(request) -> response`. No framework
lock-in. Add tool use, RAG, streaming, memory **by composition**, not by
bloating the base class.

See `.claude/skills/ai-agent-architect/SKILL.md` for design guidance.

## Observability

- **Logs**: structured JSON on stdout → Docker → your log stack in prod.
- **Health**: `/healthz` (liveness), `/readyz` (readiness). Extend readiness
  to check DB + Redis + LLM provider before claiming ready.
- **Metrics**: not included. Add `prometheus-fastapi-instrumentator` when needed.
- **Traces**: not included. Add OpenTelemetry once you have > 2 services.

## Environments

| | dev | prod-like |
|---|---|---|
| Compose overlay | `docker-compose.dev.yml` | `docker-compose.prod.yml` |
| Source code | Mounted (hot reload) | Baked into image |
| Ports exposed | 5173, 8000, 5432, 6379 | 8080 only |
| Log level | DEBUG | INFO |
| Resource limits | none | memory + cpu caps |
| Image tag | n/a | `hackaton/*:${TAG}` |

## What's intentionally NOT here

- CI pipelines (add `.github/workflows/ci.yml` once the team agrees on the platform)
- Alembic migrations (add when you define your first model)
- Auth / sessions (add when the demo requires it)
- Real LLM evals (add a `backend/evals/` directory with a `pytest` harness when agents grow)
- Metrics / tracing (add only if the demo includes performance)

The rule: **only add it when it earns its place.** Hackathon scope discipline.
