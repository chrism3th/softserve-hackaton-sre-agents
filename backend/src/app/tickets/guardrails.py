"""Lightweight prompt-injection guardrails.

Heuristic, deterministic, fast. The goal is not to be a full classifier
but to catch the obvious attempts and tag them so we can (a) audit them
in Postgres and (b) decide whether to sanitize-and-continue or block.
"""

from __future__ import annotations

import re

from app.tickets.models import GuardrailFlag, GuardrailVerdict

_PATTERNS: list[tuple[GuardrailFlag, re.Pattern[str]]] = [
    (
        GuardrailFlag.instruction_override,
        re.compile(
            r"\b(ignore|disregard|forget)\b[^.\n]{0,40}\b("
            r"previous|above|prior|earlier|all)\b[^.\n]{0,40}"
            r"\b(instructions?|prompts?|rules?|messages?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        GuardrailFlag.role_hijack,
        re.compile(
            r"(?:^|\n)\s*(system|assistant|developer)\s*[:>]",
            re.IGNORECASE,
        ),
    ),
    (
        GuardrailFlag.role_hijack,
        re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    ),
    (
        GuardrailFlag.secret_exfil,
        re.compile(
            r"(reveal|print|show|leak|exfiltrat\w+)\b[^.\n]{0,40}"
            r"\b(api[_\s-]?key|secret|token|password|env|credentials?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        GuardrailFlag.code_fence_injection,
        re.compile(
            r"```[^\n]*\n[^`]*\b(ignore|system|assistant)\b",
            re.IGNORECASE,
        ),
    ),
    (
        GuardrailFlag.suspicious_url,
        re.compile(
            r"https?://[^\s)>\"']+\.(?:ru|tk|xyz|top|click|zip|mov)\b",
            re.IGNORECASE,
        ),
    ),
]

# Flags that we consider hard-block. Anything else is sanitize-and-tag.
_BLOCKING: set[GuardrailFlag] = {GuardrailFlag.secret_exfil}


def scan_for_injection(text: str) -> GuardrailVerdict:
    """Return a guardrail verdict for the given text."""
    flags: list[GuardrailFlag] = []
    for flag, pattern in _PATTERNS:
        if pattern.search(text) and flag not in flags:
            flags.append(flag)

    cleaned = _sanitize(text) if flags else text
    blocked = any(f in _BLOCKING for f in flags)
    return GuardrailVerdict(flags=flags, cleaned_text=cleaned, blocked=blocked)


def _sanitize(text: str) -> str:
    """Neuter the most common injection payloads while preserving intent.

    We deliberately keep the original surrounding text so the human triager
    can still see what the reporter wrote.
    """
    out = text
    for _, pattern in _PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out
