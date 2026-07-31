"""
analyzer.py
-----------
The deterministic core of the engine. Converts raw RepoTelemetry into:
  1) sub-scores (0-10) for velocity, structure, PR engagement, message quality
  2) explicit RedFlag objects with evidence
  3) a weighted rule_based_score for the repo/candidate

This module has ZERO network or LLM dependencies on purpose -- it is pure,
testable Python so the scoring logic can be unit-tested and audited without
needing API keys. See JOURNAL.md Entry 5 for why this layer exists at all.
"""
from datetime import datetime, timedelta
from typing import Optional

from . import config
from .models import CommitRecord, RepoTelemetry, RepoAnalysis, RedFlag, CandidateReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_dates(commits: list[CommitRecord]) -> list[datetime]:
    dates = []
    for c in commits:
        if not c.author_date:
            continue
        try:
            dates.append(datetime.fromisoformat(c.author_date.replace("Z", "+00:00")))
        except ValueError:
            continue
    return sorted(dates)


def _densest_24h_window_ratio(dates: list[datetime]) -> float:
    """Sliding-window scan: what fraction of all commits fall inside the
    densest rolling 24-hour window? O(n^2) but n is capped at MAX_COMMITS_PER_REPO."""
    if not dates:
        return 0.0
    n = len(dates)
    best = 1
    for i in range(n):
        window_end = dates[i] + timedelta(hours=24)
        count = sum(1 for d in dates if dates[i] <= d <= window_end)
        best = max(best, count)
    return best / n


def _is_generic_message(message: str) -> bool:
    """A message is 'generic' if it IS a bare filler token/short phrase, not merely if it
    contains one -- e.g. 'update dependency to fix CVE-2024-xxxx' is NOT generic even though
    it contains the word 'fix'. Only very short, low-information messages are flagged."""
    msg = message.strip().lower()
    if not msg or len(msg) <= 4:
        return True
    word_count = len(msg.split())
    if word_count <= 2 and any(msg == p or msg.startswith(p) for p in config.GENERIC_MESSAGE_PATTERNS):
        return True
    return False


# ---------------------------------------------------------------------------
# Red flag detectors (each returns Optional[RedFlag])
# ---------------------------------------------------------------------------
def detect_single_day_dump(repo: RepoTelemetry) -> Optional[RedFlag]:
    if len(repo.commits) < config.SINGLE_DAY_DUMP_MIN_COMMITS:
        return None
    dates = _parse_dates(repo.commits)
    ratio = _densest_24h_window_ratio(dates)
    if ratio >= config.SINGLE_DAY_DUMP_RATIO_THRESHOLD:
        return RedFlag(
            code="single_day_dump",
            severity="high",
            message=(f"{ratio:.0%} of commits in '{repo.name}' landed within a single "
                      f"24-hour window, out of {len(dates)} analyzed commits."),
            evidence={"densest_24h_ratio": round(ratio, 3), "commit_count": len(dates)},
        )
    return None


def detect_flat_structure(repo: RepoTelemetry) -> Optional[RedFlag]:
    if repo.file_count == 0:
        return None
    if repo.max_file_tree_depth <= config.FLAT_STRUCTURE_MAX_DEPTH and repo.file_count > 1:
        return RedFlag(
            code="flat_structure",
            severity="medium",
            message=(f"'{repo.name}' has {repo.file_count} files but a max directory depth of "
                      f"only {repo.max_file_tree_depth} -- little evidence of layered architecture."),
            evidence={"max_depth": repo.max_file_tree_depth, "file_count": repo.file_count},
        )
    return None


def detect_no_pr_history(repo: RepoTelemetry) -> Optional[RedFlag]:
    if len(repo.commits) >= 10 and repo.pull_request_count == 0:
        return RedFlag(
            code="no_pr_history",
            severity="low",
            message=(f"'{repo.name}' has {len(repo.commits)}+ commits but zero pull requests -- "
                      f"no evidence of branching, review, or iterative merge workflow."),
            evidence={"pull_request_count": 0, "commit_count": len(repo.commits)},
        )
    return None


def detect_generic_messages(repo: RepoTelemetry) -> Optional[RedFlag]:
    if len(repo.commits) < 5:
        return None
    generic_count = sum(1 for c in repo.commits if _is_generic_message(c.message))
    ratio = generic_count / len(repo.commits)
    if ratio >= config.GENERIC_MESSAGE_RATIO_FLAG:
        return RedFlag(
            code="generic_commit_messages",
            severity="low",
            message=(f"{ratio:.0%} of commit messages in '{repo.name}' are generic "
                      f"(e.g. 'update', 'fix', 'wip') with little descriptive content."),
            evidence={"generic_ratio": round(ratio, 3)},
        )
    return None


REPO_RED_FLAG_DETECTORS = [
    detect_single_day_dump,
    detect_flat_structure,
    detect_no_pr_history,
    detect_generic_messages,
]


# ---------------------------------------------------------------------------
# Sub-scores (0-10 each, higher = more evidence of authentic, sustained depth)
# ---------------------------------------------------------------------------
def score_velocity_consistency(repo: RepoTelemetry) -> float:
    dates = _parse_dates(repo.commits)
    if len(dates) < 2:
        return 5.0  # not enough data to judge either way -- neutral
    ratio = _densest_24h_window_ratio(dates)
    span_days = max((dates[-1] - dates[0]).total_seconds() / 86400, 0.01)
    # Reward: long span + low burst concentration. Penalize: short span + high concentration.
    span_score = min(span_days / 30, 1.0) * 10          # full credit at 30+ days of activity
    burst_penalty = ratio * 10                          # 0 (spread out) .. 10 (all in one day)
    raw = (span_score * 0.6) + ((10 - burst_penalty) * 0.4)
    return round(max(0.0, min(10.0, raw)), 2)


def score_structural_depth(repo: RepoTelemetry) -> float:
    if repo.file_count == 0:
        return 5.0  # unknown -- neutral, don't punish for a fetch gap
    depth_score = min(repo.max_file_tree_depth / 3, 1.0) * 10   # full credit at depth 3+
    size_bonus = min(repo.file_count / 20, 1.0) * 2              # small bonus for non-trivial size
    raw = min(depth_score + size_bonus, 10.0)
    return round(raw, 2)


def score_pr_engagement(repo: RepoTelemetry) -> float:
    if repo.pull_request_count == 0:
        return 2.0 if len(repo.commits) >= 10 else 5.0
    raw = min(repo.pull_request_count / 5, 1.0) * 10
    return round(raw, 2)


def score_message_quality(repo: RepoTelemetry) -> float:
    if not repo.commits:
        return 5.0
    generic_count = sum(1 for c in repo.commits if _is_generic_message(c.message))
    ratio = generic_count / len(repo.commits)
    avg_len = sum(len(c.message) for c in repo.commits) / len(repo.commits)
    length_score = min(avg_len / 50, 1.0) * 10
    raw = (length_score * 0.5) + ((1 - ratio) * 10 * 0.5)
    return round(raw, 2)


def compute_rule_based_score(sub_scores: dict) -> float:
    total = sum(sub_scores[k] * w for k, w in config.SCORE_WEIGHTS.items())
    return round(max(1.0, min(10.0, total)), 2)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def analyze_repo(repo: RepoTelemetry) -> RepoAnalysis:
    velocity = score_velocity_consistency(repo)
    structure = score_structural_depth(repo)
    pr_eng = score_pr_engagement(repo)
    msg_quality = score_message_quality(repo)

    red_flags = [f for f in (d(repo) for d in REPO_RED_FLAG_DETECTORS) if f is not None]

    return RepoAnalysis(
        repo=repo,
        velocity_consistency_score=velocity,
        structural_depth_score=structure,
        pr_engagement_score=pr_eng,
        message_quality_score=msg_quality,
        red_flags=red_flags,
    )


def build_candidate_payload(username: str, repo_analyses: list[RepoAnalysis]) -> dict:
    """Aggregates all repo-level analysis into ONE compact JSON-serializable payload.
    This is what gets sent to the LLM (single call for the whole candidate --
    see JOURNAL.md Entry 3). Deliberately excludes raw README/file content --
    only numeric/structural telemetry is included, to avoid prompt-injection
    surface area from candidate-controlled text (see JOURNAL.md Entry 5)."""
    repos_summary = []
    for ra in repo_analyses:
        r = ra.repo
        repos_summary.append({
            "name": r.name,
            "commit_count": len(r.commits),
            "pull_requests": r.pull_request_count,
            "max_dir_depth": r.max_file_tree_depth,
            "file_count": r.file_count,
            "language": r.language,
            "stars": r.stargazers_count,
            "sub_scores": {
                "velocity_consistency": ra.velocity_consistency_score,
                "structural_depth": ra.structural_depth_score,
                "pr_engagement": ra.pr_engagement_score,
                "message_quality": ra.message_quality_score,
            },
            "red_flags": [f.code for f in ra.red_flags],
            # sample of commit message *lengths/generic-ness only*, not literal candidate text,
            # beyond a small illustrative sample capped by config -- kept short deliberately.
            "sample_commit_messages": [
                c.message for c in r.commits[: config.LLM_MAX_COMMIT_MESSAGES_SAMPLED_PER_REPO // 8]
            ],
        })
    return {"username": username, "repos": repos_summary}
