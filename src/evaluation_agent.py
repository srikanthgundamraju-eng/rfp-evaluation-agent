
import json
import os

from openai import OpenAI
from src.validation import validate_scorecard


def evaluate_document(
    supplier_name,
    document_text,
    criteria,
    api_key,
    model=None,
    retrieved_evidence=None,
):
    """Evaluate a supplier using retrieved proposal evidence."""

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    criteria_payload = [
        {
            "criterion_id": c["criterion_id"],
            "name": c["name"],
            "description": c["description"],
            "max_score": c["max_score"],
        }
        for c in criteria
    ]

    system = """You are a careful supplier proposal evaluator.

Evaluate only evidence present in the supplied proposal passages.
Return a single valid JSON object, no markdown.

Do not calculate weighted scores, peer benchmarks, PPI, or rank.

For each active criterion return:
criterion_id, score, max_score, justification, evidence,
and source_chunk_ids.

source_chunk_ids must contain only the chunk_id values of passages
that directly support the evidence and justification for that criterion.

Do not invent chunk IDs.
If no retrieved passage supports the evaluation, return an empty list
for source_chunk_ids.

Do not invent evidence. If evidence is missing, say so and score accordingly.
Scores must be numeric and within 0..max_score.

Retrieved passages are evidence candidates, not proof of compliance.
Do not claim a requirement is met unless the supplied text supports it.

Required shape:
{
  "supplier_name": "...",
  "criteria": [
    {
      "criterion_id": 1,
      "score": 0,
      "max_score": 5,
      "justification": "...",
      "evidence": "...",
      "source_chunk_ids": [0, 2]
    }
  ],
  "risks": ["..."],
  "overall_summary": "..."
}"""

    # Maintain a mapping between retrieved chunk IDs and their
    # original PDF source information.
    source_lookup = {}

    if retrieved_evidence is None:
        # Preserve compatibility with direct callers and existing tests.
        context = document_text[:80000]

    else:
        context = {}

        for criterion in criteria:
            criterion_id = str(criterion["criterion_id"])

            passages = retrieved_evidence.get(criterion_id, [])

            context[criterion_id] = {
                "criterion": criterion["name"],
                "retrieved_passages": passages,
            }

            for passage in passages:
                chunk_id = passage.get("chunk_id")

                if chunk_id is None:
                    continue

                source_lookup[(criterion_id, str(chunk_id))] = {
                    "file_name": passage.get("file_name", ""),
                    "page_number": passage.get("page_number"),
                }

    user = {
        "supplier_name": supplier_name,
        "active_criteria": criteria_payload,
        "proposal_evidence": context,
    }

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=0,
    )

    raw = response.choices[0].message.content
    scorecard = json.loads(raw)

    # Resolve LLM-selected chunk IDs into trusted source metadata.
    if retrieved_evidence is not None and isinstance(scorecard, dict):
        raw_items = scorecard.get("criteria", [])

        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue

                criterion_id = str(item.get("criterion_id", ""))
                chunk_ids = item.get("source_chunk_ids", [])

                sources = []

                if isinstance(chunk_ids, list):
                    for chunk_id in chunk_ids:
                        source = source_lookup.get(
                            (criterion_id, str(chunk_id))
                        )

                        if not source:
                            continue

                        file_name = source["file_name"]
                        page_number = source["page_number"]

                        if (
                            isinstance(file_name, str)
                            and file_name.strip()
                            and isinstance(page_number, int)
                            and not isinstance(page_number, bool)
                            and page_number >= 1
                        ):
                            source_reference = {
                                "file_name": file_name,
                                "page_number": page_number,
                            }

                            if source_reference not in sources:
                                sources.append(source_reference)

                item["sources"] = sources

    return validate_scorecard(scorecard, criteria, supplier_name)
