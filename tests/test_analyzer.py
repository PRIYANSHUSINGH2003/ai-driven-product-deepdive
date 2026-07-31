"""
test_analyzer.py
-----------------
Pure unit tests for the deterministic scoring/red-flag layer. No network
calls, no API keys required -- run with `pytest tests/`.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta, timezone
from src.models import CommitRecord, RepoTelemetry
from src import analyzer


def _make_repo(commits, pr_count=0, max_depth=0, file_count=0, name="test-repo"):
    return RepoTelemetry(
        name=name, full_name=f"tester/{name}", html_url="", created_at="", pushed_at="",
        is_fork=False, stargazers_count=0, language="Python",
        commits=commits, pull_request_count=pr_count,
        max_file_tree_depth=max_depth, file_count=file_count,
    )


def _commits_on_single_day(n=10):
    base = datetime(2024, 3, 2, 8, 0, tzinfo=timezone.utc)
    return [
        CommitRecord(sha=f"s{i}", message=f"add feature {i}",
                     author_date=(base + timedelta(minutes=i * 5)).isoformat())
        for i in range(n)
    ]


def _commits_over_months(n=20, days_span=180):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    step = timedelta(days=days_span / n)
    return [
        CommitRecord(sha=f"s{i}", message=f"refactor module {i} to improve error handling",
                     author_date=(base + step * i).isoformat())
        for i in range(n)
    ]


# --- Red flag detectors ------------------------------------------------------
def test_single_day_dump_detected():
    repo = _make_repo(_commits_on_single_day(10))
    flag = analyzer.detect_single_day_dump(repo)
    assert flag is not None
    assert flag.code == "single_day_dump"
    assert flag.evidence["densest_24h_ratio"] >= 0.9


def test_single_day_dump_not_flagged_for_sustained_activity():
    repo = _make_repo(_commits_over_months(20, 180))
    flag = analyzer.detect_single_day_dump(repo)
    assert flag is None


def test_single_day_dump_ignored_below_min_commits():
    repo = _make_repo(_commits_on_single_day(3))  # below SINGLE_DAY_DUMP_MIN_COMMITS
    flag = analyzer.detect_single_day_dump(repo)
    assert flag is None


def test_flat_structure_detected():
    repo = _make_repo(_commits_over_months(5, 30), max_depth=0, file_count=6)
    flag = analyzer.detect_flat_structure(repo)
    assert flag is not None
    assert flag.code == "flat_structure"


def test_flat_structure_not_flagged_for_layered_repo():
    repo = _make_repo(_commits_over_months(5, 30), max_depth=3, file_count=40)
    flag = analyzer.detect_flat_structure(repo)
    assert flag is None


def test_no_pr_history_flagged_with_many_commits_and_no_prs():
    repo = _make_repo(_commits_over_months(15, 90), pr_count=0)
    flag = analyzer.detect_no_pr_history(repo)
    assert flag is not None
    assert flag.code == "no_pr_history"


def test_no_pr_history_not_flagged_with_prs_present():
    repo = _make_repo(_commits_over_months(15, 90), pr_count=4)
    flag = analyzer.detect_no_pr_history(repo)
    assert flag is None


def test_generic_messages_detected():
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    commits = [
        CommitRecord(sha=f"s{i}", message="update", author_date=(base + timedelta(days=i)).isoformat())
        for i in range(8)
    ]
    repo = _make_repo(commits)
    flag = analyzer.detect_generic_messages(repo)
    assert flag is not None
    assert flag.code == "generic_commit_messages"


def test_descriptive_messages_not_flagged():
    repo = _make_repo(_commits_over_months(10, 60))
    flag = analyzer.detect_generic_messages(repo)
    assert flag is None


# --- Sub-scores --------------------------------------------------------------
def test_velocity_score_lower_for_bursty_repo_than_sustained_repo():
    bursty = _make_repo(_commits_on_single_day(10))
    sustained = _make_repo(_commits_over_months(20, 180))
    bursty_score = analyzer.score_velocity_consistency(bursty)
    sustained_score = analyzer.score_velocity_consistency(sustained)
    assert sustained_score > bursty_score


def test_structural_depth_score_rewards_depth_and_size():
    flat = _make_repo([], max_depth=0, file_count=3)
    layered = _make_repo([], max_depth=4, file_count=50)
    assert analyzer.score_structural_depth(layered) > analyzer.score_structural_depth(flat)


def test_pr_engagement_score_zero_prs_with_many_commits_is_penalized():
    repo = _make_repo(_commits_over_months(15, 90), pr_count=0)
    score = analyzer.score_pr_engagement(repo)
    assert score <= 3.0


# --- Rule-based aggregate score ----------------------------------------------
def test_compute_rule_based_score_bounds():
    sub_scores = {"velocity_consistency": 0, "structural_depth": 0, "pr_engagement": 0, "message_quality": 0}
    assert analyzer.compute_rule_based_score(sub_scores) == 1.0  # clamped to min 1.0

    sub_scores_max = {"velocity_consistency": 10, "structural_depth": 10, "pr_engagement": 10, "message_quality": 10}
    assert analyzer.compute_rule_based_score(sub_scores_max) == 10.0


def test_analyze_repo_end_to_end_flags_a_synthetic_dump():
    repo = _make_repo(_commits_on_single_day(10), pr_count=0, max_depth=0, file_count=3)
    result = analyzer.analyze_repo(repo)
    flag_codes = {f.code for f in result.red_flags}
    assert "single_day_dump" in flag_codes
    assert result.velocity_consistency_score < 5


def test_analyze_repo_end_to_end_clean_for_sustained_project():
    repo = _make_repo(_commits_over_months(30, 240), pr_count=6, max_depth=3, file_count=60)
    result = analyzer.analyze_repo(repo)
    flag_codes = {f.code for f in result.red_flags}
    assert "single_day_dump" not in flag_codes
    assert "flat_structure" not in flag_codes
    assert "no_pr_history" not in flag_codes
