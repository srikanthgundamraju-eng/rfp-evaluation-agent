import json
import os
from openai import OpenAI
from src.validation import validate_scorecard

def evaluate_document(supplier_name, document_text, criteria, api_key, model=None):
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)
    criteria_payload = [{
        "criterion_id": c["criterion_id"], "name": c["name"],
        "description": c["description"], "max_score": c["max_score"]
    } for c in criteria]
    system = """You are a careful supplier proposal evaluator. Evaluate only evidence present in the supplied document.
Return a single valid JSON object, no markdown. Do not calculate weighted scores, peer benchmarks, PPI, or rank.
For each active criterion return criterion_id, score, max_score, justification, and supporting evidence.
Do not invent evidence. If evidence is missing, say so and score accordingly.
Scores must be numeric and within 0..max_score.
Required shape: {"supplier_name":"...","criteria":[{"criterion_id":1,"score":0,"max_score":5,"justification":"...","evidence":"..."}],"risks":["..."],"overall_summary":"..."}"""
    user = {
        "supplier_name": supplier_name,
        "active_criteria": criteria_payload,
        "proposal_text": document_text[:80000]
    }
    response = client.chat.completions.create(
        model=model,
        response_format={"type":"json_object"},
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(user)}],
        temperature=0
    )
    raw = response.choices[0].message.content
    return validate_scorecard(json.loads(raw), criteria, supplier_name)

