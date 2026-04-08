# CLAUDE.md — Project instructions for Claude Code

This file tells Claude Code how to work in this repo. Keep it short, keep it current.

## Project

Hackathon project targeting the **SoftServe "Next Generation AI Agents"** theme.
Python (FastAPI) backend with an agent framework, plus a Vite/React frontend.
Everything runs locally via `docker compose` to mirror production.

## Ground rules

1. **Read before you write.** Never edit a file you haven't read in this session.
2. **Minimal diffs.** Do what was asked — no gratuitous refactors or cleanup.
3. **Use the Makefile.** Never invent new scripts when a target exists. Add a new
   target if needed.
4. **Tests are non-negotiable.** Every new behavior ships with a test; every bug
   fix ships with a regression test.
5. **Docker is the source of truth.** If a command doesn't work in the container,
   it doesn't work. Fix the Dockerfile or compose, not your shell.
6. **Secrets never commit.** Use `.env` (gitignored) or the secret manager.
7. **Ask when stuck.** Don't grind. Use AskUserQuestion after two failed attempts.

## Tooling (stick to these)

- **Python** 3.12, **src-layout** package, **pyproject.toml** as the source of truth
- **ruff** for lint + format (no black, no isort, no flake8)
- **mypy** in strict mode
- **pytest** + **pytest-asyncio** + **pytest-cov**
- **FastAPI** + **Pydantic v2** + **SQLAlchemy 2.x (async)** + **asyncpg**
- **structlog** for logs (JSON to stdout, never `print`)
- **Node 20**, **npm** (not yarn/pnpm unless asked)
- **Vite** + **React 18** + **TypeScript** strict, **Vitest** for tests

## Commands you'll use

```bash
make up               # bring up dev stack
make down             # tear it down
make test             # backend + frontend tests
make lint             # ruff + mypy + tsc + eslint
make format           # auto-format
make shell-backend    # interactive shell in the container
make logs             # tail everything
make smoke            # quick health-check curl
```

Run `make help` for the full menu.

## Style rules (short version — see `.claude/skills/` for details)

### Python
- Type hints everywhere. `from __future__ import annotations` at the top.
- `pathlib.Path`, not `os.path`.
- f-strings, not `.format()`.
- `structlog` loggers: `logger.info("event.name", key=value)` — no f-strings inside log calls.
- Catch the narrowest exception. Always `raise ... from e`.
- Prefer pure functions at the core and side effects at the edges.
- No mutable default args. No `from x import *`.

### TypeScript
- `strict: true` and `noUncheckedIndexedAccess: true` are set. Don't loosen them.
- No `any` without a written justification.
- Prefer function components and hooks. No class components.
- Keep API types in `src/api/client.ts` (or split later when it grows).

### Docker
- Multi-stage builds. Non-root user. Pinned base images (no `:latest`).
- `.dockerignore` everything that isn't needed in the image.
- `HEALTHCHECK` on every image. `depends_on` with `condition: service_healthy`.

### Git
- Conventional commits: `feat: ...`, `fix: ...`, `chore: ...`, etc.
- Small commits. Each passes `make check`.
- Never `git push --force` to main. Never commit `.env`.

## Skills directory

`.claude/skills/` contains role-based playbooks. You (Claude) will auto-discover
them based on the task. When the user asks for work that clearly fits a role,
apply that skill's principles. Don't announce "I'm using the X skill" — just
apply it.

## Hackathon mode

We have hours, not weeks. That means:

- **Demo-driven development.** Build toward the demo script, not the product roadmap.
- **Happy path first.** Error handling and edge cases *after* the demo works end-to-end.
- **Hardcode what's hard.** Seeded data, fake auth, placeholder images — all fine if the
  story is intact.
- **One metric, one narrative.** If a change doesn't serve either, cut it.
- **No pivots after hour 6** of the event. Execute the committed plan.

But even in hackathon mode:
- Never commit secrets.
- Never skip tests on core business logic (the thing the judges will actually see).
- Keep `make up` working. A broken dev stack costs the whole team.

## When asked to add a new agent

1. Subclass `Agent` in `backend/src/app/agents/<name>.py`.
2. Register it in `backend/src/app/agents/registry.py`.
3. Add a unit test mocking any external calls (`respx` for HTTP).
4. Expose it automatically via `GET /api/v1/agents` and `POST /api/v1/agents/<name>/invoke`.
5. Document the agent's purpose in one paragraph at the top of its file.

## What not to do

- Don't add new Python dependencies without updating `pyproject.toml` *and* `requirements.txt`.
- Don't add a CI pipeline unless asked. The `Makefile` *is* the CI target.
- Don't create files in the repo root. Use `backend/`, `frontend/`, `infra/`, `docs/`.
- Don't touch `.env` automatically. Print the suggested change and let the user apply it.
- Don't bypass `make` with raw `docker` commands unless debugging.
