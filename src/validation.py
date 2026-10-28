def validate_scorecard(raw, criteria, supplier_name):
    """Normalize LLM JSON into one valid entry for every active criterion."""
    if not isinstance(raw, dict):
        raise ValueError("LLM response must be a JSON object.")
    raw_items = raw.get("criteria", [])
    if not isinstance(raw_items, list):
        raw_items = []
    by_id = {}
    for item in raw_items:
        if isinstance(item, dict) and item.get("criterion_id") is not None:
            by_id[str(item["criterion_id"])] = item
    normalized = []
    warnings = []
    for c in criteria:
        item = by_id.get(str(c["criterion_id"]))
        if not item:
            normalized.append({
                "criterion_id": c["criterion_id"], "name": c["name"], "score": 0.0,
                "max_score": c["max_score"], "justification": "Missing or malformed LLM score; defaulted to zero.",
                "evidence": "No supporting evidence returned."
            })
            warnings.append(f'Missing criterion result: {c["name"]}; score defaulted to zero.')
            continue
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            score = 0.0
            warnings.append(f'Invalid score for {c["name"]}; defaulted to zero.')
        if score < 0 or score > float(c["max_score"]):
            warnings.append(f'Out-of-range score for {c["name"]}; clamped to valid range.')
            score = min(max(score, 0.0), float(c["max_score"]))
        justification = item.get("justification")
        evidence = item.get("evidence")
        if not isinstance(justification, str) or not justification.strip():
            justification = "No usable justification returned."
            warnings.append(f'Missing justification for {c["name"]}.')
        if not isinstance(evidence, str) or not evidence.strip():
            evidence = "No supporting evidence returned."
            warnings.append(f'Missing evidence for {c["name"]}.')
        normalized.append({
            "criterion_id": c["criterion_id"], "name": c["name"], "score": score,
            "max_score": float(c["max_score"]), "weight": float(c["weight"]),
            "justification": justification.strip(), "evidence": evidence.strip()
        })
    risks = raw.get("risks", [])
    if not isinstance(risks, list):
        risks = [str(risks)]
        warnings.append("Malformed risks field normalized to a list.")
    summary = raw.get("overall_summary", "")
    if not isinstance(summary, str):
        summary = str(summary)
        warnings.append("Malformed overall_summary converted to text.")
    return {
        "supplier_name": str(raw.get("supplier_name") or supplier_name),
        "criteria": normalized,
        "risks": [str(x) for x in risks],
        "overall_summary": summary,
    }, warnings
