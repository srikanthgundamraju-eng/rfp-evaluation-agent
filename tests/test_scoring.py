from src.scoring import calculate_batch_scores

def test_scores_and_rank_are_deterministic():
    criteria=[{"criterion_id":1,"name":"Tech","weight":1.0,"max_score":5}]
    results=[
      {"name":"B","submission_date":"2026-10-20","experience_rating":4,"criteria":[{"criterion_id":1,"score":4,"max_score":5}]},
      {"name":"A","submission_date":"2026-10-19","experience_rating":3,"criteria":[{"criterion_id":1,"score":4,"max_score":5}]},
    ]
    ranked=calculate_batch_scores(results,criteria)
    assert ranked[0]["name"]=="A"
    assert ranked[0]["absolute_score"]==0.8
    assert ranked[0]["ppi"]==100


from src.scoring import calculate_batch_scores


def test_peer_benchmark_and_ppi():
    criteria = [
        {
            "criterion_id": 1,
            "name": "Technical",
            "weight": 1.0,
            "max_score": 5
        }
    ]

    results = [
        {
            "name": "Supplier A",
            "submission_date": "2026-10-20",
            "experience_rating": 3,
            "criteria": [
                {"criterion_id": 1, "score": 5, "max_score": 5}
            ]
        },
        {
            "name": "Supplier B",
            "submission_date": "2026-10-21",
            "experience_rating": 4,
            "criteria": [
                {"criterion_id": 1, "score": 3, "max_score": 5}
            ]
        }
    ]

    ranked = calculate_batch_scores(results, criteria)

    supplier_a = next(r for r in ranked if r["name"] == "Supplier A")
    supplier_b = next(r for r in ranked if r["name"] == "Supplier B")

    assert supplier_a["absolute_score"] == 1.0
    assert supplier_b["absolute_score"] == 0.6

    assert supplier_a["criteria"][0]["benchmark_score"] == 5
    assert supplier_b["criteria"][0]["benchmark_score"] == 5

    assert supplier_a["criteria"][0]["gap"] == 0
    assert supplier_b["criteria"][0]["gap"] == -2

    assert supplier_a["ppi"] == 100
    assert supplier_b["ppi"] == 60


def test_tie_break_uses_earlier_submission_date():
    criteria = [
        {
            "criterion_id": 1,
            "name": "Technical",
            "weight": 1.0,
            "max_score": 5
        }
    ]

    results = [
        {
            "name": "Supplier B",
            "submission_date": "2026-10-22",
            "experience_rating": 5,
            "criteria": [
                {"criterion_id": 1, "score": 4, "max_score": 5}
            ]
        },
        {
            "name": "Supplier A",
            "submission_date": "2026-10-20",
            "experience_rating": 3,
            "criteria": [
                {"criterion_id": 1, "score": 4, "max_score": 5}
            ]
        }
    ]

    ranked = calculate_batch_scores(results, criteria)

    assert ranked[0]["name"] == "Supplier A"
    assert ranked[0]["final_rank"] == 1
    assert ranked[1]["final_rank"] == 2


def test_zero_benchmark_does_not_crash():
    criteria = [
        {
            "criterion_id": 1,
            "name": "Technical",
            "weight": 1.0,
            "max_score": 5
        }
    ]

    results = [
        {
            "name": "Supplier A",
            "submission_date": "2026-10-20",
            "experience_rating": 3,
            "criteria": [
                {"criterion_id": 1, "score": 0, "max_score": 5}
            ]
        },
        {
            "name": "Supplier B",
            "submission_date": "2026-10-21",
            "experience_rating": 4,
            "criteria": [
                {"criterion_id": 1, "score": 0, "max_score": 5}
            ]
        }
    ]

    ranked = calculate_batch_scores(results, criteria)

    assert len(ranked) == 2
    assert all(r["criteria"][0]["benchmark_score"] == 0 for r in ranked)
    assert all(r["absolute_score"] == 0 for r in ranked)
    assert all(r["ppi"] == 100 for r in ranked)
