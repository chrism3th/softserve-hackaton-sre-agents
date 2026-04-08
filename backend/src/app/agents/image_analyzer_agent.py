"""Image Analyzer agent — Claude Vision over incident attachments.

Receives a list of ``IncidentImage`` (URLs extracted from a GitHub issue
or API payload) and produces ``ImageInsight`` objects: caption, OCR-like
text transcription, and concrete error signals the on-call engineer
should care about.

## Safety

Image URLs come from untrusted user input, so the analyzer enforces a
**host allowlist** before sending the URL to Claude. Anything pointing
outside the allowlist is rejected with an ``error`` field on the insight
(no SSRF, no exfiltration). The allowlist covers GitHub's user-content
hosts and the standard image-hosting CDNs we expect from real reporters.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError

from app.agents.base import Agent, AgentRequest, AgentResponse
from app.agents.prompts import load_prompt
from app.config import get_settings
from app.core.logging import get_logger
from app.tickets.models import ImageInsight, IncidentImage

logger = get_logger(__name__)

# Hosts we trust enough to forward to Claude. Subdomain match is suffix-based.
_HOST_ALLOWLIST: tuple[str, ...] = (
    "user-images.githubusercontent.com",
    "private-user-images.githubusercontent.com",
    "github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
)


class _LLMImageOutput(BaseModel):
    caption: str = ""
    extracted_text: str = ""
    error_signals: list[str] = Field(default_factory=list)


class ImageAnalyzerAgent(Agent):
    """Extract visual evidence from incident attachments."""

    name = "image_analyzer"

    async def run(self, request: AgentRequest) -> AgentResponse:
        ctx = request.context or {}
        urls = ctx.get("images") or []
        if not urls and request.input:
            urls = [request.input]
        images = [IncidentImage(url=u) if isinstance(u, str) else IncidentImage(**u) for u in urls]
        insights = await self.analyze(images)
        return AgentResponse(
            output=insights[0].caption if insights else "no images",
            agent=self.name,
            iterations=1,
            metadata={"insights": [i.model_dump() for i in insights]},
        )

    async def analyze(self, images: list[IncidentImage]) -> list[ImageInsight]:
        if not images:
            return []
        settings = get_settings()
        if not settings.anthropic_api_key:
            logger.warning("image_analyzer.no_api_key")
            return [ImageInsight(url=img.url, error="no_api_key") for img in images]

        results: list[ImageInsight] = []
        for img in images:
            insight = await self._analyze_one(img)
            results.append(insight)
        return results

    async def _analyze_one(self, image: IncidentImage) -> ImageInsight:
        if not _is_allowed(image.url):
            logger.warning("image_analyzer.host_blocked", url=image.url)
            return ImageInsight(url=image.url, error="host_not_allowed")

        try:
            from anthropic import AsyncAnthropic

            settings = get_settings()
            client = AsyncAnthropic(
                api_key=settings.anthropic_api_key,
                timeout=settings.llm_timeout_seconds,
            )
            message = await client.messages.create(
                model=settings.llm_model,
                max_tokens=600,
                system=load_prompt("image_analyzer"),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "url", "url": image.url},
                            },
                            {
                                "type": "text",
                                "text": "Analyze this incident attachment.",
                            },
                        ],
                    }
                ],
            )
            raw = "".join(
                b.text for b in message.content if getattr(b, "type", "") == "text"
            )
            parsed = _LLMImageOutput.model_validate_json(_extract_json(raw))
            return ImageInsight(
                url=image.url,
                caption=parsed.caption,
                extracted_text=parsed.extracted_text,
                error_signals=parsed.error_signals,
            )
        except ValidationError as e:
            logger.warning("image_analyzer.parse_failed", error=str(e))
            return ImageInsight(url=image.url, error="parse_failed")
        except Exception as e:  # noqa: BLE001
            logger.warning("image_analyzer.failed", error=str(e), url=image.url)
            return ImageInsight(url=image.url, error=str(e)[:200])


def _is_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in _HOST_ALLOWLIST)


def _extract_json(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text
