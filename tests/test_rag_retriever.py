
from unittest.mock import Mock

import pytest

from src.rag_retriever import (
    chunk_text,
    chunk_pdf_pages,
    cosine_similarity,
    embed_texts_in_batches,
    retrieve_relevant_chunks,
)


def test_chunk_text_returns_empty_list_for_empty_text():
    assert chunk_text("   ") == []


def test_chunk_text_splits_long_text():
    text = "A" * 3000

    chunks = chunk_text(text, chunk_size=1200, overlap=200)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 1200 for chunk in chunks)


def test_chunk_text_preserves_all_text_content():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."

    chunks = chunk_text(text, chunk_size=30, overlap=5)

    combined = " ".join(chunks)
    assert "Paragraph one." in combined
    assert "Paragraph two." in combined
    assert "Paragraph three." in combined


def test_chunk_pdf_pages_preserves_page_numbers_and_text():
    pages = [
        {"page_number": 1, "text": "Technical architecture details."},
        {"page_number": 3, "text": "Security and compliance details."},
    ]

    chunks = chunk_pdf_pages(pages)

    assert len(chunks) == 2
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["text"] == "Technical architecture details."
    assert chunks[1]["page_number"] == 3
    assert chunks[1]["text"] == "Security and compliance details."


def test_chunk_pdf_pages_preserves_original_page_numbers():
    pages = [
        {"page_number": 2, "text": "First extracted page."},
        {"page_number": 5, "text": "Second extracted page."},
    ]

    chunks = chunk_pdf_pages(pages)

    assert [chunk["page_number"] for chunk in chunks] == [2, 5]


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)


def test_cosine_similarity_rejects_different_dimensions():
    with pytest.raises(ValueError):
        cosine_similarity([1, 2], [1])


def test_retrieval_rejects_empty_document():
    with pytest.raises(ValueError, match="No extractable"):
        retrieve_relevant_chunks(
            " ",
            [{"criterion_id": 1, "name": "Security"}],
        )


def test_retrieval_rejects_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="API key"):
        retrieve_relevant_chunks(
            "A proposal contains technical details.",
            [{"criterion_id": 1, "name": "Technical capability"}],
            api_key=None,
        )


def test_embed_texts_in_batches_preserves_order():
    client = Mock()

    client.embeddings.create.side_effect = [
        Mock(data=[
            Mock(index=1, embedding=[2.0]),
            Mock(index=0, embedding=[1.0]),
        ]),
        Mock(data=[
            Mock(index=0, embedding=[3.0]),
        ]),
    ]

    result = embed_texts_in_batches(
        client=client,
        texts=["A", "B", "C"],
        model="test-model",
        batch_size=2,
    )

    assert result == [[1.0], [2.0], [3.0]]
    assert client.embeddings.create.call_count == 2
