# ADR 0003: Docker Compose topology — base + dev/prod overlays

Date: 2026-04-06
Status: Accepted

## Context

We want a local dev experience that (a) mirrors production as closely as
possible and (b) still supports fast iteration (hot-reload, source mounts,
exposed ports for direct DB access).

## Decision

Three compose files:

1. `docker-compose.yml` — base topology: services, networks, volumes,
   env-var wiring, healthchecks. Does **not** declare `build:` or volume
   mounts for source code.
2. `docker-compose.dev.yml` — dev overlay: uses `Dockerfile.dev`, mounts
   source code for hot-reload, exposes 5173/8000/5432/6379 on the host.
3. `docker-compose.prod.yml` — prod overlay: uses multi-stage `Dockerfile`,
   bakes source into the image, sets resource limits, tags images, exposes
   only the public port (8080).

Two networks (`backend_net`, `frontend_net`) so the frontend cannot reach
the DB directly. Same as production would be behind a VPC.

The `Makefile` hides the overlay juggling:

```
make up       → compose -f base -f dev up
make up-prod  → compose -f base -f prod up
```

## Alternatives considered

- **Single `docker-compose.yml` with env-var switches**: rejected. Becomes
  spaghetti with conditional mounts and builds.
- **One big compose per environment**: rejected. Massive duplication; drift
  guaranteed between dev and prod.
- **Skaffold / Tilt / Devspace**: overkill for a 48-hour project. Good choices
  once we move to Kubernetes.

## Consequences

- **Positive**: dev and prod share the same topology; differences are
  auditable in a single overlay file.
- **Positive**: adding a new service only requires editing the base file.
- **Negative**: contributors must remember `make up`, not `docker compose up`.
  Mitigated by `make help` and the README.
- **Neutral**: the prod overlay is "prod-like" but not prod — no TLS, no
  secrets manager, no orchestrator. That's by design.
