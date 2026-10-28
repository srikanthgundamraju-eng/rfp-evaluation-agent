import json

from database import db
from src import batch_processor


def test_batch_evaluation_and_database_persistence(tmp_path, monkeypatch):
    """Successful suppliers are saved; failed suppliers generate warnings."""

    # Use a temporary database so the real project database is untouched.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_rfp.db")
    db.init_db()

    # Use a single criterion with a weight of 100%.
    criteria = [
        {
            "criterion_id": 1,
            "name": "Technical Capability",
            "description": "Technical design and capabilities",
            "weight": 1.0,
            "max_score": 5.0,
        }
    ]

    # Create a run and its criteria snapshot.
    run_id = db.create_run()

    # Mock PDF extraction: no real PDF parsing is needed in this test.
    def fake_extract_pdf_text(pdf_bytes):
        if pdf_bytes == b"bad-pdf":
            raise ValueError("Invalid PDF")
        return "A valid synthetic supplier proposal."

    monkeypatch.setattr(
        batch_processor, "extract_pdf_text", fake_extract_pdf_text
    )

    # Mock the LLM evaluation: no API call or API credits.
    def fake_evaluate_supplier(
        supplier_name,
        document_text,
        criteria,
        api_key,
        file_name="",
    ):
        if supplier_name == "Failed Supplier":
            raise RuntimeError("Simulated evaluation failure")

        # Match the structure expected by src/scoring.py:
        # each result has a "criteria" list and each entry has criterion_id.
        return (
            {
                "criteria": [
                    {
                        "criterion_id": 1,
                        "criterion": "Technical Capability",
                        "score": 4,
                        "justification": "Strong technical proposal",
                        "evidence": "Synthetic test evidence",
                    }
                ],
                "absolute_score": 0.0,
                "ppi": 0.0,
                "final_rank": 0,
            },
            [],
        )

    monkeypatch.setattr(
        batch_processor, "evaluate_supplier", fake_evaluate_supplier
    )

    suppliers = [
        {
            "name": "Successful Supplier",
            "submission_date": "2026-10-20",
            "experience_rating": 4.0,
            "file_name": "success.pdf",
            "bytes": b"valid-pdf",
        },
        {
            "name": "Failed Supplier",
            "submission_date": "2026-10-21",
            "experience_rating": 3.0,
            "file_name": "failed.pdf",
            "bytes": b"valid-pdf",
        },
    ]

    ranked_results, warnings = batch_processor.process_supplier_batch(
        suppliers=suppliers,
        criteria=criteria,
        api_key="test-key",
    )

    # Only the successful supplier should be ranked.
    assert len(ranked_results) == 1
    assert ranked_results[0]["name"] == "Successful Supplier"
    assert ranked_results[0]["final_rank"] == 1

    # The failure must be reported without stopping the batch.
    assert any("Failed Supplier" in warning for warning in warnings)
    assert any(
        "Simulated evaluation failure" in warning for warning in warnings
    )

    # Persist the successful result and complete the run with warnings.
    for result in ranked_results:
        db.save_supplier_result(run_id, result)

    db.complete_run(run_id, "completed_with_warnings", warnings)

    # Verify the saved status and warnings.
    with db.connect() as con:
        run = con.execute(
            """
            SELECT status, warnings_json
            FROM rfp_runs
            WHERE rfp_run_id = ?
            """,
            (run_id,),
        ).fetchone()

    assert run["status"] == "completed_with_warnings"

    saved_warnings = json.loads(run["warnings_json"])
    assert any("Failed Supplier" in warning for warning in saved_warnings)

    # Verify the persisted leaderboard results.
    saved_results = db.get_run_results(run_id)

    assert len(saved_results) == 1
    assert saved_results[0]["name"] == "Successful Supplier"
    assert saved_results[0]["final_rank"] == 1
