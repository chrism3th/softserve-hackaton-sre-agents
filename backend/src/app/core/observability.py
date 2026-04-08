"""OpenTelemetry tracing wired to Arize Phoenix.

Why Phoenix and not Langfuse: OpenTelemetry-native means we can swap the
backend (Phoenix → Tempo → Honeycomb → vendor X) without touching agent
code, and the same instrumentation scales to a real production OTel
collector pipeline.

Auto-instrumentation of the Anthropic SDK comes from
``openinference-instrumentation-anthropic`` — every ``messages.create``
call becomes a span with model, prompt, completion, and token usage.

Custom orchestration spans are added explicitly via ``get_tracer()``.
"""

from __future__ import annotations

from functools import lru_cache

from opentelemetry import trace
from opentelemetry.trace import Tracer

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_initialized = False


def init_tracing() -> None:
    """Initialise the tracer provider and auto-instrument Anthropic.

    Idempotent: safe to call from app startup and from tests.
    """
    global _initialized
    if _initialized:
        return

    settings = get_settings()
    try:
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
        from phoenix.otel import register

        register(
            project_name=settings.phoenix_project_name,
            endpoint=f"{settings.phoenix_collector_endpoint}/v1/traces",
            auto_instrument=False,
            set_global_tracer_provider=True,
        )
        AnthropicInstrumentor().instrument()
        logger.info(
            "tracing.initialized",
            backend="phoenix",
            endpoint=settings.phoenix_collector_endpoint,
            project=settings.phoenix_project_name,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("tracing.init_failed", error=str(e))
    finally:
        _initialized = True


@lru_cache(maxsize=1)
def get_tracer() -> Tracer:
    return trace.get_tracer("app.agents")
