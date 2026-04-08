# ADR 0002: Python toolchain — ruff + mypy + pytest + FastAPI

Date: 2026-04-06
Status: Accepted

## Context

A hackathon repo needs a Python toolchain that is fast, boring, and modern.
We want strict type safety, fast linting, good test ergonomics, and zero
time wasted choosing between overlapping tools.

## Decision

- **FastAPI** for HTTP. Async-native, Pydantic-integrated, OpenAPI for free.
- **Pydantic v2** + **pydantic-settings** for models and config.
- **SQLAlchemy 2.x (async)** + **asyncpg** for Postgres.
- **Redis** client from `redis-py` (async).
- **ruff** for both linting and formatting (replaces black, isort, flake8, pyupgrade).
- **mypy** in strict mode for type checking.
- **pytest** + **pytest-asyncio** + **pytest-cov** + **respx** for tests.
- **structlog** for structured JSON logs.
- **src-layout** (`src/app/...`) + **pyproject.toml** as the single source of truth.
- **pip** + `requirements.txt` for Docker image builds (simpler than uv in the multi-stage build).

## Alternatives considered

- **black + isort + flake8**: rejected. Ruff does all three, 10–100× faster.
- **Django**: rejected. Overkill for a small agent API; slower async story.
- **Flask**: rejected. No async-native story, no type integration.
- **uv** inside the Dockerfile: deferred. uv is great locally; keeping pip in
  the image avoids an extra tool for contributors in their first hour.
- **Poetry**: rejected. Slower than pip+requirements, more ceremony, and the
  `pyproject.toml` already works without it.

## Consequences

- **Positive**: one formatter/linter (ruff) instead of three. Strict mypy
  catches bugs before they ship. FastAPI gives us OpenAPI docs with zero effort.
- **Negative**: strict mypy has a learning curve. Some libraries lack stubs.
- **Neutral**: contributors used to black/isort need to run `ruff format` instead,
  but the behavior is nearly identical.
