"""GitHub webhook setup endpoint.

Provides a convenience endpoint to register the GitHub webhook on the
configured repository so that issue events are delivered to this backend.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.core.logging import get_logger
from app.integrations.github.client import GitHubClient, GitHubError

logger = get_logger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


class SetupWebhookRequest(BaseModel):
    payload_url: str = Field(
        ...,
        description="Public HTTPS URL where GitHub will deliver webhook events, "
        "e.g. https://xxxx.ngrok-free.app/api/v1/tickets/github-webhook",
    )


class SetupWebhookResponse(BaseModel):
    created: bool
    webhook_id: int | None = None
    message: str


@router.post(
    "/setup-webhook",
    response_model=SetupWebhookResponse,
    summary="Register or verify the GitHub issues webhook",
)
async def setup_webhook(body: SetupWebhookRequest) -> SetupWebhookResponse:
    settings = get_settings()

    if not settings.github_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GITHUB_REPO is not configured",
        )
    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GITHUB_WEBHOOK_SECRET is not configured",
        )

    try:
        async with GitHubClient() as client:
            # Check if a webhook with this URL already exists.
            hooks = await client.list_webhooks(settings.github_repo)
            for hook in hooks:
                config = hook.get("config", {})
                if config.get("url") == body.payload_url:
                    logger.info(
                        "github.webhook_already_exists",
                        webhook_id=hook.get("id"),
                        url=body.payload_url,
                    )
                    return SetupWebhookResponse(
                        created=False,
                        webhook_id=hook.get("id"),
                        message=f"Webhook already exists (id={hook.get('id')})",
                    )

            # Create a new webhook.
            result = await client.create_webhook(
                repo=settings.github_repo,
                url=body.payload_url,
                secret=settings.github_webhook_secret,
                events=["issues"],
            )

            logger.info(
                "github.webhook_created",
                webhook_id=result.get("id"),
                url=body.payload_url,
            )
            return SetupWebhookResponse(
                created=True,
                webhook_id=result.get("id"),
                message="Webhook created successfully",
            )

    except GitHubError as e:
        logger.error("github.setup_webhook_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
