# PRD — AI-Era Candidate Authenticity & Evaluation Engine

**Status:** PoC v0.1
**Owner:** Solo builder (Senior PM / Lead Eng hat)
**Last updated:** 2026-07-31

---

## 1. Problem Statement

Generative AI has collapsed the cost of *producing* code and prose to near zero. A candidate can generate a dozen polished-looking repositories, a portfolio README, and a project write-up in an afternoon. This has broken two of the oldest, cheapest signals recruiters and engineering managers relied on:

- **Volume as a proxy for effort.** A large GitHub profile used to correlate with sustained building. It no longer does.
- **Polish as a proxy for competence.** Clean commit messages and tidy READMEs used to correlate with engineering discipline. AI assistants can now generate both without the underlying skill.

What recruiters and engineering managers actually want to know is not "does this person have repos" but **"did this person build this over time, iteratively, and does the shape of the work match a real engineering trajectory?"**

There is no existing lightweight, self-hostable tool that turns public GitHub telemetry into an *authenticity and depth* signal. Existing tools (GitHub's own contribution graph, tools like `git-quality` linters) measure code style, not building behavior over time.

## 2. Goal

Ship a free, open-source, self-hostable PoC that takes a GitHub username or repo URL and produces:
1. A **Depth & Authenticity Score (1–10)**.
2. A **commit velocity graph** exposing burstiness vs. sustained effort.
3. A list of **explicit red flags** with evidence (not just a black-box score).

The PoC is explicitly *not* trying to detect "was this code AI-generated" (that's a losing arms race). It is trying to detect **behavioral patterns of shallow, dumped, or fabricated project history** — which is a more durable signal than trying to fingerprint AI-written code.

## 3. Target Personas

| Persona | Need | Success looks like |
|---|---|---|
| **Early-stage tech founder** hiring their first 3–5 engineers | Fast, cheap pre-screen before a costly technical interview | Runs the tool on a shortlist in <10 min, deprioritizes obvious dumps |
| **Engineering manager / recruiter at a scaling startup** | A second opinion to accompany resume screening at volume | Consistent, explainable scoring they can defend to a hiring committee |
| **Candidates themselves (secondary persona)** | Understand how their own public profile reads to evaluators | Can self-audit and improve genuine building habits |

Explicitly **out of scope**: enterprise ATS integration, private repo analysis requiring OAuth app review, plagiarism/code-clone detection, resume parsing.

## 4. Core User Stories

1. As a founder, I paste a GitHub username and get a score + red flags in under 30 seconds, without paying for API credits.
2. As a recruiter, I can see *why* a candidate scored low (e.g., "83% of commits across all repos landed within a single 6-hour window on 2024-03-02") rather than trusting an opaque number.
3. As an engineer building this tool, I can run it entirely on free tiers (GitHub REST API + Groq/Gemini free tier) with no database, no paid hosting, and no credit card on file.

## 5. Functional Scope (PoC)

| # | Feature | In scope for PoC |
|---|---|---|
| 1 | Fetch public repo list, commits, PRs, file tree for a user or single repo | ✅ |
| 2 | Deterministic red-flag detection (single-day dumps, flat file structure, zero PRs, generic commit messages) | ✅ |
| 3 | Hybrid scoring: rule-based sub-scores + LLM narrative review | ✅ |
| 4 | CLI output | ✅ |
| 5 | Streamlit dashboard with velocity chart | ✅ |
| 6 | Multi-repo aggregate candidate score | ✅ |
| 7 | Private repo / OAuth login analysis | ❌ (future) |
| 8 | Persistent storage / historical tracking of candidates | ❌ (future — deliberately in-memory only for PoC, see JOURNAL.md) |
| 9 | Team/collaborative commentary, ATS export | ❌ (future) |

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Cost** | $0 infrastructure. Only free tiers: GitHub REST API (unauthenticated 60 req/hr, or PAT for 5,000 req/hr — free), Groq free tier (Llama 3.x), optional Gemini free tier as fallback. No paid DB, no paid hosting. |
| **Latency** | Single-candidate analysis (up to 8 repos) completes in **< 20s** on a warm run, **< 45s** worst case including LLM call, under normal free-tier rate limits. |
| **Rate-limit safety** | Tool must degrade gracefully (cached partial results, clear error) rather than crash when GitHub or Groq rate limits are hit. Never silently retries into a paid tier. |
| **Reliability of scoring** | LLM narrative score must be **bounded** by the deterministic rule-based score (±2) so a prompt-injected README or hallucinating model cannot arbitrarily flip a candidate's score. |
| **Explainability** | Every score must ship with the underlying evidence (raw metrics + red flag list), never a bare number. |
| **Portability** | Runs locally with `pip install -r requirements.txt`; no Docker required for PoC, no cloud account required beyond free API keys. |
| **Privacy** | Only public data is fetched. No data persisted beyond the current process (in-memory only) unless the user explicitly exports a report file. |
| **Security** | API keys read from environment variables / `.env`, never hardcoded, never logged. |

## 7. Latency & Cost Guardrails (explicit)

- **GitHub API budget:** cap analysis to a configurable `MAX_REPOS_PER_CANDIDATE` (default 8, most recently pushed) to stay well inside the 60 req/hr unauthenticated limit; recommend a free PAT for real usage (5,000 req/hr).
- **LLM API budget:** exactly **one** LLM call per candidate (not per repo) — the deterministic layer pre-aggregates all repo telemetry into a single compact JSON payload before the LLM call. This is a deliberate cost/latency control, see JOURNAL.md §2.
- **Token budget:** payload to the LLM is capped (commit message sample truncated to last 40 messages per repo, aggregated) to stay comfortably inside free-tier context and rate limits.
- **No polling/webhooks:** PoC is pull-based, on-demand only — no background jobs, no always-on compute, so it can run entirely on a laptop or a free Streamlit Community Cloud instance.

## 8. Success Metrics (for the PoC, informal)

- Correctly flags a synthetic "single-day dump" repo as high-risk in manual testing.
- Correctly scores a long-running, multi-contributor, PR-heavy repo as high-depth.
- Runs end-to-end for $0 across at least 20 manual test candidates.
- A non-technical recruiter can read the output and explain the score back in their own words.

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| GitHub rate limits block unauthenticated use | Support optional `GITHUB_TOKEN`, clearly documented in README |
| LLM hallucinates a score disconnected from evidence | Hybrid scoring with hard clamp against deterministic sub-scores |
| Tool used as sole hiring gate ("AI said no") | README + PRD explicitly frame this as a **pre-screen signal**, not a hiring decision; dashboard always shows raw evidence |
| False positives (e.g., legitimate hackathon projects flagged as "dumps") | Red flags are labeled as *flags to investigate*, not disqualifiers; score explanation always shown |
| Free LLM tier deprecated/changed | Provider abstraction layer (`ai_scorer.py`) supports swapping Groq ↔ Gemini via config with no code changes elsewhere |
