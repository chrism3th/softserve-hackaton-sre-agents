# SRE Incident Intake & Triage Agent

An automated multi-agent system that ingests incident reports (text + screenshots),
triages them with LLM-powered analysis, creates tickets in Linear, detects duplicates,
and keeps reporters informed via GitHub and email — all without human intervention.

Built for the **SoftServe "Next Generation AI Agents"** hackathon.

## The problem

On-call engineers waste time on manual triage: reading reports, assessing severity,
creating tickets, checking for duplicates, and updating reporters. This system
automates that entire pipeline so engineers can focus on fixing, not filing.

## How it works

```
GitHub Issue ──webhook──▶ ┌───────────────────────────────┐
                          │    TicketOrchestratorAgent     │
API Request ──POST──────▶ │                               │
                          │  1. GuardrailAgent  (security) │
                          │  2. ImageAnalyzer   (vision)   │
                          │  3. TriageDrafter   (severity)  │
                          │  4. DedupAgent      (duplicates)│
                          │  5. LinearClient    (ticket)    │
                          └──────────┬────────────────────┘
                                     │
                          ┌──────────▼────────────────────┐
                          │     Linear Webhook (state Δ)   │
                          │                               │
                          │  ▶ QAHandoffAgent (→ GitHub PR)│
                          │  ▶ GitHubIssueCommenter (bot)  │
                          │  ▶ NotifyReporter (email)      │
                          └───────────────────────────────┘
```

**End-to-end flow:** submit → triage → ticket created → team notified → resolved → reporter notified

## Agents

| Agent | What it does |
|---|---|
| **TicketOrchestratorAgent** | Coordinates the full pipeline. Single entry point for all incidents. |
| **GuardrailAgent** | Two-stage prompt injection defense: regex pre-filter + LLM classifier. |
| **ImageAnalyzerAgent** | Claude Vision extracts captions, OCR text, and error signals from screenshots. |
| **TriageDrafterAgent** | LLM-powered severity classification (P0-P3) with keyword fallback. |
| **DedupAgent** | Semantic duplicate detection against existing Linear tickets. |
| **QAHandoffAgent** | Auto-creates GitHub PR when ticket reaches QA state. |
| **GitHubIssueCommenterAgent** | Posts status updates on GitHub issues as ticket state changes. |

## Tech stack

| Layer | Tools | Why |
|---|---|---|
| **Backend** | FastAPI, Python 3.12, asyncio, Pydantic v2 | FastAPI's native async support handles concurrent webhook ingestion without blocking. Pydantic v2 gives us zero-cost request validation and typed settings, critical when every payload must be parsed reliably. |
| **LLM** | Anthropic Claude (Sonnet 4.6) — multimodal (vision) | Claude's vision capability lets us extract error evidence directly from screenshots (stack traces, dashboards, error modals) in a single API call — no separate OCR pipeline needed. Sonnet balances cost and quality for real-time triage. |
| **Database** | PostgreSQL 16 (async via SQLAlchemy 2.x + asyncpg) | Postgres gives us JSONB for flexible incident metadata, full-text search for dedup, and `pgvector`-ready extensibility if we add embeddings. asyncpg is the fastest async Postgres driver available. |
| **Cache** | Redis 7 | Sub-millisecond reads for dedup lookups and rate limiting on webhook endpoints. Also serves as a lightweight pub/sub bus if we need real-time frontend updates. |
| **Integrations** | Linear (GraphQL), GitHub (REST v3), Resend (email) | Linear is the team's existing ticket tracker — GraphQL lets us fetch exactly the fields we need for dedup. GitHub webhooks are the natural incident entry point. Resend provides transactional email with a simple API and no SMTP config. |
| **Observability** | OpenTelemetry + Arize Phoenix, structlog (JSON) | Full distributed tracing across every agent hop — Phoenix gives us an LLM-specific trace UI (token usage, prompt/response pairs). structlog emits structured JSON so logs are queryable from day one. |
| **Infra** | Docker Compose (dev + prod overlays), Makefile, Nginx | Single `make up` boots the entire stack identically for every developer. Compose overlays let us keep dev (hot-reload, mounts) and prod (resource limits, built images) separate. Nginx acts as reverse proxy with security headers. |
| **Dev tooling** | ruff, mypy (strict), pytest + respx, Alembic | ruff replaces black + isort + flake8 in one tool (~100× faster). mypy strict catches type errors before runtime. respx mocks HTTP calls deterministically so agent tests never hit external APIs. Alembic manages schema migrations safely. |
| **Resilience** | tenacity (retries) | External APIs (Linear, GitHub, Anthropic) can flake. tenacity gives us declarative exponential backoff with jitter so transient failures don't kill the pipeline. |

## Quick start

> For detailed setup see [QUICKGUIDE.md](QUICKGUIDE.md).

```bash
# 1. Clone and configure
git clone https://github.com/<your-org>/softserve-hackaton-sre-agents.git
cd softserve-hackaton-sre-agents
make init                   # copies .env.example → .env
$EDITOR .env                # fill in API keys

# 2. Start everything
make up                     # builds + runs via docker compose (detached)

# 3. Verify
make smoke                  # health check
```

| Service | URL |
|---|---|
| Backend (Swagger) | http://localhost:8000/docs |
| Phoenix (traces) | http://localhost:6006 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

> All `make` targets run through `docker compose` under the hood — see [Makefile](Makefile) for the full list.

## Webhook setup guide

The system uses two webhook integrations: **GitHub** (incident ingestion) and **Linear** (ticket state changes). Both require an HTTPS tunnel for local development.

### Step 1: Start the stack and ngrok

```bash
# Terminal 1 — start services
make up

# Terminal 2 — start HTTPS tunnel
make ngrok
```

ngrok will print a public URL like `https://abcd1234.ngrok-free.app`. Copy it — you'll need it for both webhooks.

> You can also inspect webhook traffic at http://localhost:4040 (ngrok inspector).

### Step 2: Configure GitHub webhook

**Option A — Automatic (recommended):**

```bash
curl -s -X POST http://localhost:8000/api/v1/github/setup-webhook \
  -H "Content-Type: application/json" \
  -d '{"payload_url": "https://<your-ngrok-id>.ngrok-free.app/api/v1/tickets/github-webhook"}'
```

Response:
```json
{"created": true, "webhook_id": 12345678, "message": "Webhook created successfully"}
```

**Option B — Manual (via GitHub UI):**

1. Go to `https://github.com/<owner>/<repo>/settings/hooks`
2. Click **Add webhook**
3. Fill in:
   - **Payload URL:** `https://<your-ngrok-id>.ngrok-free.app/api/v1/tickets/github-webhook`
   - **Content type:** `application/json`
   - **Secret:** paste the value of `GITHUB_WEBHOOK_SECRET` from your `.env`
   - **Events:** select "Issues" only (or "Let me select individual events" → check "Issues")
4. Click **Add webhook**
5. GitHub will send a ping — check `make logs` to confirm receipt

### Step 3: Test GitHub webhook

1. Go to `https://github.com/<owner>/<repo>/issues`
2. Click **New issue**
3. Write a title like: `Checkout API returning 500 errors`
4. Add a body with details (attach a screenshot if you want to test vision)
5. Submit the issue

**What happens:**
- Backend receives the `issues.opened` webhook
- GuardrailAgent scans for prompt injection
- ImageAnalyzerAgent extracts evidence from screenshots (if any)
- TriageDrafterAgent classifies severity (P0-P3)
- DedupAgent checks for existing duplicates in Linear
- Linear ticket is created automatically
- Bot comments on the GitHub issue with the ticket link

**Where to see it:**
- http://localhost:8000/docs → Swagger UI (API responses)
- http://localhost:6006 → Phoenix (full trace of the pipeline)
- `make logs-backend` → structured JSON logs
- http://localhost:4040 → ngrok inspector (raw webhook payloads)
- Your Linear workspace → the new ticket

### Step 4: Configure Linear webhook

1. Go to `https://linear.app/settings/api` → **Webhooks** section
2. Click **Create webhook**
3. Fill in:
   - **URL:** `https://<your-ngrok-id>.ngrok-free.app/api/v1/webhooks/linear`
   - **Events:** check "Issues" (create, update, remove)
4. After creation, Linear shows a **Signing secret** — copy it
5. Paste the secret in your `.env`:
   ```
   LINEAR_WEBHOOK_SECRET=<the-signing-secret-from-linear>
   ```
6. Restart the backend:
   ```bash
   make down && make up
   ```

### Step 5: Test Linear webhook (full loop)

1. Open your Linear workspace
2. Find the ticket that was auto-created in Step 3
3. Move it through states:
   - **Backlog → In Progress** → bot comments on GitHub: "Your ticket is now **In Progress**"
   - **In Progress → In Review** → bot comments: "Your ticket is now **In Review**"
   - **In Review → Done** → bot comments: "Your ticket has been marked as **Done**"
   - Moving to **QA** → auto-creates a GitHub PR and requests Copilot review

**Where to see it:**
- The original GitHub issue → bot comments appear
- http://localhost:6006 → traces for each webhook event
- `make logs-backend` → events like `github_issue_commenter.comment_posted`

### Step 6: Test direct API ingestion (no webhooks needed)

You can also submit incidents directly without GitHub:

```bash
curl -s -X POST http://localhost:8000/api/v1/tickets/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection pool exhausted",
    "body": "PostgreSQL max_connections reached. All API requests timing out since 14:00 UTC.",
    "reporter": "oncall@example.com",
    "images": []
  }' | jq .
```

### Webhook endpoints summary

| Webhook | Endpoint | Auth header | Secret env var |
|---|---|---|---|
| GitHub Issues | `POST /api/v1/tickets/github-webhook` | `X-Hub-Signature-256` | `GITHUB_WEBHOOK_SECRET` |
| Linear Issues | `POST /api/v1/webhooks/linear` | `Linear-Signature` | `LINEAR_WEBHOOK_SECRET` |
| GitHub setup | `POST /api/v1/github/setup-webhook` | — (uses `GITHUB_API_TOKEN`) | `GITHUB_WEBHOOK_SECRET` |

### URLs you'll use during the demo

| What | URL |
|---|---|
| Swagger UI (API docs + testing) | http://localhost:8000/docs |
| Phoenix (traces + LLM calls) | http://localhost:6006 |
| ngrok inspector (webhook payloads) | http://localhost:4040 |
| GitHub issues (submit incidents) | `https://github.com/<owner>/<repo>/issues` |
| GitHub webhooks config | `https://github.com/<owner>/<repo>/settings/hooks` |
| Linear workspace (tickets) | `https://linear.app` |
| Linear webhooks config | `https://linear.app/settings/api` → Webhooks |

## Project layout

```
.
├── backend/
│   ├── src/app/
│   │   ├── agents/         # All agent implementations + prompts
│   │   ├── api/            # FastAPI routes (tickets, webhooks, github, agents)
│   │   ├── core/           # Logging, observability, errors
│   │   ├── integrations/   # Linear client + parser, GitHub client
│   │   ├── services/       # Domain services (notifications, dispatch)
│   │   ├── tickets/        # Guardrails implementation
│   │   ├── config.py       # Settings (pydantic-settings)
│   │   └── main.py         # FastAPI app factory + lifespan
│   ├── tests/              # 70 tests (pytest + respx)
│   ├── Dockerfile          # Multi-stage prod image
│   └── Dockerfile.dev      # Hot-reload dev image
├── docs/                   # Architecture, getting-started, ADRs
├── docker-compose.yml      # Base topology
├── docker-compose.dev.yml  # Dev overlay (mounts, hot-reload)
├── docker-compose.prod.yml # Prod overlay (limits, built images)
├── Makefile                # Single entry point (wraps docker compose)
├── AGENTS_USE.md           # Agent documentation
├── SCALING.md              # Scalability analysis
├── QUICKGUIDE.md           # Step-by-step run guide
└── .env.example            # Environment template
```

## Make targets

```
make up / make down       Start / stop dev stack (docker compose)
make test                 Run tests in container
make lint                 ruff + mypy
make check                lint + tests
make smoke                Health check endpoints
make logs                 Tail all service logs
make logs-backend         Backend logs only (structured JSON)
make shell-backend        Shell into backend container
make ngrok                Start HTTPS tunnel for webhooks
make help                 Full target list
```

## Documentation

| File | Purpose |
|---|---|
| [QUICKGUIDE.md](QUICKGUIDE.md) | Step-by-step setup and testing |
| [AGENTS_USE.md](AGENTS_USE.md) | Agent implementation details, observability evidence, security |
| [SCALING.md](SCALING.md) | Scalability analysis and decisions |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and design |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Developer onboarding |

## License

MIT
