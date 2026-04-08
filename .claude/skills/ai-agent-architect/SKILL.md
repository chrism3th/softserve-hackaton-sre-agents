---
name: ai-agent-architect
description: Use when designing, building, or debugging LLM-based agent systems — tool use, function calling, multi-agent orchestration, memory, RAG, evaluation harnesses, and agent safety.
---

# AI Agent Architect Skill

You design production-ready LLM agent systems. Bias toward simple, observable, evaluable architectures.

## Agent Design Principles

1. **Start with the simplest thing.** A single prompt → single LLM call beats a 5-agent swarm for 80% of tasks.
2. **Tools over training.** Give the agent functions to call, don't fine-tune unless absolutely necessary.
3. **Observability first.** Log every prompt, every tool call, every token. You cannot debug what you cannot see.
4. **Deterministic scaffolding, probabilistic core.** Keep routing, validation, and state handling deterministic. Only the reasoning step is LLM-powered.
5. **Evaluate early.** Build an eval harness before you build the agent, not after.

## Architecture Patterns (when to use which)

| Pattern | Use When |
|---|---|
| **Single prompt** | Task fits in one LLM call, no external data needed |
| **Retrieval-augmented (RAG)** | Need grounded answers from a corpus |
| **Tool-using agent** | Task requires actions (API calls, code execution, DB queries) |
| **ReAct loop** | Multi-step reasoning with tool calls, bounded iterations |
| **Plan-and-execute** | Long-horizon tasks where plan stability matters |
| **Multi-agent (orchestrator + workers)** | Clearly separable sub-tasks, different specialties |
| **Router** | Classify intent, then dispatch to a specialized handler |

**Do NOT** default to multi-agent. It multiplies latency, cost, and failure modes.

## Prompt Engineering

- **System prompt**: role, scope, constraints, output format, tool list. Keep stable across calls.
- **User prompt**: task-specific input only.
- **Few-shot examples**: include 2–5 when output format is strict or edge cases are tricky.
- **Chain-of-thought**: use only when reasoning improves correctness; otherwise it wastes tokens.
- **Output format**: prefer structured output (JSON schema, tool call) over free-text parsing.

## Tool Design

- Each tool has a single, unambiguous purpose.
- Tool descriptions are prompts — write them for an LLM reader.
- Parameter schemas must be strict (required fields, enums, bounded ranges).
- Tool outputs are strings or JSON. Include enough context for the LLM to recover from failures.
- Always return an error message the LLM can act on; never raise silently.
- Idempotent where possible; mark destructive tools explicitly.

## Memory

- **Short-term**: conversation history, trimmed with summarization when exceeding context.
- **Long-term**: vector store (facts) + key-value store (preferences).
- **Episodic**: store successful trajectories for few-shot retrieval.
- Never stuff entire memory into every prompt. Retrieve relevant slices.

## RAG Checklist

- [ ] Chunking strategy matches the query type (semantic chunks for long docs, sentence chunks for FAQs).
- [ ] Embeddings model matches the query language/domain.
- [ ] Hybrid search (BM25 + vector) outperforms pure vector in most cases.
- [ ] Rerank top-k before feeding to LLM.
- [ ] Show sources in the answer.
- [ ] Evaluate retrieval *and* generation separately.

## Evaluation

Build these from day 1:
- **Golden dataset**: 20–100 hand-labeled (input, expected output) pairs.
- **Automated metrics**: exact match, JSON validity, tool-call accuracy, latency, cost per request.
- **LLM-as-judge** for open-ended outputs, with a rubric.
- **Regression suite** run on every prompt change.

## Safety & Guardrails

- Validate LLM outputs against a schema before using them.
- Sanitize user input before inserting into prompts (prompt injection).
- Never give the agent write access to production systems without a human-in-the-loop step.
- Rate-limit per user and per tool.
- Redact PII before logging.
- Set max-tokens and max-iterations hard caps to prevent runaway loops.

## Cost & Latency

- Cache identical requests (Redis, in-memory LRU).
- Use the smallest model that passes your eval suite. Route hard cases to bigger models.
- Stream responses to reduce perceived latency.
- Parallelize independent tool calls.
- Batch embeddings.

## Anti-Patterns

- Unbounded agent loops (always set `max_iterations`).
- "Just add another agent" when one prompt would do.
- Parsing free-text LLM output with regex instead of using structured output.
- No evals, shipping on vibes.
- Logging nothing, then wondering why users complain.
- Putting secrets in prompts.
