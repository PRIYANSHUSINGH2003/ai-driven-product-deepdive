"""Orchestrate ingestion, deterministic analysis, optional AI narration, and audit output."""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from . import ai_scorer, analyzer, github_client
from .models import CandidateReport, RepoAnalysis


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _default_verification_questions(report: CandidateReport) -> list[str]:
    questions: list[str] = []
    if any(flag.code == "high_change_concentration" for flag in report.aggregate_red_flags):
        questions.append("Walk through one project whose work was concentrated into a short period. What changed during that period, and what happened before or after it?")
    if any(flag.code == "low_information_commit_messages" for flag in report.aggregate_red_flags):
        questions.append("Pick two important commits and explain the problem, design trade-off, and verification work behind them.")
    if any(flag.code == "solo_workflow" for flag in report.aggregate_red_flags):
        questions.append("Describe how you review, test, or validate changes when working without a pull-request workflow.")
    if not questions:
        questions.append("Choose one repository and explain the most significant architectural decision you made and how you validated it.")
    return questions[:4]


def analyze_candidate(target: str, max_repos: int | None = None, max_commits: int | None = None, include_forks: bool = False) -> CandidateReport:
    username, repo_name = github_client.parse_repo_url_or_username(target)
    errors: list[str] = []
    mode = "repository" if repo_name else "profile"
    max_repos = max_repos or config.MAX_REPOS_PER_CANDIDATE
    max_commits = max_commits or config.MAX_COMMITS_PER_REPO

    if repo_name:
        owner_repo_pairs = [(username, repo_name)]
    else:
        repos = github_client.fetch_user_repos(username, max_repos=max_repos, include_forks=include_forks)
        owner_repo_pairs = [(username, repo["name"]) for repo in repos]

    repo_analyses: list[RepoAnalysis] = []
    for owner, name in owner_repo_pairs:
        try:
            telemetry = github_client.fetch_repo_telemetry(owner, name, max_commits=max_commits)
            if telemetry.fetch_error:
                errors.append(f"{owner}/{name}: {telemetry.fetch_error}")
            repo_analyses.append(analyzer.analyze_repo(telemetry))
        except github_client.GitHubRateLimitError:
            raise
        except (github_client.GitHubClientError, ValueError) as exc:
            errors.append(f"{owner}/{name}: {exc}")

    generated_at = datetime.now(timezone.utc).isoformat()
    if not repo_analyses:
        return CandidateReport(
            username=username, target=target, analysis_mode=mode, repos_analyzed=0,
            rule_based_score=5.0, final_score=5.0,
            llm_narrative="No analyzable public repositories were returned. A neutral baseline is shown because there is insufficient evidence.",
            llm_used=False, confidence=0.0, data_quality=0.0,
            limitations=["No repository telemetry was available for this run."],
            errors=_unique(errors or ["No repositories returned usable telemetry."]),
            generated_at=generated_at,
            analysis_limits={"max_repos": max_repos, "max_commits": max_commits, "include_forks": include_forks},
        )

    attrs = {
        "activity_continuity": mean(ra.activity_continuity_score for ra in repo_analyses),
        "structural_depth": mean(ra.structural_depth_score for ra in repo_analyses),
        "workflow": mean(ra.workflow_score for ra in repo_analyses),
        "communication": mean(ra.communication_score for ra in repo_analyses),
        "maintenance": mean(ra.maintenance_score for ra in repo_analyses),
        "breadth": mean(ra.breadth_score for ra in repo_analyses),
    }
    rule_score = analyzer.compute_rule_based_score(attrs)
    payload = analyzer.build_candidate_payload(username, repo_analyses)
    ai_result, llm_used, provider, provider_errors = ai_scorer.get_llm_narrative(payload)
    adjustment = int(ai_result.get("suggested_adjustment", 0)) if llm_used else 0
    final_score = ai_scorer.clamp_final_score(rule_score, adjustment)

    data_quality = round(mean(ra.data_quality for ra in repo_analyses), 2)
    coverage = min(len(repo_analyses) / 3.0, 1.0)
    confidence = round((data_quality * 0.75 + coverage * 0.25) * 100, 1)

    flags = [flag for ra in repo_analyses for flag in ra.red_flags]
    positive_evidence = _unique(ai_result.get("positive_evidence", []))
    limitations = _unique(ai_result.get("limitations", []))
    verification_questions = _unique(ai_result.get("verification_questions", []))

    if len(repo_analyses) < 3:
        limitations.insert(0, "Only a small number of repositories were analyzed; profile-level conclusions are less representative.")
    if any(ra.data_quality < 0.8 for ra in repo_analyses):
        limitations.insert(0, "Some repository telemetry was incomplete; unknown fields were neutralized rather than treated as negative evidence.")
    if not verification_questions:
        verification_questions = _default_verification_questions(CandidateReport(
            username=username, target=target, analysis_mode=mode, repos_analyzed=len(repo_analyses),
            rule_based_score=rule_score, final_score=final_score, llm_narrative=None, llm_used=False,
            aggregate_red_flags=flags,
        ))

    if provider_errors:
        errors.extend([f"LLM provider: {message}" for message in provider_errors])

    return CandidateReport(
        username=username,
        target=target,
        analysis_mode=mode,
        repos_analyzed=len(repo_analyses),
        rule_based_score=rule_score,
        final_score=final_score,
        llm_narrative=ai_result.get("narrative"),
        llm_used=llm_used,
        llm_provider=provider,
        llm_adjustment=adjustment,
        confidence=confidence,
        data_quality=data_quality,
        repo_analyses=repo_analyses,
        aggregate_red_flags=flags,
        verification_questions=verification_questions[:4],
        positive_evidence=positive_evidence[:4],
        limitations=limitations[:6],
        errors=_unique(errors),
        generated_at=generated_at,
        analysis_limits={"max_repos": max_repos, "max_commits": max_commits, "include_forks": include_forks},
    )
