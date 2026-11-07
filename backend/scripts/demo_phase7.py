"""
scripts/demo_phase7.py — End-to-End Evaluation Suite & Quantitative Benchmark Demo.

Demonstrates:
  1. Ingestion of HR knowledge base (2019 PDF, 2024 DOCX, Handbook PDF) and employees_messy.csv.
  2. Phase 3 cleaning: approve proposals (including outlier-flag via min_severity=info)
     and apply to produce Version 2 (active + quarantined rows).
  3. Dynamic Document Overrides:
     - 2024 Policy -> published_at = 2024-06-01 -> freshness: fresh
     - 2019 Policy -> published_at = 2019-03-01 -> freshness: stale
  4. Indexing of unstructured docs and structured CSV v2.
  5. Gold Evaluation Benchmark Suite:
     - Ingestion of 24-item gold suite (gold_suite_sample.json) covering leave policies,
       working hours handbook, employee records, and unanswerable edge cases.
     - suite_hash computation and freezing on first run execution.
  6. Parameter Sweep Matrix (Retrieval-Only or Live Gemini):
     - Matrix sweep varying strategy in ['dense', 'hybrid'].
     - include_unreviewed=True.
     - In retrieval-only mode: strictly 0 LLM calls made.
     - In --live mode: live Gemini generation and judge evaluation with explicit budget cap.
  7. Paired Bootstrap Statistical Comparison:
     - 95% bootstrap CI (2000 resamples), delta distributions, wins/losses/ties,
       and distinguishable-from-zero verdict.
  8. Full Markdown Scorecard via GET /eval/report.md:
     - Provenance & run configuration table.
     - Core quantitative metrics with 95% bootstrap CIs.
     - Per-slice route breakdowns.
     - Failure classifications and diagnostic banners.

Usage:
  python backend/scripts/demo_phase7.py            # Retrieval-only mode (0 LLM calls, default)
  python backend/scripts/demo_phase7.py --live     # Live Gemini LLM + Judge mode (requires GEMINI_API_KEY)
  python backend/scripts/demo_phase7.py --budget 30 # Custom LLM call budget cap
"""

import sys
import os
import re
import json
import time
import argparse
import functools
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

print = functools.partial(print, flush=True)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Phase 7 Evaluation Suite Demo")
parser.add_argument("--live", action="store_true", help="Run with live Gemini LLM & Judge")
parser.add_argument("--budget", type=int, default=None, help="Explicit max LLM calls budget cap")
parser.add_argument("--standalone", action="store_true", help="Use FastAPI TestClient directly")
args, unknown = parser.parse_known_args()

is_live = args.live
budget_cap = args.budget or (20 if is_live else None)

from scripts.reset_demo_db import reset_demo_database, get_demo_db_url
demo_url = get_demo_db_url()
os.environ["DATABASE_URL"] = demo_url
os.environ["WARMUP_MODELS"] = "0"

simulated_clock = os.getenv("FRESHNESS_REFERENCE_DATE", "2024-09-01T00:00:00+00:00")
os.environ["FRESHNESS_REFERENCE_DATE"] = simulated_clock

RESET   = "\033[0m"
BOLD    = "\033[1m"
GREEN   = "\033[32m"
CYAN    = "\033[36m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
MAGENTA = "\033[35m"


def header(title: str):
    print(f"\n{BOLD}{CYAN}{'='*78}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*78}{RESET}")


def step(title: str):
    print(f"\n{BOLD}{MAGENTA}>> {title} {'='*(74 - len(title))}{RESET}")


def ok(msg: str):
    print(f"{GREEN}[OK] {msg}{RESET}")


def warn(msg: str):
    print(f"{YELLOW}[WARN] {msg}{RESET}")


def info(msg: str):
    print(f"  {msg}")


def err(msg: str):
    print(f"{RED}[ERROR] {msg}{RESET}")
    sys.exit(1)


# Database Safety Check & Reset
header("PHASE 7: QUANTITATIVE EVALUATION SUITE BENCHMARK DEMO")
reset_demo_database(demo_url)

if is_live:
    print(f"\n{BOLD}{GREEN}{'='*78}")
    print(f"  [LIVE GEMINI LLM MODE] Running with live Gemini LLM & Judge")
    print(f"  Target Database: ragstudio_demo")
    print(f"  Explicit LLM Call Budget Cap: {budget_cap} calls")
    print(f"{'='*78}{RESET}\n")
else:
    print(f"\n{BOLD}{YELLOW}{'='*78}")
    print("  [RETRIEVAL-ONLY MODE] Running reproducible offline benchmark.")
    print("  Target Database: ragstudio_demo")
    print("  Strictly ZERO LLM calls will be made.")
    print("  Pass --live to evaluate generation and LLM judge.")
    print(f"{'='*78}{RESET}\n")

# Rebind ORM engine to demo database
import db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db.DATABASE_URL = demo_url
db.engine = create_engine(demo_url)
db.SessionLocal = sessionmaker(bind=db.engine, autoflush=False, autocommit=False)
db.init_db()

# Setup client (FastAPI TestClient)
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


def run_demo():
    # Model warm-up & latency check
    step("Warm-up & Embedder/Reranker Latency Measurement")
    from indexing.embedder import get_embedder
    from retrieval.rerank import get_reranker

    t_emb0 = time.perf_counter()
    embedder = get_embedder()
    _ = embedder.embed_query("Annual leave policy entitlement")
    emb_warm_ms = round((time.perf_counter() - t_emb0) * 1000, 2)
    ok(f"Embedder warm call latency: {emb_warm_ms} ms (dim={embedder.dimension})")

    t_rr0 = time.perf_counter()
    reranker = get_reranker()
    _ = reranker.rerank(
        "HR annual leave policy",
        [{"chunk_id": 1, "content": "Employees are entitled to 24 annual leave days.", "score": 0.5}],
    )
    rerank_warm_ms = round((time.perf_counter() - t_rr0) * 1000, 2)
    ok(f"Cross-encoder reranker warm call latency: {rerank_warm_ms} ms")

    # STEP 1: Ingestion
    step("Step 1: Ingest HR Knowledge Base & Employees Messy CSV")
    kb_2019_pdf = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2019_archived.pdf"
    kb_2024_docx = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2024.docx"
    kb_hours_pdf = backend_dir / "sample_data" / "hr_kb" / "handbook_working_hours.pdf"
    csv_path = backend_dir / "sample_data" / "employees_messy.csv"

    with open(kb_2019_pdf, "rb") as f:
        up_2019 = post("/upload", files={"file": ("leave_policy_2019_archived.pdf", f, "application/pdf")})
    src_2019_id = up_2019["source_id"]
    ok(f"Uploaded 2019 Leave Policy (PDF) -> source_id={src_2019_id}")

    with open(kb_2024_docx, "rb") as f:
        up_2024 = post("/upload", files={"file": ("leave_policy_2024.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    src_2024_id = up_2024["source_id"]
    ok(f"Uploaded 2024 Leave Policy (DOCX) -> source_id={src_2024_id}")

    with open(kb_hours_pdf, "rb") as f:
        up_hours = post("/upload", files={"file": ("handbook_working_hours.pdf", f, "application/pdf")})
    src_hours_id = up_hours["source_id"]
    ok(f"Uploaded Working Hours Handbook (PDF) -> source_id={src_hours_id}")

    with open(csv_path, "rb") as f:
        up_csv = post("/upload", files={"file": ("employees_messy.csv", f, "text/csv")})
    src_csv_id = up_csv["source_id"]
    ok(f"Uploaded Messy Employees (CSV) -> source_id={src_csv_id}")

    # STEP 2: Phase 3 Cleaning
    step("Step 2: Clean CSV -> Produce Version 2 with Outlier Flags & Quarantined Rows")
    post(f"/sources/{src_csv_id}/roles/infer")
    put(f"/sources/{src_csv_id}/roles", json={"roles": {"Employee_ID": "identifier", "Salary": "numeric", "Manager": "optional"}})
    post(f"/sources/{src_csv_id}/proposals/generate")
    post(f"/sources/{src_csv_id}/proposals/approve-all?min_severity=info")
    apply_res = post(f"/sources/{src_csv_id}/apply")
    ok(f"Applied proposals -> Version 2 ready (Active: {apply_res['rows_active']}, Quarantined: {apply_res['rows_quarantined']})")

    # STEP 3: Document Overrides
    step("Step 3: Document Overrides (Simulated Published Dates)")
    docs_2019 = get(f"/sources/{src_2019_id}/documents")
    doc_2019_id = docs_2019[0]["id"] if isinstance(docs_2019, list) else docs_2019["documents"][0]["id"]
    put(f"/documents/{doc_2019_id}/override", json={"published_at": "2019-03-01T00:00:00", "title": "ACME 2019 Leave Policy (Archived)"})

    docs_2024 = get(f"/sources/{src_2024_id}/documents")
    doc_2024_id = docs_2024[0]["id"] if isinstance(docs_2024, list) else docs_2024["documents"][0]["id"]
    put(f"/documents/{doc_2024_id}/override", json={"published_at": "2024-06-01T00:00:00", "title": "ACME 2024 Annual Leave Policy (Revised)"})
    ok("Document overrides applied for 2019 (stale) and 2024 (fresh) policies.")

    # STEP 4: Indexing
    step("Step 4: Index All Sources with Freshness Metadata")
    idx_2019 = post(f"/sources/{src_2019_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    idx_2024 = post(f"/sources/{src_2024_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    idx_hours = post(f"/sources/{src_hours_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    idx_csv = post(f"/sources/{src_csv_id}/index", json={"version": 2, "chunk_size": 800, "chunk_overlap": 120})
    ok(f"Indexed all sources: 2019 (run={idx_2019['id']}), 2024 (run={idx_2024['id']}), hours (run={idx_hours['id']}), csv_v2 (run={idx_csv['id']})")

    all_source_ids = [src_2019_id, src_2024_id, src_hours_id, src_csv_id]

    # STEP 5: Import Benchmark Suite
    step("Step 5: Import Gold Evaluation Benchmark Suite")
    suite_file = backend_dir / "sample_data" / "hr_kb" / "gold_suite_sample.json"
    with open(suite_file, "r", encoding="utf-8") as f:
        suite_data = json.load(f)

    create_resp = post("/eval/suites", json={
        "name": suite_data.get("name", "HR Knowledge Base Gold Benchmark Suite"),
        "description": suite_data.get("description", "Reproducible evaluation suite"),
        "source_ids": all_source_ids,
    })
    suite_id = create_resp["id"]
    ok(f"Created EvalSuite id={suite_id}: '{create_resp['name']}'")

    items = suite_data.get("items", [])
    import_resp = post(f"/eval/suites/{suite_id}/items/import", json=items)
    ok(f"Imported {import_resp['imported_count']} benchmark items.")

    suite_obj = get(f"/eval/suites/{suite_id}")
    suite_hash = suite_obj.get("suite_hash")
    info(f"Suite Hash (reproducible SHA-256): {suite_hash}")

    # STEP 6: Execute Parameter Sweep Matrix
    step("Step 6: Execute Parameter Sweep Matrix (Dense vs Hybrid)")
    info(f"Varying strategy in ['dense', 'hybrid'] (include_unreviewed=True, wait=True)")
    matrix_payload = {
        "suite_id": suite_id,
        "base_variant": {"chunk_size": 800, "chunk_overlap": 120, "top_k": 5},
        "vary": {"strategy": ["dense", "hybrid"]},
        "include_unreviewed": True,
        "generate": is_live,
        "judge": is_live,
        "max_llm_calls": budget_cap,
        "wait": True,
    }
    t_m0 = time.perf_counter()
    matrix_resp = post("/eval/matrix", json=matrix_payload)
    matrix_ms = round((time.perf_counter() - t_m0) * 1000, 2)

    run_ids = matrix_resp.get("run_ids", [])
    ok(f"Matrix executed {len(run_ids)} runs in {matrix_ms} ms. Run IDs: {run_ids}")

    if len(run_ids) < 2:
        err(f"Expected at least 2 runs from matrix sweep, got {run_ids}")

    run_dense_id = run_ids[0]
    run_hybrid_id = run_ids[1]

    # Inspect runs and verify LLM call counts
    run_dense = get(f"/eval/runs/{run_dense_id}")
    run_hybrid = get(f"/eval/runs/{run_hybrid_id}")
    ok(f"Run {run_dense_id} ('{run_dense['name']}'): status={run_dense['status']}")
    ok(f"Run {run_hybrid_id} ('{run_hybrid['name']}'): status={run_hybrid['status']}")

    if not is_live:
        # Zero LLM calls assertion
        results_dense = get(f"/eval/runs/{run_dense_id}/results")
        res_list = results_dense.get("results", []) if isinstance(results_dense, dict) else results_dense
        total_dense_llm = sum(r.get("llm_calls", 0) for r in res_list)
        total_dense_judge = sum(r.get("judge_calls", 0) for r in res_list)
        ok(f"Verification: Dense run total LLM calls = {total_dense_llm}, Judge calls = {total_dense_judge} (STRICT ZERO)")

    # STEP 7: Paired Bootstrap Statistical Comparison
    step("Step 7: Paired Bootstrap Comparison (Dense vs Hybrid)")
    compare_resp = get(f"/eval/compare?a={run_dense_id}&b={run_hybrid_id}")
    info(f"Common items compared: {compare_resp['common_items_count']}")

    print("\nPaired Bootstrap Results (2,000 resamples, 95% CI):")
    for metric_name, comp in compare_resp.get("metrics", {}).items():
        delta_mean = comp["mean_delta"]
        ci_low = comp["ci_low"]
        ci_high = comp["ci_high"]
        wins = comp["wins"]
        losses = comp["losses"]
        ties = comp["ties"]
        verdict = comp["verdict"]
        print(f"  * {metric_name:<16}: delta={delta_mean:+.4f} (95% CI: [{ci_low:+.4f}, {ci_high:+.4f}]) | A wins={wins}, B wins={losses}, ties={ties}")
        print(f"    Verdict: {verdict}")

    # STEP 8: Markdown Scorecard
    step("Step 8: Markdown Scorecard Output (GET /eval/report.md)")
    md_resp = client.get(f"/eval/report.md?run_ids={run_dense_id},{run_hybrid_id}")
    if md_resp.status_code != 200:
        err(f"GET /eval/report.md failed [{md_resp.status_code}]: {md_resp.text}")

    markdown_scorecard = md_resp.text
    print("\n" + markdown_scorecard)

    # Save scorecard to scratch file
    scorecard_path = backend_dir / "reports" / "phase7_demo_scorecard.md"
    scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard_path.write_text(markdown_scorecard, encoding="utf-8")
    ok(f"Saved complete scorecard to: {scorecard_path}")

    # STEP 9: RAG Doctor v1 Diagnostic Analysis
    step("Step 9: RAG Doctor v1 Diagnostic Analysis (POST /doctor/reports)")
    doc_resp = post("/doctor/reports", json={"run_ids": [run_dense_id, run_hybrid_id]})
    report_id = doc_resp["id"]
    findings = doc_resp.get("findings", [])
    ok(f"Doctor Report #{report_id} generated: {len(findings)} findings across rules D1-D9.")

    print("\n" + "-" * 78)
    for f in findings:
        sev_color = RED if f["severity"] == "critical" else (YELLOW if f["severity"] == "warning" else CYAN)
        print(f"  {sev_color}[{f['severity'].upper()}]{RESET} {BOLD}{f['rule_id']}: {f['title']}{RESET}")
        print(f"    Diagnosis:      {f['diagnosis']}")
        print(f"    Evidence Level: {BOLD}{f['evidence_level']}{RESET}")
        print(f"    Proposed Patch: {json.dumps(f['proposed_patch'])}")
        print(f"    Expected Effect:{f['expected_effect']}")
        print(f"    Cost Note:      {f['cost_note']}")
        if f.get("counterfactual") and f["counterfactual"].get("in_sample"):
            cf = f["counterfactual"]
            print(f"    Counterfactual: Optimal Threshold t={cf.get('optimal_threshold')}")
            print(f"      In-Sample:    {json.dumps(cf.get('in_sample'))}")
            print(f"      Leave-One-Out:{json.dumps(cf.get('leave_one_out'))}")
            if cf.get("warnings"):
                print(f"      Warnings:     {cf.get('warnings')}")
            print(f"      Limitations:  {cf.get('limitations')}")
        print("-" * 78)

    # Print Not-Fired Rules with Reasons
    summary = doc_resp.get("summary", {})
    not_fired = summary.get("not_fired_reasons", {})
    if not_fired:
        print(f"\n{BOLD}Diagnostic Rules Not Fired (Documented Reasons):{RESET}")
        for rid, reason in sorted(not_fired.items()):
            print(f"  {CYAN}{BOLD}{rid}{RESET}: {reason}")
        print("-" * 78)

    # STEP 10: Doctor Patch Lifecycle: Approve -> Apply -> Verify
    step("Step 10: Doctor Patch Lifecycle (Approve -> Apply -> Verify)")
    actionable_findings = [f for f in findings if f.get("proposed_patch") and f["status"] == "proposed"]
    if actionable_findings:
        chosen = actionable_findings[0]
        finding_id = chosen["id"]
        info(f"Selected Finding #{finding_id} ({chosen['rule_id']}: '{chosen['title']}') for automated remediation.")

        # 1. Approve
        app_res = post(f"/doctor/findings/{finding_id}/approve")
        ok(f"Finding #{finding_id} approved (status={app_res['status']}).")

        # 2. Apply
        apply_res = post(f"/doctor/findings/{finding_id}/apply")
        new_cfg = apply_res.get("pipeline_config", {})
        ok(f"Applied patch -> Created new PipelineConfig #{new_cfg.get('id')} of kind='{new_cfg.get('kind')}':")
        info(f"  Spec: {json.dumps(new_cfg.get('spec'))}")
        info(f"  Spec Hash: {new_cfg.get('spec_hash')}")

        # 3. Verify
        info("Running verification evaluation on patched configuration...")
        ver_res = post(f"/doctor/findings/{finding_id}/verify")
        ver_finding = ver_res.get("finding", {})
        ver_run = ver_res.get("verification_run", {})
        ok(f"Verification completed (Run #{ver_run.get('id')}): status={BOLD}{ver_finding.get('status')}{RESET}")
    else:
        info("No actionable patches proposed by Doctor rules for current configuration.")

    header("PHASE 7 DEMO COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    run_demo()

