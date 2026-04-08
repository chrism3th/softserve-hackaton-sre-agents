# Claude Skills

A set of role-based skills to steer Claude Code toward the right mindset and conventions for each task.

## Available skills

| Skill | When to use |
|---|---|
| `software-engineer` | General SWE tasks: implementation, refactoring, code review, bug fixing |
| `python-developer` | Python-specific work: packaging, typing, pytest, async, modern toolchain |
| `ai-agent-architect` | Designing LLM/agent systems: tools, RAG, orchestration, evals |
| `data-scientist` | EDA, feature engineering, modeling, honest validation |
| `ml-engineer` | Productionizing models: pipelines, serving, monitoring, MLOps |
| `ux-designer` | User flows, IA, wireframes, a11y, microcopy |
| `devops-engineer` | Docker, compose, CI/CD, IaC, observability, secrets |
| `qa-engineer` | Test strategy, unit/integration/e2e, agent evals, fighting flakiness |
| `product-manager` | Specs, prioritization, scope control, hackathon execution |
| `technical-writer` | READMEs, API docs, runbooks, ADRs, release notes |
| `security-engineer` | Threat modeling, authz/authn, secrets, OWASP, LLM safety |

## How they work

Each skill is a `SKILL.md` with YAML frontmatter (`name`, `description`) and a body
containing principles, checklists, and anti-patterns. Claude Code will discover and
use the skill that best matches the current task based on the `description` field.

## Adding a skill

```bash
mkdir .claude/skills/my-skill
$EDITOR .claude/skills/my-skill/SKILL.md
```

Required frontmatter:

```yaml
---
name: my-skill
description: Use when <specific trigger conditions>.
---
```

Write for the next engineer (or Claude) who'll read this under time pressure.
Lead with principles, then concrete rules, end with anti-patterns.

## Philosophy

These skills encode **taste and non-negotiables**, not tutorials. They prevent
common mistakes and align work with the team's standards. They assume the reader
already knows how to code — they tell them *what good looks like* in this project.
