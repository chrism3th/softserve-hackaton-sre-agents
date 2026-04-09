"""Domain models for the Ticket Orchestrator pipeline."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IncidentSource(StrEnum):
    api = "api"
    github_issue = "github_issue"


class IncidentImage(BaseModel):
    url: str
    mime: str | None = None


class ImageInsight(BaseModel):
    url: str
    caption: str = ""
    extracted_text: str = ""
    error_signals: list[str] = Field(default_factory=list)
    error: str | None = None  # populated if analysis failed


class IncidentDTO(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(default="", max_length=20_000)
    reporter: str | None = None
    source: IncidentSource = IncidentSource.api
    images: list[IncidentImage] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class Severity(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class GuardrailFlag(StrEnum):
    instruction_override = "instruction_override"
    role_hijack = "role_hijack"
    secret_exfil = "secret_exfil"  # noqa: S105
    code_fence_injection = "code_fence_injection"
    suspicious_url = "suspicious_url"


class GuardrailVerdict(BaseModel):
    flags: list[GuardrailFlag] = Field(default_factory=list)
    cleaned_text: str
    blocked: bool = False

    @property
    def triggered(self) -> bool:
        return bool(self.flags)


class OrchestratorResult(BaseModel):
    linear_identifier: str | None = None
    linear_url: str | None = None
    severity: Severity
    score: int = Field(ge=0, le=100)
    dedup_of: str | None = None
    guardrail_flags: list[GuardrailFlag] = Field(default_factory=list)
    blocked: bool = False
    title: str
    description: str
