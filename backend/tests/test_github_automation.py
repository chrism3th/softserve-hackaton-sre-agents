"""Tests for GitHub automation agents and actions."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.actions.handlers.github_automation import (
    GitHubIssueCommentAutomationAction,
    QAHandoffAutomationAction,
    _extract_github_issue_url,
)
from app.agents.base import AgentRequest
from app.agents.github_issue_commenter_agent import GitHubIssueCommenterAgent
from app.agents.qa_handoff_agent import QAHandoffAgent
from app.config import get_settings
from app.domain.events import IssueState, IssueStatusChangedEvent
from app.integrations.github.schemas import (
    GitHubIssueReference,
    GitHubPullRequestResponse,
    GitHubRequestedReviewersResponse,
)

NOW = datetime.now(UTC)


@pytest.fixture()
def github_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_API_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPO", "acme/repo")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _event(to_state: str = "In Progress") -> IssueStatusChangedEvent:
    return IssueStatusChangedEvent(
        issue_id="issue-id",
        issue_identifier="TEA-42",
        issue_title="Investigate outage",
        team_key="TEA",
        occurred_at=NOW,
        previous_state=IssueState(id="s1", name="Todo", type="unstarted"),
        current_state=IssueState(id="s2", name=to_state, type="started"),
        reporter_email="reporter@example.com",
    )


class TestExtractGitHubIssueUrl:
    def test_extracts_url_from_description(self) -> None:
        desc = "**Source:** github_issue\n**GitHub Issue:** https://github.com/acme/repo/issues/42\n\n## Summary"
        assert _extract_github_issue_url(desc) == "https://github.com/acme/repo/issues/42"

    def test_returns_none_when_no_url(self) -> None:
        assert _extract_github_issue_url("Just a regular description") is None

    def test_returns_none_for_none_description(self) -> None:
        assert _extract_github_issue_url(None) is None

    def test_extracts_url_with_org_and_numbers(self) -> None:
        desc = "**GitHub Issue:** https://github.com/my-org/my-repo-123/issues/999"
        assert _extract_github_issue_url(desc) == "https://github.com/my-org/my-repo-123/issues/999"

    def test_extracts_url_from_markdown_link(self) -> None:
        desc = "**GitHub Issue:** [https://github.com/acme/repo/issues/42](https://github.com/acme/repo/issues/42)"
        assert _extract_github_issue_url(desc) == "https://github.com/acme/repo/issues/42"

    def test_extracts_url_from_markdown_link_with_angle_brackets(self) -> None:
        desc = "**GitHub Issue:** [https://github.com/GMBarra/reaction/issues/7](<https://github.com/GMBarra/reaction/issues/7>)"
        assert _extract_github_issue_url(desc) == "https://github.com/GMBarra/reaction/issues/7"


class TestGitHubIssueCommenterAgent:
    async def test_posts_comment_on_state_change(self, github_env: None) -> None:
        agent = GitHubIssueCommenterAgent()
        request = AgentRequest(
            input="state change",
            context={
                "repo": "acme/repo",
                "linear_issue_id": "TEA-42",
                "from_state": "Todo",
                "to_state": "In Progress",
            },
        )

        with patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.find_issue_by_branch_or_title",
            new_callable=AsyncMock,
            return_value=GitHubIssueReference(number=7),
        ), patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.create_issue_comment",
            new_callable=AsyncMock,
        ) as create_comment:
            response = await agent.run(request)

        assert "issue #7" in response.output
        create_comment.assert_awaited_once()

    async def test_skips_when_issue_not_found(self, github_env: None) -> None:
        agent = GitHubIssueCommenterAgent()
        request = AgentRequest(
            input="state change",
            context={
                "repo": "acme/repo",
                "linear_issue_id": "TEA-42",
                "from_state": "Todo",
                "to_state": "QA",
            },
        )

        with patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.find_issue_by_branch_or_title",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.create_issue_comment",
            new_callable=AsyncMock,
        ) as create_comment:
            response = await agent.run(request)

        assert "skipped" in response.output.lower()
        create_comment.assert_not_awaited()

    async def test_uses_direct_url_when_available(self, github_env: None) -> None:
        agent = GitHubIssueCommenterAgent()
        request = AgentRequest(
            input="state change",
            context={
                "repo": "acme/repo",
                "linear_issue_id": "TEA-42",
                "from_state": "Todo",
                "to_state": "In Progress",
                "github_issue_url": "https://github.com/acme/repo/issues/15",
            },
        )

        with patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.find_issue_by_branch_or_title",
            new_callable=AsyncMock,
        ) as find_issue, patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.create_issue_comment",
            new_callable=AsyncMock,
        ) as create_comment:
            response = await agent.run(request)

        assert "issue #15" in response.output
        # Should NOT call the heuristic search when URL is available.
        find_issue.assert_not_awaited()
        create_comment.assert_awaited_once()

    async def test_passes_title_and_branch_lookup_hints(self, github_env: None) -> None:
        agent = GitHubIssueCommenterAgent()
        request = AgentRequest(
            input="state change",
            context={
                "repo": "acme/repo",
                "linear_issue_id": "TEA-42",
                "linear_title": "Investigate outage",
                "linear_branch_name": "tea-42",
                "from_state": "Todo",
                "to_state": "In Review",
            },
        )

        with patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.find_issue_by_branch_or_title",
            new_callable=AsyncMock,
            return_value=GitHubIssueReference(number=7),
        ) as find_issue, patch(
            "app.agents.github_issue_commenter_agent.GitHubClient.create_issue_comment",
            new_callable=AsyncMock,
        ):
            await agent.run(request)

        find_issue.assert_awaited_once_with(
            "acme/repo",
            "TEA-42",
            linear_title="Investigate outage",
            linear_branch_name="tea-42",
        )


class TestQAHandoffAgent:
    async def test_noop_when_state_is_not_qa(self, github_env: None) -> None:
        agent = QAHandoffAgent()
        request = AgentRequest(
            input="state change",
            context={
                "repo": "acme/repo",
                "linear_issue_id": "TEA-42",
                "linear_title": "Investigate outage",
                "linear_branch_name": "tea-42",
                "to_state": "In Progress",
            },
        )

        with patch(
            "app.agents.qa_handoff_agent.GitHubClient.create_pull_request",
            new_callable=AsyncMock,
        ) as create_pr:
            response = await agent.run(request)

        assert "no-op" in response.output.lower()
        create_pr.assert_not_awaited()

    async def test_creates_pr_and_requests_copilot_review(self, github_env: None) -> None:
        agent = QAHandoffAgent()
        request = AgentRequest(
            input="state change",
            context={
                "repo": "acme/repo",
                "linear_issue_id": "TEA-42",
                "linear_title": "Investigate outage",
                "linear_branch_name": "tea-42",
                "to_state": "QA",
            },
        )

        with patch(
            "app.agents.qa_handoff_agent.GitHubClient.create_pull_request",
            new_callable=AsyncMock,
            return_value=GitHubPullRequestResponse(number=99),
        ) as create_pr, patch(
            "app.agents.qa_handoff_agent.GitHubClient.request_reviewer",
            new_callable=AsyncMock,
            return_value=GitHubRequestedReviewersResponse(id=1),
        ) as request_reviewer:
            response = await agent.run(request)

        assert "#99" in response.output
        create_pr.assert_awaited_once_with(
            repo="acme/repo",
            title="[TEA-42] Investigate outage",
            head_branch="tea-42",
            base_branch="main",
            body="Auto-created from Linear QA state transition.",
        )
        request_reviewer.assert_awaited_once_with(
            repo="acme/repo",
            pr_number=99,
            reviewers=["copilot-pull-request-reviewer[bot]"],
        )


class TestBuildContext:
    async def test_includes_github_url_from_description(self) -> None:
        from app.actions.handlers.github_automation import _build_context

        event = IssueStatusChangedEvent(
            issue_id="id",
            issue_identifier="TEA-1",
            issue_title="Fix bug",
            issue_description="**GitHub Issue:** https://github.com/acme/repo/issues/7",
            team_key="TEA",
            occurred_at=NOW,
            previous_state=IssueState(id="s1", name="Todo", type="unstarted"),
            current_state=IssueState(id="s2", name="In Progress", type="started"),
        )
        ctx = await _build_context(event)
        assert ctx["github_issue_url"] == "https://github.com/acme/repo/issues/7"

    async def test_fetches_url_from_api_when_not_in_event(self) -> None:
        from app.actions.handlers.github_automation import _build_context

        event = IssueStatusChangedEvent(
            issue_id="id",
            issue_identifier="TEA-1",
            issue_title="Fix bug",
            team_key="TEA",
            occurred_at=NOW,
            previous_state=IssueState(id="s1", name="Todo", type="unstarted"),
            current_state=IssueState(id="s2", name="In Progress", type="started"),
        )
        with patch(
            "app.actions.handlers.github_automation.LinearClient",
        ) as mock_linear_cls:
            mock_client = AsyncMock()
            mock_client.get_issue_description = AsyncMock(
                return_value="**GitHub Issue:** https://github.com/acme/repo/issues/99"
            )
            mock_linear_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_linear_cls.return_value.__aexit__ = AsyncMock(return_value=None)
            ctx = await _build_context(event)

        assert ctx["github_issue_url"] == "https://github.com/acme/repo/issues/99"

    async def test_github_url_is_none_when_not_found(self) -> None:
        from app.actions.handlers.github_automation import _build_context

        event = IssueStatusChangedEvent(
            issue_id="id",
            issue_identifier="TEA-1",
            issue_title="Fix bug",
            team_key="TEA",
            occurred_at=NOW,
            previous_state=IssueState(id="s1", name="Todo", type="unstarted"),
            current_state=IssueState(id="s2", name="In Progress", type="started"),
        )
        with patch(
            "app.actions.handlers.github_automation.LinearClient",
        ) as mock_linear_cls:
            mock_client = AsyncMock()
            mock_client.get_issue_description = AsyncMock(return_value="No github url here")
            mock_linear_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_linear_cls.return_value.__aexit__ = AsyncMock(return_value=None)
            ctx = await _build_context(event)

        assert ctx["github_issue_url"] is None


class TestAutomationActions:
    async def test_comment_action_invokes_agent(self, github_env: None) -> None:
        action = GitHubIssueCommentAutomationAction()
        agent = MagicMock()
        agent.run = AsyncMock()

        with patch(
            "app.actions.handlers.github_automation.get_agent",
            return_value=agent,
        ) as get_agent_mock:
            await action.execute(_event(to_state="In Review"))

        get_agent_mock.assert_called_once_with("github_issue_commenter")
        agent.run.assert_awaited_once()
        request = agent.run.call_args.args[0]
        assert isinstance(request, AgentRequest)
        assert request.context["linear_branch_name"] == "fix/tea-42"

    async def test_qa_action_invokes_agent_for_qa_transition(self, github_env: None) -> None:
        action = QAHandoffAutomationAction()
        agent = MagicMock()
        agent.run = AsyncMock()

        with patch(
            "app.actions.handlers.github_automation.get_agent",
            return_value=agent,
        ) as get_agent_mock:
            await action.execute(_event(to_state="QA"))

        get_agent_mock.assert_called_once_with("qa_handoff")
        agent.run.assert_awaited_once()
