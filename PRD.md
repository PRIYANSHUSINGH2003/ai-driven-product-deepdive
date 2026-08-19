# PRD — CandidateSignal Production v1

## Problem

Hiring teams need a second-opinion signal about whether a public GitHub portfolio shows an iterative engineering trajectory. Raw repository count and polished README files are weak proxies. The product should make observable repository behavior easier to inspect without pretending that public telemetry can prove authorship, competence, or intent.

## User outcome

A user enters a GitHub username or repository and receives, in one view:

1. a 1–10 deterministic depth/building-pattern score,
2. an optional AI-written evidence narrative,
3. confidence/data completeness,
4. explicit red flags with evidence,
5. per-repository sub-scores, and
6. an exportable JSON audit record.

## Product principles

- **Evidence before interpretation:** raw metrics remain visible.
- **AI cannot own the score:** AI may only adjust the deterministic result within a hard bound.
- **Unknown is not negative:** incomplete telemetry lowers confidence.
- **Privacy by minimization:** no raw README/file text is sent to the model.
- **Human review required:** never present a hiring recommendation as an automated fact.

## v1 functional scope

- Public GitHub username analysis.
- Single repository analysis.
- GitHub URL / `owner/repo` input parsing.
- Commit velocity analysis.
- Structural depth analysis.
- PR and contributor workflow signals.
- Commit-message quality signal.
- Explicit high/medium/low flags.
- Mistral-first narrative layer with fallback providers.
- Responsive Streamlit dashboard.
- CLI.
- JSON export.
- Unit tests for deterministic scoring and privacy boundaries.

## Non-functional requirements

### Reliability

A failed LLM call must never prevent a deterministic report. A partial GitHub failure must be surfaced explicitly and must not silently become a negative score.

### Security

Secrets come from environment variables/secret stores. No API key is committed. The LLM payload is minimized and excludes raw candidate-controlled content.

### Performance

Default repository and commit caps keep public GitHub usage bounded. The system performs one LLM call per candidate.

### Explainability

Every score is accompanied by sub-scores, telemetry, and red flags. Confidence is separate from score.

## Future roadmap

- Optional authenticated multi-user teams.
- Persistent, opt-in historical comparisons.
- Organization/batch mode with job queues.
- Candidate self-audit mode with improvement suggestions.
- Threshold calibration and fairness review tooling.
- ATS/export integrations only after privacy, authorization, and audit requirements are designed.
