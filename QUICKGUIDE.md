# Quick Guide

Step-by-step instructions to run and test the SRE Incident Intake & Triage Agent.

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose v2)
- API keys for: **Anthropic Claude**, **Linear**, **GitHub** (PAT with `repo` scope)
- Optional: **Resend** API key for email notifications

## 1. Clone & configure

```bash
git clone https://github.com/<your-org>/softserve-hackaton-sre-agents.git
cd softserve-hackaton-sre-agents

# Create .env from the template
make init          # copies .env.example → .env

# Fill in your API keys
$EDITOR .env       # at minimum set ANTHROPIC_API_KEY, LINEAR_API_KEY, GITHUB_API_TOKEN
```

## 2. Start the stack

```bash
make up            # builds images and starts all services (detached)
```

This runs `docker compose` under the hood. Services started:

| Service   | URL                          | Purpose                       |
|-----------|------------------------------|-------------------------------|
| backend   | http://localhost:8000/docs    | FastAPI (Swagger UI)          |
| phoenix   | http://localhost:6006         | Arize Phoenix (traces UI)     |
| db        | localhost:5432               | PostgreSQL 16                 |
| redis     | localhost:6379               | Redis 7                       |

## 3. Smoke test

```bash
make smoke
```

Expected output:

```
 — backend OK
 — backend ready
[{"name":"echo", ...}]
```

## 4. Submit an incident (API)

```bash
curl -s -X POST http://localhost:8000/api/v1/tickets/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Checkout endpoint returning 500",
    "body": "POST /api/orders fails with Internal Server Error since 3pm UTC. All users affected.",
    "reporter": "alice@example.com",
    "images": []
  }' | jq .
```

The response includes: Linear ticket URL, severity (P0-P3), score, dedup info, and guardrail flags.

## 5. Submit via GitHub Issues (webhook)

```bash
# First, register the webhook (requires ngrok or similar for HTTPS):
make ngrok                     # in a separate terminal
curl -s -X POST http://localhost:8000/api/v1/github/setup-webhook \
  -H "Content-Type: application/json" \
  -d '{"payload_url": "https://<your-ngrok-id>.ngrok-free.app/api/v1/tickets/github-webhook"}'
```

Then create an issue in your GitHub repo — the agent will:
1. Receive the webhook
2. Run guardrails + triage + dedup
3. Create a Linear ticket
4. Comment on the GitHub issue with the ticket link

## 6. View traces

Open http://localhost:6006 (Arize Phoenix) to see distributed traces for every agent call, including LLM inputs/outputs and span attributes.

## 7. Run tests

```bash
make test          # unit tests inside Docker
make test-cov      # with coverage report
make lint          # ruff + mypy
make check         # lint + tests (full CI check)
```

## 8. View logs

```bash
make logs          # tail all services
make logs-backend  # backend only (structured JSON)
```

## 9. Stop

```bash
make down          # stop all services
make nuke          # stop + delete volumes (resets DB)
```

## Available Make targets

Run `make help` for the full list. Key targets:

```
make up / make down      Start / stop dev stack
make test / make lint    Tests / linting
make smoke               Health check
make logs                Tail logs
make shell-backend       Shell into backend container
```
