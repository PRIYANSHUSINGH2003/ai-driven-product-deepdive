"""
models.py
---------
Lightweight dataclasses used to pass structured data between ingestion,
analysis, scoring, and presentation layers. Kept dependency-free (stdlib only)
so the core logic never requires a specific web framework or ORM.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CommitRecord:
    sha: str
    message: str
    author_date: str          # ISO 8601 string
    additions: int = 0
    deletions: int = 0


@dataclass
class RepoTelemetry:
    name: str
    full_name: str
    html_url: str
    created_at: str
    pushed_at: str
    is_fork: bool
    stargazers_count: int
    language: Optional[str]
    commits: list = field(default_factory=list)          # list[CommitRecord]
    pull_request_count: int = 0
    max_file_tree_depth: int = 0
    file_count: int = 0
    fetch_error: Optional[str] = None                     # populated if partial fetch failure


@dataclass
class RedFlag:
    code: str
    severity: str            # "high" | "medium" | "low"
    message: str
    evidence: dict = field(default_factory=dict)


@dataclass
class RepoAnalysis:
    repo: RepoTelemetry
    velocity_consistency_score: float
    structural_depth_score: float
    pr_engagement_score: float
    message_quality_score: float
    red_flags: list = field(default_factory=list)         # list[RedFlag]


@dataclass
class CandidateReport:
    username: str
    repos_analyzed: int
    rule_based_score: float
    final_score: float
    llm_narrative: Optional[str]
    llm_used: bool
    repo_analyses: list = field(default_factory=list)      # list[RepoAnalysis]
    aggregate_red_flags: list = field(default_factory=list)  # list[RedFlag]
    errors: list = field(default_factory=list)
