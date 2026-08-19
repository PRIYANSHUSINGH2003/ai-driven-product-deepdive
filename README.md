# CandidateSignal — Engineering Evidence Review Platform

CandidateSignal turns public GitHub telemetry into a transparent **engineering-evidence profile**. It is designed for human-led technical review, not for detecting AI-authored code and not for making hiring or misconduct decisions automatically.

## Product architecture

```text
Streamlit UI / FastAPI / CLI
            │
            ▼
      Pipeline service
            │
      ┌─────┴─────┐
      ▼           ▼
 GitHub client  Deterministic analyzer
      │           │
      │      score + observations
      │           │
      └─────┬─────┘
            ▼
     Privacy-minimized
       AI payload
            │
            ▼
      Mistral narrator
            │
            ▼
 Evidence brief + verification questions
            │
            ▼
       Audit JSON report
```

### Core design decisions

- The deterministic layer owns the score.
- Mistral narrates evidence and may adjust the score by at most ±2.
- Raw commit text, repository URLs, README contents, and source files are excluded from the Mistral payload.
- Unknown GitHub telemetry is represented explicitly and lowers confidence rather than becoming a negative signal.
- Collaboration telemetry is not interpreted as a proxy for ability when the repository is legitimately solo.
- Every run contains limitations, observations, data-quality indicators, and neutral verification questions.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

CLI:

```bash
python cli.py octocat
python cli.py octocat/Hello-World --export report.json
```

API:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Then `POST /v1/analyze` with `{"target":"owner/repo"}`. Set `APP_API_KEY` to require an `X-API-Key` header.

## Mistral

Set a **new** secret outside source control:

```env
MISTRAL_API_KEY=your_new_key
MISTRAL_MODEL=mistral-large-latest
LLM_PROVIDER=mistral
```

The implementation prefers Mistral Structured Outputs when the installed SDK supports `chat.parse`, and falls back to JSON mode. Mistral currently documents both structured outputs and JSON mode. 

## Production deployment checklist

- Use a secret manager for `MISTRAL_API_KEY`, `GITHUB_TOKEN`, and `APP_API_KEY`.
- Put authentication and rate limiting in front of the API when exposed publicly.
- Keep the deterministic tests in CI.
- Monitor GitHub API rate-limit state and Mistral failures without logging secrets or raw candidate content.
- Validate score usefulness on a representative, ethically reviewed historical dataset before operational hiring use.
- Prefer this system as a review accelerator: human evidence review → interview/work sample → decision.

## Project structure

```text
src/
  models.py          Domain entities and report serialization
  config.py          Bounded environment configuration
  github_client.py   GitHub ingestion + rate-limit/error semantics
  analyzer.py        Deterministic features + observations
  ai_scorer.py       Mistral structured narrative boundary
  pipeline.py        Application orchestration
app.py               Streamlit operator UI
api.py               FastAPI production HTTP surface
cli.py               Automation-friendly CLI
tests/               Regression tests
```

## GitHub API budget handling

CandidateSignal now checks GitHub's `core` and `search` rate-limit buckets before profile analysis. The `GET /rate_limit` endpoint does not consume the primary REST quota, and the application uses the returned budgets to cap profile sampling when necessary. GitHub's REST API has separate primary and search buckets; unauthenticated public-data requests are limited to 60 requests/hour, while authenticated requests have a substantially higher primary allowance. See the official GitHub REST API rate-limit documentation for current limits and secondary-limit behavior.

For local or deployed use, configure a read-only `GITHUB_TOKEN` through your environment or platform secret manager. Never enter the token into source code, client-side JavaScript, or a committed `.env` file.

When a run hits a rate limit, the UI:

- explains which limit failed and when the reset is expected;
- avoids manufacturing a new score from a failed run;
- uses the configured sampling controls to reduce request pressure;
- may show the last successful report with an explicit stale/cached warning;
- preserves partial repository telemetry when only PR/search/structure endpoints are unavailable.
