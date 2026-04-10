"""Registry of agent implementations.

Register new agents here by importing and adding them to ``_REGISTRY``.
Keep this simple: a dict is a perfectly good registry for dozens of agents.
"""

from __future__ import annotations

from app.agents.base import Agent, EchoAgent
from app.agents.branch_creator_agent import BranchCreatorAgent
from app.agents.claude_agent import ClaudeAgent
from app.agents.dedup_agent import DedupAgent
from app.agents.github_issue_commenter_agent import GitHubIssueCommenterAgent
from app.agents.guardrail_agent import GuardrailAgent
from app.agents.image_analyzer_agent import ImageAnalyzerAgent
from app.agents.qa_handoff_agent import QAHandoffAgent
from app.agents.ticket_orchestrator import TicketOrchestratorAgent
from app.agents.triage_drafter_agent import TriageDrafterAgent

_REGISTRY: dict[str, Agent] = {
    EchoAgent.name: EchoAgent(),
    BranchCreatorAgent.name: BranchCreatorAgent(),
    ClaudeAgent.name: ClaudeAgent(),
    DedupAgent.name: DedupAgent(),
    GuardrailAgent.name: GuardrailAgent(),
    ImageAnalyzerAgent.name: ImageAnalyzerAgent(),
    TriageDrafterAgent.name: TriageDrafterAgent(),
    TicketOrchestratorAgent.name: TicketOrchestratorAgent(),
    GitHubIssueCommenterAgent.name: GitHubIssueCommenterAgent(),
    QAHandoffAgent.name: QAHandoffAgent(),
}


def get_agent(name: str) -> Agent:
    """Return the registered agent for ``name``.

    Raises:
        KeyError: if no agent is registered under that name.
    """
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(name) from e


def list_agents() -> list[str]:
    """Return the sorted list of registered agent names."""
    return sorted(_REGISTRY)
