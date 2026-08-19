from src.ai_scorer import _validate_result, clamp_final_score


def test_validate_result_clamps_and_normalizes():
    result = _validate_result({
        "narrative": "Evidence is mixed.",
        "suggested_adjustment": 99,
        "adjustment_reason": "Strong structural signal.",
        "positive_evidence": ["A", "B"],
        "limitations": ["C"],
        "verification_questions": ["D"],
    })
    assert result["suggested_adjustment"] == 2
    assert result["narrative"] == "Evidence is mixed."
    assert result["positive_evidence"] == ["A", "B"]


def test_clamp_final_score():
    assert clamp_final_score(9.5, 2) == 10.0
    assert clamp_final_score(1.5, -2) == 1.0
