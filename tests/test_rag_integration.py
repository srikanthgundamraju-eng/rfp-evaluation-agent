
from unittest.mock import patch

from src.orchestrator import evaluate_supplier


def test_orchestrator_passes_retrieved_evidence_to_evaluator():
    criteria = [
        {
            "criterion_id": 1,
            "name": "Technical Capability",
            "description": "Evaluate technical capabilities.",
            "max_score": 5,
            "weight": 1.0,
        }
    ]

    retrieved = {
        "1": [
            {
                "chunk_id": 0,
                "text": "The supplier supports automated data migration.",
                "similarity": 0.91,
            }
        ]
    }

    scorecard = {
        "criteria": [
            {
                "criterion_id": 1,
                "name": "Technical Capability",
                "score": 4.0,
                "max_score": 5.0,
                "weight": 1.0,
                "justification": "Relevant technical evidence was provided.",
                "evidence": "The supplier supports automated data migration.",
            }
        ],
        "risks": [],
        "overall_summary": "Good technical capability.",
    }

    with (
        patch(
            "src.orchestrator.retrieve_relevant_chunks",
            return_value=retrieved,
        ) as mock_retrieve,
        patch(
            "src.orchestrator.evaluate_document",
            return_value=(scorecard, []),
        ) as mock_evaluate,
    ):
        result, warnings = evaluate_supplier(
            supplier_name="Supplier A",
            document_text="Full proposal text.",
            criteria=criteria,
            api_key="test-key",
            file_name="supplier_a.pdf",
        )

    mock_retrieve.assert_called_once_with(
        document_text="Full proposal text.",
        document_pages=None,
        file_name="supplier_a.pdf",
        criteria=criteria,
        api_key="test-key",
    )

    mock_evaluate.assert_called_once_with(
        supplier_name="Supplier A",
        document_text="Full proposal text.",
        criteria=criteria,
        api_key="test-key",
        retrieved_evidence=retrieved,
    )

    assert result["name"] == "Supplier A"
    assert result["file_name"] == "supplier_a.pdf"
    assert result["criteria"] == scorecard["criteria"]
    assert warnings == []
