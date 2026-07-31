"""
pipeline.py
-----------
The single orchestration entrypoint shared by cli.py and app.py, so both
front-ends are provably running the exact same logic (see JOURNAL.md Entry 1:
"UI layer never contains scoring logic").
"""
from . import config, github_client, analyzer, ai_scorer
from .models import CandidateReport, RepoAnalysis


def analyze_candidate(target: str) -> CandidateReport:
    """
    target: a GitHub username OR a full repo URL/`owner/repo` string.
    If a specific repo is given, only that repo is analyzed (still produces
    a full CandidateReport shape for UI consistency).
    """
    username, repo_name = github_client.parse_repo_url_or_username(target)
    errors: list[str] = []

    if repo_name:
        repo_dicts = [{"name": repo_name, "owner": {"login": username}}]
        owner_repo_pairs = [(username, repo_name)]
    else:
        try:
            repos = github_client.fetch_user_repos(username)
        except github_client.GitHubRateLimitError as e:
            raise
        except ValueError as e:
            raise
        owner_repo_pairs = [(username, r["name"]) for r in repos]

    repo_analyses: list[RepoAnalysis] = []
    for owner, name in owner_repo_pairs:
        try:
            telemetry = github_client.fetch_repo_telemetry(owner, name)
        except github_client.GitHubRateLimitError as e:
            errors.append(f"{owner}/{name}: {e}")
            continue
        if telemetry.fetch_error:
            errors.append(f"{owner}/{name}: {telemetry.fetch_error}")
            # still include it -- analyzer handles empty telemetry gracefully with neutral scores
        repo_analyses.append(analyzer.analyze_repo(telemetry))

    if not repo_analyses:
        return CandidateReport(
            username=username, repos_analyzed=0, rule_based_score=1.0, final_score=1.0,
            llm_narrative="No analyzable public repositories found.", llm_used=False,
            errors=errors or ["No repositories returned data."],
        )

    # Aggregate sub-scores across repos (simple mean -- each repo contributes equally;
    # see README roadmap for possible recency-weighting in a future version)
    def avg(attr):
        vals = [getattr(ra, attr) for ra in repo_analyses]
        return sum(vals) / len(vals)

    aggregate_sub_scores = {
        "velocity_consistency": avg("velocity_consistency_score"),
        "structural_depth": avg("structural_depth_score"),
        "pr_engagement": avg("pr_engagement_score"),
        "message_quality": avg("message_quality_score"),
    }
    rule_based_score = analyzer.compute_rule_based_score(aggregate_sub_scores)

    payload = analyzer.build_candidate_payload(username, repo_analyses)
    narrative, adjustment, llm_used = ai_scorer.get_llm_narrative(payload)
    final_score = ai_scorer.clamp_final_score(rule_based_score, adjustment)

    aggregate_red_flags = [f for ra in repo_analyses for f in ra.red_flags]

    return CandidateReport(
        username=username,
        repos_analyzed=len(repo_analyses),
        rule_based_score=rule_based_score,
        final_score=final_score,
        llm_narrative=narrative,
        llm_used=llm_used,
        repo_analyses=repo_analyses,
        aggregate_red_flags=aggregate_red_flags,
        errors=errors,
    )
