from fastapi.testclient import TestClient

from api import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_request_accepts_analysis_controls():
    from api import AnalyzeRequest
    req = AnalyzeRequest(target="octocat", max_repos=3, max_commits=40, include_forks=True)
    assert req.max_repos == 3
    assert req.max_commits == 40
    assert req.include_forks is True
