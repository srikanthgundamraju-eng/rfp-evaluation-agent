
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from openai import AuthenticationError

from src.evaluation_agent import evaluate_document


CRITERIA = [
    {
        "criterion_id": 1,
        "name": "Technical Capability",
        "description": "Technical capabilities",
        "max_score": 5,
        "weight": 1.0,
    }
]


def make_authentication_error():
    response = Mock()
    response.status_code = 401
    response.headers = {}

    return AuthenticationError(
        "Invalid API key",
        response=response,
        body={"error": {"message": "Invalid API key"}},
    )


def make_api_response(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


@patch("src.evaluation_agent.OpenAI")
def test_api_authentication_failure_is_propagated(mock_openai):
    mock_openai.return_value.chat.completions.create.side_effect = (
        make_authentication_error()
    )

    with pytest.raises(AuthenticationError):
        evaluate_document(
            supplier_name="Test Supplier",
            document_text="Sample proposal text",
            criteria=CRITERIA,
            api_key="invalid-test-key",
        )


@patch("src.evaluation_agent.OpenAI")
def test_malformed_json_response_is_rejected(mock_openai):
    mock_openai.return_value.chat.completions.create.return_value = (
        make_api_response("This is not valid JSON")
    )

    with pytest.raises(json.JSONDecodeError):
        evaluate_document(
            supplier_name="Test Supplier",
            document_text="Sample proposal text",
            criteria=CRITERIA,
            api_key="fake-test-key",
        )


@patch("src.evaluation_agent.OpenAI")
def test_valid_json_response_is_processed(mock_openai):
    content = json.dumps({
        "supplier_name": "Test Supplier",
        "criteria": [
            {
                "criterion_id": 1,
                "score": 4,
                "max_score": 5,
                "justification": "Clear technical approach",
                "evidence": "The proposal describes its architecture.",
            }
        ],
        "risks": [],
        "overall_summary": "A technically capable supplier.",
    })

    mock_openai.return_value.chat.completions.create.return_value = (
        make_api_response(content)
    )

    scorecard, warnings = evaluate_document(
        supplier_name="Test Supplier",
        document_text="Sample proposal text",
        criteria=CRITERIA,
        api_key="fake-test-key",
    )

    assert scorecard["criteria"][0]["score"] == 4
    assert warnings == []
    mock_openai.return_value.chat.completions.create.assert_called_once()
