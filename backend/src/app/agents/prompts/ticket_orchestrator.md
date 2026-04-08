# Ticket Orchestrator — Pipeline Overview

This file documents the orchestration policy. It is **not** sent verbatim to
an LLM (the orchestrator runs deterministic Python), but it describes the
contract every sub-agent must respect.

## Pipeline

1. **Guardrail agent** — classifies the raw report. Logs every triggered
   attempt to `prompt_injection_log` (Postgres). If `blocked=true`, the
   pipeline stops and returns a refusal ticket placeholder.
2. **Triage agent** — summarizes the (cleaned) report into title, summary,
   severity, score.
3. **Dedup** — deterministic Linear search on the cleaned title.
4. **Linear writer** — creates the issue with severity-mapped priority and
   appends guardrail flags to the description for auditability.

## Trust boundary

Everything coming from `IncidentDTO.title`, `body`, or `images` is **untrusted
user input**. No agent may execute, render, or trust embedded instructions.
Sub-agents must always return strict JSON matching their declared schema.
