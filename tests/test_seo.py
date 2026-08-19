from src.seo import (
    AUTHOR_GITHUB,
    AUTHOR_LINKEDIN,
    AUTHOR_PORTFOLIO,
    PROJECT_GITHUB,
    SITE_DESCRIPTION,
    SITE_NAME,
    SITE_TITLE,
    build_structured_data,
)


def test_seo_identity_is_consistent():
    assert SITE_NAME == "CandidateSignal"
    assert "GitHub Engineering Evidence Review" in SITE_TITLE
    assert "public GitHub telemetry" in SITE_DESCRIPTION


def test_structured_data_contains_project_and_creator():
    data = build_structured_data()
    assert PROJECT_GITHUB in data
    assert AUTHOR_GITHUB in data
    assert AUTHOR_PORTFOLIO in data
    assert AUTHOR_LINKEDIN in data
