
"""Lightweight RAG retrieval for supplier proposal evaluation."""

import os
from math import sqrt

from openai import OpenAI


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_BATCH_SIZE = 64


def chunk_text(text, chunk_size=1200, overlap=200):
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Prefer a paragraph boundary near the end of the chunk.
        if end < len(text):
            boundary = text.rfind(
                "\n", start + chunk_size // 2, end
            )
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Retain some context from the previous chunk.
        start = max(start + 1, end - overlap)

    return chunks


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two numeric vectors."""
    if len(vector_a) != len(vector_b):
        raise ValueError("Embedding vectors must have equal dimensions.")

    norm_a = sqrt(sum(value * value for value in vector_a))
    norm_b = sqrt(sum(value * value for value in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return sum(
        a * b for a, b in zip(vector_a, vector_b)
    ) / (norm_a * norm_b)


def embed_texts_in_batches(
    client,
    texts,
    model,
    batch_size=DEFAULT_EMBEDDING_BATCH_SIZE,
):
    """Generate embeddings in batches, preserving input order."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")

    embeddings = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]

        response = client.embeddings.create(
            model=model,
            input=batch,
        )

        # Response indices are local to each individual batch.
        ordered = sorted(
            response.data,
            key=lambda item: item.index,
        )
        embeddings.extend(item.embedding for item in ordered)

        if len(ordered) != len(batch):
            raise ValueError(
                "Embedding API returned an unexpected number of results."
            )

    return embeddings


def retrieve_relevant_chunks(
    document_text,
    criteria,
    api_key=None,
    top_k=3,
    chunk_size=1200,
    overlap=200,
    model=None,
):
    """Retrieve the most relevant proposal chunks for each criterion."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    chunks = chunk_text(document_text, chunk_size, overlap)

    if not chunks:
        raise ValueError(
            "No extractable proposal text is available for retrieval."
        )

    if not criteria:
        return {}

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenAI API key is required for RAG embeddings."
        )

    model = model or os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    )
    client = OpenAI(api_key=api_key)

    # Embed proposal chunks in batches.
    chunk_embeddings = embed_texts_in_batches(
        client=client,
        texts=chunks,
        model=model,
    )

    # Create one query for each active evaluation criterion.
    queries = [
        (
            f"Evaluation criterion: {criterion['name']}. "
            f"Description: {criterion.get('description', '')}"
        )
        for criterion in criteria
    ]

    query_embeddings = embed_texts_in_batches(
        client=client,
        texts=queries,
        model=model,
    )

    retrieved = {}

    for criterion, query_embedding in zip(
        criteria, query_embeddings
    ):
        ranked = [
            {
                "chunk_id": index,
                "text": chunk,
                "similarity": cosine_similarity(
                    query_embedding,
                    chunk_embeddings[index],
                ),
            }
            for index, chunk in enumerate(chunks)
        ]

        ranked.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        retrieved[str(criterion["criterion_id"])] = ranked[:top_k]

    return retrieved
