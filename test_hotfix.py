from src.models import CandidateReport
from src.reporting import report_to_dict

r = CandidateReport(
    username="octo",
    repos_analyzed=0,
    rule_based_score=1.0,
    final_score=1.0,
    llm_narrative="none",
    llm_used=False,
)
p = report_to_dict(r)
assert p["schema_version"] == "2.0"
assert "analysis" in p and "ai" in p and "repositories" in p
assert r.target == ""
assert r.analysis_mode == "profile"
print("hotfix smoke test passed")
