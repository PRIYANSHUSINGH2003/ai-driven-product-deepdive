"""GitHub REST ingestion with explicit data-quality semantics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config
from .models import CommitRecord, RepoTelemetry


class GitHubRateLimitError(RuntimeError):
    """Raised when GitHub explicitly reports rate exhaustion."""


class GitHubClientError(RuntimeError):
    """Raised for non-rate-limit GitHub transport/API errors."""


@dataclass(slots=True)
class RateLimitBucket:
    limit: int
    remaining: int
    reset_epoch: int
    used: int = 0

    @property
    def reset_at(self) -> datetime | None:
        if not self.reset_epoch:
            return None
        return datetime.fromtimestamp(self.reset_epoch, tz=timezone.utc)


@dataclass(slots=True)
class GitHubRateLimitStatus:
    authenticated: bool
    core: RateLimitBucket
    search: RateLimitBucket


_SESSION = requests.Session()
_SESSION.headers.update({
    "Accept": "application/vnd.github+json",
    "User-Agent": "candidate-signal/2.0",
})
_SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
    ),
)


def _headers() -> dict[str, str]:
    headers = {"X-GitHub-Api-Version": "2022-11-28"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers



def _bucket(data: dict) -> RateLimitBucket:
    return RateLimitBucket(
        limit=int(data.get("limit", 0) or 0),
        remaining=int(data.get("remaining", 0) or 0),
        reset_epoch=int(data.get("reset", 0) or 0),
        used=int(data.get("used", 0) or 0),
    )


def get_rate_limit_status() -> GitHubRateLimitStatus:
    """Read GitHub's current core/search budgets without consuming primary quota."""
    try:
        response = _SESSION.get(
            f"{config.GITHUB_API_BASE}/rate_limit",
            headers=_headers(),
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise GitHubClientError(f"Network error while checking GitHub rate limit: {exc}") from exc
    if response.status_code != 200:
        raise GitHubClientError(f"GitHub rate-limit endpoint returned HTTP {response.status_code}.")
    resources = response.json().get("resources", {})
    return GitHubRateLimitStatus(
        authenticated=bool(config.GITHUB_TOKEN),
        core=_bucket(resources.get("core", {})),
        search=_bucket(resources.get("search", {})),
    )

def _get(url: str, params: Optional[dict] = None) -> requests.Response:
    try:
        response = _SESSION.get(url, headers=_headers(), params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise GitHubClientError(f"Network error while contacting GitHub: {exc}") from exc

    if response.status_code in (403, 429) and (
        response.headers.get("x-ratelimit-remaining") == "0"
        or "rate limit" in response.text.lower()
        or "secondary rate limit" in response.text.lower()
    ):
        reset = response.headers.get("x-ratelimit-reset")
        suffix = f" Reset epoch: {reset}." if reset else ""
        resource = response.headers.get("x-ratelimit-resource", "unknown")
        raise GitHubRateLimitError(
            f"GitHub {resource} rate limit exhausted." + suffix
        )
    return response


def parse_repo_url_or_username(target: str) -> tuple[str, Optional[str]]:
    target = target.strip().rstrip("/")
    if not target:
        raise ValueError("Please enter a GitHub username or repository URL.")
    target = re.sub(r"^git@github\.com:", "https://github.com/", target)

    simple = re.fullmatch(r"([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)", target)
    if simple:
        return simple.group(1), simple.group(2)

    match = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)(?:/([^/#?]+))?/?$", target)
    if match:
        return match.group(1), (match.group(2)[:-4] if match.group(2) and match.group(2).endswith(".git") else match.group(2))

    if re.fullmatch(r"[A-Za-z0-9-]+", target):
        return target, None
    raise ValueError("Invalid GitHub target. Use a username, owner/repo, or https://github.com/owner/repo.")


def fetch_user_repos(username: str, max_repos: int = config.MAX_REPOS_PER_CANDIDATE, include_forks: bool = False) -> list[dict]:
    response = _get(
        f"{config.GITHUB_API_BASE}/users/{username}/repos",
        params={"sort": "pushed", "direction": "desc", "per_page": 100, "type": "owner"},
    )
    if response.status_code == 404:
        raise ValueError(f"GitHub user '{username}' not found.")
    response.raise_for_status()
    repos = response.json()
    filtered = [r for r in repos if not r.get("archived")]
    if not include_forks:
        filtered = [r for r in filtered if not r.get("fork")]
    return filtered[:max_repos]


def fetch_single_repo(owner: str, repo: str) -> dict:
    response = _get(f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}")
    if response.status_code == 404:
        raise ValueError(f"Repository '{owner}/{repo}' was not found or is private.")
    response.raise_for_status()
    return response.json()


def fetch_commits(owner: str, repo: str, branch: str, max_commits: int = config.MAX_COMMITS_PER_REPO) -> list[CommitRecord]:
    response = _get(
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
        params={"sha": branch, "per_page": min(max_commits, 100)},
    )
    if response.status_code != 200:
        raise GitHubClientError(f"GitHub commits endpoint returned HTTP {response.status_code}.")

    records: list[CommitRecord] = []
    for item in response.json():
        data = item.get("commit", {})
        author = data.get("author") or {}
        message = (data.get("message") or "").split("\n", 1)[0][:200]
        records.append(CommitRecord(
            sha=str(item.get("sha", ""))[:7],
            message=message,
            author_date=author.get("date", ""),
        ))
    return records


def fetch_pull_request_count(owner: str, repo: str) -> int:
    response = _get(
        f"{config.GITHUB_API_BASE}/search/issues",
        params={"q": f"repo:{owner}/{repo} is:pr", "per_page": 1},
    )
    if response.status_code != 200:
        raise GitHubClientError(f"GitHub PR search returned HTTP {response.status_code}.")
    return int(response.json().get("total_count", 0))


def fetch_contributor_count(owner: str, repo: str) -> int:
    response = _get(
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/contributors",
        params={"per_page": 100, "anon": "true"},
    )
    if response.status_code != 200:
        raise GitHubClientError(f"GitHub contributors endpoint returned HTTP {response.status_code}.")
    link = response.headers.get("Link", "")
    match = re.search(r"page=(\d+)>; rel=\"last\"", link)
    return int(match.group(1)) if match else len(response.json())


def fetch_file_tree_metrics(owner: str, repo: str, default_branch: str) -> tuple[int, int, bool]:
    response = _get(
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}",
        params={"recursive": "1"},
    )
    if response.status_code != 200:
        raise GitHubClientError(f"GitHub tree endpoint returned HTTP {response.status_code}.")
    data = response.json()
    files = [entry for entry in data.get("tree", []) if entry.get("type") == "blob"]
    max_depth = max((entry.get("path", "").count("/") for entry in files), default=0)
    return max_depth, len(files), bool(data.get("truncated", False))


def fetch_repo_telemetry(owner: str, repo_name: str, max_commits: int = config.MAX_COMMITS_PER_REPO) -> RepoTelemetry:
    repo_data = fetch_single_repo(owner, repo_name)
    branch = repo_data.get("default_branch") or "main"
    telemetry = RepoTelemetry(
        name=repo_data.get("name", repo_name),
        full_name=repo_data.get("full_name", f"{owner}/{repo_name}"),
        html_url=repo_data.get("html_url", ""),
        created_at=repo_data.get("created_at", ""),
        pushed_at=repo_data.get("pushed_at", ""),
        updated_at=repo_data.get("updated_at", ""),
        default_branch=branch,
        is_fork=bool(repo_data.get("fork", False)),
        is_archived=bool(repo_data.get("archived", False)),
        is_disabled=bool(repo_data.get("disabled", False)),
        stargazers_count=int(repo_data.get("stargazers_count", 0)),
        watchers_count=int(repo_data.get("watchers_count", 0)),
        open_issues_count=int(repo_data.get("open_issues_count", 0)),
        size_kb=int(repo_data.get("size", 0)),
        language=repo_data.get("language"),
    )

    errors: list[str] = []
    try:
        telemetry.commits = fetch_commits(owner, repo_name, branch, max_commits=max_commits)
    except (GitHubRateLimitError, GitHubClientError) as exc:
        telemetry.fetch_error = f"Commit history unavailable: {exc}"
        if isinstance(exc, GitHubRateLimitError):
            raise

    try:
        telemetry.pull_request_count = fetch_pull_request_count(owner, repo_name)
    except GitHubRateLimitError:
        telemetry.pr_data_available = False
        errors.append("PR history unavailable because GitHub rate limit was reached.")
    except GitHubClientError as exc:
        telemetry.pr_data_available = False
        errors.append(str(exc))

    try:
        telemetry.contributor_count = fetch_contributor_count(owner, repo_name)
    except GitHubRateLimitError:
        telemetry.contributor_data_available = False
        errors.append("Contributor count unavailable because GitHub rate limit was reached.")
    except GitHubClientError as exc:
        telemetry.contributor_data_available = False
        errors.append(f"Contributor count unavailable: {exc}")

    try:
        depth, count, truncated = fetch_file_tree_metrics(owner, repo_name, branch)
        telemetry.max_file_tree_depth = depth
        telemetry.file_count = count
        telemetry.tree_truncated = truncated
    except GitHubRateLimitError:
        telemetry.tree_data_available = False
        errors.append("Repository structure unavailable because GitHub rate limit was reached.")
    except GitHubClientError as exc:
        telemetry.tree_data_available = False
        errors.append(f"Repository structure unavailable: {exc}")

    if errors:
        telemetry.fetch_error = (telemetry.fetch_error + " " if telemetry.fetch_error else "") + " ".join(errors)
    return telemetry
