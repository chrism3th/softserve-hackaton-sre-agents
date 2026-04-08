# ADR 0001: Record architecture decisions

Date: 2026-04-06
Status: Accepted

## Context

We want to capture the *why* behind non-obvious technical choices so that
future contributors (and our future selves) can understand trade-offs without
archaeology.

## Decision

We will use lightweight Architecture Decision Records (ADRs) in
`docs/adr/NNNN-title.md`, following Michael Nygard's format.

Rules:

- **One decision per file.** Keep the scope tight.
- **Numbered sequentially.** No gaps.
- **Append-only.** To change a decision, write a new ADR that **supersedes**
  the old one. Old ADRs stay for history.
- **Short.** Usually under one page. Long ADRs suggest the decision needs more
  work before it's made.
- **Commit in the PR** that implements or relates to the decision.

## Template

```markdown
# ADR NNNN: <short decision title>

Date: YYYY-MM-DD
Status: Proposed | Accepted | Deprecated | Superseded by ADR XXXX

## Context
What forces are at play? What problem are we solving?

## Decision
What we decided, in a sentence or two. Then the key reasoning.

## Alternatives considered
- Alt A: why rejected
- Alt B: why rejected

## Consequences
- Positive: ...
- Negative: ...
- Neutral: ...
```

## Consequences

- **Positive**: decisions are discoverable, reviewable, and reversible.
- **Negative**: small documentation tax on each significant change.
- **Neutral**: we commit to reading them in onboarding.
