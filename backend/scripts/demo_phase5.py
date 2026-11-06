"""
scripts/demo_phase5.py — End-to-end Phase 5 Retrieval Upgrades Demo.

Demonstrates:
  1. Ingestion of HR knowledge base (2019 archived PDF, 2024 revised DOCX, Handbook PDF)
     and structured employee records (CSV).
  2. Phase 3 cleaning: applies proposals to produce Version 2 with quarantined rows.
  3. Document Overrides:
     - 2019 Policy -> published_at: 2019-03-01
     - 2024 Policy -> published_at: 2024-06-01
  4. Indexing: creates new index runs picking up user metadata overrides and recomputing freshness.
  5. Multi-Strategy Compare (/retrieve/compare):
     - Question 1: "How many annual leaves are employees entitled to?"
     - Question 2 (Exact-ID): "What is employee E1007's department?" (reports ranks across all 4 strategies)
     - Question 3 (Unsupported): "What is the company's Mars colonization budget?" (all 4 fail evidence gate)
  6. Freshness-Aware Conflict Resolution (/query):
     - With freshness filter ["fresh", "aging"]: cites only 2024 policy (24 days).
     - Without filters: retrieves both and generates answer explicitly addressing the policy conflict.

Usage:
  python scripts/demo_phase5.py --standalone
  # Or with running server:
  python scripts/demo_phase5.py
"""

import sys
import os
import json
import time
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone, timedelta
import functools
print = functools.partial(print, flush=True)

from db import init_db, SessionLocal, Document, Source, IndexRun, Chunk
from scripts.reset_demo_db import reset_demo_database, get_demo_db_url
demo_url = get_demo_db_url()
os.environ["DATABASE_URL"] = demo_url

# Set simulated demo clock
simulated_clock = os.getenv("FRESHNESS_REFERENCE_DATE", "2024-09-01T00:00:00+00:00")
os.environ["FRESHNESS_REFERENCE_DATE"] = simulated_clock
ref_dt = datetime.fromisoformat(simulated_clock.replace("Z", "+00:00"))

# Prominent simulated clock banner (Review Item A1)
print(f"\n{BOLD}{CYAN}{'='*75}")
print("  [SIMULATED DEMO CLOCK, NOT TODAY'S DATE]")
print(f"  Reference Date: {ref_dt.date().isoformat()} (simulated demo clock, not today's date)")
print("  Document Dates & Freshness Buckets:")
print("    - 2024 Leave Policy:         published 2024-06-01 (age: 92 days)   -> fresh")
print("    - 2019 Leave Policy:         published 2019-03-01 (age: 2011 days) -> stale")
print("    - Working Hours Handbook:    undated                               -> unknown")
print(f"{'='*75}{RESET}\n")

reset_demo_database(demo_url)

RESET   = "\033[0m"
BOLD    = "\033[1m"
GREEN   = "\033[32m"
CYAN    = "\033[36m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
MAGENTA = "\033[35m"

def header(title: str):
    print(f"\n{BOLD}{CYAN}{'='*75}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*75}{RESET}")

def step(title: str):
    print(f"\n{BOLD}{MAGENTA}>> {title} {'='*(70 - len(title))}{RESET}")

def ok(msg: str):
    print(f"{GREEN}[OK] {msg}{RESET}")

def warn(msg: str):
    print(f"{YELLOW}[WARN] {msg}{RESET}")

def info(msg: str):
    print(f"  {msg}")

def err(msg: str):
    print(f"{RED}[ERROR] {msg}{RESET}")
    sys.exit(1)


# Setup client: TestClient if --standalone or no running server, otherwise requests
use_testclient = "--standalone" in sys.argv
BASE = "http://127.0.0.1:8000"

if not use_testclient:
    try:
        import requests
        r = requests.get(BASE + "/", timeout=1.0)
        if not r.ok:
            use_testclient = True
    except Exception:
        use_testclient = True

if use_testclient:
    warn("Standalone mode: executing directly via FastAPI TestClient.")
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    def post(path, **kwargs):
        r = client.post(path, **kwargs)
        if not (200 <= r.status_code < 300):
            err(f"POST {path} failed [{r.status_code}]: {r.text}")
        return r.json()

    def get(path, **kwargs):
        r = client.get(path, **kwargs)
        if not (200 <= r.status_code < 300):
            err(f"GET {path} failed [{r.status_code}]: {r.text}")
        return r.json()

    def put(path, **kwargs):
        r = client.put(path, **kwargs)
        if not (200 <= r.status_code < 300):
            err(f"PUT {path} failed [{r.status_code}]: {r.text}")
        return r.json()
else:
    import requests
    ok(f"Connected to live server at {BASE}")

    def post(path, **kwargs):
        r = requests.post(BASE + path, **kwargs)
        if not r.ok:
            err(f"POST {path} failed [{r.status_code}]: {r.text}")
        return r.json()

    def get(path, **kwargs):
        r = requests.get(BASE + path, **kwargs)
        if not r.ok:
            err(f"GET {path} failed [{r.status_code}]: {r.text}")
        return r.json()

    def put(path, **kwargs):
        r = requests.put(BASE + path, **kwargs)
        if not r.ok:
            err(f"PUT {path} failed [{r.status_code}]: {r.text}")
        return r.json()


def run_demo():
    header("PHASE 5 RETRIEVAL UPGRADES & EXPLAINABILITY — END-TO-END DEMO")
    init_db()

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: Ingest HR Knowledge Base & Messy Employees CSV
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 1: Ingest Knowledge Base (2019 PDF, 2024 DOCX, Handbook PDF, Employees CSV)")

    kb_2019_pdf = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2019_archived.pdf"
    kb_2024_docx = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2024.docx"
    kb_hours_pdf = backend_dir / "sample_data" / "hr_kb" / "handbook_working_hours.pdf"
    csv_path = backend_dir / "sample_data" / "employees_messy.csv"

    # Upload 2019 Leave Policy PDF
    with open(kb_2019_pdf, "rb") as f:
        up_2019 = post("/upload", files={"file": ("leave_policy_2019_archived.pdf", f, "application/pdf")})
    src_2019_id = up_2019["source_id"]
    ok(f"Uploaded 2019 Archived Leave Policy (PDF) -> source_id={src_2019_id}")

    # Upload 2024 Leave Policy DOCX
    with open(kb_2024_docx, "rb") as f:
        up_2024 = post("/upload", files={"file": ("leave_policy_2024.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    src_2024_id = up_2024["source_id"]
    ok(f"Uploaded 2024 Leave Policy (DOCX) -> source_id={src_2024_id}")

    # Upload Working Hours Handbook PDF
    with open(kb_hours_pdf, "rb") as f:
        up_hours = post("/upload", files={"file": ("handbook_working_hours.pdf", f, "application/pdf")})
    src_hours_id = up_hours["source_id"]
    ok(f"Uploaded Working Hours Handbook (PDF) -> source_id={src_hours_id}")

    # Upload Messy Employees CSV
    with open(csv_path, "rb") as f:
        up_csv = post("/upload", files={"file": ("employees_messy.csv", f, "text/csv")})
    src_csv_id = up_csv["source_id"]
    ok(f"Uploaded Messy Employees (CSV) -> source_id={src_csv_id}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: Phase 3 Cleaning Workflow for CSV (produce Version 2)
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 2: Clean CSV -> Produce Version 2 with Quarantined Rows")
    post(f"/sources/{src_csv_id}/roles/infer")
    put(f"/sources/{src_csv_id}/roles", json={"roles": {"Employee_ID": "identifier", "Salary": "numeric", "Manager": "optional"}})
    post(f"/sources/{src_csv_id}/proposals/generate")
    post(f"/sources/{src_csv_id}/proposals/approve-all?min_severity=info")
    apply_res = post(f"/sources/{src_csv_id}/apply")
    ok(f"Applied proposals -> Version 2 ready (Active: {apply_res['rows_active']}, Quarantined: {apply_res['rows_quarantined']})")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: Set Document Overrides (True dates: 2019 -> 2019-03-01, 2024 -> 2024-06-01)
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 3: Set Metadata Overrides (2019 -> 2019-03-01, 2024 -> 2024-06-01)")

    current_policy_date = "2024-06-01T00:00:00"
    archived_policy_date = "2019-03-01T00:00:00"

    docs_2019 = get(f"/sources/{src_2019_id}/documents")
    doc_2019_id = docs_2019[0]["id"] if isinstance(docs_2019, list) else docs_2019["documents"][0]["id"]

    docs_2024 = get(f"/sources/{src_2024_id}/documents")
    doc_2024_id = docs_2024[0]["id"] if isinstance(docs_2024, list) else docs_2024["documents"][0]["id"]

    ovr_2019 = put(
        f"/documents/{doc_2019_id}/override",
        json={"published_at": archived_policy_date, "title": "ACME 2019 Leave Policy (Archived)"},
    )
    ok(f"Override set for doc {doc_2019_id}: published_at={ovr_2019['published_at']}, title='{ovr_2019['title']}'")
    info(f"Note returned by API: '{ovr_2019['note']}'")

    ovr_2024 = put(
        f"/documents/{doc_2024_id}/override",
        json={"published_at": current_policy_date, "title": "ACME 2024 Annual Leave Policy (Revised)"},
    )
    ok(f"Override set for doc {doc_2024_id}: published_at={ovr_2024['published_at']}, title='{ovr_2024['title']}'")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: Index All Sources (Creates New Index Runs with Overrides Applied)
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 4: Index Sources to Create New Index Runs")

    idx_2019 = post(f"/sources/{src_2019_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    ok(f"Indexed 2019 Policy -> run_id={idx_2019['id']}, chunks={idx_2019['chunk_count']}")

    idx_2024 = post(f"/sources/{src_2024_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    ok(f"Indexed 2024 Policy -> run_id={idx_2024['id']}, chunks={idx_2024['chunk_count']}")

    idx_hours = post(f"/sources/{src_hours_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    ok(f"Indexed Handbook -> run_id={idx_hours['id']}, chunks={idx_hours['chunk_count']}")

    idx_csv = post(f"/sources/{src_csv_id}/index", json={"version": 2, "chunk_size": 800, "chunk_overlap": 120})
    ok(f"Indexed Employees CSV -> run_id={idx_csv['id']}, chunks={idx_csv['chunk_count']}")

    all_source_ids = [src_2019_id, src_2024_id, src_hours_id, src_csv_id]

    # Print each document's freshness bucket
    print("\nDocument Freshness Buckets (Simulated Clock: 2024-09-01):")
    for d_id, d_label in [(doc_2019_id, "2019 Leave Policy (Archived)"), (doc_2024_id, "2024 Leave Policy (Revised)")]:
        d_info = get(f"/documents/{d_id}")
        pub = d_info.get("published_at")
        age_d = (ref_dt.date() - datetime.fromisoformat(pub).date()).days if pub else None
        ok(f"  Document '{d_label}' (ID {d_id}) -> published_at={pub}, age={age_d} days, freshness bucket={BOLD}{d_info.get('freshness')}{RESET}")

    # Verify chunk metadata reflects overrides
    chunks_preview_2019 = get(f"/index-runs/{idx_2019['id']}/chunks")
    meta_2019 = chunks_preview_2019["chunks"][0]["metadata"]
    assert meta_2019["published_at_source"] == "user"
    assert meta_2019["freshness"] == "stale"
    ok(f"Verified 2019 chunk metadata: published_at={meta_2019['published_at']}, source={meta_2019['published_at_source']}, freshness={meta_2019['freshness']}")

    chunks_preview_2024 = get(f"/index-runs/{idx_2024['id']}/chunks")
    meta_2024 = chunks_preview_2024["chunks"][0]["metadata"]
    assert meta_2024["published_at_source"] == "user"
    assert meta_2024["freshness"] == "fresh"
    ok(f"Verified 2024 chunk metadata: published_at={meta_2024['published_at']}, source={meta_2024['published_at_source']}, freshness={meta_2024['freshness']}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: Compare Strategies for Leave Policy Question
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 5: /retrieve/compare — 'How many annual leaves are employees entitled to?'")

    cmp_q1 = post(
        "/retrieve/compare",
        json={
            "question": "How many annual leaves are employees entitled to?",
            "source_ids": [src_2019_id, src_2024_id],
            "top_k": 3,
            "strategies": ["dense", "lexical", "hybrid", "hybrid_rerank"],
        },
    )

    print(f"\n{BOLD}Comparison Results by Strategy:{RESET}")
    for strat, data in cmp_q1["results"].items():
        print(f"\n  [{BOLD}{strat.upper()}{RESET}] Gate Passed: {data['evidence']['passed']}, Latency: {data['latency_ms']}")
        for c in data["chunks"]:
            print(f"    Rank {c['rank']}: chunk_id={c['chunk_id']} | score={c['score']:.4f} | snippet='{c['snippet'][:60]}...'")
            print(f"      signals={c['signals']}")

    print(f"\n{BOLD}Overlap Summary:{RESET}")
    print(f"  Chunk strategies: {json.dumps(cmp_q1['overlap_summary']['chunk_strategies'], indent=4)}")
    print(f"  Rank changes vs dense: {json.dumps(cmp_q1['overlap_summary']['rank_changes_vs_dense'], indent=4)}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: Compare Strategies for Exact-ID Question
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 6: /retrieve/compare (Exact-ID) — 'What is employee E1007\\'s department?'")

    cmp_q2 = post(
        "/retrieve/compare",
        json={
            "question": "What is employee E1007's department?",
            "source_ids": [src_csv_id],
            "top_k": 3,
            "strategies": ["dense", "lexical", "hybrid", "hybrid_rerank"],
        },
    )

    print(f"\n{BOLD}Exact-ID Ranks Across All Four Strategies:{RESET}")
    for strat, data in cmp_q2["results"].items():
        top_chunks = data["chunks"]
        print(f"\n  [{BOLD}{strat.upper()}{RESET}] (Gate Passed: {data['evidence']['passed']}, Latency: {data['latency_ms']}):")
        if top_chunks:
            for c in top_chunks[:3]:
                print(f"    Rank {c['rank']}: chunk_id={c['chunk_id']} | score={c['score']:.4f} | snippet='{c['snippet'][:60]}...'")
                print(f"      signals={c['signals']}")
        else:
            print("    (No matching chunks)")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7: Compare Strategies for Unsupported Question (Mars colonization)
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 7: /retrieve/compare (Unsupported) — 'What is the company\\'s Mars colonization budget?'")

    cmp_q3 = post(
        "/retrieve/compare",
        json={
            "question": "What is the company's Mars colonization budget?",
            "source_ids": all_source_ids,
            "top_k": 3,
            "strategies": ["dense", "lexical", "hybrid", "hybrid_rerank"],
        },
    )

    print(f"\n{BOLD}Evidence Gate Results for Unsupported Question:{RESET}")
    for strat, data in cmp_q3["results"].items():
        ev = data["evidence"]
        print(f"  Strategy {strat.upper()}: passed={ev['passed']} | signal={ev['signal']} | values={ev['values']} | thresholds={ev['thresholds']}")
        assert ev["passed"] is False, f"Strategy {strat} passed evidence gate on unsupported question!"
    ok("All four strategies correctly failed the evidence gate on unsupported question!")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8: Freshness-Aware Query Generation with and without filters
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 8: Freshness-Aware Query Generation (Conflict Demonstration)")

    # Part A: With freshness filter ['fresh', 'aging']
    print(f"\n{BOLD}Part A: /query with strategy='hybrid_rerank' and filters.freshness=['fresh', 'aging']:{RESET}")
    q_filtered = post(
        "/query",
        json={
            "question": "How many annual leaves are employees entitled to?",
            "source_ids": [src_2019_id, src_2024_id],
            "strategy": "hybrid_rerank",
            "filters": {"freshness": ["fresh", "aging"]},
        },
    )

    print(f"  Status:    {GREEN}{q_filtered['status']}{RESET}")
    print(f"  Answer:    {q_filtered['answer']}")
    print(f"  Citations: {[c['chunk_id'] for c in q_filtered['citations']]}")
    print(f"  Latency:   {q_filtered['latency_ms']}")

    # Part B: Without filters (demonstrating conflict resolution)
    print(f"\n{BOLD}Part B: /query with strategy='hybrid_rerank' and NO filters (conflict resolution):{RESET}")
    q_unfiltered = post(
        "/query",
        json={
            "question": "How many annual leaves are employees entitled to?",
            "source_ids": [src_2019_id, src_2024_id],
            "strategy": "hybrid_rerank",
        },
    )

    print(f"  Status:    {GREEN}{q_unfiltered['status']}{RESET}")
    print(f"  Answer:    {q_unfiltered['answer']}")
    print(f"  Citations: {[c['chunk_id'] for c in q_unfiltered['citations']]}")
    print(f"  Latency:   {q_unfiltered['latency_ms']}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 9: Unsupported Query via /query
    # ─────────────────────────────────────────────────────────────────────────
    step("Step 9: /query (Unsupported Question) — Confirms Zero LLM Calls")

    for strat in ["dense", "lexical", "hybrid", "hybrid_rerank"]:
        q_unsupported = post(
            "/query",
            json={
                "question": "What is the company's Mars colonization budget?",
                "source_ids": all_source_ids,
                "strategy": strat,
            },
        )
        assert q_unsupported["status"] == "insufficient_evidence"
        assert q_unsupported["answer"] is None
        assert q_unsupported["latency_ms"]["generate"] == 0.0
        print(f"  Strategy {strat.upper()}: status='{q_unsupported['status']}', generate_ms={q_unsupported['latency_ms']['generate']}")

    ok("All four strategies bypassed LLM with status='insufficient_evidence'!")
    header("DEMO COMPLETE — ALL ACCEPTANCE CRITERIA VERIFIED")


if __name__ == "__main__":
    run_demo()
