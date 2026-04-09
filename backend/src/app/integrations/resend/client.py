"""Thin async wrapper around the Resend Python SDK.

Uses ``resend.Emails.send_async`` (native async, backed by httpx).

The API key is read from settings on every send() call — not cached at
import time — so the correct key is always used regardless of when the
module is first imported relative to env-var loading.
"""

from __future__ import annotations

import resend

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ResendClient:
    async def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
    ) -> str:
        """Send an email and return the Resend message ID.

        Raises ``ValueError`` if no API key is configured.
        Raises ``resend.exceptions.ResendError`` on API-level failures.
        """
        settings = get_settings()

        if not settings.resend_api_key:
            raise ValueError(
                "RESEND_API_KEY is not set — add it to .env and docker-compose.yml"
            )

        # resend.api_key is a module-level global; set it before every call
        # so it stays in sync with settings (e.g. after a hot-reload).
        resend.api_key = settings.resend_api_key

        params: resend.Emails.SendParams = {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }

        response: resend.Emails.SendResponse = await resend.Emails.send_async(params)
        message_id = str(response["id"])
        logger.info("email.sent", to=to, subject=subject, message_id=message_id)
        return message_id


resend_client = ResendClient()
