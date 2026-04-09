"""Email notification service.

Owns the decision of *when* to send, *what* template to render, and
delegates the actual delivery to ``ResendClient``.  Business logic lives
here; transport details stay in the client.

To add a new trigger state, extend ``TRIGGER_STATES`` and add a branch
in ``_render_template``.
"""

from __future__ import annotations

import resend.exceptions

from app.core.logging import get_logger
from app.integrations.resend.client import resend_client

logger = get_logger(__name__)

# State names (lowercased) that trigger a notification email.
TRIGGER_STATES: frozenset[str] = frozenset({"done", "todo"})


async def notify_status_change(
    *,
    to: str,
    issue_identifier: str,
    issue_title: str,
    new_state: str,
) -> None:
    """Send a status-change notification to the issue reporter.

    Silently skips states not in ``TRIGGER_STATES``.
    Logs and suppresses any delivery errors so callers are never blocked.
    """
    if new_state.lower() not in TRIGGER_STATES:
        return

    subject, html = _render_template(issue_identifier, issue_title, new_state)

    try:
        msg_id = await resend_client.send(to=to, subject=subject, html=html)
        logger.info(
            "email_service.sent",
            to=to,
            msg_id=msg_id,
            state=new_state,
            issue=issue_identifier,
        )
    except resend.exceptions.ResendError as exc:
        logger.error(
            "email_service.send_failed",
            to=to,
            state=new_state,
            issue=issue_identifier,
            error=exc.message,
            code=exc.code,
        )
    except Exception:
        logger.exception(
            "email_service.unexpected_error",
            to=to,
            state=new_state,
            issue=issue_identifier,
        )


def _render_template(
    identifier: str,
    title: str,
    state: str,
) -> tuple[str, str]:
    """Return (subject, html) for the given state name."""
    if state.lower() == "done":
        return _render_done(identifier, title)
    return _render_ready_to_start(identifier, title, state)


def _render_done(identifier: str, title: str) -> tuple[str, str]:
    subject = f"Your issue has been completed — {identifier}"
    html = f"""
<!DOCTYPE html>
<html lang="en">
<body style="font-family:sans-serif;color:#1a1a1a;max-width:560px;margin:auto;padding:24px">
  <h2 style="color:#16a34a">Issue completed</h2>
  <p>The following issue has been marked as <strong>Done</strong>:</p>
  <blockquote style="border-left:4px solid #16a34a;padding:8px 16px;margin:16px 0;color:#374151">
    <strong>{identifier}</strong> — {title}
  </blockquote>
  <p>Thank you for reporting it. The team has finished working on it.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
  <p style="font-size:12px;color:#6b7280">This message was sent automatically by the SRE system.</p>
</body>
</html>
""".strip()
    return subject, html


def _render_ready_to_start(identifier: str, title: str, state: str) -> tuple[str, str]:
    subject = f"Your issue is ready to start — {identifier}"
    html = f"""
<!DOCTYPE html>
<html lang="en">
<body style="font-family:sans-serif;color:#1a1a1a;max-width:560px;margin:auto;padding:24px">
  <h2 style="color:#2563eb">Issue ready to start</h2>
  <p>The following issue has moved to <strong>{state}</strong>:</p>
  <blockquote style="border-left:4px solid #2563eb;padding:8px 16px;margin:16px 0;color:#374151">
    <strong>{identifier}</strong> — {title}
  </blockquote>
  <p>Your request is now queued for work. The team will begin shortly.</p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
  <p style="font-size:12px;color:#6b7280">This message was sent automatically by the SRE system.</p>
</body>
</html>
""".strip()
    return subject, html
