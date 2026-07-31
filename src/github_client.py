"""
github_client.py
-----------------
Thin wrapper around the public GitHub REST API v3. No auth required to run,
but will use GITHUB_TOKEN from config if present (raises rate limit
60/hr -> 5,000/hr, still $0).

Design note: every network call is wrapped so a single repo's failure
(rate limit, 404, empty repo) never crashes the whole candidate analysis --
it's recorded on RepoTelemetry.fetch_error and surfaced to the user instead.
"""
import re
import requests
from datetime import datetime
from typing import Optional

from . import config
from .models import CommitRecord, RepoTelemetry


class GitHubRateLimitError(Exception):
    """Raised when GitHub's rate limit is exhausted -- caller should degrade gracefully."""
    pass


def _headers() -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "candidate-authenticity-poc"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def _get(url: str, params: Optional[dict] = None) -> requests.Response:
    resp = requests.get(url, headers=_headers(), params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise GitHubRateLimitError(
            "GitHub API rate limit exhausted. Set a free GITHUB_TOKEN env var to raise the "
            "limit from 60/hr to 5,000/hr (see README)."
        )
    return resp


def parse_repo_url_or_username(target: str) -> tuple[str, Optional[str]]:
    """
    Accepts either a bare username ('octocat') or a full repo URL
    ('https://github.com/octocat/Hello-World') and returns (username, repo_name_or_None).
    """
    target = target.strip().rstrip("/")
    match = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)(?:/([^/]+))?/?$", target)
    if match:
        return match.group(1), match.group(2)
    return target, None  # treat as bare username


def fetch_user_repos(username: str, max_repos: int = config.MAX_REPOS_PER_CANDIDATE) -> list[dict]:
    """Fetch the user's most recently pushed public, non-fork repos (capped for cost control)."""
    resp = _get(
        f"{config.GITHUB_API_BASE}/users/{username}/repos",
        params={"sort": "pushed", "direction": "desc", "per_page": 100, "type": "owner"},
    )
    if resp.status_code == 404:
        raise ValueError(f"GitHub user '{username}' not found.")
    resp.raise_for_status()
    repos = resp.json()
    non_forks = [r for r in repos if not r.get("fork")]
    return non_forks[:max_repos]


def fetch_single_repo(owner: str, repo: str) -> dict:
    resp = _get(f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}")
    if resp.status_code == 404:
        raise ValueError(f"Repo '{owner}/{repo}' not found or is private.")
    resp.raise_for_status()
    return resp.json()


def fetch_commits(owner: str, repo: str, max_commits: int = config.MAX_COMMITS_PER_REPO) -> list[CommitRecord]:
    """Fetch commit history (author date + message). Skips per-commit stat calls to conserve
    the free rate-limit budget -- additions/deletions are left at 0 unless later enriched."""
    resp = _get(
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
        params={"per_page": min(max_commits, 100)},
    )
    if resp.status_code != 200:
        return []  # empty repo, or history unavailable -- non-fatal
    raw_commits = resp.json()

    records = []
    for c in raw_commits:
        commit_data = c.get("commit", {})
        author = commit_data.get("author", {}) or {}
        records.append(
            CommitRecord(
                sha=c.get("sha", "")[:7],
                message=(commit_data.get("message") or "").split("\n")[0][:200],
                author_date=author.get("date", ""),
            )
        )
    return records


def fetch_pull_request_count(owner: str, repo: str) -> int:
    """Uses the search API to get a fast total count of PRs (open+closed) without paginating."""
    resp = _get(
        f"{config.GITHUB_API_BASE}/search/issues",
        params={"q": f"repo:{owner}/{repo} is:pr", "per_page": 1},
    )
    if resp.status_code != 200:
        return 0
    return resp.json().get("total_count", 0)


def fetch_file_tree_metrics(owner: str, repo: str, default_branch: str) -> tuple[int, int]:
    """Returns (max_depth, file_count) using the recursive git trees API in a single call."""
    resp = _get(f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}",
                params={"recursive": "1"})
    if resp.status_code != 200:
        return 0, 0
    data = resp.json()
    tree = data.get("tree", [])
    files = [t for t in tree if t.get("type") == "blob"]
    max_depth = max((t["path"].count("/") for t in files), default=0)
    return max_depth, len(files)


def fetch_repo_telemetry(owner: str, repo_name: str) -> RepoTelemetry:
    """Orchestrates the full per-repo fetch. Never raises for partial failures -- records
    them on RepoTelemetry.fetch_error so the analysis layer can proceed with best-effort data."""
    try:
        repo_data = fetch_single_repo(owner, repo_name)
    except ValueError as e:
        # Fully unusable repo -- return an empty telemetry object with the error attached.
        return RepoTelemetry(
            name=repo_name, full_name=f"{owner}/{repo_name}", html_url="",
            created_at="", pushed_at="", is_fork=False, stargazers_count=0,
            language=None, fetch_error=str(e),
        )

    telemetry = RepoTelemetry(
        name=repo_data.get("name", repo_name),
        full_name=repo_data.get("full_name", f"{owner}/{repo_name}"),
        html_url=repo_data.get("html_url", ""),
        created_at=repo_data.get("created_at", ""),
        pushed_at=repo_data.get("pushed_at", ""),
        is_fork=repo_data.get("fork", False),
        stargazers_count=repo_data.get("stargazers_count", 0),
        language=repo_data.get("language"),
    )

    try:
        telemetry.commits = fetch_commits(owner, repo_name)
    except GitHubRateLimitError:
        telemetry.fetch_error = "rate_limited_on_commits"
        return telemetry

    try:
        telemetry.pull_request_count = fetch_pull_request_count(owner, repo_name)
    except GitHubRateLimitError:
        pass  # non-fatal, PR count just stays 0 -- reflected as lower engagement score

    default_branch = repo_data.get("default_branch", "main")
    try:
        depth, count = fetch_file_tree_metrics(owner, repo_name, default_branch)
        telemetry.max_file_tree_depth = depth
        telemetry.file_count = count
    except GitHubRateLimitError:
        pass

    return telemetry
