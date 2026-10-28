
from unittest.mock import patch

from src.batch_processor import process_supplier_batch


CRITERIA = [
    {
        "criterion_id": 1,
        "name": "Technical Capability",
        "description": "Technical capabilities",
        "weight": 1.0,
        "max_score": 5,
    }
]


def make_supplier(name):
    return {
        "name": name,
        "submission_date": "2026-10-28",
        "experience_rating": 3.0,
        "file_name": f"{name.lower().replace(' ', '_')}.pdf",
        "bytes": b"fake PDF bytes",
    }


def make_result(name):
    return {
        "name": name,
        "criteria": [
            {
                "criterion_id": 1,
                "name": "Technical Capability",
                "score": 4,
                "max_score": 5,
                "justification": "Good technical approach",
                "evidence": "Evidence from proposal",
            }
        ],
        "risks": [],
        "overall_summary": "Test result",
    }


@patch("src.batch_processor.calculate_batch_scores")
@patch("src.batch_processor.evaluate_supplier")
@patch("src.batch_processor.extract_pdf_text")
def test_one_supplier_fails_and_another_succeeds(
    mock_extract, mock_evaluate, mock_score
):
    mock_extract.side_effect = [
        ValueError("Unreadable PDF"),
        "Valid proposal text",
    ]

    mock_evaluate.return_value = (make_result("Supplier B"), [])
    mock_score.side_effect = lambda results, criteria: results

    suppliers = [
        make_supplier("Supplier A"),
        make_supplier("Supplier B"),
    ]

    results, warnings = process_supplier_batch(
        suppliers, CRITERIA, "fake-test-key"
    )

    assert len(results) == 1
    assert results[0]["name"] == "Supplier B"
    assert any("Supplier A" in warning for warning in warnings)
    mock_evaluate.assert_called_once()
    mock_score.assert_called_once()


@patch("src.batch_processor.calculate_batch_scores")
@patch("src.batch_processor.evaluate_supplier")
@patch("src.batch_processor.extract_pdf_text")
def test_all_suppliers_fail(
    mock_extract, mock_evaluate, mock_score
):
    mock_extract.side_effect = ValueError("Unreadable PDF")

    suppliers = [
        make_supplier("Supplier A"),
        make_supplier("Supplier B"),
    ]

    results, warnings = process_supplier_batch(
        suppliers, CRITERIA, "fake-test-key"
    )

    assert results == []
    assert len(warnings) == 2
    assert any("Supplier A" in warning for warning in warnings)
    assert any("Supplier B" in warning for warning in warnings)
    mock_evaluate.assert_not_called()
    mock_score.assert_not_called()
