# JOURNAL — Decision & AI-Audit Log

This log tracks architecture decisions for the PoC, and — in the spirit of the project itself —
is transparent about where AI-assisted suggestions during the build were suboptimal and had to be
corrected. Newest entries at the top.

---

## Entry 5 — Scoring must be *bounded*, not LLM-authored

**Initial AI suggestion:** Send the full telemetry payload to Groq/Gemini and let the model output
the final 1–10 score directly, with reasoning.

**Why it's tempting:** Simplest code path — one prompt, one parsed number, done.

**Why it's wrong:** An LLM score with no anchor is exactly the kind of black-box, unauditable
number this project is trying to replace. Two runs on the same data could plausibly disagree by
several points. Worse, since some of the "evidence" fed to the model ultimately derives from
public repo content (e.g., README text could theoretically be crafted to include instructions),
an ungrounded LLM call is a soft prompt-injection surface — a candidate could stuff their README
with text aimed at the evaluator model.

**Correction:** Split scoring into two layers:
1. **Deterministic sub-scores** (0–10 each) computed in plain Python from structural metrics:
   commit velocity/burstiness, structural depth, PR engagement, commit-message quality.
   These are weighted into a `rule_based_score`.
2. **LLM narrative pass** receives only the *aggregated numeric telemetry* (never raw README/file
   content) and is asked to (a) write a human-readable explanation and (b) propose an
   `llm_adjusted_score`. The final score is `rule_based_score`, adjusted by at most **±2** from the
   LLM's suggestion, and clamped to `[1, 10]`.

This makes the system fail safe: if the LLM call fails, times out, or hits a rate limit, the tool
still returns a fully defensible rule-based score with evidence — it just loses the natural-language
narrative. See `src/analyzer.py::compute_rule_based_score` and `src/ai_scorer.py::clamp_score`.

---

## Entry 4 — No database for the PoC

**Initial AI suggestion:** Stand up a Postgres/SQLite schema (candidates, repos, commits, scores
tables) to "make the architecture look production-ready."

**Why it's tempting:** Feels more "real," easier to demo persistence, historical trend lines.

**Why it's wrong for this stage:** This is a PoC whose entire pitch is $0 infra and instant
run-anywhere setup. A DB schema adds migration files, a connection layer, and a dependency
(even SQLite adds file-state assumptions) that buys nothing for the core question the PoC needs
to answer: *does the scoring logic work on real data?* It also tempts scope creep into building a
candidate-tracking system, which is explicitly out of scope (see PRD §5).

**Correction:** Keep everything in-memory for the duration of a single CLI run / Streamlit
session. If the user wants to keep a result, the tool offers a one-shot JSON/Markdown export to
disk (`--export report.json`) rather than a persistent store. Historical tracking across runs is
explicitly deferred to a "v2" note in the README roadmap, not built now.

---

## Entry 3 — One LLM call per candidate, not per repo

**Initial AI suggestion:** Loop over each of the candidate's repos and call the LLM once per repo
for a "per-repo depth rating," then average them.

**Why it's tempting:** Feels more granular, and mirrors how a human reviewer might look at repos
one at a time.

**Why it's wrong:** With free-tier rate limits (Groq free tier is generous but still capped per
minute/day) and a candidate with 8+ repos, that's 8+ LLM calls per candidate — multiplying latency
and burning through the free quota roughly 8x faster for no proportional signal gain, since the
interesting comparative signal (bursty single-repo dump vs. sustained multi-repo pattern) is
actually *cross-repo*, not per-repo.

**Correction:** Pre-aggregate all repo telemetry into one compact structured JSON summary in
Python first (`src/analyzer.py::build_candidate_payload`), then make exactly one LLM call for the
whole candidate. Per-repo detail is still preserved and shown in the dashboard/CLI — it's just
computed deterministically, not via repeated model calls.

---

## Entry 2 — "Single-day dump" needs a relative, not absolute, threshold

**Initial AI suggestion:** Flag any repo where all commits happened on the same calendar date.

**Why it's tempting:** Simple to implement, checks a literal reading of the requirement.

**Why it's wrong:** This produces false positives on entirely legitimate small utility scripts,
weekend hackathon projects, and genuinely fast one-sitting builds by strong engineers — punishing
exactly the kind of rapid, competent shipping the tool shouldn't penalize. The signal that
actually matters is *disproportionate concentration relative to the repo's claimed history* —
e.g., a repo with commit timestamps spanning "6 months" of authored dates where 90%+ of the actual
diff volume landed in one contiguous 24-hour window (consistent with a bulk import/generation
followed by cosmetic backfilled commits).

**Correction:** Compute burstiness as `% of total commits (or lines changed) within the densest
rolling 24-hour window`, and only flag when that ratio exceeds a configurable threshold
(default 90%) **and** the repo has more than a minimum commit count (avoids flagging trivially
small repos where the stat is meaningless). See `src/analyzer.py::detect_single_day_dump`.

---

## Entry 1 — Initial architecture decisions

- **Language:** Python 3.11+, `requests` for GitHub REST calls (no GraphQL — REST is simpler to
  reason about for a PoC and has a friendlier free rate limit story for unauthenticated use).
- **LLM provider:** Groq (Llama 3.x, e.g. `llama-3.3-70b-versatile`) as primary — fastest free
  inference available, generous free tier, OpenAI-compatible-ish REST API. Gemini (`gemini-1.5-flash`
  free tier) supported as a drop-in fallback via a small provider abstraction, so the tool doesn't
  hard-depend on a single vendor's free tier surviving long-term.
- **No auth/session system.** PoC operates purely on public data; no login, no OAuth app review
  needed from GitHub, which would slow down "clone and run" onboarding.
- **Interfaces:** Both a CLI (`cli.py`, zero extra dependencies beyond `requests`) and a Streamlit
  dashboard (`app.py`) share the exact same `src/` core logic — the UI layer never contains
  scoring logic, to keep the two front-ends provably consistent.
- **Rate-limit posture:** default to unauthenticated GitHub calls for a quick demo, but read an
  optional `GITHUB_TOKEN` env var and use it automatically if present (60 req/hr → 5,000 req/hr),
  documented clearly in README rather than assumed.
