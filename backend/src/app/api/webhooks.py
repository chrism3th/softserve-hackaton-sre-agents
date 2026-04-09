"""Webhook ingestion endpoints.

Currently handles Linear webhooks.  Adding a new provider means adding a
new route — the rest of the stack (parser → dispatcher → actions) is
provider-agnostic.

Linear webhook spec: https://developers.linear.app/docs/graphql/webhooks
"""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from pydantic import ValidationError

from app.config import get_settings
from app.core.event_dispatcher import event_dispatcher
from app.core.logging import get_logger
from app.integrations.linear.parser import parse_webhook
from app.integrations.linear.schemas import LinearWebhookPayload

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Linear retries on HTTP 500; any other non-200 is treated as final.
# We use 204 (no body) to keep the response fast.
_WEBHOOK_OK = status.HTTP_204_NO_CONTENT

# Replay-attack window: reject payloads older than this many seconds.
_MAX_AGE_SECONDS = 300  # 5 minutes (Linear docs suggest 60 s; 5 min is lenient)


@router.post("/linear", status_code=_WEBHOOK_OK, summary="Linear webhook receiver")
async def linear_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    linear_signature: str | None = Header(default=None, alias="Linear-Signature"),
) -> None:
    """Receive, validate, parse and dispatch a Linear webhook event.

    Returns 204 immediately after scheduling dispatch as a background
    task — the webhook caller is never blocked by handler execution.
    """
    body = await request.body()

    _verify_signature(body, linear_signature)

    try:
        payload = LinearWebhookPayload.model_validate_json(body)
    except ValidationError as exc:
        logger.warning("linear_webhook.invalid_payload", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload shape",
        ) from exc

    _check_timestamp(payload.webhookTimestamp)

    logger.info(
        "linear_webhook.received",
        action=payload.action,
        entity_type=payload.type,
        webhook_id=payload.webhookId,
    )

    if payload.action == "update":
        logger.debug(
            "linear_webhook.update_detail",
            updated_from=payload.updatedFrom.model_dump() if payload.updatedFrom else None,
            current_state=payload.data.state.model_dump() if payload.data.state else None,
        )

    event = parse_webhook(payload)

    if event is None:
        logger.debug(
            "linear_webhook.ignored",
            action=payload.action,
            entity_type=payload.type,
        )
        return

    logger.info(
        "linear_webhook.dispatching",
        event_type=event.event_type,
        issue=event.issue_identifier,
    )

    # Schedule dispatch as a background task so we return 204 immediately.
    # Linear considers any non-500 response a success and won't retry.
    background_tasks.add_task(event_dispatcher.dispatch, event)


# ── helpers ──────────────────────────────────────────────────────────────────


def _verify_signature(body: bytes, signature: str | None) -> None:
    """Verify the Linear-Signature HMAC-SHA256 header.

    Linear sends a raw hex digest (no "sha256=" prefix).
    If no secret is configured (local dev), the check is skipped with a warning.
    """
    secret = get_settings().linear_webhook_secret
    if not secret:
        logger.warning("linear_webhook.no_secret_configured")
        return

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Linear-Signature header",
        )

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )


def _check_timestamp(webhook_timestamp_ms: int | None) -> None:
    """Reject payloads that are too old (replay-attack mitigation).

    Linear docs recommend a 60-second window; we use 5 minutes to be
    lenient with clock skew in dev environments.
    """
    if webhook_timestamp_ms is None:
        return  # field is optional in the spec; skip check if absent

    age_seconds = abs(time.time() - webhook_timestamp_ms / 1000)
    if age_seconds > _MAX_AGE_SECONDS:
        logger.warning(
            "linear_webhook.stale_payload",
            age_seconds=age_seconds,
            max_age=_MAX_AGE_SECONDS,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is too old",
        )
