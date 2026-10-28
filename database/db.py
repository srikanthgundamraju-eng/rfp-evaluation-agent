import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "rfp_evaluation.db"
DEFAULT_CRITERIA = [
    ("Technical Capability", "Architecture fit, technical depth, migration, performance and reliability.", 0.30, 5),
    ("Implementation Plan", "Timeline, milestones, staffing, testing, cutover and rollback.", 0.20, 5),
    ("Commercial Value", "Price transparency, assumptions, total cost, value and commercial risks.", 0.20, 5),
    ("Security & Compliance", "Access controls, encryption, auditability, data protection and compliance evidence.", 0.20, 5),
    ("Support & Experience", "Relevant experience, references, support coverage and service levels.", 0.10, 5),
]

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS evaluation_criteria (
          criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          weight REAL NOT NULL CHECK(weight >= 0),
          max_score REAL NOT NULL DEFAULT 5,
          is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS rfp_runs (
          rfp_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL,
          status TEXT NOT NULL,
          warnings_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS supplier_results (
          supplier_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
          rfp_run_id INTEGER NOT NULL,
          supplier_name TEXT NOT NULL,
          submission_date TEXT NOT NULL,
          experience_rating REAL NOT NULL,
          absolute_score REAL NOT NULL,
          ppi REAL NOT NULL,
          final_rank INTEGER NOT NULL,
          result_json TEXT NOT NULL,
          FOREIGN KEY(rfp_run_id) REFERENCES rfp_runs(rfp_run_id)
        );
        CREATE TABLE IF NOT EXISTS run_criteria_snapshot (
          rfp_run_id INTEGER NOT NULL,
          criterion_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          weight REAL NOT NULL,
          max_score REAL NOT NULL,
          PRIMARY KEY(rfp_run_id, criterion_id)
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if count == 0:
            con.executemany("INSERT INTO evaluation_criteria(name,description,weight,max_score,is_active) VALUES(?,?,?,?,1)", DEFAULT_CRITERIA)

def get_active_criteria():
    with connect() as con:
        rows = con.execute("SELECT criterion_id,name,description,weight,max_score FROM evaluation_criteria WHERE is_active=1 ORDER BY criterion_id").fetchall()
    return [dict(r) for r in rows]

def create_run():
    criteria = get_active_criteria()
    if abs(sum(c["weight"] for c in criteria) - 1.0) > 1e-6:
        raise ValueError("Active criteria weights must total 100%.")
    with connect() as con:
        cur = con.execute("INSERT INTO rfp_runs(created_at,status) VALUES(?,?)", (datetime.now(timezone.utc).isoformat(), "running"))
        run_id = cur.lastrowid
        con.executemany("INSERT INTO run_criteria_snapshot VALUES(?,?,?,?,?,?)", [
            (run_id,c["criterion_id"],c["name"],c["description"],c["weight"],c["max_score"]) for c in criteria
        ])
        return run_id

def save_supplier_result(run_id, result):
    with connect() as con:
        con.execute("""INSERT INTO supplier_results
        (rfp_run_id,supplier_name,submission_date,experience_rating,absolute_score,ppi,final_rank,result_json)
        VALUES(?,?,?,?,?,?,?,?)""", (
            run_id, result["name"], result["submission_date"], result["experience_rating"],
            result["absolute_score"], result["ppi"], result["final_rank"], json.dumps(result)
        ))

def complete_run(run_id, status, warnings):
    with connect() as con:
        con.execute("UPDATE rfp_runs SET status=?, warnings_json=? WHERE rfp_run_id=?", (status, json.dumps(warnings), run_id))

def list_runs():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM rfp_runs ORDER BY rfp_run_id DESC").fetchall()]

def get_run_results(run_id):
    with connect() as con:
        rows = con.execute("SELECT result_json FROM supplier_results WHERE rfp_run_id=? ORDER BY final_rank", (run_id,)).fetchall()
    return [json.loads(r["result_json"]) for r in rows]


def save_criteria(updated_criteria):
    """Validate and save the active evaluation criteria."""
    active = [
        c for c in updated_criteria
        if c.get("is_active", True)
    ]

    if not active:
        raise ValueError("At least one criterion must be active.")

    total_weight = sum(float(c["weight"]) for c in active)

    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError(
            f"Active weights must total 100%. "
            f"Current total: {total_weight * 100:.2f}%"
        )

    for criterion in updated_criteria:
        weight = float(criterion["weight"])
        max_score = float(criterion["max_score"])

        if weight < 0 or weight > 1:
            raise ValueError("Each weight must be between 0 and 1.")

        if max_score <= 0:
            raise ValueError("Maximum score must be greater than zero.")

        if not criterion["name"].strip():
            raise ValueError("Criterion names cannot be empty.")

    with connect() as con:
        for criterion in updated_criteria:
            con.execute(
                """
                UPDATE evaluation_criteria
                SET name = ?, description = ?, weight = ?,
                    max_score = ?, is_active = ?
                WHERE criterion_id = ?
                """,
                (
                    criterion["name"].strip(),
                    criterion["description"].strip(),
                    float(criterion["weight"]),
                    float(criterion["max_score"]),
                    int(bool(criterion.get("is_active", True))),
                    int(criterion["criterion_id"]),
                ),
            )
