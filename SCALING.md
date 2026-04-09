# Scaling

How the SRE Incident Intake & Triage Agent scales, including assumptions and technical decisions.

## Architecture overview

The system is a stateless FastAPI backend backed by PostgreSQL (state) and Redis (cache/queue). All agents are stateless functions — they read from context and write to external systems (Linear, GitHub). This makes horizontal scaling straightforward.

```
                    ┌─────────────┐
                    │  Load       │
                    │  Balancer   │
                    └──────┬──────┘
               ┌───────────┼───────────┐
               ▼           ▼           ▼
          ┌─────────┐ ┌─────────┐ ┌─────────┐
          │ Backend │ │ Backend │ │ Backend │   ← stateless replicas
          │  (N)    │ │  (N)    │ │  (N)    │
          └────┬────┘ └────┬────┘ └────┬────┘
               │           │           │
        ┌──────┴───────────┴───────────┴──────┐
        │           Shared services            │
        │  ┌──────┐  ┌───────┐  ┌──────────┐  │
        │  │ Postgres│ │ Redis │  │ Phoenix  │  │
        │  └──────┘  └───────┘  └──────────┘  │
        └──────────────────────────────────────┘
```

## Scaling dimensions

### 1. Backend (FastAPI) — horizontal

**Current:** single container, async (uvicorn + asyncio).

**At scale:**
- Add replicas behind a load balancer. No shared state between instances.
- The prod compose already sets resource limits (`1 CPU, 1 GB RAM`).
- Webhook signature verification is stateless — any replica can handle any request.
- Background tasks (webhook handlers) run in-process. At higher volume, move to a Redis-backed task queue (Celery, arq, or SAQ) so tasks survive container restarts.

**Assumption:** below ~100 incidents/hour, a single instance is sufficient. The LLM API call (1-3s) is the bottleneck, not the application server.

### 2. LLM API calls — the real bottleneck

Each incident triggers up to 4 LLM calls in sequence:
1. Guardrail classifier (~600 tokens)
2. Image analysis (~600 tokens per image)
3. Triage drafter (~600 tokens)
4. Dedup evaluator (~300 tokens)

**Mitigation strategies:**
- **Fallback-everywhere:** Every agent has a non-LLM fallback (regex, keyword heuristics, exact match). If the API is rate-limited or slow, the system degrades gracefully instead of failing.
- **Low token budgets:** Max tokens capped at 300-600 per call. Keeps costs and latency predictable.
- **Parallelization opportunity:** Guardrails and image analysis are independent — they could run concurrently (current implementation is sequential for simplicity).
- **Caching:** Dedup queries to Linear could be cached in Redis to reduce redundant API calls.

**Assumption:** Anthropic API rate limits (~1000 RPM on standard tier) are sufficient for hackathon-scale traffic. Production would need batching or a queue.

### 3. Database (PostgreSQL) — vertical then horizontal

**Current:** single Postgres 16 instance with connection pooling via SQLAlchemy async.

**At scale:**
- Prompt injection audit log is append-only — good candidate for partitioning by date.
- Read replicas for dashboard queries.
- Connection pooling via PgBouncer if replica count grows.

**Assumption:** incident volume is low enough that a single Postgres instance handles all writes. The audit log is the only write-heavy table.

### 4. Observability (Phoenix) — independent scaling

**Current:** single Phoenix container receiving OTLP traces over HTTP.

**At scale:**
- Phoenix is stateless from the app's perspective — swap for any OTLP-compatible backend (Tempo, Honeycomb, Datadog) without code changes.
- OpenTelemetry SDK handles buffering and async export, so trace overhead is negligible.
- At high volume, add a collector (OpenTelemetry Collector) between backend and Phoenix for sampling/batching.

### 5. External API rate limits

| Service | Limit | Mitigation |
|---------|-------|------------|
| Anthropic Claude | ~1000 RPM | Fallback heuristics, low token budgets |
| Linear GraphQL | 1500 req/hr | Cache issue searches in Redis |
| GitHub REST | 5000 req/hr (with PAT) | Batch webhook operations |
| Resend email | 100 emails/day (free) | Queue + rate-limit outbound emails |

### 6. Webhook ingestion — burst handling

**Current:** webhooks processed synchronously in background tasks.

**At scale:**
- Accept webhook, validate signature, enqueue to Redis, return 202 immediately.
- Worker pool processes the queue at a controlled rate.
- This prevents webhook timeout failures during traffic spikes.

**Assumption:** GitHub/Linear webhook retry policies (exponential backoff) provide natural burst smoothing for the hackathon demo.

## Key design decisions for scale

| Decision | Why |
|----------|-----|
| Stateless agents | Any replica handles any request — no sticky sessions needed |
| Fallback-everywhere | System stays functional under LLM API degradation |
| Background webhook dispatch | Prevents timeout under slow downstream calls |
| OpenTelemetry (vendor-agnostic) | Swap Phoenix for production-grade backends without code changes |
| Docker Compose with prod overlay | Resource limits mirror production constraints |
| Async throughout (asyncio + asyncpg) | Single process handles many concurrent I/O-bound requests |

## What would change at 10x / 100x scale

| Scale | Change needed |
|-------|---------------|
| 10x (~1000 incidents/day) | Add Redis task queue, parallelize guardrails + image analysis, cache Linear searches |
| 100x (~10,000 incidents/day) | Dedicated worker pool, LLM request batching, DB read replicas, OTLP collector with sampling |
| 1000x | Event streaming (Kafka), sharded DB, multi-region deployment, LLM proxy with load balancing |
