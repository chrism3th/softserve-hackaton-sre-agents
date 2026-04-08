"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    """Return 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe")
async def readyz() -> dict[str, str]:
    """Return 200 if the app is ready to serve traffic.

    In a real deployment, extend this to verify downstream dependencies
    (database, cache, LLM provider) before returning OK.
    """
    return {"status": "ready"}
