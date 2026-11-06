"""
scripts/measure_warmup_latency.py — Model warm-up measurement and stage latency validation.

Requirements (Patch 6A.3 Item A2):
1. Separate startup breakdown: python import time, model resolve/network time,
   weight load, and first inference for both embedder and cross-encoder.
2. Execute two successive calls to /retrieve/compare with strategy hybrid_rerank.
3. Read stage latencies from the real response structure and exit 1 if any
   hybrid_rerank stage is missing or exactly 0.0.
4. Print real rerank milliseconds of the first and second call after startup.
"""

import sys
import os
import time
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Support offline flags if present
import config
from huggingface_hub import try_to_load_from_cache

print("=" * 78)
print("  MODEL WARM-UP & STAGE LATENCY MEASUREMENT TOOL")
print("=" * 78)

# ── 1. Embedder Breakdown ─────────────────────────────────────────────────────
print("\n[1/3] Measuring Embedder Startup Breakdown...")
t0 = time.perf_counter()
from indexing.embedder import get_embedder
t_import_embed = time.perf_counter() - t0

embed_model_name = config.EMBED_MODEL
t0 = time.perf_counter()
cached_embed = try_to_load_from_cache(embed_model_name, "config.json")
t_resolve_embed = time.perf_counter() - t0

t0 = time.perf_counter()
embedder = get_embedder()
embedder._ensure_loaded()
t_load_embed = time.perf_counter() - t0

t0 = time.perf_counter()
embedder.embed_query("warmup probe")
t_infer_embed = time.perf_counter() - t0

print(f"  Embedder Model:      {embed_model_name}")
print(f"    - Python Import:   {t_import_embed:.4f} s")
print(f"    - Resolve/Network: {t_resolve_embed:.4f} s (cached={cached_embed is not None})")
print(f"    - Weight Load:     {t_load_embed:.4f} s")
print(f"    - First Inference: {t_infer_embed:.4f} s")
print(f"    - Total Startup:   {t_import_embed + t_resolve_embed + t_load_embed + t_infer_embed:.4f} s")

# ── 2. Cross-Encoder Breakdown ────────────────────────────────────────────────
print("\n[2/3] Measuring Cross-Encoder Startup Breakdown...")
t0 = time.perf_counter()
from retrieval.rerank import get_reranker
t_import_rerank = time.perf_counter() - t0

rerank_model_name = config.RERANK_MODEL
t0 = time.perf_counter()
cached_rerank = try_to_load_from_cache(rerank_model_name, "config.json")
t_resolve_rerank = time.perf_counter() - t0

t0 = time.perf_counter()
reranker = get_reranker()
reranker._get_model()
t_load_rerank = time.perf_counter() - t0

t0 = time.perf_counter()
reranker.rerank("warmup query", [{"chunk_id": -1, "content": "warmup candidate chunk content", "score": 0.5}])
t_infer_rerank = time.perf_counter() - t0

print(f"  Cross-Encoder Model: {rerank_model_name}")
print(f"    - Python Import:   {t_import_rerank:.4f} s")
print(f"    - Resolve/Network: {t_resolve_rerank:.4f} s (cached={cached_rerank is not None})")
print(f"    - Weight Load:     {t_load_rerank:.4f} s")
print(f"    - First Inference: {t_infer_rerank:.4f} s")
print(f"    - Total Startup:   {t_import_rerank + t_resolve_rerank + t_load_rerank + t_infer_rerank:.4f} s")

# ── 3. Test Ingestion & Successive /retrieve/compare Calls ─────────────────────
print("\n[3/3] Testing Stage Latencies on Real /retrieve/compare Calls...")

# Setup test DB or use demo DB URL
from scripts.reset_demo_db import get_demo_db_url, reset_demo_database
demo_url = get_demo_db_url()
os.environ["DATABASE_URL"] = demo_url
reset_demo_database(demo_url)

from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

# Ingest sample policy for indexing
pdf_path = backend_dir / "sample_data" / "hr_kb" / "leave_policy_2019_archived.pdf"
with open(pdf_path, "rb") as f:
    up = client.post("/upload", files={"file": ("leave_policy_2019_archived.pdf", f, "application/pdf")}).json()
src_id = up["source_id"]

# Index the source
idx_res = client.post(f"/sources/{src_id}/index", json={"chunk_size": 800, "chunk_overlap": 120}).json()
print(f"  Indexed source_id={src_id} into index_run_id={idx_res['id']} ({idx_res['chunk_count']} chunks)")

question = "How many days of annual leave are employees entitled to?"
req_payload = {
    "question": question,
    "source_ids": [src_id],
    "strategies": ["hybrid_rerank"],
}

REQUIRED_STAGES = ["filter", "dense", "lexical", "fuse", "rerank"]

# Call 1 (first call after startup)
resp1 = client.post("/retrieve/compare", json=req_payload)
if not resp1.is_success:
    print(f"[FAIL] Call 1 failed ({resp1.status_code}): {resp1.text}")
    sys.exit(1)
data1 = resp1.json()
res1 = data1["results"]["hybrid_rerank"]
lat1 = res1.get("latency_ms", {})

print(f"\n  Call 1 Latencies (ms): {lat1}")
print(f"    -> Rerank Stage: {lat1.get('rerank')} ms")

# Validate all stages are present and non-zero
for stage in REQUIRED_STAGES:
    val = lat1.get(stage)
    if val is None:
        print(f"[FAIL] Call 1 is missing stage '{stage}' in latency_ms!")
        sys.exit(1)
    if val == 0.0:
        print(f"[FAIL] Call 1 stage '{stage}' latency is exactly 0.0 ms!")
        sys.exit(1)

# Call 2 (second call after startup)
resp2 = client.post("/retrieve/compare", json=req_payload)
if not resp2.is_success:
    print(f"[FAIL] Call 2 failed ({resp2.status_code}): {resp2.text}")
    sys.exit(1)
data2 = resp2.json()
res2 = data2["results"]["hybrid_rerank"]
lat2 = res2.get("latency_ms", {})

print(f"\n  Call 2 Latencies (ms): {lat2}")
print(f"    -> Rerank Stage: {lat2.get('rerank')} ms")

# Validate all stages in Call 2
for stage in REQUIRED_STAGES:
    val = lat2.get(stage)
    if val is None:
        print(f"[FAIL] Call 2 is missing stage '{stage}' in latency_ms!")
        sys.exit(1)
    if val == 0.0:
        print(f"[FAIL] Call 2 stage '{stage}' latency is exactly 0.0 ms!")
        sys.exit(1)

rerank_ms_1 = lat1["rerank"]
rerank_ms_2 = lat2["rerank"]

print("\n" + "=" * 78)
print("  WARM-UP LATENCY SUMMARY")
print(f"  First call rerank latency:  {rerank_ms_1:.2f} ms")
print(f"  Second call rerank latency: {rerank_ms_2:.2f} ms")
print("  All hybrid_rerank stages present and > 0.0 ms: PASS")
print("=" * 78)

sys.exit(0)

