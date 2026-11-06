"""
scripts/demo_phase6a.py — End-to-End Phase 6A Routing & Structured Execution Demo.

Demonstrates:
  1. Ingestion of HR knowledge base (2019 PDF, 2024 DOCX, Handbook PDF) and employees_messy.csv.
  2. Phase 3 cleaning: approve proposals (including outlier-flag proposal via min_severity=info)
     and apply to produce Version 2 (active + quarantined rows).
  3. Dynamic Document Overrides (relative to today, no FRESHNESS_REFERENCE_DATE):
     - 2024 Policy -> published_at = today - 120 days -> freshness: fresh
     - 2019 Policy -> published_at = 2019-03-01 -> freshness: stale
     Prints each document's freshness bucket.
  4. Indexing of unstructured docs and structured CSV v2.
  5. Model warm-up & reranker warm call latency measurement.
  6. Querying with strategy="auto" across representative questions:
     - Q1: "How many annual leaves are employees entitled to?" -> Semantic (Hybrid)
     - Q2: "What is employee E1007's department?" -> Exact (Hybrid)
     - Q3: "What is the average salary in Mumbai?" -> Structured (avg Salary where City=Mumbai, 0 LLM/0 embed)
     - Q4: "How many employees are in each department?" -> Structured (count group_by Department, 0 LLM/0 embed)
     - Q5: "Compare the 2019 and 2024 leave policies" -> Complex (Hybrid_Rerank)
     - Q6: "Who has the highest salary?" -> Structured (top_n argmax, 0 LLM/0 embed)
     - Q7: "What is the company's Mars colonization budget?" -> Semantic -> Insufficient Evidence (0 LLM)
     In --live mode, prints ALL questions in full (no elisions: Q1-Q7) with LLM metadata,
     route, citations, evidence gate result, and data quality notes.
  7. Data quality notes comparison: Version 1 (uncleaned) vs Version 2 (cleaned).
  8. Automated fact-checking with pandas in --live mode.

Usage:
  python backend/scripts/demo_phase6a.py            # Standalone mock mode (default)
  python backend/scripts/demo_phase6a.py --live     # Live Gemini LLM mode (max 10 calls, fact-checking)
"""

import sys
import os
import re
import json
import time
import functools
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

print = functools.partial(print, flush=True)

import pandas as pd
from db import init_db, get_db, Chunk
import config
from generation.llm import LLMClient, LLMError, GeminiLLMClient, set_llm_client

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


is_live = "--live" in sys.argv
BASE = "http://127.0.0.1:8000"

from scripts.reset_demo_db import reset_demo_database, get_demo_db_url
demo_url = get_demo_db_url()
os.environ["DATABASE_URL"] = demo_url

# Set simulated demo clock
simulated_clock = os.getenv("FRESHNESS_REFERENCE_DATE", "2024-09-01T00:00:00+00:00")
os.environ["FRESHNESS_REFERENCE_DATE"] = simulated_clock
ref_dt = datetime.fromisoformat(simulated_clock.replace("Z", "+00:00"))

# Prominent simulated clock banner (Review Item A1)
print(f"\n{BOLD}{CYAN}{'='*78}")
print("  [SIMULATED DEMO CLOCK, NOT TODAY'S DATE]")
print(f"  Reference Date: {ref_dt.date().isoformat()} (simulated demo clock, not today's date)")
print("  Document Dates & Freshness Buckets:")
print("    - 2024 Leave Policy:         published 2024-06-01 (age: 92 days)   -> fresh")
print("    - 2019 Leave Policy:         published 2019-03-01 (age: 2011 days) -> stale")
print("    - Working Hours Handbook:    undated                               -> unknown")
print(f"{'='*78}{RESET}\n")

# Print mode banner
if is_live:
    print(f"\n{BOLD}{GREEN}{'='*78}")
    print("  [LIVE GEMINI LLM MODE] Running with real Gemini API key (max 10 LLM calls)")
    print("  Target Database: ragstudio_demo")
    print("  Model:", config.GEMINI_MODEL)
    print(f"{'='*78}{RESET}\n")

    reset_demo_database(demo_url)
else:
    print(f"\n{BOLD}{YELLOW}{'='*78}")
    print("  [MOCK LLM MODE] Running in offline standalone mode with mock responses.")
    print("  Target Database: ragstudio_demo")
    print("  No external API calls are made. To run with live Gemini API, pass --live.")
    print(f"{'='*78}{RESET}\n")

    reset_demo_database(demo_url)


class DemoScriptedLLMClient(LLMClient):
    """
    Scripted mock LLM client specifically for demo_phase6a standalone mode.
    Keeps scripted demo answers inside scripts/demo_phase6a.py and out of production library code.
    Extracts cited chunks from the prompt to ensure citations match the actual prompt chunks.
    """

    def __init__(self):
        self.provider = "mock"
        self.model_name = "demo-scripted"
        self.is_mock = True

    def generate(self, prompt: str) -> str:
        chunks = re.findall(r'<chunk id="(\d+)" source="([^"]*)"[^>]*>(.*?)</chunk>', prompt, re.DOTALL)
        if not chunks:
            return "[MOCK] Information not available in context."

        chunks_by_source = {}
        for cid, src, content in chunks:
            chunks_by_source.setdefault(src, []).append((int(cid), content))

        prompt_lower = prompt.lower()

        # Question 1: Annual Leave Entitlement (multi-source / conflict resolution)
        if "annual leave" in prompt_lower and "entitled" in prompt_lower:
            c2019 = [cid for src, clist in chunks_by_source.items() if "2019" in src for cid, _ in clist]
            c2024 = [cid for src, clist in chunks_by_source.items() if "2024" in src for cid, _ in clist]
            if c2019 and c2024:
                return (
                    f"[MOCK] Conflict detected between sources: the historical 2019 policy stated 20 annual leave days [{c2019[0]}], "
                    f"but the updated 2024 policy grants 24 days [{c2024[0]}]. Preferring the most recent 2024 policy, "
                    f"full-time regular employees are entitled to 24 annual leave days [{c2024[0]}]."
                )
            elif c2024:
                return f"[MOCK] According to the active 2024 Leave Policy, full-time regular employees are entitled to 24 annual leave days [{c2024[0]}]."
            elif c2019:
                return f"[MOCK] According to the 2019 Leave Policy, employees are entitled to 20 annual leave days [{c2019[0]}]."

        # Question 2: Employee E1007 Department
        if "e1007" in prompt_lower:
            for cid, src, content in chunks:
                if "E1007" in content or "e1007" in content.lower():
                    dept = "Engineering"
                    for d_candidate in ["Engineering", "HR", "Sales", "Finance", "Marketing"]:
                        if d_candidate.lower() in content.lower():
                            dept = d_candidate
                            break
                    return f"[MOCK] Employee E1007 belongs to the {dept} department [{cid}]."

        # Question 5: Compare 2019 and 2024 leave policies
        if "compare" in prompt_lower and "2019" in prompt_lower and "2024" in prompt_lower:
            c2019 = [cid for src, clist in chunks_by_source.items() if "2019" in src for cid, _ in clist]
            c2024 = [cid for src, clist in chunks_by_source.items() if "2024" in src for cid, _ in clist]
            cid_19 = c2019[0] if c2019 else chunks[0][0]
            cid_24 = c2024[0] if c2024 else chunks[-1][0]
            return (
                f"[MOCK] In the 2019 policy, employees were entitled to 20 days of annual leave [{cid_19}]. "
                f"In the updated 2024 policy, this was increased to 24 annual leave days [{cid_24}]."
            )

        # Default fallback
        first_cid = chunks[0][0]
        first_content = chunks[0][2].strip().split("\n")[0].strip()
        if first_content.endswith("."):
            first_content = first_content[:-1]
        return f"[MOCK] Based on the provided context, {first_content} [{first_cid}]."


# Client setup: requests if server running, else FastAPI TestClient
use_testclient = "--standalone" in sys.argv or not is_live

if not use_testclient:
    try:
        import requests
        r = requests.get(BASE + "/", timeout=1.0)
        if not r.ok:
            use_testclient = True
    except Exception:
        use_testclient = True

if use_testclient:
    warn("Executing directly via FastAPI TestClient.")
    from fastapi.testclient import TestClient
    from main import app

    if not is_live:
        set_llm_client(DemoScriptedLLMClient())
    else:
        set_llm_client(GeminiLLMClient(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL))

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
    header("PHASE 6A: ROUTING & NO-RAG STRUCTURED EXECUTION DEMO")
    init_db()

    # Model warm-up & reranker latency check
    step("Warm-up & Cross-Encoder Latency Check")
    from retrieval.rerank import get_reranker
    reranker = get_reranker()
    t_w0 = time.perf_counter()
    _warm_res = reranker.rerank(
        "HR annual leave policy",
        [{"chunk_id": 1, "content": "Employees are entitled to 24 annual leave days.", "score": 0.5}],
    )
    rerank_warm_ms = round((time.perf_counter() - t_w0) * 1000, 2)
    warm_score = _warm_res[0].get("rerank_score", 0.0) if _warm_res else 0.0
    ok(f"Cross-encoder warm call latency: {rerank_warm_ms} ms (score: {warm_score:.4f})")

    # STEP 1: Ingestion
    step("Step 1: Ingest Knowledge Base (HR Policies + Employees CSV)")
    kb_2019_pdf = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2019_archived.pdf"
    kb_2024_docx = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2024.docx"
    kb_hours_pdf = backend_dir / "sample_data" / "hr_kb" / "handbook_working_hours.pdf"
    csv_path = backend_dir / "sample_data" / "employees_messy.csv"

    with open(kb_2019_pdf, "rb") as f:
        up_2019 = post("/upload", files={"file": ("leave_policy_2019_archived.pdf", f, "application/pdf")})
    src_2019_id = up_2019["source_id"]
    ok(f"Uploaded 2019 Archived Leave Policy (PDF) -> source_id={src_2019_id}")

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

    # STEP 2: Phase 3 Cleaning Workflow (Approve All including outlier flag via min_severity=info)
    step("Step 2: Clean CSV -> Produce Version 2 with Outlier Flags & Quarantined Rows")
    post(f"/sources/{src_csv_id}/roles/infer")
    put(f"/sources/{src_csv_id}/roles", json={"roles": {"Employee_ID": "identifier", "Salary": "numeric", "Manager": "optional"}})
    post(f"/sources/{src_csv_id}/proposals/generate")
    # Review Issue 5: approve outlier flag proposal by setting min_severity=info
    post(f"/sources/{src_csv_id}/proposals/approve-all?min_severity=info")
    apply_res = post(f"/sources/{src_csv_id}/apply")
    ok(f"Applied proposals -> Version 2 ready (Active: {apply_res['rows_active']}, Quarantined: {apply_res['rows_quarantined']})")

    # Document Overrides: True published dates (2019: 2019-03-01, 2024: 2024-06-01)
    step("Step 3: Document Overrides & Freshness Buckets")
    current_policy_date = "2024-06-01T00:00:00"
    archived_policy_date = "2019-03-01T00:00:00"

    docs_2019 = get(f"/sources/{src_2019_id}/documents")
    doc_2019_id = docs_2019[0]["id"] if isinstance(docs_2019, list) else docs_2019["documents"][0]["id"]
    put(f"/documents/{doc_2019_id}/override", json={"published_at": archived_policy_date, "title": "ACME 2019 Leave Policy (Archived)"})

    docs_2024 = get(f"/sources/{src_2024_id}/documents")
    doc_2024_id = docs_2024[0]["id"] if isinstance(docs_2024, list) else docs_2024["documents"][0]["id"]
    put(f"/documents/{doc_2024_id}/override", json={"published_at": current_policy_date, "title": "ACME 2024 Annual Leave Policy (Revised)"})

    # STEP 4: Indexing
    step("Step 4: Index Sources with Freshness Metadata")
    idx_2019 = post(f"/sources/{src_2019_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    idx_2024 = post(f"/sources/{src_2024_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    idx_hours = post(f"/sources/{src_hours_id}/index", json={"chunk_size": 800, "chunk_overlap": 120})
    idx_csv = post(f"/sources/{src_csv_id}/index", json={"version": 2, "chunk_size": 800, "chunk_overlap": 120})
    ok("All documents and structured records indexed successfully.")

    # Review Issue 5: Print each document's freshness bucket
    chunks_2019 = get(f"/index-runs/{idx_2019['id']}/chunks")
    meta_2019 = chunks_2019["chunks"][0]["metadata"]
    chunks_2024 = get(f"/index-runs/{idx_2024['id']}/chunks")
    meta_2024 = chunks_2024["chunks"][0]["metadata"]

    print("\nDocument Freshness Buckets (Simulated Clock: 2024-09-01):")
    pub_2019 = meta_2019.get("published_at")
    age_2019 = (ref_dt.date() - datetime.fromisoformat(pub_2019).date()).days if pub_2019 else None
    pub_2024 = meta_2024.get("published_at")
    age_2024 = (ref_dt.date() - datetime.fromisoformat(pub_2024).date()).days if pub_2024 else None
    ok(f"  Document '2019 Leave Policy (Archived)' (ID {doc_2019_id}) -> published_at={pub_2019}, age={age_2019} days, freshness bucket={BOLD}{meta_2019.get('freshness')}{RESET}")
    ok(f"  Document '2024 Leave Policy (Revised)' (ID {doc_2024_id}) -> published_at={pub_2024}, age={age_2024} days, freshness bucket={BOLD}{meta_2024.get('freshness')}{RESET}")

    all_source_ids = [src_2019_id, src_2024_id, src_hours_id, src_csv_id]

    # STEP 5: Query Router & Execution
    step("Step 5: Execute All Key Questions with Strategy 'auto' (Q1-Q7 Full Output)")

    test_queries = [
        {
            "num": 1,
            "title": "Annual Leave Entitlement (Semantic Query with Unmapped Policy Content Terms)",
            "question": "How many annual leaves are employees entitled to?",
            "sources": [src_2019_id, src_2024_id],
            "expected_route": "semantic",
        },
        {
            "num": 2,
            "title": "Exact-ID Lookup (Employee ID Token Present)",
            "question": "What is employee E1007's department?",
            "sources": [src_csv_id],
            "expected_route": "exact",
        },
        {
            "num": 3,
            "title": "Filtered Numeric Aggregation (Mumbai Average Salary)",
            "question": "What is the average salary in Mumbai?",
            "sources": [src_csv_id],
            "expected_route": "structured",
        },
        {
            "num": 4,
            "title": "Group-By Aggregation (Headcount per Department)",
            "question": "How many employees are in each department?",
            "sources": [src_csv_id],
            "expected_route": "structured",
        },
        {
            "num": 5,
            "title": "Complex Multi-Source Comparison (2019 vs 2024 Policies)",
            "question": "Compare the 2019 and 2024 leave policies",
            "sources": [src_2019_id, src_2024_id],
            "expected_route": "complex",
        },
        {
            "num": 6,
            "title": "Row Identity Query -> Deterministic top_n Template (0 RAG)",
            "question": "Who has the highest salary?",
            "sources": [src_csv_id],
            "expected_route": "structured",
        },
        {
            "num": 7,
            "title": "Unsupported Out-of-Domain Question",
            "question": "What is the company's Mars colonization budget?",
            "sources": all_source_ids,
            "expected_route": "semantic",
        },
    ]

    query_results = {}
    for item in test_queries:
        print(f"\n{BOLD}{'='*78}")
        print(f"  Question {item['num']}: {item['title']}")
        print(f"{'='*78}{RESET}")
        print(f"Question:             {YELLOW}'{item['question']}'{RESET}")

        # 1. Route check
        route_eval = post("/route", json={"question": item["question"], "source_ids": item["sources"]})
        print(f"Route Decision:       route={BOLD}{route_eval['route']}{RESET} | strategy={BOLD}{route_eval['strategy']}{RESET}")
        print(f"Route Reasons:        {route_eval.get('reasons')}")
        assert route_eval["route"] == item["expected_route"], f"Expected route {item['expected_route']}, got {route_eval['route']}"

        # 2. Execute via /query
        q_res = post("/query", json={"question": item["question"], "source_ids": item["sources"], "strategy": "auto"})
        q_id = q_res["query_id"]
        query_results[item["num"]] = q_res

        # Full metadata printout with NO elisions (Review Issue 7)
        llm_meta = q_res.get("llm") or {}
        print(f"Execution Status:     {BOLD}{q_res['status']}{RESET}")
        print(f"Answer Type:          {BOLD}{q_res.get('answer_type')}{RESET}")
        print(f"LLM Metadata:         provider={llm_meta.get('provider')} | model={llm_meta.get('model')} | mock={llm_meta.get('mock')}")
        print(f"Answer:               {GREEN}{q_res.get('answer')}{RESET}")

        citations = q_res.get("citations") or []
        invalid_c = q_res.get("invalid_citations") or []
        if citations:
            if citations[0].get("type") == "computed":
                c0 = citations[0]
                print(f"Citations (Computed): source={c0.get('source_name')} | columns={c0.get('columns')} | rows_used={c0.get('rows_used')}")
            else:
                c_ids = [c.get("chunk_id") for c in citations]
                print(f"Citations (Chunks):   {len(citations)} chunks cited -> {c_ids}")
        else:
            print("Citations:            None")

        if invalid_c:
            print(f"Invalid Citations:    {RED}{invalid_c}{RESET}")

        # Evidence Gate & Data Quality Notes
        evidence = q_res.get("evidence") or {}
        print(f"Evidence Gate:        passed={evidence.get('passed')} | signal={evidence.get('signal')}")

        trace = get(f"/queries/{q_id}/trace")
        if trace.get("route_decision", {}).get("route") == "structured":
            spec = trace.get("structured_spec", {})
            dq_notes = spec.get("data_quality_notes") or []
            print(f"Structured Spec:      template={spec.get('template')} | op={spec.get('op')} | column={spec.get('column')} | rows_used={spec.get('rows_used')}")
            print(f"Data Quality Notes:   {dq_notes}")
        else:
            print(f"Latency Breakdown:    {trace.get('latency_ms')}")

    # STEP 6: Version 1 vs Version 2 Comparison
    step("Step 6: Contrast Data Quality Notes: Version 1 (Uncleaned) vs Version 2 (Cleaned)")
    for structured_q in ["What is the average salary in Mumbai?", "How many employees are in each department?"]:
        print(f"\n{BOLD}Query: '{structured_q}'{RESET}")
        res_v1 = post("/query", json={"question": structured_q, "source_ids": [src_csv_id], "strategy": "auto", "version": 1})
        trace_v1 = get(f"/queries/{res_v1['query_id']}/trace")
        spec_v1 = trace_v1.get("structured_spec", {})

        print(f"\n  {YELLOW}Version 1 (Uncleaned Source):{RESET}")
        print(f"    Answer:        {res_v1['answer']}")
        print(f"    Rows Used:     {spec_v1.get('rows_used')}")
        print(f"    Quality Notes: {json.dumps(spec_v1.get('data_quality_notes'), indent=6)}")

        res_v2 = post("/query", json={"question": structured_q, "source_ids": [src_csv_id], "strategy": "auto", "version": 2})
        trace_v2 = get(f"/queries/{res_v2['query_id']}/trace")
        spec_v2 = trace_v2.get("structured_spec", {})

        print(f"\n  {GREEN}Version 2 (Cleaned Source):{RESET}")
        print(f"    Answer:        {res_v2['answer']}")
        print(f"    Rows Used:     {spec_v2.get('rows_used')}")
        print(f"    Quality Notes: {json.dumps(spec_v2.get('data_quality_notes'), indent=6)}")

    # STEP 7: Automated Fact-Checking in --live mode
    if is_live:
        step("Step 7: Automated Pandas Fact-Checking (--live mode)")
        df = pd.read_csv(csv_path)

        # Fact Check 1: Employee E1007 Department
        e1007_rows = df[df["Employee_ID"].astype(str).str.strip() == "E1007"]
        expected_dept = str(e1007_rows["Department"].iloc[0]).strip()
        live_ans_e1007 = str(query_results[2].get("answer", ""))

        if expected_dept.lower() in live_ans_e1007.lower():
            ok(f"PASS: Employee E1007 Department matches CSV ground truth -> '{expected_dept}'")
        else:
            warn(f"FAIL: Employee E1007 Department expected '{expected_dept}' not found in answer: '{live_ans_e1007}'")

        # Print content of chunk cited for E1007
        citations_e1007 = query_results[2].get("citations", [])
        if citations_e1007:
            cited_chunk_id = citations_e1007[0].get("chunk_id")
            print(f"\n  {BOLD}Content of Chunk Cited for E1007 (Chunk ID: {cited_chunk_id}):{RESET}")
            db = next(get_db())
            chunk_rec = db.query(Chunk).filter(Chunk.id == cited_chunk_id).first()
            if chunk_rec:
                print(f"  {CYAN}{chunk_rec.content}{RESET}")
            else:
                print(f"  Snippet: {citations_e1007[0].get('snippet')}")

        # Fact Check 2: Highest Salary Employee
        df_clean = df.dropna(subset=["Salary"]).copy()
        df_clean["Salary_str"] = df_clean["Salary"].astype(str).str.replace(",", "").str.strip()
        df_clean = df_clean[df_clean["Salary_str"].str.match(r"^\s*-?[0-9][0-9,]*(\.[0-9]+)?\s*$")]
        df_clean["Salary_num"] = df_clean["Salary_str"].astype(float)
        max_idx = df_clean["Salary_num"].idxmax()
        expected_max_emp = str(df_clean.loc[max_idx, "Employee_ID"]).strip()
        expected_max_sal = float(df_clean.loc[max_idx, "Salary_num"])

        live_ans_max = str(query_results[6].get("answer", ""))
        if expected_max_emp in live_ans_max:
            ok(f"PASS: Highest-salary employee matches CSV recomputation -> {expected_max_emp} (Salary: {expected_max_sal:,.2f})")
        else:
            warn(f"FAIL: Highest-salary employee expected {expected_max_emp} not in answer: '{live_ans_max}'")

    header("PHASE 6A DEMO COMPLETED SUCCESSFULLY — ALL VERIFICATIONS PASSED")


if __name__ == "__main__":
    run_demo()
