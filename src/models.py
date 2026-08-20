"""Domain models for the CandidateSignal evidence pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class CommitRecord:
    sha: str
    message: str
    author_date: str
    additions: int = 0
    deletions: int = 0


@dataclass(slots=True)
class RepoTelemetry:
    name: str
    full_name: str
    html_url: str
    created_at: str
    pushed_at: str
    updated_at: str = ""
    default_branch: str = "main"
    is_fork: bool = False
    is_archived: bool = False
    is_disabled: bool = False
    stargazers_count: int = 0
    watchers_count: int = 0
    open_issues_count: int = 0
    size_kb: int = 0
    language: Optional[str] = None
    commits: list[CommitRecord] = field(default_factory=list)
    pull_request_count: int = 0
    contributor_count: int = 0
    max_file_tree_depth: int = 0
    file_count: int = 0
    tree_truncated: bool = False
    fetch_error: Optional[str] = None
    pr_data_available: bool = True
    contributor_data_available: bool = True
    tree_data_available: bool = True


@dataclass(slots=True)
class RedFlag:
    code: str
    severity: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    category: str = "observation"


@dataclass(slots=True)
class RepoAnalysis:
    repo: RepoTelemetry
    activity_continuity_score: float
    structural_depth_score: float
    workflow_score: float
    communication_score: float
    maintenance_score: float
    breadth_score: float
    red_flags: list[RedFlag] = field(default_factory=list)
    data_quality: float = 1.0
    evidence_notes: list[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        from . import config

        values = {
            "activity_continuity": self.activity_continuity_score,
            "structural_depth": self.structural_depth_score,
            "workflow": self.workflow_score,
            "communication": self.communication_score,
            "maintenance": self.maintenance_score,
            "breadth": self.breadth_score,
        }
        return round(sum(values[k] * config.SCORE_WEIGHTS[k] for k in config.SCORE_WEIGHTS), 2)


@dataclass(slots=True)
class CandidateReport:
    username: str
    repos_analyzed: int
    rule_based_score: float
    final_score: float
    llm_narrative: Optional[str]
    llm_used: bool
    # Backward-compatible metadata introduced in schema v2.
    # Defaults keep existing callers/tests that construct the first v1 fields
    # positionally or by keyword working without weakening the runtime schema.
    target: str = ""
    analysis_mode: str = "profile"
    llm_provider: str = "none"
    llm_adjustment: int = 0
    confidence: float = 0.0
    data_quality: float = 0.0
    repo_analyses: list[RepoAnalysis] = field(default_factory=list)
    aggregate_red_flags: list[RedFlag] = field(default_factory=list)
    verification_questions: list[str] = field(default_factory=list)
    positive_evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    generated_at: str = ""
    analysis_limits: dict[str, Any] = field(default_factory=dict)
    rate_limit_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
