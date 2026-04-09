"""GitHub integration package."""

from app.integrations.github.client import (
    GitHubClient,
    GitHubError,
)
from app.integrations.github.schemas import (
    GitHubCreatePullRequestRequest,
    GitHubIssueCommentRequest,
    GitHubIssueCommentResponse,
    GitHubIssueReference,
    GitHubPullRequestResponse,
    GitHubRequestedReviewersResponse,
    GitHubRequestReviewersRequest,
    GitHubSearchIssueItem,
    GitHubSearchIssuesResponse,
)

__all__ = [
    "GitHubClient",
    "GitHubCreatePullRequestRequest",
    "GitHubError",
    "GitHubIssueCommentRequest",
    "GitHubIssueCommentResponse",
    "GitHubIssueReference",
    "GitHubPullRequestResponse",
    "GitHubRequestReviewersRequest",
    "GitHubRequestedReviewersResponse",
    "GitHubSearchIssueItem",
    "GitHubSearchIssuesResponse",
]
