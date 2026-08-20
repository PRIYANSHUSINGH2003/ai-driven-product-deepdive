"""Centralized runtime configuration and scoring weights."""
from __future__ import annotations

import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest").strip()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GITHUB_API_BASE = "https://api.github.com"
MAX_REPOS_PER_CANDIDATE = max(1, min(_int("MAX_REPOS_PER_CANDIDATE", 8), 20))
MAX_COMMITS_PER_REPO = max(10, min(_int("MAX_COMMITS_PER_REPO", 100), 100))
REQUEST_TIMEOUT_SECONDS = max(5, _int("REQUEST_TIMEOUT_SECONDS", 15))
LLM_TIMEOUT_SECONDS = max(5, _int("LLM_TIMEOUT_SECONDS", 25))
LLM_MAX_TOKENS = max(128, _int("LLM_MAX_TOKENS", 700))
STALE_REPO_DAYS = max(30, _int("STALE_REPO_DAYS", 365))
LLM_SCORE_ADJUSTMENT_CLAMP = 2

SINGLE_DAY_DUMP_RATIO_THRESHOLD = 0.90
SINGLE_DAY_DUMP_MIN_COMMITS = 5
GENERIC_MESSAGE_PATTERNS = [
    "update", "fix", "initial commit", "wip", "changes", "test", "final",
    "commit", "misc", "stuff", "asdf", "temp",
]
GENERIC_MESSAGE_RATIO_FLAG = 0.70

SCORE_WEIGHTS = {
    "activity_continuity": 0.25,
    "structural_depth": 0.20,
    "workflow": 0.15,
    "communication": 0.10,
    "maintenance": 0.15,
    "breadth": 0.15,
}

LLM_MAX_COMMIT_MESSAGES_SAMPLED_PER_REPO = 0
CACHE_TTL_SECONDS = max(30, _int("CACHE_TTL_SECONDS", 300))
