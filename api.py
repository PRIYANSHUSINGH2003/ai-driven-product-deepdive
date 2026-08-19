"""Small production HTTP API around the shared analysis service."""
from __future__ import annotations

import hmac

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from src import config
from src.pipeline import analyze_candidate
from src.github_client import GitHubRateLimitError

app = FastAPI(
    title="CandidateSignal API",
    version="2.0.0",
    description="Explainable public GitHub engineering-evidence analysis. Not a hiring decision engine.",
)


class AnalyzeRequest(BaseModel):
    target: str = Field(min_length=1, max_length=300, description="GitHub username, owner/repo, or public repository URL")
    max_repos: int = Field(default=8, ge=1, le=20)
    max_commits: int = Field(default=100, ge=10, le=100)
    include_forks: bool = False


class AnalyzeResponse(BaseModel):
    schema_version: str
    report: dict


def authorize(x_api_key: str | None = Header(default=None)) -> None:
    if not config.APP_API_KEY:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, config.APP_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "candidate-signal", "version": "2.0.0"}


@app.post("/v1/analyze", response_model=AnalyzeResponse, dependencies=[Depends(authorize)])
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        report = analyze_candidate(request.target.strip(), max_repos=request.max_repos, max_commits=request.max_commits, include_forks=request.include_forks)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AnalyzeResponse(schema_version="2.0", report=report.to_dict())
