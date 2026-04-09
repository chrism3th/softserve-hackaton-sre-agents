"""Tests for the reporter notification pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.actions.handlers.notify_reporter import NotifyReporterAction
from app.domain.events import DomainEvent, EventType, IssueState, IssueStatusChangedEvent
from app.services.email_service import TRIGGER_STATES, _render_template, notify_status_change

# ── helpers ───────────────────────────────────────────────────────────────────

NOW = datetime.now(timezone.utc)


def _make_event(
    state_name: str = "Done",
    state_type: str = "completed",
    reporter_email: str | None = "reporter@example.com",
) -> IssueStatusChangedEvent:
    return IssueStatusChangedEvent(
        issue_id="issue-1",
        issue_identifier="TEA-42",
        issue_title="Production is on fire",
        team_key="TEA",
        occurred_at=NOW,
        previous_state=IssueState(id="prev", name="In Progress", type="started"),
        current_state=IssueState(id="curr", name=state_name, type=state_type),
        reporter_email=reporter_email,
    )


# ── email_service tests ───────────────────────────────────────────────────────


class TestRenderTemplate:
    def test_done_subject_and_body(self) -> None:
        subject, html = _render_template("TEA-42", "Fire alert", "Done")
        assert "completada" in subject
        assert "TEA-42" in subject
        assert "Done" in html or "completada" in html.lower()
        assert "TEA-42" in html
        assert "Fire alert" in html

    def test_ready_to_start_subject_and_body(self) -> None:
        subject, html = _render_template("TEA-42", "Fire alert", "Ready to Start")
        assert "lista para comenzar" in subject
        assert "TEA-42" in subject
        assert "Ready to Start" in html
        assert "Fire alert" in html

    def test_trigger_states_are_case_insensitive(self) -> None:
        assert "done" in TRIGGER_STATES
        assert "todo" in TRIGGER_STATES


class TestNotifyStatusChange:
    async def test_sends_email_for_done(self) -> None:
        with patch(
            "app.services.email_service.resend_client.send",
            new_callable=AsyncMock,
            return_value="msg-id-123",
        ) as mock_send:
            await notify_status_change(
                to="user@example.com",
                issue_identifier="TEA-42",
                issue_title="Fire",
                new_state="Done",
            )
        mock_send.assert_awaited_once()
        call = mock_send.call_args
        assert call.kwargs["to"] == "user@example.com"
        assert "TEA-42" in call.kwargs["subject"]

    async def test_sends_email_for_todo(self) -> None:
        with patch(
            "app.services.email_service.resend_client.send",
            new_callable=AsyncMock,
            return_value="msg-id-456",
        ) as mock_send:
            await notify_status_change(
                to="user@example.com",
                issue_identifier="TEA-1",
                issue_title="Deploy",
                new_state="Todo",
            )
        mock_send.assert_awaited_once()

    async def test_skips_non_trigger_state(self) -> None:
        with patch(
            "app.services.email_service.resend_client.send",
            new_callable=AsyncMock,
        ) as mock_send:
            await notify_status_change(
                to="user@example.com",
                issue_identifier="TEA-1",
                issue_title="Deploy",
                new_state="In Progress",
            )
        mock_send.assert_not_awaited()

    async def test_logs_and_swallows_resend_error(self) -> None:
        import resend.exceptions

        exc = resend.exceptions.ResendError("bad request", 400, "validation_error", "fix it")

        with patch(
            "app.services.email_service.resend_client.send",
            new_callable=AsyncMock,
            side_effect=exc,
        ):
            # Must not raise
            await notify_status_change(
                to="user@example.com",
                issue_identifier="TEA-1",
                issue_title="Fire",
                new_state="Done",
            )

    async def test_logs_and_swallows_unexpected_error(self) -> None:
        with patch(
            "app.services.email_service.resend_client.send",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network down"),
        ):
            await notify_status_change(
                to="user@example.com",
                issue_identifier="TEA-1",
                issue_title="Fire",
                new_state="Done",
            )


# ── NotifyReporterAction tests ────────────────────────────────────────────────


class TestNotifyReporterAction:
    async def test_sends_for_done(self) -> None:
        action = NotifyReporterAction()
        event = _make_event(state_name="Done", reporter_email="r@example.com")
        with patch(
            "app.actions.handlers.notify_reporter.notify_status_change",
            new_callable=AsyncMock,
        ) as mock_notify:
            await action.execute(event)
        mock_notify.assert_awaited_once_with(
            to="r@example.com",
            issue_identifier="TEA-42",
            issue_title="Production is on fire",
            new_state="Done",
        )

    async def test_sends_for_todo(self) -> None:
        action = NotifyReporterAction()
        event = _make_event(state_name="Todo", state_type="unstarted")
        with patch(
            "app.actions.handlers.notify_reporter.notify_status_change",
            new_callable=AsyncMock,
        ) as mock_notify:
            await action.execute(event)
        mock_notify.assert_awaited_once()

    async def test_skips_non_trigger_state(self) -> None:
        action = NotifyReporterAction()
        event = _make_event(state_name="In Progress", state_type="started")
        with patch(
            "app.actions.handlers.notify_reporter.notify_status_change",
            new_callable=AsyncMock,
        ) as mock_notify:
            await action.execute(event)
        mock_notify.assert_not_awaited()

    async def test_skips_when_no_email(self) -> None:
        action = NotifyReporterAction()
        event = _make_event(state_name="Done", reporter_email=None)
        with patch(
            "app.actions.handlers.notify_reporter.notify_status_change",
            new_callable=AsyncMock,
        ) as mock_notify:
            await action.execute(event)
        mock_notify.assert_not_awaited()

    async def test_ignores_non_status_changed_event(self) -> None:
        action = NotifyReporterAction()
        other_event = DomainEvent(
            event_type=EventType.issue_created,
            issue_id="x",
            issue_identifier="TEA-1",
            issue_title="T",
            team_key="TEA",
            occurred_at=NOW,
        )
        with patch(
            "app.actions.handlers.notify_reporter.notify_status_change",
            new_callable=AsyncMock,
        ) as mock_notify:
            await action.execute(other_event)
        mock_notify.assert_not_awaited()
