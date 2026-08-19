"""Deterministic, auditable engineering-evidence analysis."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Optional

from . import config
from .models import CommitRecord, RedFlag, RepoAnalysis, RepoTelemetry


def _parse_dates(commits: list[CommitRecord]) -> list[datetime]:
    dates: list[datetime] = []
    for commit in commits:
        if not commit.author_date:
            continue
        try:
            dates.append(datetime.fromisoformat(commit.author_date.replace("Z", "+00:00")))
        except ValueError:
            continue
    return sorted(dates)


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_between(start: str, end: str) -> Optional[float]:
    a, b = _parse_iso(start), _parse_iso(end)
    if not a or not b:
        return None
    return max((b - a).total_seconds() / 86400, 0.0)


def _densest_24h_window_ratio(dates: list[datetime]) -> float:
    if not dates:
        return 0.0
    left = 0
    best = 1
    for right, current in enumerate(dates):
        while current - dates[left] > timedelta(hours=24):
            left += 1
        best = max(best, right - left + 1)
    return best / len(dates)


def _is_generic_message(message: str) -> bool:
    msg = message.strip().lower()
    if not msg or len(msg) <= 4:
        return True
    words = msg.split()
    if len(words) <= 2 and any(msg == p or msg.startswith(p) for p in config.GENERIC_MESSAGE_PATTERNS):
        return True
    return False


def _message_metrics(repo: RepoTelemetry) -> tuple[Optional[float], Optional[float]]:
    if not repo.commits:
        return None, None
    generic_ratio = sum(_is_generic_message(c.message) for c in repo.commits) / len(repo.commits)
    avg_len = mean(len(c.message.strip()) for c in repo.commits)
    return generic_ratio, avg_len


def detect_single_day_concentration(repo: RepoTelemetry) -> Optional[RedFlag]:
    if len(repo.commits) < config.SINGLE_DAY_DUMP_MIN_COMMITS:
        return None
    dates = _parse_dates(repo.commits)
    ratio = _densest_24h_window_ratio(dates)
    if ratio < config.SINGLE_DAY_DUMP_RATIO_THRESHOLD:
        return None
    return RedFlag(
        code="high_change_concentration",
        severity="medium",
        category="activity",
        message=(
            f"{ratio:.0%} of the sampled commits landed inside one rolling 24-hour window. "
            "This is a workflow pattern to verify, not evidence of poor or inauthentic work."
        ),
        evidence={"densest_24h_ratio": round(ratio, 3), "commit_count": len(dates)},
    )


def detect_generic_messages(repo: RepoTelemetry) -> Optional[RedFlag]:
    if len(repo.commits) < 5:
        return None
    ratio, _ = _message_metrics(repo)
    if ratio is None or ratio < config.GENERIC_MESSAGE_RATIO_FLAG:
        return None
    return RedFlag(
        code="low_information_commit_messages",
        severity="low",
        category="communication",
        message=(f"{ratio:.0%} of sampled commit subjects are low-information. "
                 "This is only a communication-quality observation."),
        evidence={"generic_ratio": round(ratio, 3)},
    )


def detect_missing_collaboration_context(repo: RepoTelemetry) -> Optional[RedFlag]:
    if not repo.pr_data_available or not repo.contributor_data_available:
        return None
    if repo.contributor_count <= 1 and repo.pull_request_count == 0:
        return RedFlag(
            code="solo_workflow",
            severity="low",
            category="workflow",
            message="Repository appears to be primarily solo work; PR-based collaboration signals are therefore limited.",
            evidence={"contributors": repo.contributor_count, "pull_requests": repo.pull_request_count},
        )
    return None


def detect_stale_repo(repo: RepoTelemetry) -> Optional[RedFlag]:
    pushed = _parse_iso(repo.pushed_at)
    if not pushed:
        return None
    age = (datetime.now(timezone.utc) - pushed.astimezone(timezone.utc)).days
    if age < config.STALE_REPO_DAYS or repo.is_archived:
        return None
    return RedFlag(
        code="stale_repository",
        severity="low",
        category="maintenance",
        message=f"No recorded push in roughly {age} days. This may simply reflect a completed project or an intentionally inactive repository.",
        evidence={"days_since_push": age},
    )


def score_activity_continuity(repo: RepoTelemetry) -> float:
    dates = _parse_dates(repo.commits)
    if len(dates) < 2:
        return 5.0
    span_days = max((dates[-1] - dates[0]).total_seconds() / 86400, 1.0)
    burst_ratio = _densest_24h_window_ratio(dates)
    span_score = min(span_days / 180.0, 1.0) * 10.0
    concentration_penalty = burst_ratio * 5.0
    return round(max(0.0, min(10.0, span_score - concentration_penalty + 4.0)), 2)


def score_structural_depth(repo: RepoTelemetry) -> float:
    if not repo.tree_data_available or repo.file_count == 0:
        return 5.0
    depth_component = min(repo.max_file_tree_depth / 4.0, 1.0) * 6.0
    size_component = min(repo.file_count / 60.0, 1.0) * 4.0
    return round(max(0.0, min(10.0, depth_component + size_component)), 2)


def score_workflow(repo: RepoTelemetry) -> float:
    if not repo.pr_data_available or not repo.contributor_data_available:
        return 5.0
    if repo.contributor_count <= 1:
        # No PR workflow is normal for solo repos; do not punish it.
        return 6.0 if repo.pull_request_count == 0 else 8.0
    pr_component = min(repo.pull_request_count / 5.0, 1.0) * 7.0
    collaboration_component = min(repo.contributor_count / 4.0, 1.0) * 3.0
    return round(min(10.0, pr_component + collaboration_component), 2)


def score_communication(repo: RepoTelemetry) -> float:
    ratio, avg_len = _message_metrics(repo)
    if ratio is None or avg_len is None:
        return 5.0
    length_component = min(avg_len / 55.0, 1.0) * 5.0
    specificity_component = (1.0 - ratio) * 5.0
    return round(min(10.0, length_component + specificity_component), 2)


def score_maintenance(repo: RepoTelemetry) -> float:
    if not repo.pushed_at:
        return 5.0
    pushed = _parse_iso(repo.pushed_at)
    if not pushed:
        return 5.0
    age = max((datetime.now(timezone.utc) - pushed.astimezone(timezone.utc)).days, 0)
    recency = 10.0 if age <= 30 else 8.5 if age <= 90 else 7.0 if age <= 180 else 5.5 if age <= 365 else 4.0
    if repo.is_archived:
        recency = min(recency, 5.0)
    return round(recency, 2)


def score_breadth(repo: RepoTelemetry) -> float:
    score = 4.0
    if repo.language:
        score += 1.5
    if repo.file_count >= 10:
        score += 1.5
    if repo.size_kb >= 25:
        score += 1.0
    if repo.stargazers_count > 0:
        score += 0.5
    if repo.open_issues_count > 0:
        score += 0.5
    return round(min(score, 10.0), 2)


def compute_rule_based_score(sub_scores: dict[str, float]) -> float:
    total = sum(sub_scores[key] * weight for key, weight in config.SCORE_WEIGHTS.items())
    return round(max(1.0, min(10.0, total)), 2)


def compute_data_quality(repo: RepoTelemetry) -> float:
    checks = [
        bool(repo.commits),
        repo.pr_data_available,
        repo.contributor_data_available,
        repo.tree_data_available,
        not repo.tree_truncated,
    ]
    return round(sum(checks) / len(checks), 2)


def analyze_repo(repo: RepoTelemetry) -> RepoAnalysis:
    detectors = [detect_single_day_concentration, detect_generic_messages, detect_missing_collaboration_context, detect_stale_repo]
    red_flags = [flag for detector in detectors if (flag := detector(repo)) is not None]
    notes: list[str] = []
    if len(repo.commits) >= config.MAX_COMMITS_PER_REPO:
        notes.append(f"Commit history is capped at {config.MAX_COMMITS_PER_REPO} sampled commits; older activity may be underrepresented.")
    if repo.tree_truncated:
        notes.append("GitHub returned a truncated repository tree; structural metrics are partial.")
    if not repo.pr_data_available:
        notes.append("Pull-request history is unavailable; workflow scoring is neutralized.")
    if not repo.contributor_data_available:
        notes.append("Contributor count is unavailable; collaboration scoring is neutralized.")
    if repo.is_archived:
        notes.append("Repository is archived.")

    return RepoAnalysis(
        repo=repo,
        activity_continuity_score=score_activity_continuity(repo),
        structural_depth_score=score_structural_depth(repo),
        workflow_score=score_workflow(repo),
        communication_score=score_communication(repo),
        maintenance_score=score_maintenance(repo),
        breadth_score=score_breadth(repo),
        red_flags=red_flags,
        data_quality=compute_data_quality(repo),
        evidence_notes=notes,
    )


def build_candidate_payload(username: str, repo_analyses: list[RepoAnalysis]) -> dict:
    """Create the privacy-minimized LLM payload; never include raw candidate text or URLs."""
    summaries: list[dict] = []
    for index, ra in enumerate(repo_analyses, start=1):
        repo = ra.repo
        generic_ratio, avg_len = _message_metrics(repo)
        summaries.append({
            "repo_index": index,
            "commit_count_sampled": len(repo.commits),
            "pull_requests": repo.pull_request_count if repo.pr_data_available else None,
            "contributors": repo.contributor_count if repo.contributor_data_available else None,
            "max_dir_depth": repo.max_file_tree_depth if repo.tree_data_available else None,
            "file_count": repo.file_count if repo.tree_data_available else None,
            "tree_truncated": repo.tree_truncated,
            "language": repo.language,
            "stars": repo.stargazers_count,
            "size_kb": repo.size_kb,
            "open_issues": repo.open_issues_count,
            "archived": repo.is_archived,
            "days_since_push": None if not repo.pushed_at else max((datetime.now(timezone.utc) - _parse_iso(repo.pushed_at).astimezone(timezone.utc)).days, 0) if _parse_iso(repo.pushed_at) else None,
            "generic_message_ratio": round(generic_ratio, 3) if generic_ratio is not None else None,
            "avg_commit_message_length": round(avg_len, 1) if avg_len is not None else None,
            "sub_scores": {
                "activity_continuity": ra.activity_continuity_score,
                "structural_depth": ra.structural_depth_score,
                "workflow": ra.workflow_score,
                "communication": ra.communication_score,
                "maintenance": ra.maintenance_score,
                "breadth": ra.breadth_score,
            },
            "observations": [flag.code for flag in ra.red_flags],
            "data_quality": ra.data_quality,
        })
    return {
        "candidate_scope": "public_github_telemetry",
        "repo_count": len(summaries),
        "repos": summaries,
    }
