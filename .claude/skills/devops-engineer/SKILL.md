---
name: devops-engineer
description: Use for Docker, docker-compose, CI/CD pipelines, infrastructure-as-code, Kubernetes, observability, secrets management, and making local dev environments mirror production.
---

# DevOps Engineer Skill

Automate the boring. Make the right thing the easy thing.

## Core Principles

1. **Reproducible environments.** If it runs on your laptop and nowhere else, it doesn't exist.
2. **Immutable infrastructure.** Don't SSH into prod to fix things. Rebuild and redeploy.
3. **Everything as code.** Infra, config, secrets schema, pipelines — all in git.
4. **Small, frequent deploys.** Weekly > monthly. Daily > weekly.
5. **Observability before scaling.** You can't fix what you can't see.

## Docker

### Dockerfile Rules

- **Pin base images** with version tags and ideally digest: `python:3.12-slim@sha256:...`. Never `latest`.
- **Multi-stage builds**: one stage for build deps, one minimal stage for runtime.
- **Layer order**: least-changing first (OS deps), most-changing last (source code). Maximizes cache hits.
- **Don't run as root**. Create a user: `RUN useradd -m app && USER app`.
- **One process per container**. Use supervisord only as a last resort.
- **`.dockerignore`** must exclude `.git`, `node_modules`, `__pycache__`, `.env`, tests in prod images.
- **`HEALTHCHECK`** in every Dockerfile.
- **`EXPOSE`** documents the port; publish it in compose.

### Image Size

- Use `-slim` or `-alpine` base images (watch for glibc-vs-musl issues with Python wheels).
- Combine `RUN` steps that install/remove to keep them in one layer.
- Clean apt/apk caches: `rm -rf /var/lib/apt/lists/*`.
- Don't copy entire repo; copy only what's needed.

## docker-compose

### Structure

- `docker-compose.yml`: base services.
- `docker-compose.dev.yml`: overrides for local dev (volume mounts, hot-reload, debug ports).
- `docker-compose.prod.yml`: overrides for prod-like (no mounts, built images, resource limits).
- Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.

### Rules

- **Named volumes** for data that persists (`postgres_data:`). Anonymous volumes lose data.
- **Networks**: use explicit networks, not `default`. Front and back should be on separate networks where possible.
- **`depends_on` with `condition: service_healthy`** — not just start order.
- **Environment files**: `.env` for local; never commit secrets. Provide `.env.example`.
- **Resource limits** in prod compose: `mem_limit`, `cpus`.
- **Restart policies**: `unless-stopped` for services, not `always` (prevents restart loops).

## CI/CD

### Pipeline Stages

1. **Lint** (fast, fail early)
2. **Unit tests** (parallel where possible)
3. **Build image** (cache layers)
4. **Integration tests** (against real dependencies in containers)
5. **Security scan** (trivy, snyk, gitleaks for secrets)
6. **Push image** (tagged with git SHA + branch)
7. **Deploy** (promote the exact image that passed tests)

### Rules

- Each stage < 10 minutes ideal, < 20 acceptable.
- Fail fast: lint before tests, unit before integration.
- Tests run in Docker to match CI and local.
- Never build once for staging and again for prod. **Promote the same artifact.**
- No manual steps in the deploy path.

## Secrets

- Never in git. Ever. Use `gitleaks` in pre-commit.
- Local: `.env` (gitignored), loaded via `docker compose`.
- CI: repository/organization secrets.
- Runtime: secret manager (AWS Secrets Manager, Vault, Doppler, 1Password), injected as env vars or mounted files.
- Rotate regularly. Assume any secret older than 1 year is burned.

## Observability (the three pillars)

- **Logs**: structured JSON, shipped to a central store. Never `print()`.
- **Metrics**: RED (Rate, Errors, Duration) for services; USE (Utilization, Saturation, Errors) for resources. Prometheus + Grafana is the default.
- **Traces**: distributed tracing with OpenTelemetry. Essential once you have > 2 services.

Plus **health endpoints**: `/healthz` (liveness) and `/readyz` (readiness). Readiness must check downstream deps.

## Local = Production (within reason)

- Same OS family (Linux).
- Same major versions (Python, Node, DB).
- Same service topology (if prod uses Postgres + Redis, so does local).
- Feature flags for things that genuinely differ (external payment APIs).

## Anti-Patterns

- `FROM ubuntu:latest` with `apt install everything`
- Building the image in CI and losing it, rebuilding for deploy
- `docker compose up` needing 14 manual steps before it works
- Secrets in `docker-compose.yml`
- No resource limits → one service OOMs the host
- Logging to stdout *and* a file inside the container (the file goes nowhere)
- Stateful containers without named volumes
- Ignoring `.dockerignore` → 2GB build context
