"""Shared orchestration service used by Streamlit, FastAPI and CLI."""
from __future__ import annotations

from datetime import datetime, timezone

from . import ai_scorer, analyzer, config, github_client
from .models import CandidateReport, RepoAnalysis


def _confidence(repo_analyses: list[RepoAnalysis]) -> tuple[float, float]:
    if not repo_analyses:
        return 0.0, 0.0
    quality = sum(ra.data_quality for ra in repo_analyses) / len(repo_analyses)
    sample_factor = min(len(repo_analyses) / 3.0, 1.0)
    confidence = round(max(0.0, min(100.0, quality * 85.0 + sample_factor * 15.0)), 1)
    return confidence, round(quality, 2)


def analyze_candidate(
    target: str,
    max_repos: int | None = None,
    max_commits: int | None = None,
    include_forks: bool = False,
) -> CandidateReport:
    username, repo_name = github_client.parse_repo_url_or_username(target)
    max_repos = max_repos or config.MAX_REPOS_PER_CANDIDATE
    max_commits = max_commits or config.MAX_COMMITS_PER_REPO
    errors: list[str] = []

    if repo_name:
        owner_repo_pairs = [(username, repo_name)]
        mode = "repository"
    else:
        repos = github_client.fetch_user_repos(
            username,
            max_repos=max_repos,
            include_forks=include_forks,
        )
        owner_repo_pairs = [(username, r["name"]) for r in repos]
        mode = "profile"

    repo_analyses: list[RepoAnalysis] = []
    for owner, name in owner_repo_pairs:
        try:
            telemetry = github_client.fetch_repo_telemetry(
                owner,
                name,
                max_commits=max_commits,
            )
        except github_client.GitHubRateLimitError as exc:
            errors.append(f"{owner}/{name}: {exc}")
            if repo_name:
                raise
            continue
        except (github_client.GitHubClientError, ValueError) as exc:
            errors.append(f"{owner}/{name}: {exc}")
            continue

        if telemetry.fetch_error:
            errors.append(f"{owner}/{name}: {telemetry.fetch_error}")
        repo_analyses.append(analyzer.analyze_repo(telemetry))

    if not repo_analyses:
        return CandidateReport(
            username=username,
            repos_analyzed=0,
            rule_based_score=1.0,
            final_score=1.0,
            llm_narrative="No analyzable public repositories found.",
            llm_used=False,
            target=target,
            analysis_mode=mode,
            errors=errors or ["No repositories returned analyzable telemetry."],
            generated_at=datetime.now(timezone.utc).isoformat(),
            analysis_limits={"max_repos": max_repos, "max_commits": max_commits, "include_forks": include_forks},
        )

    aggregate_sub_scores = {
        key: sum(getattr(ra, attr) for ra in repo_analyses) / len(repo_analyses)
        for key, attr in {
            "activity_continuity": "activity_continuity_score",
            "structural_depth": "structural_depth_score",
            "workflow": "workflow_score",
            "communication": "communication_score",
            "maintenance": "maintenance_score",
            "breadth": "breadth_score",
        }.items()
    }
    rule_based_score = analyzer.compute_rule_based_score(aggregate_sub_scores)
    payload = analyzer.build_candidate_payload(username, repo_analyses)
    narrative, llm_used, provider, llm_errors = ai_scorer.get_llm_narrative(payload)
    errors.extend(llm_errors)
    adjustment = int(narrative.get("suggested_adjustment", 0)) if isinstance(narrative, dict) else 0
    final_score = ai_scorer.clamp_final_score(rule_based_score, adjustment)
    confidence, quality = _confidence(repo_analyses)

    return CandidateReport(
        username=username,
        repos_analyzed=len(repo_analyses),
        rule_based_score=rule_based_score,
        final_score=final_score,
        llm_narrative=narrative.get("narrative", "") if isinstance(narrative, dict) else str(narrative),
        llm_used=llm_used,
        target=target,
        analysis_mode=mode,
        llm_provider=provider,
        llm_adjustment=adjustment,
        confidence=confidence,
        data_quality=quality,
        repo_analyses=repo_analyses,
        aggregate_red_flags=[f for ra in repo_analyses for f in ra.red_flags],
        verification_questions=narrative.get("verification_questions", []) if isinstance(narrative, dict) else [],
        positive_evidence=narrative.get("positive_evidence", []) if isinstance(narrative, dict) else [],
        limitations=narrative.get("limitations", []) if isinstance(narrative, dict) else [],
        errors=errors,
        generated_at=datetime.now(timezone.utc).isoformat(),
        analysis_limits={"max_repos": max_repos, "max_commits": max_commits, "include_forks": include_forks},
    )
