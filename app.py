"""CandidateSignal — responsive engineering evidence review workspace."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
import streamlit as st

from src.github_client import GitHubClientError, GitHubRateLimitError, get_rate_limit_status
from src.pipeline import analyze_candidate

st.set_page_config(
    page_title="CandidateSignal · Engineering Evidence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Design system
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      :root {
        --cs-border: rgba(148,163,184,.20);
        --cs-border-strong: rgba(148,163,184,.30);
        --cs-muted: rgba(148,163,184,.92);
        --cs-soft: rgba(148,163,184,.07);
        --cs-brand: #7c83ff;
        --cs-brand-soft: rgba(124,131,255,.12);
        --cs-green: #35c98f;
        --cs-green-soft: rgba(53,201,143,.10);
        --cs-amber: #f3b760;
        --cs-amber-soft: rgba(243,183,96,.10);
        --cs-red: #f07171;
        --cs-red-soft: rgba(240,113,113,.10);
      }

      .stApp { background: radial-gradient(circle at 18% -10%, rgba(124,131,255,.09), transparent 32%), radial-gradient(circle at 90% 0%, rgba(53,201,143,.05), transparent 28%); }
      .block-container { max-width: 1460px; padding-top: 1.15rem; padding-bottom: 4rem; }
      [data-testid="stSidebar"] { border-right: 1px solid var(--cs-border); }
      [data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

      .brandbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-top: 1.9rem; margin-bottom:1.1rem; }
      .brandmark { display:flex; align-items:center; gap:.72rem; }
      .logo {
        width:2.55rem; height:2.55rem; border-radius:13px; display:grid; place-items:center;
        font-weight:900; font-size:1.15rem; color:white; background:linear-gradient(135deg,#7c83ff,#5e6bff);
        box-shadow:0 10px 28px rgba(92,102,255,.24);
      }
      .brandname { font-size:1.05rem; font-weight:850; letter-spacing:-.02em; }
      .brandtag { color:var(--cs-muted); font-size:.76rem; margin-top:.08rem; }
      .top-badge { border:1px solid var(--cs-border); background:rgba(255,255,255,.02); border-radius:999px; padding:.38rem .65rem; font-size:.73rem; color:var(--cs-muted); }

      .hero { padding:1.35rem 1.45rem; border:1px solid var(--cs-border); border-radius:22px; background:linear-gradient(135deg, rgba(124,131,255,.11), rgba(255,255,255,.025) 46%, rgba(53,201,143,.06)); margin-bottom:1rem; }
      .eyebrow { text-transform:uppercase; letter-spacing:.13em; font-size:.67rem; font-weight:850; color:var(--cs-muted); margin-bottom:.42rem; }
      .hero h1 { margin:0 0 .3rem 0; font-size:clamp(2rem,3vw,3rem); letter-spacing:-.055em; line-height:1.02; }
      .hero p { margin:0; max-width:980px; color:var(--cs-muted); line-height:1.65; font-size:.95rem; }
      .hero-meta { display:flex; flex-wrap:wrap; gap:.48rem; margin-top:.95rem; }
      .hero-pill { border:1px solid var(--cs-border); background:rgba(0,0,0,.08); border-radius:999px; padding:.38rem .63rem; font-size:.72rem; color:var(--cs-muted); }

      .section-label { font-size:.72rem; text-transform:uppercase; letter-spacing:.12em; font-weight:850; color:var(--cs-muted); margin:.15rem 0 .5rem; }
      .surface { border:1px solid var(--cs-border); border-radius:18px; background:rgba(255,255,255,.018); padding:1rem 1.05rem; height:100%; }
      .surface-compact { border:1px solid var(--cs-border); border-radius:15px; background:rgba(255,255,255,.015); padding:.75rem .8rem; height:100%; }
      .surface-title { font-weight:820; font-size:.96rem; letter-spacing:-.015em; }
      .surface-subtitle { color:var(--cs-muted); font-size:.76rem; line-height:1.45; margin-top:.16rem; }

      .metric-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.7rem; margin:.75rem 0 1rem; }
      .metric-card { border:1px solid var(--cs-border); border-radius:16px; padding:.82rem .9rem; background:rgba(255,255,255,.018); min-height:92px; }
      .metric-label { color:var(--cs-muted); text-transform:uppercase; letter-spacing:.08em; font-size:.62rem; font-weight:850; }
      .metric-value { font-size:1.52rem; font-weight:850; letter-spacing:-.045em; line-height:1.05; margin-top:.24rem; }
      .metric-note { color:var(--cs-muted); font-size:.69rem; margin-top:.25rem; }

      .score-card { border:1px solid var(--cs-border-strong); border-radius:20px; padding:1.12rem; background:linear-gradient(145deg, rgba(124,131,255,.13), rgba(255,255,255,.018) 58%); }
      .score-caption { color:var(--cs-muted); text-transform:uppercase; letter-spacing:.09em; font-size:.66rem; font-weight:850; }
      .score-number { font-size:3.25rem; line-height:.96; font-weight:900; letter-spacing:-.06em; margin:.22rem 0 .35rem; }
      .score-note { color:var(--cs-muted); font-size:.77rem; line-height:1.45; }
      .score-row { display:flex; align-items:center; gap:.65rem; margin-top:.72rem; }
      .score-track { flex:1; height:7px; background:rgba(148,163,184,.12); border-radius:999px; overflow:hidden; }
      .score-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#6e77ff,#8e95ff); }

      .status-chip { display:inline-flex; align-items:center; gap:.42rem; padding:.31rem .58rem; border:1px solid var(--cs-border); border-radius:999px; font-size:.69rem; font-weight:780; color:var(--cs-muted); }
      .dot { width:7px; height:7px; border-radius:50%; background:var(--cs-green); box-shadow:0 0 0 3px rgba(53,201,143,.10); }
      .dot.warn { background:var(--cs-amber); box-shadow:0 0 0 3px rgba(243,183,96,.10); }
      .dot.bad { background:var(--cs-red); box-shadow:0 0 0 3px rgba(240,113,113,.10); }

      .evidence-item { border:1px solid var(--cs-border); border-radius:13px; padding:.72rem .82rem; background:rgba(255,255,255,.012); margin-bottom:.5rem; }
      .evidence-item:last-child { margin-bottom:0; }
      .evidence-item strong { font-size:.8rem; }
      .evidence-item div { color:var(--cs-muted); font-size:.75rem; line-height:1.45; margin-top:.17rem; }

      .warning-box, .good-box, .neutral-box { border:1px solid var(--cs-border); border-radius:15px; padding:.8rem .9rem; }
      .warning-box { background:var(--cs-amber-soft); border-color:rgba(243,183,96,.24); }
      .good-box { background:var(--cs-green-soft); border-color:rgba(53,201,143,.24); }
      .neutral-box { background:rgba(124,131,255,.06); border-color:rgba(124,131,255,.20); }
      .box-title { font-weight:820; font-size:.79rem; }
      .box-copy { color:var(--cs-muted); font-size:.74rem; line-height:1.5; margin-top:.18rem; }

      .repo-card { border:1px solid var(--cs-border); border-radius:16px; padding:.9rem; background:rgba(255,255,255,.012); margin-bottom:.55rem; }
      .repo-name { font-weight:820; font-size:.87rem; }
      .repo-meta { color:var(--cs-muted); font-size:.71rem; margin-top:.22rem; }
      .repo-score { font-size:1.2rem; font-weight:850; letter-spacing:-.04em; }
      .dimension { display:flex; justify-content:space-between; gap:.5rem; font-size:.7rem; color:var(--cs-muted); margin-top:.3rem; }
      .dimension b { color:inherit; }

      .footer-note { color:var(--cs-muted); font-size:.7rem; line-height:1.55; padding-top:.65rem; }

      @media (max-width: 1100px) {
        .metric-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
      }
      @media (max-width: 780px) {
        .block-container { padding-left:.72rem; padding-right:.72rem; }
        .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .hero { padding:1rem; border-radius:18px; }
        .hero h1 { font-size:2rem; }
        .brandbar { align-items:flex-start; }
        .top-badge { display:none; }
        .repo-card { padding:.78rem; }
      }
      @media (max-width: 480px) {
        .metric-grid { grid-template-columns:1fr 1fr; gap:.55rem; }
        .metric-card { min-height:82px; padding:.68rem; }
        .metric-value { font-size:1.22rem; }
        .score-number { font-size:2.55rem; }
      }

      /* Streamlit controls: quieter, denser, more product-like. */
      .stButton > button { border-radius:11px; min-height:2.5rem; font-weight:800; }
      .stTextInput > div > div, .stSelectbox > div > div, .stTextArea > div > div { border-radius:11px; }
      .stSlider [data-baseweb="slider"] { padding-left:.15rem; padding-right:.15rem; }
      [data-testid="stMetric"] { background:transparent; }
      [data-testid="stExpander"] { border:1px solid var(--cs-border); border-radius:14px; overflow:hidden; }
      [data-testid="stTabs"] button { font-weight:780; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _fmt_reset(epoch: int) -> str:
    if not epoch:
        return "unknown"
    dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return dt.astimezone().strftime("%d %b %Y, %I:%M %p")


@st.cache_data(ttl=15, show_spinner=False)
def _rate_status():
    return get_rate_limit_status()


def _rate_budget(status) -> tuple[int, int, int]:
    repo_budget_core = max((status.core.remaining - 1) // 4, 0)
    repo_budget_search = max(status.search.remaining, 0)
    return repo_budget_core, repo_budget_core, repo_budget_search


def _score_color(score: float) -> str:
    if score >= 7.5:
        return "#35c98f"
    if score >= 5.5:
        return "#f3b760"
    return "#f07171"


def _quality_label(value: float) -> str:
    if value >= 0.85:
        return "Strong"
    if value >= 0.65:
        return "Partial"
    return "Limited"


def _review_readiness(report) -> tuple[str, str]:
    if report.repos_analyzed == 0:
        return "Not ready", "No repository telemetry is available for review."
    if report.confidence < 55:
        return "Needs verification", "Use the report to identify questions, not conclusions."
    if report.data_quality < 0.75 or report.confidence < 75:
        return "Review with caution", "Evidence is usable, but some important telemetry is incomplete."
    return "Ready for review", "Coverage is sufficient for a structured human evidence review."


def _run_id() -> str:
    return st.session_state.get("run_id", "")


def _set_run(report):
    st.session_state["last_report"] = report
    st.session_state["run_id"] = f"CS-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:6].upper()}"
    st.session_state["review_checks"] = {
        "reviewed_limitations": False,
        "inspected_repositories": False,
        "selected_verification_questions": False,
    }


def _repo_activity_frame(report):
    rows = []
    for analysis in report.repo_analyses:
        for commit in analysis.repo.commits:
            if not commit.author_date:
                continue
            try:
                date = datetime.fromisoformat(commit.author_date.replace("Z", "+00:00")).date()
            except ValueError:
                continue
            rows.append({"date": date, "repository": analysis.repo.name})
    if not rows:
        return None
    return pd.DataFrame(rows).groupby(["date", "repository"]).size().reset_index(name="commits")


def _render_repo_card(ra):
    repo = ra.repo
    cols = st.columns([4.1, 1.0, 1.0])
    with cols[0]:
        st.markdown(f"<div class='repo-name'>{repo.full_name}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='repo-meta'>{repo.language or 'Unknown language'} · {len(repo.commits)} commits sampled · {repo.size_kb:,} KB · {repo.stargazers_count:,} stars</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown("<div class='metric-label'>Evidence</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='repo-score'>{ra.weighted_score:.1f}</div>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown("<div class='metric-label'>Quality</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='repo-score'>{ra.data_quality:.0%}</div>", unsafe_allow_html=True)

    dims = [
        ("Activity", ra.activity_continuity_score),
        ("Structure", ra.structural_depth_score),
        ("Workflow", ra.workflow_score),
        ("Communication", ra.communication_score),
        ("Maintenance", ra.maintenance_score),
        ("Breadth", ra.breadth_score),
    ]
    dcols = st.columns(3)
    for idx, (label, value) in enumerate(dims):
        with dcols[idx % 3]:
            st.markdown(
                f"<div class='dimension'><span>{label}</span><b>{value:.1f}</b></div>",
                unsafe_allow_html=True,
            )
            st.progress(min(max(value / 10, 0), 1), text=None)

    if ra.red_flags:
        labels = ", ".join(flag.code.replace("_", " ").title() for flag in ra.red_flags[:3])
        st.caption(f"Observations: {labels}")
    elif ra.evidence_notes:
        st.caption(ra.evidence_notes[0])

    if repo.html_url:
        st.link_button("Open repository ↗", repo.html_url)


# -----------------------------------------------------------------------------
# Header / sidebar
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="brandbar">
      <div class="brandmark">
        <div class="logo">◈</div>
        <div><div class="brandname">CandidateSignal</div><div class="brandtag">Engineering evidence review workspace</div></div>
      </div>
      <div class="top-badge">Audit-first · Human review · No verdicts</div>
    </div>
    <div class="hero">
      <div class="eyebrow">Public GitHub telemetry → auditable evidence</div>
      <h1>Review engineering patterns without pretending they are verdicts.</h1>
      <p>CandidateSignal turns repository telemetry into a structured review workspace. Deterministic rules own the score; AI only summarizes evidence and suggests neutral verification questions.</p>
      <div class="hero-meta">
        <span class="hero-pill">6 evidence families</span><span class="hero-pill">Privacy-minimized AI payload</span><span class="hero-pill">Rate-limit aware</span><span class="hero-pill">Exportable audit trail</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Analyze")
    target = st.text_input(
        "GitHub target",
        placeholder="username · owner/repo · URL",
        help="Analyze a profile or one public repository.",
    )
    max_repos = st.slider("Profile repositories", 1, 20, 8, 1)
    max_commits = st.slider("Commits per repository", 10, 100, 100, 10)
    include_forks = st.checkbox(
        "Include forks",
        value=False,
        help="Forks may contain inherited work and are excluded by default.",
    )
    run = st.button("Run evidence review", type="primary", use_container_width=True)

    st.divider()
    st.markdown("### API budget")
    try:
        rate = _rate_status()
        budget, _, search_budget = _rate_budget(rate)
        auth_label = "Authenticated" if rate.authenticated else "Unauthenticated"
        dot_class = "" if rate.authenticated else "warn"
        st.markdown(f"<span class='status-chip'><span class='dot {dot_class}'></span>{auth_label}</span>", unsafe_allow_html=True)
        st.metric("Core", f"{rate.core.remaining:,}", help=f"Reset: {_fmt_reset(rate.core.reset_epoch)}")
        st.metric("Search", f"{rate.search.remaining:,}", help=f"Reset: {_fmt_reset(rate.search.reset_epoch)}")
        if not rate.authenticated:
            st.caption("A read-only GITHUB_TOKEN gives you a more reliable API budget.")
        if target and "/" not in target and budget < max_repos:
            st.warning(f"This budget safely supports ~{budget} profile repos. The run will cap at that level.")
        if search_budget == 0:
            st.caption("Search quota is exhausted; PR telemetry may be unknown while core repository data remains available.")
    except GitHubClientError as exc:
        rate = None
        st.markdown(f"<div class='warning-box'><div class='box-title'>Budget status unavailable</div><div class='box-copy'>{exc}</div></div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("### Evidence model")
    st.markdown(
        "<div class='surface-compact'><div class='surface-title'>Six observable families</div><div class='surface-subtitle'>Activity · Structure · Workflow · Communication · Maintenance · Breadth</div></div>",
        unsafe_allow_html=True,
    )
    st.caption("Unknown telemetry reduces confidence instead of becoming negative evidence.")

# -----------------------------------------------------------------------------
# Run logic
# -----------------------------------------------------------------------------
if run and not target.strip():
    st.warning("Enter a GitHub username, owner/repo, or public repository URL.")
    st.stop()

report = st.session_state.get("last_report")
run_error = None
if run:
    selected_repos = max_repos
    if "/" not in target and rate is not None:
        safe_profile_cap = max(_rate_budget(rate)[0], 0)
        selected_repos = min(max_repos, safe_profile_cap)
        if selected_repos == 0:
            st.error("The available GitHub core budget is too low for a new profile analysis.")
            st.info(f"Core budget resets at {_fmt_reset(rate.core.reset_epoch)}. Add a read-only GITHUB_TOKEN or analyze a repository when the budget is available.")
            st.stop()
    with st.spinner("Collecting telemetry and assembling the evidence profile…"):
        try:
            fresh_report = analyze_candidate(target.strip(), max_repos=selected_repos, max_commits=max_commits, include_forks=include_forks)
            _set_run(fresh_report)
            report = fresh_report
        except GitHubRateLimitError as exc:
            run_error = str(exc)
            if report is not None:
                st.warning("GitHub telemetry is rate-limited. Your last successful report is preserved below and marked as cached.")
            else:
                st.error("GitHub telemetry is temporarily unavailable because the API budget is exhausted.")
        except (GitHubClientError, ValueError) as exc:
            run_error = str(exc)
            if report is not None:
                st.warning("The new run failed; the last successful report is preserved below.")
            else:
                st.error(str(exc))

if report is None:
    st.markdown("### A calmer workflow for technical review")
    a, b, c = st.columns(3)
    with a:
        st.markdown("<div class='surface'><div class='surface-title'>01 · Triage</div><div class='surface-subtitle'>Start with evidence score, confidence, sample coverage, and API health.</div></div>", unsafe_allow_html=True)
    with b:
        st.markdown("<div class='surface'><div class='surface-title'>02 · Investigate</div><div class='surface-subtitle'>Inspect repository-level signals, observations, unknowns, and timeline patterns.</div></div>", unsafe_allow_html=True)
    with c:
        st.markdown("<div class='surface'><div class='surface-title'>03 · Verify</div><div class='surface-subtitle'>Turn observations into neutral work-sample or interview questions.</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='neutral-box' style='margin-top:1rem'><div class='box-title'>Safety boundary</div><div class='box-copy'>GitHub telemetry does not prove authorship, skill, intent, misconduct, or AI use. CandidateSignal is a structured evidence aid for human review.</div></div>", unsafe_allow_html=True)
    st.stop()

# -----------------------------------------------------------------------------
# Report context / resilience state
# -----------------------------------------------------------------------------
ready_label, ready_copy = _review_readiness(report)
if run_error:
    st.markdown(
        f"<div class='warning-box'><div class='box-title'>Freshness notice</div><div class='box-copy'>The latest refresh did not complete: {run_error}. The workspace is showing the last successful report, not inventing a new score.</div></div>",
        unsafe_allow_html=True,
    )

st.markdown(
    f"<div class='section-label'>Review { _run_id() or 'current report' }</div>",
    unsafe_allow_html=True,
)

# Score + readiness row
score_col, brief_col, ready_col = st.columns([1.0, 1.55, 1.0])
with score_col:
    color = _score_color(report.final_score)
    pct = min(max(report.final_score / 10, 0), 1) * 100
    st.markdown(
        f"""<div class='score-card'>
        <div class='score-caption'>Evidence strength</div>
        <div class='score-number' style='color:{color}'>{report.final_score:.2f}<span style='font-size:1rem;color:var(--cs-muted);font-weight:700'> / 10</span></div>
        <div class='score-note'>Not a probability of candidate quality.</div>
        <div class='score-row'><div class='score-track'><div class='score-fill' style='width:{pct:.1f}%'></div></div><span style='font-size:.7rem;color:var(--cs-muted)'>{report.confidence:.0f}% conf.</span></div>
        </div>""",
        unsafe_allow_html=True,
    )
with brief_col:
    st.markdown("<div class='surface'><div class='surface-title'>Reviewer brief</div>", unsafe_allow_html=True)
    st.write(report.llm_narrative or "Deterministic evidence only for this run.")
    narrator = report.llm_provider if report.llm_used else "deterministic-only"
    st.caption(f"Narrator: {narrator} · AI adjustment: {report.llm_adjustment:+d} · Generated: {report.generated_at[:19].replace('T', ' ')} UTC")
    st.markdown("</div>", unsafe_allow_html=True)
with ready_col:
    cls = "" if ready_label == "Ready for review" else "warn"
    st.markdown(
        f"<div class='surface'><span class='status-chip'><span class='dot {cls}'></span>{ready_label}</span><div class='surface-title' style='margin-top:.8rem'>Review posture</div><div class='surface-subtitle'>{ready_copy}</div></div>",
        unsafe_allow_html=True,
    )

# Compact KPI grid
quality_label = _quality_label(report.data_quality)
metrics = [
    ("Deterministic", f"{report.rule_based_score:.2f}", "Rule-based source of truth"),
    ("Confidence", f"{report.confidence:.0f}%", "Coverage + sample size"),
    ("Repositories", str(report.repos_analyzed), "Analyzed this run"),
    ("Data quality", f"{report.data_quality:.0%}", quality_label),
    ("AI adjustment", f"{report.llm_adjustment:+d}", "Bounded to ±2"),
]
metric_html = ["<div class='metric-grid'>"]
for label, value, note in metrics:
    metric_html.append(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>")
metric_html.append("</div>")
st.markdown("".join(metric_html), unsafe_allow_html=True)

# Quality strip
if report.confidence < 60 or report.data_quality < .7:
    st.markdown("<div class='warning-box'><div class='box-title'>Evidence coverage is limited</div><div class='box-copy'>Read the limitations and repository notes before using the report. Missing GitHub fields are neutralized rather than converted into negative evidence.</div></div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='good-box'><div class='box-title'>Evidence coverage is usable</div><div class='box-copy'>Confidence reflects telemetry coverage and sample size. It does not claim correctness or candidate quality.</div></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Workspace tabs
# -----------------------------------------------------------------------------
overview, repos_tab, review_tab, methodology, export_tab = st.tabs(["Overview", "Repositories", "Review desk", "Methodology", "Export"])

with overview:
    left, right = st.columns([1.35, 1.0])
    with left:
        st.markdown("<div class='section-label'>Signal summary</div>", unsafe_allow_html=True)
        if report.positive_evidence:
            for item in report.positive_evidence:
                st.markdown(f"<div class='evidence-item'><strong>Positive evidence</strong><div>{item}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='neutral-box'><div class='box-title'>No AI-positive summary</div><div class='box-copy'>The deterministic report remains usable without a narrative provider.</div></div>", unsafe_allow_html=True)

        st.markdown("<div class='section-label' style='margin-top:1rem'>Observations to investigate</div>", unsafe_allow_html=True)
        if not report.aggregate_red_flags:
            st.markdown("<div class='good-box'><div class='box-title'>No configured observations</div><div class='box-copy'>The current rules did not trigger a configured observation. This is not proof of absence of issues.</div></div>", unsafe_allow_html=True)
        else:
            order = {"high": 0, "medium": 1, "low": 2}
            for flag in sorted(report.aggregate_red_flags, key=lambda x: order.get(x.severity, 3)):
                icon = {"high": "●", "medium": "●", "low": "●"}.get(flag.severity, "•")
                with st.expander(f"{icon} {flag.code.replace('_', ' ').title()} · {flag.severity}"):
                    st.write(flag.message)
                    st.json(flag.evidence)

    with right:
        st.markdown("<div class='section-label'>Verify next</div>", unsafe_allow_html=True)
        if report.verification_questions:
            for idx, question in enumerate(report.verification_questions, start=1):
                st.markdown(f"<div class='evidence-item'><strong>{idx:02d}</strong><div>{question}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='neutral-box'><div class='box-title'>No generated questions</div><div class='box-copy'>Use repository observations as prompts for a work sample.</div></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-label' style='margin-top:1rem'>Activity trajectory</div>", unsafe_allow_html=True)
    frame = _repo_activity_frame(report)
    if frame is not None:
        pivot = frame.pivot(index="date", columns="repository", values="commits").fillna(0)
        st.line_chart(pivot, use_container_width=True, height=300)
    else:
        st.info("No valid commit dates were available for charting.")

    st.markdown("<div class='section-label' style='margin-top:1rem'>Current limitations</div>", unsafe_allow_html=True)
    for item in report.limitations[:6]:
        st.markdown(f"<div class='evidence-item'><strong>Limitation</strong><div>{item}</div></div>", unsafe_allow_html=True)

with repos_tab:
    st.markdown("<div class='surface-subtitle'>Repository-level evidence lets a reviewer understand where the profile score is coming from instead of relying on one aggregate number.</div>", unsafe_allow_html=True)
    if report.repo_analyses:
        rows = []
        for ra in report.repo_analyses:
            repo = ra.repo
            rows.append({
                "Repository": repo.full_name,
                "Evidence": round(ra.weighted_score, 2),
                "Activity": round(ra.activity_continuity_score, 1),
                "Structure": round(ra.structural_depth_score, 1),
                "Workflow": round(ra.workflow_score, 1),
                "Maintenance": round(ra.maintenance_score, 1),
                "Quality": f"{ra.data_quality:.0%}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("<div class='section-label' style='margin-top:1rem'>Repository detail</div>", unsafe_allow_html=True)
        for ra in report.repo_analyses:
            with st.container(border=True):
                _render_repo_card(ra)
    else:
        st.info("No repository evidence is available for this report.")

with review_tab:
    st.markdown("<div class='section-label'>Reviewer checklist</div>", unsafe_allow_html=True)
    checks = st.session_state.setdefault(
        "review_checks",
        {"reviewed_limitations": False, "inspected_repositories": False, "selected_verification_questions": False},
    )
    checks["reviewed_limitations"] = st.checkbox("I reviewed current limitations and data-quality warnings.", value=checks["reviewed_limitations"], key="reviewed_limitations")
    checks["inspected_repositories"] = st.checkbox("I inspected repository-level evidence rather than using only the aggregate score.", value=checks["inspected_repositories"], key="inspected_repositories")
    checks["selected_verification_questions"] = st.checkbox("I selected neutral questions or a work sample for human verification.", value=checks["selected_verification_questions"], key="selected_verification_questions")

    completed = sum(checks.values())
    st.progress(completed / 3, text=f"Review hygiene {completed}/3 completed")

    st.markdown("<div class='section-label' style='margin-top:1rem'>Reviewer notes</div>", unsafe_allow_html=True)
    notes = st.text_area(
        "Private session notes",
        key="review_notes",
        height=160,
        placeholder="Record what you want to verify, what is still unclear, or which repositories deserve a deeper work sample.",
        label_visibility="collapsed",
    )
    st.caption("Notes remain in this browser session until refreshed; they are included only when you explicitly download the audit JSON.")

    st.markdown("<div class='section-label' style='margin-top:1rem'>Recommended verification prompts</div>", unsafe_allow_html=True)
    for q in report.verification_questions:
        st.markdown(f"<div class='evidence-item'><strong>Ask / test</strong><div>{q}</div></div>", unsafe_allow_html=True)

with methodology:
    st.markdown("<div class='section-label'>How to interpret CandidateSignal</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='surface'><div class='surface-title'>Evidence, inference, unknown</div><div class='surface-subtitle'>Observable telemetry contributes to deterministic dimensions. Incomplete telemetry stays unknown. AI can summarize the evidence but cannot become the source of truth.</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("### Six evidence families")
    family_table = pd.DataFrame({
        "Family": ["Activity continuity", "Repository structure", "Collaboration workflow", "Commit-message quality", "Maintenance", "Breadth"],
        "Purpose": [
            "Looks at continuity and concentration of observable activity.",
            "Uses repository structure/tree signals when available.",
            "Considers PRs/contributors without penalizing legitimate solo workflows.",
            "Uses message-level aggregates, never raw messages in the AI payload.",
            "Considers recent push state and repository lifecycle signals.",
            "Looks at project footprint and diversity of observable repositories.",
        ],
    })
    st.dataframe(family_table, use_container_width=True, hide_index=True)
    st.markdown("### Safety boundary")
    st.markdown("<div class='warning-box'><div class='box-title'>Human review required</div><div class='box-copy'>This tool does not establish authorship, technical skill, intent, misconduct, or AI usage. Its purpose is to make public telemetry easier to inspect and discuss.</div></div>", unsafe_allow_html=True)

with export_tab:
    export_report = report.to_dict()
    export_report["review_context"] = {
        "run_id": _run_id(),
        "review_checklist": st.session_state.get("review_checks", {}),
        "reviewer_notes": st.session_state.get("review_notes", ""),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    payload = json.dumps(export_report, indent=2, default=str)
    st.markdown("<div class='surface'><div class='surface-title'>Audit package</div><div class='surface-subtitle'>Includes deterministic scoring, repository telemetry, limitations, provider status, sampling controls, and your optional review notes.</div></div>", unsafe_allow_html=True)
    st.download_button(
        "Download audit JSON",
        data=payload,
        file_name=f"candidatesignal-{report.username}-{_run_id() or 'report'}.json",
        mime="application/json",
        use_container_width=True,
    )
    st.caption("No data is persisted by this workspace by default. The export is created only when you request it.")

st.markdown("<div class='footer-note'>CandidateSignal is an evidence-review aid. Treat every score as an input to human investigation, not as a hiring verdict.</div>", unsafe_allow_html=True)
