"""Async client for the Linear GraphQL API.

Minimal surface needed for the Ticket Orchestrator: resolve a team by key,
search issues for dedup, and create issues.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class LinearError(RuntimeError):
    """Raised when the Linear API returns an error."""


class LinearClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.linear_api_key
        self._api_url = api_url or settings.linear_api_url
        if not self._api_key:
            raise LinearError("LINEAR_API_KEY is not set")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": self._api_key,
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> LinearClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _gql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = await self._client.post(
            self._api_url,
            json={"query": query, "variables": variables or {}},
        )
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            logger.error("linear.graphql_error", errors=payload["errors"])
            raise LinearError(str(payload["errors"]))
        return cast(dict[str, Any], payload["data"])

    async def get_team_id(self, key: str) -> str:
        data = await self._gql(
            """
            query TeamByKey($key: String!) {
              teams(filter: { key: { eq: $key } }) { nodes { id key name } }
            }
            """,
            {"key": key},
        )
        nodes = data["teams"]["nodes"]
        if not nodes:
            raise LinearError(f"Linear team with key '{key}' not found")
        return str(nodes[0]["id"])

    async def search_issues(self, team_id: str, term: str, limit: int = 10) -> list[dict[str, Any]]:
        data = await self._gql(
            """
            query Search($filter: IssueFilter, $first: Int) {
              issues(filter: $filter, first: $first) {
                nodes { id identifier title url description state { name } }
              }
            }
            """,
            {
                "filter": {
                    "team": {"id": {"eq": team_id}},
                    "title": {"containsIgnoreCase": term},
                },
                "first": limit,
            },
        )
        return list(data["issues"]["nodes"])

    async def get_issue_description(self, issue_id: str) -> str | None:
        """Fetch the description of an issue by its UUID."""
        data = await self._gql(
            """
            query Issue($id: String!) {
              issue(id: $id) { description }
            }
            """,
            {"id": issue_id},
        )
        issue = data.get("issue")
        return issue.get("description") if issue else None

    async def find_label_by_name(self, team_id: str, name: str) -> str | None:
        """Return the label ID for *name* in the given team, or ``None``."""
        data = await self._gql(
            """
            query Labels($filter: IssueLabelFilter) {
              issueLabels(filter: $filter) { nodes { id name } }
            }
            """,
            {
                "filter": {
                    "team": {"id": {"eq": team_id}},
                    "name": {"eqIgnoreCase": name},
                },
            },
        )
        nodes = data["issueLabels"]["nodes"]
        return str(nodes[0]["id"]) if nodes else None

    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: str,
        priority: int = 0,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        data = await self._gql(
            """
            mutation Create($input: IssueCreateInput!) {
              issueCreate(input: $input) {
                success
                issue { id identifier title url }
              }
            }
            """,
            {
                "input": {
                    "teamId": team_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    **({"labelIds": label_ids} if label_ids else {}),
                }
            },
        )
        result = data["issueCreate"]
        if not result["success"]:
            raise LinearError("issueCreate returned success=false")
        return dict(result["issue"])

    async def update_issue_description(
        self, issue_id: str, description: str
    ) -> None:
        """Update the description of an existing issue."""
        data = await self._gql(
            """
            mutation Update($id: String!, $input: IssueUpdateInput!) {
              issueUpdate(id: $id, input: $input) { success }
            }
            """,
            {"id": issue_id, "input": {"description": description}},
        )
        if not data["issueUpdate"]["success"]:
            raise LinearError("issueUpdate returned success=false")
