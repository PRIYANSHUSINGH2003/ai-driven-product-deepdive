"""Stable versioned serialization for exports and future API integrations."""
from __future__ import annotations
from dataclasses import asdict
from .models import CandidateReport, RepoAnalysis
SCHEMA_VERSION="2.0"

def repo_to_dict(ra: RepoAnalysis)->dict:
    repo=ra.repo
    return {"name":repo.name,"full_name":repo.full_name,"html_url":repo.html_url,"language":repo.language,"archived":repo.archived,
            "commits_sampled":len(repo.commits) if repo.commit_data_available else None,"pull_requests":repo.pull_request_count if repo.pr_data_available else None,
            "contributors":repo.contributor_count if repo.contributor_data_available else None,"file_count":repo.file_count if repo.tree_data_available else None,
            "max_dir_depth":repo.max_file_tree_depth if repo.tree_data_available else None,"activity_span_days":ra.activity_span_days if repo.commit_data_available else None,
            "active_days":ra.active_days if repo.commit_data_available else None,"burst_ratio":ra.burst_ratio if repo.commit_data_available else None,"data_quality":ra.data_quality,
            "sub_scores":{"velocity_consistency":ra.velocity_consistency_score,"structural_depth":ra.structural_depth_score,"pr_engagement":ra.pr_engagement_score,"message_quality":ra.message_quality_score},
            "red_flags":[asdict(x) for x in ra.red_flags],"evidence":[asdict(x) for x in ra.evidence],"unknowns":ra.unknowns,"fetch_error":repo.fetch_error}

def report_to_dict(report: CandidateReport)->dict:
    return {"schema_version":SCHEMA_VERSION,"analysis":{"username":report.username,"target_kind":report.target_kind,"analyzed_at":report.analyzed_at,"repos_analyzed":report.repos_analyzed,"rule_based_score":report.rule_based_score,"final_score":report.final_score,"confidence":report.confidence},
            "ai":{"used":report.llm_used,"provider":report.llm_provider,"adjustment":report.llm_adjustment,"adjustment_reason":report.llm_adjustment_reason,"narrative":report.llm_narrative},
            "evidence":[asdict(x) for x in report.evidence],"unknowns":report.unknowns,"red_flags":[asdict(x) for x in report.aggregate_red_flags],"repositories":[repo_to_dict(x) for x in report.repo_analyses],"diagnostics":report.errors}
