"""Pydantic DTOs for GitHub integration request and response payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GitHubIssueReference(BaseModel):
    number: int


class GitHubIssueCommentRequest(BaseModel):
    body: str


class GitHubIssueCommentResponse(BaseModel):
    id: int


class GitHubCreatePullRequestRequest(BaseModel):
    title: str
    head: str
    base: str = "main"
    body: str = ""


class GitHubPullRequestResponse(BaseModel):
    number: int


class GitHubRequestReviewersRequest(BaseModel):
    reviewers: list[str]


class GitHubRequestedReviewersResponse(BaseModel):
    id: int | None = None


class GitHubSearchIssueItem(BaseModel):
    number: int
    pull_request: dict[str, Any] | None = None


class GitHubSearchIssuesResponse(BaseModel):
    items: list[GitHubSearchIssueItem] = Field(default_factory=list)
