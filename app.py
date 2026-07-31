"""
app.py
------
Minimal Streamlit dashboard for the AI-Era Candidate Authenticity & Evaluation
Engine. Zero infra cost: run locally with `streamlit run app.py`, or deploy
for free on Streamlit Community Cloud.

Deliberately thin: all scoring/analysis logic lives in src/pipeline.py and is
shared byte-for-byte with cli.py -- this file only handles presentation.
"""
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from src.pipeline import analyze_candidate
from src.github_client import GitHubRateLimitError

st.set_page_config(page_title="Candidate Authenticity & Depth Engine", page_icon="🔍", layout="wide")

st.title("🔍 AI-Era Candidate Authenticity & Evaluation Engine")
st.caption(
    "Paste a GitHub username or public repo URL. This is a **pre-screen signal**, not a hiring "
    "decision -- always review the evidence, not just the number."
)

with st.sidebar:
    st.header("About")
    st.write(
        "Runs entirely on free-tier APIs (GitHub REST + Groq/Gemini). No data is stored -- "
        "everything happens in-memory for this session only."
    )
    st.markdown("**Scoring model:** rule-based deterministic score, optionally narrated and "
                "lightly adjusted (±2 max) by an LLM. See `JOURNAL.md` for the reasoning.")
    st.markdown("[GitHub REST API docs](https://docs.github.com/en/rest)")

target = st.text_input("GitHub username or repo URL", placeholder="e.g. octocat or https://github.com/octocat/Hello-World")
run = st.button("Analyze", type="primary")

if run and target.strip():
    with st.spinner("Fetching GitHub telemetry and scoring..."):
        try:
            report = analyze_candidate(target.strip())
        except GitHubRateLimitError as e:
            st.error(f"Rate limit error: {e}")
            st.stop()
        except ValueError as e:
            st.error(f"Error: {e}")
            st.stop()

    if report.repos_analyzed == 0:
        st.warning(report.llm_narrative)
        for e in report.errors:
            st.write(f"- {e}")
        st.stop()

    # --- Top-line score ------------------------------------------------------
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Final Depth Score", f"{report.final_score} / 10")
    with col2:
        st.metric("Rule-based Score", f"{report.rule_based_score} / 10",
                   help="Computed purely from structural/velocity metrics, no LLM involved.")
    with col3:
        st.metric("Repos Analyzed", report.repos_analyzed)
        st.caption(f"LLM narrative used: {'✅ yes' if report.llm_used else '⚠️ no (fell back to rule-based only)'}")

    score = report.final_score
    if score >= 7:
        st.success("High confidence in sustained, authentic building depth.")
    elif score >= 4.5:
        st.warning("Mixed signal -- worth a closer look at the flags and per-repo breakdown below.")
    else:
        st.error("Low depth signal -- multiple indicators of shallow or dumped project history.")

    st.subheader("Narrative")
    st.write(report.llm_narrative)

    # --- Red flags -------------------------------------------------------------
    st.subheader(f"🚩 Red Flags ({len(report.aggregate_red_flags)})")
    if report.aggregate_red_flags:
        for f in report.aggregate_red_flags:
            icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(f.severity, "⚪")
            st.markdown(f"{icon} **{f.code}** ({f.severity}) — {f.message}")
    else:
        st.success("No red flags detected across analyzed repositories.")

    # --- Commit velocity chart --------------------------------------------------
    st.subheader("📈 Commit Velocity (all analyzed repos)")
    rows = []
    for ra in report.repo_analyses:
        for c in ra.repo.commits:
            if not c.author_date:
                continue
            try:
                dt = datetime.fromisoformat(c.author_date.replace("Z", "+00:00")).date()
            except ValueError:
                continue
            rows.append({"date": dt, "repo": ra.repo.name})
    if rows:
        df = pd.DataFrame(rows)
        daily = df.groupby(["date", "repo"]).size().reset_index(name="commits")
        pivot = daily.pivot(index="date", columns="repo", values="commits").fillna(0)
        st.bar_chart(pivot)
    else:
        st.info("No commit date data available to chart.")

    # --- Per-repo breakdown ----------------------------------------------------
    st.subheader("📂 Per-Repo Breakdown")
    table_rows = []
    for ra in report.repo_analyses:
        r = ra.repo
        table_rows.append({
            "Repo": r.name,
            "Commits": len(r.commits),
            "PRs": r.pull_request_count,
            "Max Depth": r.max_file_tree_depth,
            "Files": r.file_count,
            "Velocity": ra.velocity_consistency_score,
            "Structure": ra.structural_depth_score,
            "PR Engagement": ra.pr_engagement_score,
            "Msg Quality": ra.message_quality_score,
            "Flags": ", ".join(f.code for f in ra.red_flags) or "—",
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    if report.errors:
        with st.expander("⚠️ Fetch warnings"):
            for e in report.errors:
                st.write(f"- {e}")

    # --- Export ------------------------------------------------------------------
    export_payload = {
        "username": report.username,
        "final_score": report.final_score,
        "rule_based_score": report.rule_based_score,
        "narrative": report.llm_narrative,
        "red_flags": [f.code for f in report.aggregate_red_flags],
        "repos": table_rows,
    }
    st.download_button(
        "⬇️ Download JSON report",
        data=json.dumps(export_payload, indent=2, default=str),
        file_name=f"{report.username}_authenticity_report.json",
        mime="application/json",
    )
elif run:
    st.warning("Please enter a GitHub username or repo URL.")
