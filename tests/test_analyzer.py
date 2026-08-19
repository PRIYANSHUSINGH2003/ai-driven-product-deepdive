from src.analyzer import analyze_repo, build_candidate_payload, compute_rule_based_score
from src.github_client import parse_repo_url_or_username
from src.models import CommitRecord, RepoTelemetry


def repo(**kwargs):
    defaults = dict(
        name="demo", full_name="octo/demo", html_url="https://github.com/octo/demo",
        created_at="2026-01-01T00:00:00Z", pushed_at="2026-08-01T00:00:00Z",
        language="Python",
    )
    defaults.update(kwargs)
    return RepoTelemetry(**defaults)


def test_solo_no_pr_workflow_is_not_penalized_as_missing_collaboration():
    telemetry = repo(
        commits=[CommitRecord(str(i), "implement feature", f"2026-01-{i+1:02d}T00:00:00Z") for i in range(10)],
        contributor_count=1, pull_request_count=0, file_count=10, max_file_tree_depth=2,
    )
    analysis = analyze_repo(telemetry)
    assert analysis.workflow_score >= 5
    assert any(flag.code == "solo_workflow" for flag in analysis.red_flags)


def test_payload_excludes_raw_text_and_identity_surface():
    secret_text = "PRIVATE-CANDIDATE-CONTENT-DO-NOT-SEND"
    telemetry = repo(commits=[CommitRecord("abc", secret_text, "2026-01-01T00:00:00Z")], file_count=5, max_file_tree_depth=2)
    payload = build_candidate_payload("octo", [analyze_repo(telemetry)])
    rendered = str(payload)
    assert secret_text not in rendered
    assert "demo" not in rendered
    assert "html_url" not in rendered


def test_rule_score_is_clamped_and_uses_new_dimensions():
    keys = {"activity_continuity", "structural_depth", "workflow", "communication", "maintenance", "breadth"}
    assert keys == set(__import__("src.config", fromlist=["SCORE_WEIGHTS"]).SCORE_WEIGHTS)
    assert 1 <= compute_rule_based_score({key: 0 for key in keys}) <= 10
    assert compute_rule_based_score({key: 10 for key in keys}) == 10


def test_parse_repo_targets():
    assert parse_repo_url_or_username("octocat") == ("octocat", None)
    assert parse_repo_url_or_username("octocat/hello-world") == ("octocat", "hello-world")
    assert parse_repo_url_or_username("https://github.com/octocat/hello-world/") == ("octocat", "hello-world")
    assert parse_repo_url_or_username("git@github.com:octocat/hello-world.git") == ("octocat", "hello-world")
