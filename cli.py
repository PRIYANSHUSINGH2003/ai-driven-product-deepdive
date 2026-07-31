#!/usr/bin/env python3
"""
cli.py
------
CLI front-end for the AI-Era Candidate Authenticity & Evaluation Engine.

Usage:
    python cli.py octocat
    python cli.py https://github.com/octocat/Hello-World
    python cli.py octocat --export report.json
"""
import argparse
import json
import sys

from src.pipeline import analyze_candidate
from src.github_client import GitHubRateLimitError

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"


def score_color(score: float) -> str:
    if score >= 7:
        return GREEN
    if score >= 4.5:
        return YELLOW
    return RED


def severity_color(sev: str) -> str:
    return {"high": RED, "medium": YELLOW, "low": CYAN}.get(sev, RESET)


def print_report(report):
    print(f"\n{BOLD}=== Candidate Authenticity & Depth Report: {report.username} ==={RESET}")
    print(f"Repos analyzed: {report.repos_analyzed}")

    if report.repos_analyzed == 0:
        print(f"{RED}{report.llm_narrative}{RESET}")
        for e in report.errors:
            print(f"  - {e}")
        return

    c = score_color(report.final_score)
    print(f"\n{BOLD}Final Depth Score:{RESET} {c}{report.final_score} / 10{RESET}  "
          f"(rule-based: {report.rule_based_score}, LLM narrative used: {report.llm_used})")

    print(f"\n{BOLD}Narrative:{RESET}\n{report.llm_narrative}")

    if report.aggregate_red_flags:
        print(f"\n{BOLD}Red Flags ({len(report.aggregate_red_flags)}):{RESET}")
        for f in report.aggregate_red_flags:
            fc = severity_color(f.severity)
            print(f"  {fc}[{f.severity.upper()}]{RESET} {f.code}: {f.message}")
    else:
        print(f"\n{GREEN}No red flags detected.{RESET}")

    print(f"\n{BOLD}Per-repo breakdown:{RESET}")
    for ra in report.repo_analyses:
        r = ra.repo
        print(f"\n  {BOLD}{r.name}{RESET}  ({len(r.commits)} commits, {r.pull_request_count} PRs, "
              f"depth={r.max_file_tree_depth}, files={r.file_count})")
        print(f"    velocity={ra.velocity_consistency_score}  structure={ra.structural_depth_score}  "
              f"pr_engagement={ra.pr_engagement_score}  message_quality={ra.message_quality_score}")
        if r.fetch_error:
            print(f"    {YELLOW}note: {r.fetch_error}{RESET}")

    if report.errors:
        print(f"\n{YELLOW}Warnings during fetch:{RESET}")
        for e in report.errors:
            print(f"  - {e}")


def report_to_dict(report) -> dict:
    return {
        "username": report.username,
        "repos_analyzed": report.repos_analyzed,
        "rule_based_score": report.rule_based_score,
        "final_score": report.final_score,
        "llm_used": report.llm_used,
        "narrative": report.llm_narrative,
        "red_flags": [
            {"code": f.code, "severity": f.severity, "message": f.message, "evidence": f.evidence}
            for f in report.aggregate_red_flags
        ],
        "repos": [
            {
                "name": ra.repo.name,
                "commit_count": len(ra.repo.commits),
                "pull_requests": ra.repo.pull_request_count,
                "max_dir_depth": ra.repo.max_file_tree_depth,
                "file_count": ra.repo.file_count,
                "sub_scores": {
                    "velocity_consistency": ra.velocity_consistency_score,
                    "structural_depth": ra.structural_depth_score,
                    "pr_engagement": ra.pr_engagement_score,
                    "message_quality": ra.message_quality_score,
                },
                "red_flags": [f.code for f in ra.red_flags],
            }
            for ra in report.repo_analyses
        ],
        "errors": report.errors,
    }


def main():
    parser = argparse.ArgumentParser(description="AI-Era Candidate Authenticity & Evaluation Engine (CLI)")
    parser.add_argument("target", help="GitHub username or repo URL, e.g. 'octocat' or "
                                        "'https://github.com/octocat/Hello-World'")
    parser.add_argument("--export", metavar="FILE.json", help="Export the full report as JSON to a file")
    args = parser.parse_args()

    try:
        report = analyze_candidate(args.target)
    except GitHubRateLimitError as e:
        print(f"{RED}Rate limit error:{RESET} {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"{RED}Error:{RESET} {e}", file=sys.stderr)
        sys.exit(1)

    print_report(report)

    if args.export:
        with open(args.export, "w") as f:
            json.dump(report_to_dict(report), f, indent=2)
        print(f"\n{GREEN}Exported full report to {args.export}{RESET}")


if __name__ == "__main__":
    main()
