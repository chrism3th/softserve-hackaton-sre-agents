"""Tests for the duplicate detection agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.dedup_agent import DedupAgent, DedupResult
from app.config import get_settings


@pytest.fixture()
def _no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def _with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestDedupAgentFallback:
    async def test_no_candidates_returns_not_duplicate(self, _no_api_key: None) -> None:
        agent = DedupAgent()
        result = await agent.evaluate(
            {"new_title": "Service down", "new_body": "500 errors", "candidates": []}
        )
        assert result.is_duplicate is False

    async def test_exact_title_match_is_duplicate(self, _no_api_key: None) -> None:
        agent = DedupAgent()
        result = await agent.evaluate(
            {
                "new_title": "Checkout 500 error",
                "new_body": "Users see 500 on checkout",
                "candidates": [
                    {
                        "identifier": "TEA-10",
                        "title": "Checkout 500 error",
                        "url": "https://linear.app/team/TEA-10",
                    }
                ],
            }
        )
        assert result.is_duplicate is True
        assert result.duplicate_of_identifier == "TEA-10"

    async def test_different_title_is_not_duplicate(self, _no_api_key: None) -> None:
        agent = DedupAgent()
        result = await agent.evaluate(
            {
                "new_title": "Login page broken",
                "new_body": "Cannot login",
                "candidates": [
                    {
                        "identifier": "TEA-10",
                        "title": "Checkout 500 error",
                        "url": "https://linear.app/team/TEA-10",
                    }
                ],
            }
        )
        assert result.is_duplicate is False


class TestDedupAgentLLM:
    async def test_llm_duplicate_detection(self, _with_api_key: None) -> None:
        agent = DedupAgent()
        mock_response = '{"is_duplicate": true, "duplicate_of_identifier": "TEA-5", "duplicate_of_url": "https://linear.app/team/TEA-5", "reason": "Same root cause"}'

        with patch(
            "anthropic.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_block = AsyncMock()
            mock_block.text = mock_response
            mock_block.__class__.__name__ = "TextBlock"

            from anthropic.types.text_block import TextBlock

            text_block = TextBlock(type="text", text=mock_response)
            mock_message = AsyncMock()
            mock_message.content = [text_block]
            mock_client.messages.create = AsyncMock(return_value=mock_message)

            result = await agent.evaluate(
                {
                    "new_title": "API timeout",
                    "new_body": "POST /api/checkout times out",
                    "candidates": [
                        {
                            "identifier": "TEA-5",
                            "title": "Checkout API timeout",
                            "url": "https://linear.app/team/TEA-5",
                            "description": "Checkout endpoint times out under load",
                        }
                    ],
                }
            )

        assert result.is_duplicate is True
        assert result.duplicate_of_identifier == "TEA-5"

    async def test_llm_failure_falls_back(self, _with_api_key: None) -> None:
        agent = DedupAgent()

        with patch(
            "anthropic.AsyncAnthropic",
            side_effect=RuntimeError("API down"),
        ):
            result = await agent.evaluate(
                {
                    "new_title": "Something new",
                    "new_body": "Brand new issue",
                    "candidates": [
                        {
                            "identifier": "TEA-1",
                            "title": "Old issue",
                            "url": "https://linear.app/team/TEA-1",
                        }
                    ],
                }
            )

        assert result.is_duplicate is False
        assert "fallback" in (result.reason or "").lower()
