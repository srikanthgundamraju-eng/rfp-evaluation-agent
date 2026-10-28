
import json

from database import db


def sample_result(name="Supplier A"):
    return {
        "name": name,
        "submission_date": "2026-10-28",
        "experience_rating": 3.0,
        "absolute_score": 0.70,
        "ppi": 95.0,
        "final_rank": 1,
        "criteria": [],
        "risks": [],
        "overall_summary": "Test supplier result",
    }


def setup_temp_database(monkeypatch, tmp_path):
    # Redirect all database operations to a temporary test database.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_rfp.db")
    db.init_db()


def test_partial_success_status_and_results_are_saved(
    monkeypatch, tmp_path
):
    setup_temp_database(monkeypatch, tmp_path)

    run_id = db.create_run()
    result = sample_result()

    db.save_supplier_result(run_id, result)
    warnings = ["Supplier B: evaluation failed: unreadable PDF"]
    db.complete_run(run_id, "completed_with_warnings", warnings)

    runs = db.list_runs()
    saved_run = next(
        run for run in runs if run["rfp_run_id"] == run_id
    )
    saved_results = db.get_run_results(run_id)

    assert saved_run["status"] == "completed_with_warnings"
    assert json.loads(saved_run["warnings_json"]) == warnings
    assert len(saved_results) == 1
    assert saved_results[0]["name"] == "Supplier A"
    assert saved_results[0]["final_rank"] == 1


def test_failed_run_records_warnings_without_results(
    monkeypatch, tmp_path
):
    setup_temp_database(monkeypatch, tmp_path)

    run_id = db.create_run()
    warnings = [
        "Supplier A: evaluation failed: unreadable PDF",
        "Supplier B: evaluation failed: API error",
    ]

    db.complete_run(run_id, "failed", warnings)

    runs = db.list_runs()
    saved_run = next(
        run for run in runs if run["rfp_run_id"] == run_id
    )

    assert saved_run["status"] == "failed"
    assert json.loads(saved_run["warnings_json"]) == warnings
    assert db.get_run_results(run_id) == []


def test_successful_run_saves_all_results(
    monkeypatch, tmp_path
):
    setup_temp_database(monkeypatch, tmp_path)

    run_id = db.create_run()
    first = sample_result("Supplier A")
    second = sample_result("Supplier B")
    second["final_rank"] = 2

    db.save_supplier_result(run_id, first)
    db.save_supplier_result(run_id, second)
    db.complete_run(run_id, "completed", [])

    runs = db.list_runs()
    saved_run = next(
        run for run in runs if run["rfp_run_id"] == run_id
    )
    saved_results = db.get_run_results(run_id)

    assert saved_run["status"] == "completed"
    assert json.loads(saved_run["warnings_json"]) == []
    assert len(saved_results) == 2
    assert [r["final_rank"] for r in saved_results] == [1, 2]
