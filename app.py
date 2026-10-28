import json
from datetime import date
from pathlib import Path
import streamlit as st
from database.db import (
    init_db,
    get_active_criteria,
    create_run,
    save_supplier_result,
    complete_run,
    list_runs,
    get_run_results,
    save_criteria,
    connect,
)
from src.batch_processor import process_supplier_batch

st.set_page_config(page_title="RFP Evaluation Agent", page_icon="📑", layout="wide")
init_db()

st.title("📑 RFP Evaluation Agent")
st.caption("Evaluate supplier proposals with evidence-based LLM scoring and deterministic ranking.")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("OpenAI API key", type="password", value="")
    st.caption("The key is used only for this session. Do not paste it into source code or commit it.")
    page = st.radio("Navigate", ["Evaluation Criteria", "Supplier Input", "Leaderboard", "Run Details"])

criteria = get_active_criteria()
if page == "Evaluation Criteria":
    st.subheader("Manage evaluation criteria")
    st.write(
        "Edit the criteria used for future evaluations. "
        "The weights of active criteria must total exactly 100%."
    )

    # Load active and inactive criteria so the user can manage both.
    with connect() as con:
        rows = con.execute(
            """
            SELECT criterion_id, name, description, weight,
                   max_score, is_active
            FROM evaluation_criteria
            ORDER BY criterion_id
            """
        ).fetchall()

    all_criteria = [dict(row) for row in rows]

    if not all_criteria:
        st.warning("No criteria are configured in the database.")
    else:
        edited = []

        for criterion in all_criteria:
            criterion_id = criterion["criterion_id"]
            with st.expander(
                f'{criterion["name"]} '
                f'({"Active" if criterion["is_active"] else "Inactive"})',
                expanded=False,
            ):
                name = st.text_input(
                    "Criterion name",
                    value=criterion["name"],
                    key=f"criterion_name_{criterion_id}",
                )
                description = st.text_area(
                    "Description",
                    value=criterion["description"] or "",
                    key=f"criterion_description_{criterion_id}",
                )
                weight_pct = st.number_input(
                    "Weight (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(criterion["weight"]) * 100,
                    step=5.0,
                    key=f"criterion_weight_{criterion_id}",
                )
                max_score = st.number_input(
                    "Maximum score",
                    min_value=1.0,
                    max_value=100.0,
                    value=float(criterion["max_score"]),
                    step=1.0,
                    key=f"criterion_max_score_{criterion_id}",
                )
                is_active = st.checkbox(
                    "Active",
                    value=bool(criterion["is_active"]),
                    key=f"criterion_active_{criterion_id}",
                )

                edited.append(
                    {
                        "criterion_id": criterion_id,
                        "name": name.strip(),
                        "description": description.strip(),
                        "weight": weight_pct / 100.0,
                        "max_score": max_score,
                        "is_active": is_active,
                    }
                )

        active_total = sum(
            item["weight"] for item in edited if item["is_active"]
        )
        st.metric("Total active weight", f"{active_total * 100:.2f}%")

        if abs(active_total - 1.0) <= 1e-6:
            st.success("Active criterion weights total 100%.")
        else:
            st.warning(
                "Adjust the weights of active criteria so their total is 100% "
                "before saving."
            )

        if st.button("Save criteria", type="primary"):
            try:
                save_criteria(edited)
                st.success(
                    "Criteria saved to SQLite. These settings will be used "
                    "for future evaluation runs."
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception as error:
                st.error(f"Could not save criteria: {error}")

elif page == "Supplier Input":
    st.subheader("Create an evaluation run")
    st.write("Upload multiple supplier proposal PDFs. Each supplier needs a name, submission date, and historical experience rating.")
    uploads = st.file_uploader("Supplier proposal PDFs", type=["pdf"], accept_multiple_files=True)
    if uploads:
        supplier_inputs = []
        cols = st.columns(2)
        for i, upload in enumerate(uploads):
            with cols[i % 2]:
                st.markdown(f"**{upload.name}**")
                name = st.text_input("Supplier name", value=Path(upload.name).stem.replace("_proposal", "").replace("_", " ").title(), key=f"name_{i}")
                submitted = st.date_input("Submission date", value=date.today(), key=f"date_{i}")
                experience = st.slider("Historical experience rating (0–5)", 0.0, 5.0, 3.0, 0.1, key=f"exp_{i}")
                supplier_inputs.append({"name": name.strip(), "submission_date": submitted.isoformat(), "experience_rating": experience, "file_name": upload.name, "bytes": upload.getvalue()})
        if st.button("Evaluate supplier batch", type="primary", disabled=not api_key):
            if not criteria or abs(sum(c["weight"] for c in criteria)-1.0) > 1e-6:
                st.error("Configure active criteria with weights totaling 100% before running.")
            elif any(not s["name"] for s in supplier_inputs):
                st.error("Every supplier must have a name.")
            else:
                run_id = create_run()
                progress = st.progress(0, text="Starting supplier evaluations...")
                try:
                    ranked, warnings = process_supplier_batch(
                        suppliers=supplier_inputs,
                        criteria=criteria,
                        api_key=api_key,
                    )
                    progress.progress(1.0, text="Supplier processing finished.")

                    if ranked:
                        for result in ranked:
                            save_supplier_result(run_id, result)

                        status = (
                            "completed_with_warnings"
                            if warnings
                            else "completed"
                        )
                        complete_run(run_id, status, warnings)

                        st.success(
                            f"Run {run_id} completed. "
                            f"Evaluated {len(ranked)} supplier(s)."
                        )
                        st.session_state["last_run_id"] = run_id
                        st.json({
                            "run_id": run_id,
                            "status": status,
                            "warnings": warnings,
                            "results": ranked,
                        })
                    else:
                        complete_run(run_id, "failed", warnings)
                        st.error(
                            "No suppliers could be evaluated. "
                            "Review the warnings in Run Details."
                        )
                        if warnings:
                            for warning in warnings:
                                st.write(f"- {warning}")

                except Exception as error:
                    failure_warnings = [
                        f"Batch processing failed: {type(error).__name__}: {error}"
                    ]
                    complete_run(run_id, "failed", failure_warnings)
                    st.error("The evaluation batch failed.")
                    st.write(failure_warnings[0])
    else:
        st.info("Start by uploading the four synthetic proposal PDFs from the source-document package.")
    if not api_key:
        st.warning("Enter your API key in the sidebar to enable evaluation. It is not stored in SQLite.")
elif page == "Leaderboard":
    runs = list_runs()
    if not runs:
        st.info("No evaluation runs yet. Upload proposals to create your first run.")
    else:
        run_ids = [r["rfp_run_id"] for r in runs]
        run_id = st.selectbox("Select evaluation run", run_ids)
        results = get_run_results(run_id)
        if results:
            st.dataframe([{"Rank": r["final_rank"], "Supplier": r["name"], "Absolute score (%)": round(r["absolute_score"]*100, 2), "PPI (%)": round(r["ppi"], 2)} for r in results], use_container_width=True)
            st.download_button("Download result JSON", json.dumps(results, indent=2), file_name=f"rfp_run_{run_id}.json", mime="application/json")
        else:
            st.info("No saved supplier results for this run.")

else:
    runs = list_runs()

    if not runs:
        st.info("No runs available yet.")
    else:
        run_ids = [r["rfp_run_id"] for r in runs]
        run_id = st.selectbox("Evaluation run", run_ids)
        run_info = next(
            r for r in runs if r["rfp_run_id"] == run_id
        )

        st.subheader(f"Run {run_id} details")

        col1, col2 = st.columns(2)
        col1.metric("Status", run_info["status"])
        col2.write(f'**Created:** {run_info["created_at"]}')

        try:
            warnings = json.loads(
                run_info.get("warnings_json", "[]") or "[]"
            )
        except (TypeError, json.JSONDecodeError):
            warnings = ["Could not parse run warnings."]

        if warnings:
            st.warning("Warnings recorded for this run")
            for warning in warnings:
                st.write(f"- {warning}")
        else:
            st.success("No run-level warnings recorded.")

        results = get_run_results(run_id)

        if not results:
            st.info("No supplier results are saved.")
        else:
            names = [r["name"] for r in results]
            supplier = st.selectbox("Supplier scorecard", names)
            chosen = next(
                r for r in results if r["name"] == supplier
            )

            st.divider()
            st.header(f'{chosen["name"]} — Detailed Scorecard')
            st.write(
                chosen.get("overall_summary")
                or "No overall summary was returned."
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Final rank", f'#{chosen.get("final_rank", "—")}')
            c2.metric(
                "Absolute weighted score",
                f'{float(chosen.get("absolute_score", 0)) * 100:.2f}%'
            )
            c3.metric(
                "Peer Performance Index",
                f'{float(chosen.get("ppi", 0)):.2f}%'
            )

            st.subheader("Criterion comparison")

            rows = []
            for criterion in chosen.get("criteria", []):
                rows.append({
                    "Criterion": criterion.get("name", "Unknown"),
                    "Score": (
                        f'{criterion.get("score", 0)}/'
                        f'{criterion.get("max_score", 5)}'
                    ),
                    "Weight": (
                        f'{float(criterion.get("weight", 0)) * 100:.0f}%'
                    ),
                    "Peer benchmark": criterion.get("benchmark_score", "—"),
                    "Gap": criterion.get("gap", "—"),
                    "Relative performance": (
                        f'{float(criterion["relative_performance_pct"]):.2f}%'
                        if criterion.get("relative_performance_pct") is not None
                        else "—"
                    )
                })

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Justifications and supporting evidence")

            for i, criterion in enumerate(
                chosen.get("criteria", []), start=1
            ):
                with st.expander(
                    f'{i}. {criterion.get("name", "Criterion")} — '
                    f'{criterion.get("score", 0)}/'
                    f'{criterion.get("max_score", 5)}'
                ):
                    st.markdown("**Justification**")
                    st.write(
                        criterion.get("justification")
                        or "No justification provided."
                    )

                    st.markdown("**Supporting evidence**")
                    st.write(
                        criterion.get("evidence")
                        or "No evidence returned."
                    )

                    st.caption(
                        "Verify this LLM-generated evidence against the "
                        "original proposal before relying on it."
                    )

            st.subheader("Identified risks")
            risks = chosen.get("risks", [])

            if risks:
                for risk in risks:
                    st.write(f"- {risk}")
            else:
                st.write("No risks were returned by the LLM.")

            st.download_button(
                "Download supplier scorecard JSON",
                json.dumps(chosen, indent=2),
                file_name=(
                    f'run_{run_id}_'
                    f'{chosen["name"].lower().replace(" ", "_")}.json'
                ),
                mime="application/json"
            )

            with st.expander("Show raw JSON (debug view)"):
                st.json(chosen)

            with st.expander("Show all suppliers in this run"):
                st.dataframe(
                    [
                        {
                            "Rank": r.get("final_rank"),
                            "Supplier": r.get("name"),
                            "Absolute score (%)": round(
                                float(r.get("absolute_score", 0)) * 100, 2
                            ),
                            "PPI (%)": round(
                                float(r.get("ppi", 0)), 2
                            )
                        }
                        for r in results
                    ],
                    use_container_width=True,
                    hide_index=True
                )
