# Solution Specification — Agentic RFP Evaluation and Supplier Ranking

## Objective
Build a Streamlit application that extracts multiple supplier proposal PDFs, scores each against active SQLite criteria using an LLM, validates the returned scorecards, calculates deterministic weighted and peer-relative scores, ranks suppliers, persists the run, and presents explainable results.

## Mandatory workflow
1. Load active criteria and weights from SQLite.
2. Upload multiple supplier PDFs and enter supplier name, submission date, and historical experience rating.
3. Create an evaluation run.
4. Extract PDF text.
5. Ask the LLM for criterion scores, justifications, supporting evidence, risks, and overall summary as JSON.
6. Validate missing, malformed and out-of-range fields.
7. Calculate weighted scores, peer benchmarks, criterion gaps, relative percentages and PPI in Python.
8. Rank deterministically using the assignment tie-break order.
9. Persist results and show leaderboard, detailed scorecards, run warnings and JSON download.

## Guardrails
- LLM judges proposal content only; it does not calculate final weighted scores or determine ranks.
- Never fabricate evidence. Missing evidence should be recorded as missing.
- Keep API keys out of source control and databases.
- Preserve evaluation history; a re-evaluation creates a new run.
- Criteria weights must total 100%.
- Add tests for validation, zero benchmarks, scoring and tie-breaks.
- Enhancements such as dynamic templates, RAG and history comparison come after mandatory features work.
