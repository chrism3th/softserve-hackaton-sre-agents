---
name: technical-writer
description: Use when writing or improving READMEs, API docs, runbooks, architecture docs, ADRs, release notes, or user-facing help content. Focus on clarity, accuracy, and audience.
---

# Technical Writer Skill

Good docs are a force multiplier. Bad docs are worse than none (they lie confidently).

## Before Writing: Know Your Reader

- **Who** will read this? (new dev, ops on-call, end user, executive)
- **What** are they trying to do *right now*?
- **What** do they already know, and what must you explain?
- **When** will they read it — under calm exploration or under a 3AM incident?

Different readers, different docs. One document cannot serve all four audiences.

## The Diataxis Framework

Four distinct kinds of docs, each with a different shape:

| Type | Purpose | Voice |
|---|---|---|
| **Tutorial** | Learning | "Let's build X together" |
| **How-to** | Task completion | "To do X, do these steps" |
| **Reference** | Lookup | "X is defined as..." |
| **Explanation** | Understanding | "Why X exists, and how it fits" |

**Don't mix them.** A tutorial cluttered with reference details loses the learner. A reference wrapped in prose slows the expert.

## Writing Rules

- **Active voice**: "The system sends a webhook" not "A webhook is sent".
- **Present tense**: "The function returns X" not "The function will return X".
- **Short sentences.** 20 words is a good ceiling.
- **One idea per paragraph.**
- **Lists for parallel items, prose for flowing ideas.**
- **Examples are worth 500 words.**
- **Define terms the first time they appear.** Or link to a glossary.
- **Avoid weasel words**: "simply", "just", "easy", "obviously" — they shame confused readers.

## READMEs (the most-read, least-loved doc)

A README should answer, in order:

1. **What is this?** (one sentence)
2. **Why does it exist?** (one paragraph)
3. **Quickstart**: copy-pasteable commands that work.
4. **Requirements**: versions, OS, accounts.
5. **Usage**: the 3 most common tasks.
6. **Configuration**: env vars, flags.
7. **Development**: how to contribute / run tests.
8. **Links**: full docs, issue tracker, license.

**Test your quickstart** on a clean machine. If it doesn't work verbatim, fix it.

## API Docs

For each endpoint:
- Method + path
- Purpose (one sentence)
- Request: params, body schema, example
- Response: schema, example, status codes
- Errors: cases and what they mean
- Auth required?
- Rate limits?
- Deprecation warnings?

Generate from OpenAPI when possible. Hand-written drifts.

## Runbooks

For on-call and ops:

```
## <Incident type>: Database connection pool exhausted

### Symptom
Grafana alert "db_conn_pool_saturation > 0.9" fires.
Users see 500s on /api/*.

### Verify
1. Check Grafana dashboard X.
2. Run `kubectl exec ... -- pgbouncer-show pools`.

### Mitigate
1. Scale replica count: `kubectl scale deployment/api --replicas=N`.
2. If still failing, failover to standby: ...

### Root cause hunt (after mitigation)
- Check slow query log.
- Check for recent deploys.

### Escalation
Page <team> via PagerDuty if not recovered in 15 min.
```

Runbooks are read under stress. Optimize for speed, not style.

## Architecture Decision Records (ADRs)

One file per decision, in `docs/adr/`:

```
# ADR 0007: Use Postgres for primary storage

Date: 2026-04-06
Status: Accepted

## Context
We need a primary datastore for...

## Decision
We will use Postgres 16.

## Alternatives considered
- MongoDB: rejected because...
- MySQL: rejected because...

## Consequences
- Positive: ...
- Negative: ...
- Neutral: ...
```

ADRs are append-only history. Don't edit old ones — supersede them with new ones.

## Code Comments

- Comment **why**, not what. The code shows what.
- Comment surprises and workarounds: "This sleeps 50ms because downstream has a race condition in v1.2 (upstream issue #123)".
- Keep comments next to the code they describe; stale comments are worse than none.
- Docstrings for public APIs, always. Follow the language convention (reST, Google, NumPy for Python).

## Release Notes

For users, not engineers:

```
## v2.4.0 — 2026-04-06

### ✨ New
- Bulk export of reports as CSV.

### 🐛 Fixed
- Dashboard no longer freezes when loading > 10k rows.

### 💥 Breaking
- The `/v1/users` endpoint is removed. Use `/v2/users`.

### 📦 Dependencies
- Upgraded Postgres driver to 3.1 (you don't need to do anything).
```

Lead with impact to the reader, not internal implementation.

## Diagrams

- **Text-based** (Mermaid, PlantUML, D2) so they live in git and diff cleanly.
- One concept per diagram. Avoid the "everything" architecture poster.
- Label every arrow. "Talks to" is not a label.
- Distinguish sync vs. async flows visually.

## Maintenance

Docs rot. Fight it:
- Every code change with user impact ships with doc change in the same PR.
- Quarterly doc audit: read your quickstart, run the commands, fix what broke.
- Delete docs you cannot maintain. A 404 is more honest than a lie.

## Anti-Patterns

- README that is just the project name and "Coming soon".
- Wall of text with no headings.
- Screenshots that are outdated the day after they're taken (prefer text where possible).
- "See the code" instead of explaining.
- Internal jargon without definition.
- Copy-paste blocks that don't actually work.
- Docs written once, never updated.
- "For more info, ask @alice" — what happens when Alice leaves?
