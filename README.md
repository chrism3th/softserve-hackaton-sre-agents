# Next-Gen AI Agents — Hackathon Scaffold

A ready-to-go monorepo for the **SoftServe "Next Generation AI Agents"** hackathon.
Python backend (FastAPI + agent scaffold), pluggable frontend (Vite/React), Postgres,
Redis, and a `docker compose` setup that mirrors production locally.

Built to let you focus on the **idea**, not the boilerplate.

## What's in the box

| | |
|---|---|
| **Backend** | FastAPI · Python 3.12 · strict typing · pytest · ruff · mypy · structlog · Anthropic SDK |
| **Frontend** | Vite · React 18 · TypeScript · Vitest (swap-friendly) |
| **Infra** | docker-compose (dev + prod overlays) · Postgres 16 · Redis 7 · nginx |
| **Agents** | Base protocol, registry, echo smoke-test agent, reference Claude agent |
| **Skills** | 11 role-based Claude Code skills (SWE, Python, UX, DS, ML, Agents, DevOps, QA, PM, Tech writer, Security) |
| **Tooling** | One `Makefile` for build/test/lint/up/down. Zero bespoke scripts. |

## Quickstart

Requires: Docker Desktop (or Docker Engine) with Docker Compose v2.

```bash
# 1. create your .env
make init                            # copies .env.example -> .env
$EDITOR .env                         # add ANTHROPIC_API_KEY (optional for echo agent)

# 2. build & run the full dev stack
make up

# 3. open the apps
#    Frontend: http://localhost:5173
#    Backend:  http://localhost:8000/docs
#    Postgres: localhost:5432  (postgres/postgres/app)
#    Redis:    localhost:6379

# 4. smoke test
make smoke

# 5. run all tests
make test

# 6. stop everything
make down
```

## Project layout

```
.
├── .claude/skills/         # Role-based Claude Code skills
├── backend/                # FastAPI app (src-layout)
│   ├── src/app/
│   │   ├── api/            # HTTP routes
│   │   ├── agents/         # Agent protocol + implementations + registry
│   │   ├── core/           # Cross-cutting (logging, errors)
│   │   ├── models/         # ORM models (add as needed)
│   │   ├── schemas/        # Pydantic schemas (add as needed)
│   │   ├── services/       # Domain services (add as needed)
│   │   ├── config.py       # Settings (pydantic-settings)
│   │   └── main.py         # FastAPI factory + lifespan
│   ├── tests/              # pytest
│   ├── Dockerfile          # multi-stage prod image
│   └── Dockerfile.dev      # hot-reload dev image
├── frontend/               # Vite + React + TS (swap-friendly)
│   ├── src/
│   │   ├── api/            # Typed API client
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile          # nginx-served SPA build
│   └── Dockerfile.dev      # vite dev server
├── infra/
│   ├── nginx/              # SPA + reverse proxy config
│   └── postgres/           # init.sql
├── docs/                   # Architecture, getting-started, ADRs
├── docker-compose.yml      # Base topology
├── docker-compose.dev.yml  # Dev overlay (mounts, hot-reload, ports)
├── docker-compose.prod.yml # Prod-like overlay (built images, limits)
├── Makefile                # Entry point for everything
├── CLAUDE.md               # Instructions for Claude Code
└── .env.example
```

## Make targets

```
make up               # dev stack (hot-reload), detached
make up-fg            # dev stack, foreground (see logs)
make down             # stop dev stack
make up-prod          # production-like stack
make logs             # follow all logs
make shell-backend    # bash inside backend container
make shell-db         # psql inside db container

make build            # build dev images
make build-prod       # build prod images

make test             # backend + frontend tests
make test-backend-cov # backend tests with coverage
make lint             # ruff + mypy + eslint + tsc
make format           # auto-format all code
make check            # lint + tests (what CI should run)
make smoke            # curl health endpoints

make clean            # remove caches / build artifacts
make nuke             # full reset, including DB volumes
```

Run `make help` for the full list.

## Swapping the frontend

Nothing ties the backend to React. To replace the frontend:

1. Delete `frontend/src/*` (keep `Dockerfile.dev` and `Dockerfile` or edit them).
2. Rebuild: `make build-frontend`.

The backend API contract (`/api/v1/agents`) stays the same; just point your new
frontend's API client at it. nginx (`infra/nginx/default.conf`) proxies `/api/*`
to the backend service in prod builds.

If you prefer Next.js, SvelteKit, Solid, vanilla HTML — just replace the
`frontend/` contents and adjust `frontend/Dockerfile*`. `docker-compose.*.yml`
does not need to change as long as the dev server listens on port 5173 and the
prod build is served on port 80.

## Using the Claude skills

The `.claude/skills/` directory contains 11 role-based skills that steer
Claude Code toward the right mindset for each task. They're auto-discovered.

Examples:

- "Help me implement a RAG tool for this agent" → `ai-agent-architect`
- "Refactor this service to be testable" → `software-engineer` + `python-developer`
- "Review this login flow" → `security-engineer`
- "Design the dashboard for the judges" → `ux-designer`
- "Write the README" → `technical-writer`
- "Set up the CI pipeline" → `devops-engineer`

See `.claude/skills/README.md` for the full list.

## CLAUDE.md

`CLAUDE.md` (next to this README) sets project-wide defaults for Claude Code:
package manager choices, test commands, style rules, and what-good-looks-like.
Open it, tailor it to your team's preferences, commit it.

## License

MIT. Go win.
