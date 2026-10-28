from src.validation import validate_scorecard

def test_missing_criterion_defaults_to_zero():
    criteria = [{"criterion_id":1,"name":"Tech","weight":1.0,"max_score":5}]
    result, warnings = validate_scorecard({"criteria":[]}, criteria, "Supplier A")
    assert result["criteria"][0]["score"] == 0
    assert warnings

def test_out_of_range_score_is_clamped():
    criteria = [{"criterion_id":1,"name":"Tech","weight":1.0,"max_score":5}]
    result, warnings = validate_scorecard({"criteria":[{"criterion_id":1,"score":9,"justification":"ok","evidence":"p.1"}]}, criteria, "Supplier A")
    assert result["criteria"][0]["score"] == 5
    assert any("clamped" in w for w in warnings)
