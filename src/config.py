"""
config.py
---------
Central place for env vars, tunable thresholds, and cost/latency guardrails.
Nothing in here should ever be a secret literal — secrets always come from env vars.
"""
import os

# --- Optional credentials (all free-tier) -----------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()          # optional, raises rate limit 60->5000/hr
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()          # free tier: console.groq.com
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()      # free tier fallback: aistudio.google.com

# Which provider to try first. "groq" | "gemini" | "none" (skip LLM narrative entirely)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

# --- GitHub API guardrails ----------------------------------------------------
GITHUB_API_BASE = "https://api.github.com"
MAX_REPOS_PER_CANDIDATE = int(os.getenv("MAX_REPOS_PER_CANDIDATE", "8"))
MAX_COMMITS_PER_REPO = int(os.getenv("MAX_COMMITS_PER_REPO", "100"))
REQUEST_TIMEOUT_SECONDS = 15

# --- Red-flag detection thresholds -------------------------------------------
SINGLE_DAY_DUMP_RATIO_THRESHOLD = 0.90   # >=90% of commits in the densest 24h window
SINGLE_DAY_DUMP_MIN_COMMITS = 5          # don't evaluate burstiness on trivially small repos
FLAT_STRUCTURE_MAX_DEPTH = 1             # directory depth <=1 counts as "flat"/shallow
GENERIC_MESSAGE_PATTERNS = [
    "update", "fix", "initial commit", "wip", "changes", "test", "final",
    "commit", "misc", "stuff", "asdf", "temp",
]
GENERIC_MESSAGE_RATIO_FLAG = 0.70        # >=70% generic messages -> flag

# --- Scoring weights (deterministic rule-based layer) ------------------------
# Must sum to 1.0 — see src/analyzer.py::compute_rule_based_score
SCORE_WEIGHTS = {
    "velocity_consistency": 0.35,   # sustained vs bursty activity
    "structural_depth": 0.25,       # multi-layer architecture vs single flat file
    "pr_engagement": 0.20,          # pull request usage / collaboration signal
    "message_quality": 0.20,        # descriptive vs generic commit messages
}

# LLM narrative is allowed to move the rule-based score by at most this many points
LLM_SCORE_ADJUSTMENT_CLAMP = 2

# --- LLM call budget -----------------------------------------------------------
LLM_MAX_COMMIT_MESSAGES_SAMPLED_PER_REPO = 40
LLM_TIMEOUT_SECONDS = 20
