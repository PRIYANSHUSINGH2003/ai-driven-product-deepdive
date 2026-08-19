"""SEO and brand metadata for CandidateSignal.

Streamlit Community Cloud derives indexing signals from page title and visible
content. These constants keep the product language consistent across the app,
README, deployment metadata, and future static hosting.
"""
from __future__ import annotations

import html
import json
import os

SITE_NAME = "CandidateSignal"
SITE_TITLE = "CandidateSignal | GitHub Engineering Evidence Review & Developer Analysis"
SITE_DESCRIPTION = (
    "CandidateSignal turns public GitHub telemetry into an auditable engineering-pattern review for developers, "
    "technical reviewers, and hiring teams. Inspect activity, repository structure, workflow, maintenance, and confidence without automated verdicts."
)
KEYWORDS = (
    "GitHub engineering review, developer analysis, GitHub repository analysis, engineering evidence, "
    "developer portfolio review, technical review workspace, software engineering assessment"
)
AUTHOR_NAME = "Priyanshu Singh"
AUTHOR_GITHUB = "https://github.com/PRIYANSHUSINGH2003"
AUTHOR_PORTFOLIO = "https://priyanshu-singh-dev.vercel.app/"
AUTHOR_LINKEDIN = "https://www.linkedin.com/in/priyanshu-singh-dev"
PROJECT_GITHUB = "https://github.com/PRIYANSHUSINGH2003/ai-driven-product-deepdive"


def public_app_url() -> str:
    return os.getenv("PUBLIC_APP_URL", "https://candidatesignal.streamlit.app").strip().rstrip("/")


def build_structured_data() -> str:
    """Build lightweight JSON-LD; useful when the host preserves body scripts."""
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": SITE_NAME,
                "alternateName": "CandidateSignal Engineering Evidence Review",
                "url": public_app_url() + "/",
                "description": SITE_DESCRIPTION,
            },
            {
                "@type": "SoftwareApplication",
                "name": SITE_NAME,
                "applicationCategory": "DeveloperApplication",
                "operatingSystem": "Web",
                "description": SITE_DESCRIPTION,
                "url": public_app_url() + "/",
                "author": {
                    "@type": "Person",
                    "name": AUTHOR_NAME,
                    "url": AUTHOR_PORTFOLIO,
                    "sameAs": [AUTHOR_GITHUB, AUTHOR_LINKEDIN],
                },
                "codeRepository": PROJECT_GITHUB,
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def render_discovery_context() -> str:
    """Return visible, search-friendly context without keyword stuffing."""
    return (
        f"<div class='discovery-context'>"
        f"<div class='section-label'>GitHub engineering review</div>"
        f"<p><strong>{html.escape(SITE_NAME)}</strong> helps developers and technical reviewers inspect public GitHub evidence "
        f"such as activity continuity, repository structure, collaboration workflow, communication, maintenance, and project breadth. "
        f"It is designed for evidence-led developer portfolio analysis rather than automated hiring or authorship verdicts.</p>"
        f"</div>"
    )
