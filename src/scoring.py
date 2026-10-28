def calculate_batch_scores(results, criteria):
    """Calculate weighted scores and peer-relative PPI deterministically."""
    if not results:
        return []
    if abs(sum(float(c["weight"]) for c in criteria)-1.0) > 1e-6:
        raise ValueError("Criterion weights must total 1.0.")
    criterion_by_id = {str(c["criterion_id"]): c for c in criteria}
    benchmarks = {}
    for c in criteria:
        scores = []
        for r in results:
            entry = next((x for x in r["criteria"] if str(x["criterion_id"]) == str(c["criterion_id"])), None)
            if entry is not None:
                scores.append(float(entry["score"]))
        benchmarks[str(c["criterion_id"])] = max(scores, default=0.0)
    scored = []
    for original in results:
        r = dict(original)
        entries = []
        absolute = 0.0
        ppi = 0.0
        for e0 in r["criteria"]:
            e = dict(e0)
            c = criterion_by_id[str(e["criterion_id"])]
            score, max_score, weight = float(e["score"]), float(c["max_score"]), float(c["weight"])
            absolute += (score/max_score if max_score else 0.0) * weight
            benchmark = benchmarks[str(c["criterion_id"])]
            relative = (score/benchmark*100.0) if benchmark > 0 else 100.0
            e.update({"weight": weight, "benchmark_score": benchmark, "gap": score-benchmark, "relative_performance_pct": relative})
            ppi += relative * weight
            entries.append(e)
        r["criteria"] = entries
        r["absolute_score"] = absolute
        r["ppi"] = ppi
        scored.append(r)
    scored.sort(key=lambda r: (-r["ppi"], r["submission_date"], -float(r["experience_rating"]), r["name"].casefold()))
    for i, r in enumerate(scored, start=1):
        r["final_rank"] = i
    return scored
