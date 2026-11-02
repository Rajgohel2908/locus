"""
scripts/calibrate_thresholds.py — Empirical threshold calibration for Phase 5 retrieval strategies.

Ingests the HR knowledge base, evaluates all 4 strategies (dense, lexical, hybrid, hybrid_rerank)
across 8 answerable and 8 unanswerable questions from calibration_questions.json,
prints real score distributions, and suggests evidence-gate thresholds.
"""

import sys
import os
import json
import statistics
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from db import init_db, SessionLocal, Source, IndexRun
import config

client = TestClient(app)


from typing import List

def ingest_hr_kb() -> List[int]:
    """Upload and index HR KB documents."""
    docx_path = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2024.docx"
    pdf_path = backend_dir / "sample_data" / "hr_kb" / "handbook_working_hours.pdf"

    source_ids = []
    # 1. Upload leave policy
    with open(docx_path, "rb") as f:
        r1 = client.post(
            "/upload",
            files={"file": ("leave_policy_2024.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert r1.status_code == 200, f"Upload leave failed: {r1.text}"
        s1_id = r1.json()["source_id"]
        source_ids.append(s1_id)

    # 2. Upload working hours handbook
    with open(pdf_path, "rb") as f:
        r2 = client.post(
            "/upload",
            files={"file": ("handbook_working_hours.pdf", f, "application/pdf")},
        )
        assert r2.status_code == 200, f"Upload handbook failed: {r2.text}"
        s2_id = r2.json()["source_id"]
        source_ids.append(s2_id)

    # 3. Index both sources
    for sid in source_ids:
        r_idx = client.post(f"/sources/{sid}/index", json={"chunk_size": 800, "chunk_overlap": 120})
        assert r_idx.status_code == 200, f"Index failed: {r_idx.text}"

    return source_ids


def run_calibration():
    print("=" * 80)
    print("  PHASE 5 RETRIEVAL EVIDENCE GATE CALIBRATION")
    print("=" * 80)

    init_db()
    source_ids = ingest_hr_kb()
    print(f"[OK] Ingested and indexed HR KB sources: {source_ids}")

    cal_path = backend_dir / "sample_data" / "hr_kb" / "calibration_questions.json"
    with open(cal_path, "r", encoding="utf-8") as f:
        cal_data = json.load(f)

    answerable = cal_data["answerable"]
    unanswerable = cal_data["unanswerable"]

    strategies = ["dense", "lexical", "hybrid", "hybrid_rerank"]

    scores = {
        s: {"answerable": [], "unanswerable": [], "details": []}
        for s in strategies
    }

    # Evaluate Answerable Questions
    print("\nEvaluating 8 Answerable Questions...")
    for item in answerable:
        q_id = item["id"]
        q_text = item["question"]

        resp = client.post(
            "/retrieve/compare",
            json={
                "question": q_text,
                "source_ids": source_ids,
                "top_k": 5,
                "strategies": strategies,
            },
        )
        assert resp.status_code == 200, f"Compare failed: {resp.text}"
        res = resp.json()["results"]

        for s in strategies:
            chunks = res[s]["chunks"]
            top_score = chunks[0]["score"] if chunks else 0.0
            scores[s]["answerable"].append(top_score)
            scores[s]["details"].append((q_id, "answerable", q_text, top_score))

    # Evaluate Unanswerable Questions
    print("Evaluating 8 Unanswerable Questions...")
    for item in unanswerable:
        q_id = item["id"]
        q_text = item["question"]

        resp = client.post(
            "/retrieve/compare",
            json={
                "question": q_text,
                "source_ids": source_ids,
                "top_k": 5,
                "strategies": strategies,
            },
        )
        assert resp.status_code == 200, f"Compare failed: {resp.text}"
        res = resp.json()["results"]

        for s in strategies:
            chunks = res[s]["chunks"]
            top_score = chunks[0]["score"] if chunks else 0.0
            scores[s]["unanswerable"].append(top_score)
            scores[s]["details"].append((q_id, "unanswerable", q_text, top_score))

    # Print Summary & Distributions
    print("\n" + "=" * 80)
    print("  SCORE DISTRIBUTIONS & THRESHOLD ANALYSIS")
    print("=" * 80)

    suggested_thresholds = {}

    for s in strategies:
        ans_scores = scores[s]["answerable"]
        unans_scores = scores[s]["unanswerable"]

        ans_min = min(ans_scores) if ans_scores else 0.0
        ans_max = max(ans_scores) if ans_scores else 0.0
        ans_mean = statistics.mean(ans_scores) if ans_scores else 0.0
        ans_median = statistics.median(ans_scores) if ans_scores else 0.0

        unans_min = min(unans_scores) if unans_scores else 0.0
        unans_max = max(unans_scores) if unans_scores else 0.0
        unans_mean = statistics.mean(unans_scores) if unans_scores else 0.0
        unans_median = statistics.median(unans_scores) if unans_scores else 0.0

        print(f"\n--- Strategy: {s.upper()} ---")
        print(f"  Answerable   (n={len(ans_scores)}): Min={ans_min:.4f}, Mean={ans_mean:.4f}, Median={ans_median:.4f}, Max={ans_max:.4f}")
        print(f"  Unanswerable (n={len(unans_scores)}): Min={unans_min:.4f}, Mean={unans_mean:.4f}, Median={unans_median:.4f}, Max={unans_max:.4f}")

        # Check separation
        overlap = []
        if unans_max >= ans_min:
            print(f"  [OVERLAP DETECTED]: Unanswerable max ({unans_max:.4f}) >= Answerable min ({ans_min:.4f})")
            for qid, qtype, qtext, score in scores[s]["details"]:
                if qtype == "unanswerable" and score >= ans_min:
                    overlap.append((qid, qtext, score))
            for qid, qtext, score in overlap:
                print(f"    * Overlapping unanswerable: {qid} '{qtext[:50]}...' -> score={score:.4f}")
            # Optimal separation cutoff maximizing margin or accuracy
            # Midpoint between median unanswerable and median answerable
            suggested = round((unans_max + ans_min) / 2, 4)
            if suggested > ans_min:
                suggested = round(ans_min, 4)
        else:
            gap = ans_min - unans_max
            print(f"  [CLEAN SEPARATION]: Gap = {gap:.4f} between {unans_max:.4f} and {ans_min:.4f}")
            suggested = round((unans_max + ans_min) / 2, 4)

        print(f"  -> Suggested Threshold: {suggested}")
        suggested_thresholds[s] = suggested

    print("\n" + "=" * 80)
    print("  RECOMMENDED CONFIG DEFAULTS")
    print("=" * 80)
    print(f"  MIN_SCORE  (Dense):         {config.MIN_SCORE} (retained baseline)")
    print(f"  MIN_BM25   (Lexical):       {suggested_thresholds.get('lexical')}")
    print(f"  MIN_RERANK (Hybrid Rerank): {suggested_thresholds.get('hybrid_rerank')}")
    print("=" * 80)

    return suggested_thresholds


if __name__ == "__main__":
    run_calibration()
