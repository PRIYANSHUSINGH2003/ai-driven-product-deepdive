"""Application configuration with bounded environment-backed settings."""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _int_env(name: str, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < minimum:
        return default
    if maximum is not None and value > maximum:
        return maximum
    return value


def _float_env(name: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    if maximum is not None and value > maximum:
        return maximum
    return value


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
APP_API_KEY = os.getenv("APP_API_KEY", "").strip()

PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "https://candidatesignal.streamlit.app").strip().rstrip("/")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest").strip()

GITHUB_API_BASE = "https://api.github.com"
MAX_REPOS_PER_CANDIDATE = _int_env("MAX_REPOS_PER_CANDIDATE", 8, 1, 20)
MAX_COMMITS_PER_REPO = _int_env("MAX_COMMITS_PER_REPO", 100, 10, 100)
REQUEST_TIMEOUT_SECONDS = _float_env("REQUEST_TIMEOUT_SECONDS", 15.0, 3.0, 60.0)
LLM_TIMEOUT_SECONDS = _float_env("LLM_TIMEOUT_SECONDS", 25.0, 5.0, 90.0)
CACHE_TTL_SECONDS = _int_env("CACHE_TTL_SECONDS", 300, 0, 3600)

SINGLE_DAY_DUMP_RATIO_THRESHOLD = _float_env("SINGLE_DAY_DUMP_RATIO_THRESHOLD", 0.90, 0.50, 1.0)
SINGLE_DAY_DUMP_MIN_COMMITS = _int_env("SINGLE_DAY_DUMP_MIN_COMMITS", 8, 3, 100)
GENERIC_MESSAGE_PATTERNS = ["update", "fix", "initial commit", "wip", "changes", "test", "final", "commit", "misc", "stuff", "asdf", "temp"]
GENERIC_MESSAGE_RATIO_FLAG = _float_env("GENERIC_MESSAGE_RATIO_FLAG", 0.70, 0.50, 1.0)
STALE_REPO_DAYS = _int_env("STALE_REPO_DAYS", 365, 30, 3650)

# Weights reflect evidence quality, not hiring importance.
SCORE_WEIGHTS = {
    "activity_continuity": 0.25,
    "structural_depth": 0.20,
    "workflow": 0.15,
    "communication": 0.10,
    "maintenance": 0.15,
    "breadth": 0.15,
}

LLM_SCORE_ADJUSTMENT_CLAMP = _int_env("LLM_SCORE_ADJUSTMENT_CLAMP", 2, 0, 2)
LLM_MAX_TOKENS = _int_env("LLM_MAX_TOKENS", 700, 128, 1500)
