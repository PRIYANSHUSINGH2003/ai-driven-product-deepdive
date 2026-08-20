"""Stable versioned serialization for exports and API integrations."""
from __future__ import annotations

from dataclasses import asdict
from .models import CandidateReport, RepoAnalysis

SCHEMA_VERSION = "2.0"


def repo_to_dict(ra: RepoAnalysis) -> dict:
    repo = ra.repo
    return {
        "name": repo.name,
        "full_name": repo.full_name,
        "html_url": repo.html_url,
        "language": repo.language,
        "archived": repo.is_archived,
        "fork": repo.is_fork,
        "disabled": repo.is_disabled,
        "commits_sampled": len(repo.commits),
        "pull_requests": repo.pull_request_count if repo.pr_data_available else None,
        "contributors": repo.contributor_count if repo.contributor_data_available else None,
        "file_count": repo.file_count if repo.tree_data_available else None,
        "max_dir_depth": repo.max_file_tree_depth if repo.tree_data_available else None,
        "tree_truncated": repo.tree_truncated,
        "data_quality": ra.data_quality,
        "sub_scores": {
            "activity_continuity": ra.activity_continuity_score,
            "structural_depth": ra.structural_depth_score,
            "workflow": ra.workflow_score,
            "communication": ra.communication_score,
            "maintenance": ra.maintenance_score,
            "breadth": ra.breadth_score,
        },
        "red_flags": [asdict(x) for x in ra.red_flags],
        "evidence_notes": list(ra.evidence_notes),
        "fetch_error": repo.fetch_error,
    }


def report_to_dict(report: CandidateReport) -> dict:
    unknowns: list[str] = []
    for ra in report.repo_analyses:
        unknowns.extend(ra.evidence_notes)

    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "username": report.username,
            "target": report.target or report.username,
            "analysis_mode": report.analysis_mode,
            "generated_at": report.generated_at,
            "repos_analyzed": report.repos_analyzed,
            "rule_based_score": report.rule_based_score,
            "final_score": report.final_score,
            "confidence": report.confidence,
            "data_quality": report.data_quality,
            "limits": dict(report.analysis_limits),
        },
        "ai": {
            "used": report.llm_used,
            "provider": report.llm_provider,
            "adjustment": report.llm_adjustment,
            "narrative": report.llm_narrative,
            "positive_evidence": list(report.positive_evidence),
            "limitations": list(report.limitations),
            "verification_questions": list(report.verification_questions),
        },
        "evidence": [asdict(x) for x in report.aggregate_red_flags],
        "unknowns": unknowns,
        "red_flags": [asdict(x) for x in report.aggregate_red_flags],
        "repositories": [repo_to_dict(x) for x in report.repo_analyses],
        "diagnostics": list(report.errors),
        "rate_limit": dict(report.rate_limit_snapshot),
    }
