"""Smoke test: resolve TEA team and create a sample issue in Linear.

Usage (inside backend container):
    python scripts/linear_smoke.py
"""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.tickets.linear_client import LinearClient


async def main() -> None:
    settings = get_settings()
    async with LinearClient() as client:
        team_id = await client.get_team_id(settings.linear_team_key)
        print(f"team {settings.linear_team_key} -> {team_id}")
        issue = await client.create_issue(
            team_id=team_id,
            title="[smoke] Ticket Orchestrator connectivity test",
            description=(
                "Created by `scripts/linear_smoke.py` to validate the "
                "Linear API wiring for the SRE Ticket Orchestrator agent."
            ),
            priority=3,
        )
        print(f"created {issue['identifier']}: {issue['url']}")


if __name__ == "__main__":
    asyncio.run(main())
