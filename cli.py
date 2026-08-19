#!/usr/bin/env python3
"""Automation-friendly CandidateSignal CLI."""
from __future__ import annotations

import argparse
import json
import sys

from src.github_client import GitHubRateLimitError
from src.pipeline import analyze_candidate


def main() -> int:
    parser = argparse.ArgumentParser(description="Explainable GitHub engineering-evidence analysis")
    parser.add_argument("target", help="GitHub username, owner/repo, or public repo URL")
    parser.add_argument("--export", metavar="REPORT.json", help="Write the full audit report to JSON")
    args = parser.parse_args()

    try:
        report = analyze_candidate(args.target)
    except GitHubRateLimitError as exc:
        print(f"Rate limit error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 1

    print(f"\nCandidateSignal: {report.username}")
    print(f"Evidence score: {report.final_score:.2f}/10 | deterministic: {report.rule_based_score:.2f}/10 | confidence: {report.confidence:.0f}%")
    print(f"Mode: {report.analysis_mode} | repositories: {report.repos_analyzed} | AI: {report.llm_provider if report.llm_used else 'off'}")
    print(f"\nAI evidence brief:\n{report.llm_narrative}")

    if report.aggregate_red_flags:
        print(f"\nObservations ({len(report.aggregate_red_flags)}):")
        for flag in report.aggregate_red_flags:
            print(f"  [{flag.severity.upper()}] {flag.code}: {flag.message}")
    else:
        print("\nNo configured observations detected.")

    if report.verification_questions:
        print("\nVerification questions:")
        for question in report.verification_questions:
            print(f"  - {question}")

    if report.errors:
        print("\nDiagnostics:")
        for error in report.errors:
            print(f"  - {error}")

    if args.export:
        with open(args.export, "w", encoding="utf-8") as handle:
            json.dump(report.to_dict(), handle, indent=2, default=str)
        print(f"\nExported {args.export}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
