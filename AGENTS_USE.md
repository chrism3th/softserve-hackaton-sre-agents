# AGENTS_USE.md

Documentation of the agent implementation for the SRE Incident Intake & Triage system.

## Agent overview and tech stack

**What it does:** An automated multi-agent pipeline that ingests incident reports (text + images), triages them with LLM-powered analysis, creates tickets in Linear, detects duplicates, and notifies teams via GitHub and email.

**Tech stack:**
- **Runtime:** Python 3.12, FastAPI, asyncio
- **LLM:** Anthropic Claude (Sonnet 4.6) via official SDK — supports multimodal (vision)
- **Integrations:** Linear (GraphQL), GitHub (REST v3), Resend (email)
- **Database:** PostgreSQL 16 (async via SQLAlchemy + asyncpg)
- **Cache:** Redis 7
- **Observability:** OpenTelemetry + Arize Phoenix, structlog (JSON)
- **Containers:** Docker Compose (dev + prod overlays)

---

## Agents and their capabilities

### 1. TicketOrchestratorAgent (main pipeline)

**Purpose:** Coordinates the end-to-end incident-to-ticket flow. Composes all other agents in a fixed sequence.

**Pipeline:** Guardrails → Image Analysis → Triage → Dedup → Linear Ticket Creation

**Input:** Incident text + optional images + reporter info
**Output:** Linear ticket URL, severity (P0-P3), score (0-100), dedup info, guardrail flags

### 2. GuardrailAgent (security)

**Purpose:** Two-stage prompt injection defense.

- **Stage 1 — Regex pre-filter** (~1ms): catches `instruction_override`, `role_hijack`, `secret_exfil`, `code_fence_injection`, `suspicious_url`
- **Stage 2 — LLM classifier**: catches paraphrased/multilingual injection attempts

**Output:** List of flags, sanitized text with `[REDACTED]` replacements, blocked boolean.
**Blocking:** Only `secret_exfil` hard-blocks the pipeline. Other flags sanitize and continue.

### 3. TriageDrafterAgent (severity classification)

**Purpose:** LLM-powered severity analysis producing structured output.

**Output:**
- Clean imperative title (≤120 chars)
- Technical summary (≤600 chars)
- Severity bucket: P0 (outage/data loss) → P3 (cosmetic)
- Numeric score: 0-100

**Fallback:** Keyword heuristics if LLM unavailable (`"outage"` → P0, `"error"` → P1, `"slow"` → P2, else P3).

### 4. ImageAnalyzerAgent (multimodal vision)

**Purpose:** Claude Vision extracts evidence from incident screenshots.

**Output per image:** caption, OCR-extracted text, error signals (e.g., `["HTTP 500", "NullPointerException"]`)

**Security:** Host allowlist prevents SSRF — only GitHub CDN domains allowed.

### 5. DedupAgent (duplicate detection)

**Purpose:** Compares new incident against existing Linear tickets using LLM semantic similarity.

**Criteria:** Same root cause + same component + same failure mode = duplicate.
**Fallback:** Exact title match if LLM unavailable.

### 6. QAHandoffAgent (GitHub PR creation)

**Purpose:** When a Linear issue transitions to QA state, automatically creates a GitHub PR and requests Copilot review.

### 7. GitHubIssueCommenterAgent (status notifications)

**Purpose:** Posts bot comments on GitHub issues when Linear ticket state changes (e.g., "Your ticket is now **In Progress**").

---

## Architecture, orchestration, and error handling

### Architecture

```
GitHub Issue ──webhook──▶ ┌───────────────────────────────┐
                          │    TicketOrchestratorAgent     │
API Request ──POST──────▶ │                               │
                          │  1. GuardrailAgent.evaluate()  │
                          │  2. ImageAnalyzerAgent.analyze()│
                          │  3. TriageDrafterAgent.draft() │
                          │  4. DedupAgent.evaluate()      │
                          │  5. LinearClient.create_issue() │
                          └──────────┬────────────────────┘
                                     │
                          ┌──────────▼────────────────────┐
                          │     Linear Webhook (state Δ)   │
                          │                               │
                          │  ▶ QAHandoffAgent (→ GitHub PR)│
                          │  ▶ GitHubIssueCommenterAgent   │
                          │  ▶ NotifyReporterAgent (email) │
                          └───────────────────────────────┘
```

### Orchestration

- **Deterministic sequencing:** Fixed pipeline order (no dynamic routing). Each stage feeds the next.
- **Stateless agents:** No shared memory between agents. Context passed explicitly via function arguments.
- **Background webhook dispatch:** Linear/GitHub webhooks return 204 immediately; handlers run as background tasks.

### Error handling

- **Fallback-everywhere:** Every LLM-dependent agent has a non-LLM fallback. The system works end-to-end even without an API key (degraded quality, not broken functionality).
- **Granular failure isolation:** Image analysis failures don't block triage. Dedup failures don't block ticket creation.
- **Exception narrowing:** Each agent catches only expected errors (`ValidationError`, `httpx.TimeoutException`). Unexpected errors propagate to the caller.

---

## Context engineering approach

### Prompt design

- Each agent has a dedicated prompt file in `backend/src/app/agents/prompts/` (Markdown).
- Prompts include explicit output schemas (JSON), severity rubrics, and decision criteria.
- Token budgets are capped (300-600 tokens per call) to keep responses focused and costs low.

### Context flow

1. **Raw input** → GuardrailAgent receives untrusted text
2. **Sanitized text** → TriageDrafterAgent receives cleaned text + image evidence (appended by orchestrator)
3. **Triage output** → DedupAgent receives title + body + list of existing Linear tickets (fetched via API)
4. **Enriched description** → Linear ticket gets structured Markdown with: source, reporter, visual evidence, guardrail flags, suggested branch name

### Context boundaries

- Reporter PII (email, name) stays in metadata — never injected into LLM prompts.
- Image URLs validated against allowlist before sending to Claude Vision.
- Existing ticket descriptions truncated to 500 chars in dedup context to stay within token budget.

---

## Use cases with step-by-step flows

### Use case 1: API incident submission

1. User `POST /api/v1/tickets/ingest` with title, body, reporter, images
2. GuardrailAgent scans for injection → flags or passes
3. ImageAnalyzerAgent extracts captions/OCR from screenshots
4. TriageDrafterAgent classifies severity → P1, score 75
5. DedupAgent checks Linear for similar tickets → no duplicate
6. Linear ticket created: `TEA-42`, priority High
7. Response returned with ticket URL and metadata

### Use case 2: GitHub issue webhook

1. User opens issue in GitHub repo (can include screenshots)
2. GitHub sends `issues.opened` webhook → backend validates HMAC signature
3. Backend extracts images from issue body (Markdown, HTML, bare URLs)
4. Same pipeline as Use case 1 runs automatically
5. Bot comments on GitHub issue: "Ticket TEA-42 created (severity: P1)"

### Use case 3: Ticket state change → GitHub notification

1. Engineer moves Linear ticket to "In Progress"
2. Linear sends webhook → backend validates signature
3. GitHubIssueCommenterAgent finds linked GitHub issue
4. Posts comment: "someone picked this up! Your ticket is now **In Progress**."

### Use case 4: QA handoff

1. Engineer moves Linear ticket to QA state
2. QAHandoffAgent creates GitHub PR from the suggested branch
3. Requests Copilot review on the PR

---

## Observability — logging, tracing, metrics

### Structured logging (structlog)

All application logs are JSON to stdout via `structlog`. Every log event includes timestamp, level, logger name, and structured key-value pairs.

**Example log output:**
```json
{
  "event": "ticket.created",
  "severity": "P1",
  "score": 75,
  "linear_id": "TEA-42",
  "dedup_of": null,
  "flags": [],
  "timestamp": "2026-04-09T14:30:00Z",
  "level": "info"
}
```

**Key log events across agents:**
- `guardrail.triggered` — injection detected, includes flags and blocked status
- `image_analyzer.done` — analysis complete, includes image count and error signals
- `image_analyzer.host_blocked` — SSRF attempt prevented
- `triage_drafter.fallback` — LLM unavailable, using keyword heuristics
- `ticket.dedup_hit` — duplicate detected
- `ticket.created` — ticket created successfully
- `qa_handoff.pr_created` — GitHub PR auto-created

### Distributed tracing (OpenTelemetry → Arize Phoenix)

Every pipeline execution produces a trace with child spans per agent stage.

**Trace structure:**
```
ticket_orchestrator.orchestrate          (root span)
├── guardrail.evaluate                   (child span)
│   └── anthropic.chat                   (auto-instrumented)
├── image_analyzer.analyze               (child span)
│   └── anthropic.chat                   (auto-instrumented, per image)
├── triage_drafter.draft                 (child span)
│   └── anthropic.chat                   (auto-instrumented)
└── dedup.evaluate                       (child span)
    └── anthropic.chat                   (auto-instrumented)
```

**Span attributes captured:**
- `incident.source`, `incident.reporter`, `incident.title`
- `ticket.severity`, `ticket.score`, `ticket.linear_identifier`
- `ticket.blocked` (guardrail hard-block)
- `guardrail.flags` (comma-separated list)
- `image.count` (number of images analyzed)

**Auto-instrumentation:** The `openinference-instrumentation-anthropic` library automatically captures all Anthropic SDK calls as spans, including: model name, prompt, completion, token usage, and stop reason.

**Phoenix UI** at `http://localhost:6006` provides:
- Trace timeline visualization
- Span detail with attributes
- LLM call inspection (prompt/response)
- Latency analysis

### Metrics

Explicit metrics (Prometheus counters/histograms) are not implemented — intentionally scoped out for hackathon. Trace-derived metrics from Phoenix provide equivalent visibility (latency percentiles, call counts, error rates).

### Evidence

Tracing and logging are wired in the following source files:
- `backend/src/app/core/observability.py` — OpenTelemetry + Phoenix initialization
- `backend/src/app/core/logging.py` — structlog JSON configuration
- `backend/src/app/agents/ticket_orchestrator.py` — root span with all attributes
- `backend/src/app/agents/guardrail_agent.py` — guardrail span
- `backend/src/app/agents/triage_drafter_agent.py` — triage span
- `backend/src/app/agents/image_analyzer_agent.py` — image analysis span

---

## Security and guardrails

### Prompt injection defense (multi-layer)

| Layer | Mechanism | Latency | Catches |
|-------|-----------|---------|---------|
| **Regex pre-filter** | 5 pattern categories | ~1ms | Obvious injection templates |
| **LLM classifier** | Claude-based semantic analysis | ~1-2s | Paraphrased, multilingual, obfuscated attempts |

**Hard-blocking flags:** `secret_exfil` (attempts to extract API keys, tokens, passwords) → pipeline stops, P3 ticket created with guardrail note.

**Soft flags:** `instruction_override`, `role_hijack`, `code_fence_injection`, `suspicious_url` → text sanitized with `[REDACTED]`, pipeline continues, flags visible in ticket.

### SSRF prevention

Image URLs validated against a strict host allowlist before being sent to Claude Vision:
- `user-images.githubusercontent.com`
- `raw.githubusercontent.com`
- `github.com`
- `objects.githubusercontent.com`

Blocked URLs return `error="host_not_allowed"` without making any external request.

### Webhook signature verification

- **GitHub:** HMAC-SHA256 via `X-Hub-Signature-256` header
- **Linear:** HMAC-SHA256 via `Linear-Signature` header + timestamp freshness check (rejects > 5 min old)

### Audit trail

Prompt injection attempts are logged to the `prompt_injection_log` PostgreSQL table with: source, reporter, raw input, detected flags, blocked status, and timestamp.

### Evidence

Security implementations in:
- `backend/src/app/tickets/guardrails.py` — regex patterns + sanitization
- `backend/src/app/agents/guardrail_agent.py` — LLM classifier + merge logic
- `backend/src/app/agents/image_analyzer_agent.py` — host allowlist
- `backend/src/app/api/routes/tickets.py` — webhook signature verification
- `backend/src/app/api/routes/webhooks.py` — Linear signature + timestamp validation

---

## Scalability summary

See [SCALING.md](SCALING.md) for full details.

**Key points:**
- Stateless agents → horizontal backend scaling
- Fallback-everywhere → graceful degradation under LLM API pressure
- Async throughout (asyncio + asyncpg) → high concurrency per process
- OpenTelemetry is vendor-agnostic → swap Phoenix for Tempo/Honeycomb/Datadog
- Background webhook dispatch → prevents timeout under load
- Token budgets capped (300-600 per call) → predictable cost and latency

---

## Lessons learned and team reflections

1. **Fallbacks are essential, not optional.** Building a non-LLM fallback for every agent took extra time but made the system testable and resilient. During development, API rate limits hit multiple times — fallbacks kept the demo working.

2. **Two-tier guardrails hit the sweet spot.** Regex alone misses paraphrased attacks. LLM alone is slow and expensive. The combination provides a fast deterministic floor with an accurate but optional ceiling.

3. **Structured logging pays for itself immediately.** JSON logs with consistent event names made debugging the multi-agent pipeline dramatically easier than `print()` statements.

4. **OpenTelemetry auto-instrumentation is magic.** One line (`AnthropicInstrumentor().instrument()`) and every LLM call gets traced with full prompt/response. Phoenix made this visible with zero extra code.

5. **Stateless agents simplify everything.** No shared memory, no coordination, no race conditions. Context flows through function arguments. Testing is just "call function, assert output."

6. **Hackathon scope discipline matters.** We cut the frontend, explicit metrics, and CI pipeline early. This let us focus on the agent pipeline quality, observability, and security — the dimensions judges actually evaluate.

7. **Docker Compose as the single source of truth.** Every `make` target runs through Docker. "Works on my machine" never came up because there is no "my machine" — only the container.
