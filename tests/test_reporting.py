from src.models import CandidateReport
from src.reporting import report_to_dict

def test_report_schema_is_versioned():
    report=CandidateReport(username="octo",repos_analyzed=0,rule_based_score=1.0,final_score=1.0,llm_narrative="none",llm_used=False)
    payload=report_to_dict(report)
    assert payload["schema_version"]=="2.0"
    assert "analysis" in payload and "ai" in payload and "repositories" in payload
