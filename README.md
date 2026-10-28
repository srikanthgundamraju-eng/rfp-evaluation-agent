# RFP Evaluation Agent

A Streamlit application for evidence-based supplier proposal evaluation. This starter includes a SQLite-backed criteria/run/result store, PDF text extraction, LLM scorecard generation, deterministic score calculation and ranking, and a simple dashboard.

## Setup (Windows / VS Code)

1. Extract this project folder.
2. Open the folder in VS Code.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install packages:
   ```powershell
   pip install -r requirements.txt
   ```
5. Run the app:
   ```powershell
   streamlit run app.py
   ```

Enter the API key in the sidebar for the current session. The app does not save that key to SQLite. Never commit real API keys.

## Project layout

- `app.py`: Streamlit UI and workflow entry point
- `database/db.py`: SQLite schema, seed criteria and persistence
- `src/document_tool.py`: PDF text extraction
- `src/evaluation_agent.py`: LLM prompt and JSON response
- `src/validation.py`: normalize and validate scorecards
- `src/scoring.py`: deterministic weighted scoring, peer benchmark, PPI and tie-break
- `src/orchestrator.py`: controlled workflow
- `tests/`: unit tests for validation and deterministic ranking

## Default criteria

Technical Capability 30%, Implementation Plan 20%, Commercial Value 20%, Security & Compliance 20%, Support & Experience 10%.

## Formula and ranking

Absolute score = sum((criterion score / maximum score) * criterion weight).
Benchmark = highest valid score per criterion in the batch.
Gap = supplier score - benchmark.
Relative performance = score / benchmark * 100, with safe handling when benchmark is zero.
PPI = weighted average of criterion relative performance.
Tie-break: higher PPI, earlier submission date, higher historical experience rating, supplier name ascending.

## Important

This is a starter implementation. Before final submission, test it with all four synthetic PDFs, complete the UI and documentation, verify JSON exports, and deploy to Streamlit Community Cloud. LLM output is untrusted and is validated before calculations.
