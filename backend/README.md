# Sift — Phase 1 to Phase 6A: Routing & Structured Execution

A FastAPI + PostgreSQL (pgvector) backend that ingests files and websites, runs data-quality profiling, persists content to canonical stores, manages cleaning workflows with versioning and quarantine, provides a multi-strategy RAG system (dense, lexical, hybrid, hybrid_rerank), and features a deterministic rule-based query router with a no-RAG structured path for tabular records.

---

## What's New in Phase 6A (Query Routing & Structured Execution)

| Feature | Details |
|---|---|
| **Deterministic Query Router** | Pure rule-based query analyzer and router using `router-rules-v1` heuristic priors. Zero LLM and zero embedding calls for routing decisions. |
| **4 Execution Routes** | `structured` (fixed aggregation templates), `exact` (hybrid retrieval), `complex` (hybrid_rerank retrieval with fallback), `semantic` (hybrid retrieval). |
| **No-RAG Structured Path** | Answers simple aggregation queries (`count`, `sum`, `avg`, `min`, `max`) over tabular `records` data using SQL templates on a single source version. 0 LLM and 0 embedding calls. |
| **Standardized Numeric Parsing** | Standard SQL numeric parsing matching `^\s*-?[0-9][0-9,]*(\.[0-9]+)?\s*$`. Non-numeric entries tracked as `rows_excluded_non_numeric`. Zero usable rows returns `no_numeric_values` (`insufficient_evidence`, not 0). |
| **Group-By & Filters** | Supports optional group-by on a single category column (capped at 50 groups) and equality filters (`column = value`). |
| **Data Quality Notes** | Computed answers include context from data profiling & cleaning: duplicate rows, missingness % of used columns, pending critical proposals, and explicit uncleaned warnings on version 1. |
| **Strategy "auto"** | `POST /query` with `strategy="auto"` routes queries dynamically to structured execution or the appropriate RAG retrieval strategy. |
| **Per-Query Trace** | `GET /queries/{id}/trace` returns unified explainability for computed, retrieval, and insufficient-evidence queries. |
| **New Route Endpoint** | `POST /route` evaluates query routing decisions and feature extractions without executing retrieval or generation. |

---

## What Was Added in Earlier Phases
- **Phase 5**: Multi-strategy RAG (`dense`, `lexical`, `hybrid`, `hybrid_rerank`), document overrides (`published_at`, `title`), whitelisted metadata filters, explainability signals, stage latencies, freshness awareness, calibrated evidence gate thresholds, and `/retrieve/compare`.
- **Phase 4**: Baseline dense RAG with pgvector HNSW cosine search, grounded generation, citation verification, and `insufficient_evidence` bypass.
- **Phase 3**: Column role inference & confirmation, cleaning proposals, apply engine with transactional versioning (`active` / `quarantined` / `excluded` statuses).
- **Phase 2**: Canonical content store (`sources`, `documents`, `records`), web crawler with SSRF protection, heuristic text quality checks.
- **Phase 1**: File upload and data quality profiling.

---

## Live Embedded Widget Performance Invariant

> [!IMPORTANT]
> **Runtime Rule for Client Embedded Widgets (`POST /v1/chat`):**
> Strategy comparison (`/retrieve/compare`) and CPU Cross-Encoder neural reranking are **offline studio/benchmark tools only**.
> At runtime on a live client website:
> 1. Use **Server-Sent Events (SSE) token streaming** so the Time-To-First-Token is under 350ms.
> 2. Use **fast Dense HNSW search (15ms)** or lightweight BM25 hybrid; omit the CPU Cross-Encoder to prevent a 500ms CPU bottleneck on consumer hardware.
> 3. Enforce **Semantic Caching** for high-frequency queries (>96% similarity hits in 20ms).
> 4. Restrict context injection to the **top 2–3 chunks** to minimize LLM prefill latency.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` to check |
| PostgreSQL | PostgreSQL 16 with pgvector extension (configured via `DATABASE_URL` in `.env`) |
| Tesseract OCR | Required for image uploads only |

> **Note:** The PostgreSQL container is assumed to be already running (`pgvector/pgvector:pg16`).

---

## Setup

```bash
# 1. Navigate to the backend folder
cd backend

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies (includes Phase 2: httpx, trafilatura)
pip install -r requirements.txt

# 4. Start the server (DB tables created automatically on startup)
uvicorn main:app --reload
```

The API will be available at **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

---

## Demo: Running the Messy Site

Phase 2 ships with a local demo HTTP server that simulates real-world quality problems:

```bash
# Terminal 1 — start the demo site
python sample_data/make_messy_site.py

# Terminal 2 — start the API with the SSRF demo bypass
ALLOW_LOCALHOST_FOR_DEMO=true uvicorn main:app --reload
```

The demo server runs on **http://localhost:8765** and serves:

| Page | Quality issue |
|---|---|
| `page1.html` | Normal reference article |
| `page2.html` | **Exact duplicate** of page1 |
| `page3.html` | **Near-duplicate** of page1 (minor edits) |
| `page4.html` | **Very short** + **disallowed** by robots.txt |
| `page5.html` | Contains a **prompt-injection** sentence |
| `page6.html` | **Stale** content (Last-Modified: 2020-01-01) |
| `sitemap.xml` | Lists all pages |
| `robots.txt` | Disallows `/page4.html` for SiftBot |

---

## ⚠️ ALLOW_LOCALHOST_FOR_DEMO — Important Warning

```
ALLOW_LOCALHOST_FOR_DEMO=true
```

This environment variable **bypasses the SSRF loopback/private-IP protection** so
you can crawl the local demo server.

**NEVER set this in production.** By default it is `false` and the SSRF guard will
correctly reject requests to `127.0.0.1`, `localhost`, `10.x.x.x`, `192.168.x.x`,
and all other RFC-1918 / reserved ranges.

Even with `ALLOW_LOCALHOST_FOR_DEMO=true`:
- Credentials in URLs are still rejected
- Non-http/https schemes are still rejected
- Link-local addresses (169.254.x.x) are still rejected

---

## Running Tests

```bash
pytest tests/ -v
```

Test coverage:
- `test_text_quality.py` — all 5 quality checks
- `test_ssrf.py` — SSRF guard (127.0.0.1, localhost, 10.0.0.5, 192.168.1.1, 169.254.169.254, [::1], redirect to private IP)
- `test_crawler_safety.py` — URL validation, robots.txt parsing
- `test_freshness.py` — all 4 freshness buckets

---

## Database

Tables are created automatically on startup. Phase 2 adds three new tables via `migrations/002_phase2.sql`:

```sql
-- Phase 1 (unchanged)
CREATE TABLE files (...);
CREATE TABLE quality_reports (...);

-- Phase 2 (new)
CREATE TABLE sources (
    id          SERIAL PRIMARY KEY,
    source_type TEXT CHECK (source_type IN ('file','web')),
    name        TEXT,
    origin      TEXT,
    file_id     INT REFERENCES files(id),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE documents (
    id                    SERIAL PRIMARY KEY,
    source_id             INT REFERENCES sources(id) ON DELETE CASCADE,
    modality              TEXT,   -- 'text' | 'ocr' | 'ocr_low_confidence' | 'web'
    title                 TEXT,
    url                   TEXT,
    page_number           INT,
    content               TEXT,
    content_hash          TEXT,   -- SHA-256 of normalised content
    word_count            INT,
    extraction_confidence FLOAT,
    published_at          TIMESTAMP,
    fetched_at            TIMESTAMP DEFAULT NOW(),
    metadata              JSONB DEFAULT '{}',
    quality               JSONB DEFAULT '{}'
);

CREATE TABLE records (
    id        SERIAL PRIMARY KEY,
    source_id INT REFERENCES sources(id) ON DELETE CASCADE,
    row_index INT,
    data      JSONB
);
```

---

## curl Examples

### 1 — Upload the messy CSV (Phase 1, now also creates records rows)

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@sample_data/employees_messy.csv"
```

Response now includes `source_id`. All CSV rows are stored in the `records` table.

---

### 2 — Ingest a website via sitemap (Phase 2)

```bash
# With demo server running and ALLOW_LOCALHOST_FOR_DEMO=true in API env:
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8765", "max_pages": 10}'
```

Expected response shows `pages_stored`, `pages_skipped` (with reasons like `robots_disallowed`, `skipped_short`), and a `quality_summary`.

---

### 3 — Get the quality report for a source

```bash
# Replace 1 with the source_id returned from /ingest/url or /upload
curl http://localhost:8000/sources/1/quality
```

Response shows exact duplicate groups, near-duplicate pairs, freshness distribution, short documents, injection suspects, and a human-readable issues list with severity levels.

---

### 4 — List all sources

```bash
curl http://localhost:8000/sources
```

---

### 5 — Get a specific document (full content)

```bash
curl http://localhost:8000/documents/1
```

---

## Endpoints

### Phase 1 (unchanged)

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload file → parse → profile → save → return report + `source_id` |
| `GET` | `/reports/{file_id}` | Retrieve saved quality report |
| `GET` | `/reports` | List all uploads with summaries |

### Phase 2 (new)

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/url` | Crawl a website via sitemap, store documents |
| `GET` | `/sources` | List all sources with document/record counts |
| `GET` | `/sources/{id}/documents` | List documents for a source (no content) |
| `GET` | `/sources/{id}/quality` | Aggregate quality report with issues list |
| `GET` | `/documents/{id}` | Full document including content |

### Phase 4 & Phase 5 Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/sources/{id}/index` | Chunk active content, embed, and store in pgvector (applies document overrides) |
| `GET` | `/sources/{id}/index-runs` | List all index runs for a source (status, chunk count, model) |
| `GET` | `/index-runs/{id}/chunks` | Preview chunk content and metadata (embeddings omitted) |
| `PUT` | `/documents/{id}/override` | Set user overrides for `published_at` (ISO date <= 1 day future) and `title` |
| `GET` | `/documents/{id}/override` | Get existing override for a document |
| `DELETE` | `/documents/{id}/override` | Remove document override |
| `POST` | `/retrieve/compare` | Evaluate all 4 strategies in parallel (no LLM): candidate signals, evidence gates, and overlap summary |
| `POST` | `/query` | Execute retrieval (`dense` \| `lexical` \| `hybrid` \| `hybrid_rerank`) + filters + grounded generation |
| `GET` | `/queries/{id}` | Get query details, strategy, filters, answer, and retrieved chunks with explainability signals |
| `GET` | `/queries` | List recent search queries |

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` or set environment variables:

```ini
# Database connection
DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/sift

# Embedding Configuration
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
# (Column dimension is 384; if model dim != 384, indexing fails fast requiring a migration)

# Chunking defaults (measured in characters)
CHUNK_SIZE=800
CHUNK_OVERLAP=120

# Phase 4 Retrieval defaults
TOP_K=5
MIN_SCORE=0.30

# Phase 5 Retrieval & Reranking configuration
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
CANDIDATES_N=20
RRF_K=60
RERANK_TOP_N=20
MIN_BM25=0.50
MIN_RERANK=0.50

# LLM Generation
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
LLM_TIMEOUT=30

# Model Warm-up & Offline Cache (Phase 6A / 6A.3)
WARMUP_MODELS=1
# (Set to 1 to load embedder and cross-encoder models into memory during server startup)
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
# (Set to 1 to run Hugging Face sentence-transformers fully offline once cached, avoiding network retry delays)

# Database Isolation (Phase 6A)
TEST_DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:8887/ragstudio_test
DEMO_DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:8887/ragstudio_demo
# Safety rule: Pytest strictly enforces TEST_DATABASE_URL ending with '_test'.
# reset_demo_db.py strictly enforces DEMO_DATABASE_URL ending with '_demo'.

# Simulated Demo Clock & Test Calibration
# FRESHNESS_REFERENCE_DATE: Simulated reference date for demos (default 2024-09-01) and deterministic
# unit tests. Allows sample documents to retain their true published dates (2019 policy: 2019-03-01,
# 2024 policy: 2024-06-01) rather than faking relative dates. Production never sets this variable.
```

---

## Running the Phase 4 Demo

Phase 4 includes an automated end-to-end demo script (`scripts/demo_phase4.py`) that:
1. Ingests synthetic HR KB documents (DOCX, PDF) and messy employees (CSV).
2. Cleans the messy CSV (Phase 3 workflow) to produce Version 2 with quarantined rows.
3. Indexes active content into pgvector.
4. Directly runs SQL checks verifying that quarantined and excluded rows are never chunked.
5. Executes the leave policy question (`"How many annual leaves are employees entitled to?"`), returning `status: "answered"` with citation.
6. Executes the employee department question (`"What is employee E1007's department?"`).
7. Executes an unsupported question (`"What is the company's Mars colonization budget?"`), returning `status: "insufficient_evidence"` and bypassing the LLM.
8. Demonstrates coexisting index runs with different chunk sizes.
9. Verifies query and retrieval result database persistence.

To run the demo:

```bash
# Option A: Standalone (runs directly with TestClient, no server needed)
python scripts/demo_phase4.py --standalone

# Option B: Against running server
uvicorn main:app --reload
python scripts/demo_phase4.py
```

---

## Phase 4 Curl Examples

### 1 — Index a Source Version

Index active content of source `1` with custom chunk size and overlap:

```bash
curl -X POST http://localhost:8000/sources/1/index \
  -H "Content-Type: application/json" \
  -d '{"version": 1, "chunk_size": 800, "chunk_overlap": 120}'
```

Response:
```json
{
  "id": 1,
  "source_id": 1,
  "source_version": 1,
  "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embed_dim": 384,
  "chunk_size": 800,
  "chunk_overlap": 120,
  "chunk_count": 4,
  "status": "completed",
  "error": null,
  "created_at": "2026-10-14 11:00:00",
  "finished_at": "2026-10-14 11:00:02"
}
```

---

### 2 — Query the Knowledge Base (Answer + Citations)

Query indexed sources with dense cosine retrieval:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many annual leaves are employees entitled to?",
    "source_ids": [1],
    "top_k": 5,
    "min_score": 0.30
  }'
```

Response:
```json
{
  "query_id": 1,
  "status": "answered",
  "answer": "All full-time employees are entitled to 24 annual leave days per calendar year [1].",
  "citations": [
    {
      "chunk_id": 1,
      "source_name": "leave_policy_2024.docx",
      "page_number": null,
      "url": null,
      "row_index": null,
      "score": 0.6268,
      "snippet": "All full-time employees are entitled to 24 annual leave days per calendar year..."
    }
  ],
  "retrieved": [
    {
      "rank": 1,
      "chunk_id": 1,
      "score": 0.6268,
      "used_in_prompt": true,
      "metadata": {
        "source_name": "leave_policy_2024.docx",
        "modality": "text",
        "freshness": "unknown"
      }
    }
  ],
  "config": {
    "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
    "chunk_size": 800,
    "chunk_overlap": 120,
    "top_k": 5,
    "min_score": 0.30,
    "index_run_id": 1
  },
  "latency_ms": {
    "embed": 18.2,
    "retrieve": 18.2,
    "generate": 350.0,
    "total": 386.4
  }
}
```

---

### 3 — Retrieve Stored Query History & Citations

Inspect stored query details and chunk scores:

```bash
curl http://localhost:8000/queries/1
```

Response:
```json
{
  "id": 1,
  "question": "How many annual leaves are employees entitled to?",
  "source_ids": [1],
  "index_run_ids": [1],
  "top_k": 5,
  "min_score": 0.3,
  "status": "answered",
  "answer": "All full-time employees are entitled to 24 annual leave days per calendar year [1].",
  "retrieval_results": [
    {
      "rank": 1,
      "chunk_id": 1,
      "score": 0.6268,
      "used_in_prompt": true,
      "cited": true,
      "metadata": { "source_name": "leave_policy_2024.docx" },
      "snippet": "All full-time employees are entitled to 24 annual leave days..."
    }
  ]
}
```

---

## Phase 5 Retrieval Upgrades, Strategies, Filters, Overrides & Explainability

### 1. Retrieval Strategies

Sift Phase 5 provides 4 explicit, selectable retrieval strategies via `/query` and `/retrieve/compare`:

1. **`dense` (Baseline, Default)**:
   - Preserves exact Phase 4 behavior.
   - Computes cosine similarity (`1 - cosine_distance`) using pgvector HNSW index.
   - Evidence gate: passes if `best_dense >= MIN_SCORE` (default `0.30`).
2. **`lexical` (BM25)**:
   - Uses `rank_bm25.BM25Okapi` with in-memory indexes cached per `index_run_id` (thread-safe LRU with capacity of 8 runs).
   - Custom pure tokenizer preserving identifiers (e.g. `E1007`, `E-1007`), decimals, email addresses, and Devanagari combining marks while stripping punctuation, possessives (`'s`, `’s`), and English/Hinglish stopwords.
   - Returns matched query terms (up to 5) and BM25 score. Scores `<= 0` are treated as no match.
   - Evidence gate: passes if `best_bm25 >= MIN_BM25` (default `0.50`).
3. **`hybrid` (Dense + BM25 via Reciprocal Rank Fusion)**:
   - Fetches top `CANDIDATES_N` (20) from dense and top `CANDIDATES_N` (20) from BM25.
   - Fuses candidates using Reciprocal Rank Fusion: `RRF(d) = sum(1 / (k + rank_i))` with `RRF_K=60`.
   - Deterministic tie-breaking on `chunk_id` ensures consistent ranking.
   - Evidence gate: passes if `best_dense >= MIN_SCORE` **OR** `best_bm25 >= MIN_BM25` (the response reports which signal passed).
4. **`hybrid_rerank` (Hybrid + Cross-Encoder)**:
   - Fuses top `RERANK_TOP_N` (20) candidates from hybrid retrieval.
   - Reranks candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2` (lazy CPU singleton with sigmoid normalization to `[0.0, 1.0]`).
   - Content truncated to ~512 tokens (~2000 characters).
   - Evidence gate: passes if `best_rerank >= MIN_RERANK` (default `0.50`).

### 2. Metadata Filtering & HNSW Scan Settings

- Whitelisted filter model `RetrievalFilters` (unknown keys rejected with HTTP 422):
  - `modality: List[str]`
  - `source_type: List[str]`
  - `freshness: List[str]` (`fresh`, `aging`, `stale`, `unknown`)
  - `published_after: datetime`
  - `published_before: datetime`
  - `min_extraction_confidence: float`
  - `title_contains: str`
- Single filter function `resolve_allowed_chunk_ids(run_ids, filters)` runs parameterized SQL over `chunks.metadata` using bound parameters only (no string interpolation). Both dense and lexical retrievers share these allowed chunk IDs.
- If no chunks match filters: returns `status: "insufficient_evidence"` with `reason: "no_chunks_match_filters"` and bypasses LLM entirely.
- pgvector HNSW post-filtering tuning: session applies `SET LOCAL hnsw.ef_search = 200` and `SET LOCAL hnsw.iterative_scan = 'relaxed_order'` to ensure sufficient candidates survive post-filtering scans.

### 3. Document Overrides & Data Immutability

- `PUT /documents/{id}/override {published_at: ISO date|null, title: str|null}`
- `GET /documents/{id}/override`
- `DELETE /documents/{id}/override`
- Rejects unparsable dates and dates more than 1 day in the future.
- **Strict Immutability**: Rows in `documents` and `records` are NEVER updated or deleted. Overrides are stored in the separate `document_overrides` table.
- **Index-time Application**: Overrides take effect **only for a NEW index run**. During indexing, chunk metadata receives `published_at`, `title`, `published_at_source: 'user'`, and freshness is dynamically recomputed.

### 4. Freshness Awareness in Generation

- `<chunk id="..." source="..." published_at="..." freshness="...">` tags expose temporal context.
- System prompt instructs the LLM: if chunks conflict, prefer the most recent dated source, explicitly mention the conflict and which source was preferred, and never present an older source as current.

### 5. Candidate Explainability Signals & Latency

Every retrieved candidate exposes full pipeline signals:
```json
"signals": {
  "dense_rank": 1,
  "dense_score": 0.6268,
  "lexical_rank": 1,
  "lexical_score": 1.4820,
  "rrf_score": 0.0328,
  "rerank_score": 0.9998,
  "final_rank": 1,
  "matched_terms": ["annual", "leaves", "entitled"]
}
```
Every response includes stage-by-stage latency breakdowns:
`latency_ms: { "filter": 2.1, "dense": 15.4, "lexical": 3.2, "fuse": 0.8, "rerank": 42.1, "generate": 320.5, "total": 384.1 }`

### 6. Calibrated Evidence Gate Thresholds

Thresholds were calibrated empirically using `scripts/calibrate_thresholds.py` on 8 answerable and 8 unanswerable questions from `sample_data/hr_kb/calibration_questions.json`:

| Strategy | Metric | Answerable Min | Unanswerable Max | Calibrated Threshold | Notes |
|---|---|---|---|---|---|
| `dense` | Cosine Similarity | 0.5139 | 0.4596 | `MIN_SCORE = 0.30` | Existing Phase 4 baseline preserved |
| `lexical` | BM25Okapi | 4.8912 (exact CSV IDs) | 0.0000 | `MIN_BM25 = 0.50` | BM25 score <= 0 indicates no match on tiny corpora |
| `hybrid` | Dense / BM25 Gate | - | - | Either gate passes | Passes if dense >= 0.30 OR bm25 >= 0.50 |
| `hybrid_rerank` | CrossEncoder (Sigmoid) | 0.9959 | 0.0054 | `MIN_RERANK = 0.50` | Clean separation gap of 0.9905 |

---

## Phase 5 Curl Examples

### 1 — Set Document Metadata Override

Set human-verified publication date and title for document `1`:

```bash
curl -X PUT http://localhost:8000/documents/1/override \
  -H "Content-Type: application/json" \
  -d '{
    "published_at": "2024-06-01T00:00:00",
    "title": "ACME 2024 Annual Leave Policy (Revised)"
  }'
```

Response:
```json
{
  "document_id": 1,
  "published_at": "2024-06-01T00:00:00",
  "title": "ACME 2024 Annual Leave Policy (Revised)",
  "set_at": "2026-10-27T12:00:00",
  "note": "Overrides take effect only for a NEW index run."
}
```

---

### 2 — Compare Retrieval Strategies Without LLM

Compare all four retrieval strategies (`dense`, `lexical`, `hybrid`, `hybrid_rerank`) side-by-side with explainability signals and rank comparison:

```bash
curl -X POST http://localhost:8000/retrieve/compare \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is employee E1007'\''s department?",
    "source_ids": [4],
    "top_k": 3,
    "strategies": ["dense", "lexical", "hybrid", "hybrid_rerank"]
  }'
```

Response includes `results` for every strategy (chunks, ranks, scores, signals, evidence gates, stage latencies) plus an `overlap_summary` mapping chunk occurrences and rank changes versus dense.

---

### 3 — Query with Hybrid Reranking and Freshness Filtering

Execute a query with `hybrid_rerank` strategy filtered strictly to `fresh` and `aging` documents:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many annual leaves are employees entitled to?",
    "source_ids": [1, 2],
    "strategy": "hybrid_rerank",
    "filters": {
      "freshness": ["fresh", "aging"]
    },
    "top_k": 5
  }'
```

Response returns `status: "answered"` citing only the current 2024 policy, with full signals and latency details.

---

### 4 — Inspect Stored Query History with Explainability Signals

```bash
curl http://localhost:8000/queries/1
```

Response returns the query record with stored `strategy`, `filters`, and all retrieved chunks containing complete `signals`.

---

## Phase 6A: Routing & Structured Execution

### 1. Deterministic Query Router (`router-rules-v1`)

The router analyzes the incoming question and structured schema context (`KBSchemaContext`) to deterministically select the execution path with zero LLM or embedding calls:

```
[Question + KBSchemaContext]
             │
             ▼
     Feature Extraction
  - identifier candidates & hits (bound SQL lookup)
  - English & Hinglish aggregation intent
  - group-by hint ("per X", "by X", "har X")
  - row identity request ("who", "which", "kaun")
  - comparison intent & multi-part queries
  - column mapping (stemming / edit distance <= 1)
  - category filter values
             │
             ▼
      Route Decision Chain
  1. STRUCTURED: aggregation_intent AND NOT row_identity_request AND mappable AND single structured source
     -> route="structured", strategy="structured" (bypasses RAG completely)
  2. EXACT: identifier_hits or identifier_candidates present
     -> route="exact", strategy="hybrid"
  3. COMPLEX: comparison_intent or multi_part query
     -> route="complex", strategy="hybrid_rerank" (falls back to "hybrid" if CrossEncoder unavailable)
  4. SEMANTIC: all other questions
     -> route="semantic", strategy="hybrid"
```

### 2. No-RAG Structured Aggregation Path

Answers quantitative questions directly on tabular (`records`) data with guaranteed determinism:
- **Operations Supported**: `count`, `sum`, `avg`, `min`, `max`.
- **Group By**: Optional single category column (capped at 50 groups; reported in response).
- **Equality Filters**: Arbitrary number of `column = value` filters combined with AND (case- and space-insensitive matching).
- **Shared SQL Numeric Parsing**: Values matching `^\s*-?[0-9][0-9,]*(\.[0-9]+)?\s*$` after stripping commas are cast to NUMERIC. Non-matching values are tracked as `rows_excluded_non_numeric`.
- **Zero Usable Rows**: When numeric operations encounter 0 usable rows, reason `no_numeric_values` is returned, bypassing generation and resulting in `insufficient_evidence` (never fake 0).
- **Data Quality Notes**: Contextual data quality observations compiled from dataset profiling: duplicate row counts, missingness % of used columns, pending critical cleaning proposals, and explicit warnings when querying uncleaned Version 1 data.
- **Deterministic Text Rendering**: Pure Python templated answers in English. Zero LLM calls.

### 3. Limitations

- **Rule-Based Prior**: Rules and keyword dictionaries (`router-rules-v1`) represent heuristic priors and have not been validated against live production user query distributions.
- **Keyword Scope**: Rule matching supports English and Hinglish phrases only.
- **Single Tabular Source**: Aggregations execute on exactly one tabular structured source at a time; multi-table joins and cross-source queries are not supported.
- **Fixed Aggregation Templates**: Only simple aggregations are supported. Row identity lookups (e.g. "Who has the highest salary?") and argmax/argmin queries are rejected from the structured path and routed to RAG.

---

## Phase 6A Curl Examples

### 1 — Evaluate Query Route Without Execution

Dry-run the rule-based router to inspect feature extraction and route decisions:

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the average salary in Mumbai?",
    "source_ids": [4]
  }'
```

Response:
```json
{
  "question": "What is the average salary in Mumbai?",
  "source_ids": [4],
  "version": null,
  "route": "structured",
  "strategy": "structured",
  "reasons": [
    "rule_structured_fired: op='avg', target_col='Salary', group_by='None', filters=1, source_id=4"
  ],
  "signals": {
    "target_source_id": 4,
    "aggregation_op": "avg",
    "target_column": "Salary",
    "filter_count": 1
  },
  "fallbacks": [],
  "rules_version": "router-rules-v1",
  "features": { ... }
}
```

---

### 2 — Execute Structured Query with Strategy "auto" (No LLM / No Embeddings)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the average salary in Mumbai?",
    "source_ids": [4],
    "strategy": "auto"
  }'
```

Response:
```json
{
  "query_id": 10,
  "status": "answered",
  "answer": "Average Salary where City = mumbai: 248,894.21 (computed from 56 active rows of employees_messy.csv v2)",
  "answer_type": "computed",
  "citations": [
    {
      "type": "computed",
      "source_id": 4,
      "source_name": "employees_messy.csv",
      "version": 2,
      "columns": ["Salary", "City"],
      "filters": [{"column": "City", "value": "mumbai"}],
      "rows_used": 56
    }
  ],
  "route": {
    "route": "structured",
    "strategy": "structured",
    "rules_version": "router-rules-v1"
  },
  "latency_ms": {
    "route": 18.2,
    "execute": 12.5,
    "render": 0.04,
    "total": 31.8
  }
}
```

---

### 3 — Query with Exact Identifier Auto-Routing to Hybrid Strategy

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is employee E1007'\''s department?",
    "source_ids": [4],
    "strategy": "auto"
  }'
```

Response routes to `exact` route with strategy `hybrid`, returning retrieved chunk citations with full signals.

---

### 4 — Inspect Full Query Trace

Inspect detailed explainability trace for any computed or retrieval query:

```bash
curl http://localhost:8000/queries/10/trace
```

Response returns unified trace including route decisions, SQL-level descriptions with bound placeholders, rows considered/used/excluded, and data quality notes.

---

---

## What's New in Phase 6B (Strategy Recommender & Pipeline Graphs)

| Feature | Details |
|---|---|
| **Knowledge Base Profile** | `POST /kb-profile` extracts non-destructive, read-only corpus statistics: document/record/chunk counts, average words, freshness distributions, structured column roles, script distribution, and quality health. |
| **Strategy Recommender** | `POST /recommendations` evaluates deterministic rules **R1–R12** (`recommender-rules-v1`) based on corpus profile and goal (`qa`, `comparison`, `extraction`, `search`). Thresholds serve as baseline priors (to be empirically validated in Phase 7). |
| **Recommendation Lifecycle** | State machine: `proposed` &rarr; `approved` &rarr; `applied` (or `rejected`). Transitions are validated and idempotent. |
| **Dual Pipeline Configurations** | Applying creates both a `Phase 4 Baseline` config (800/120, dense, no reranker, router/structured path disabled) and a `Recommended` config. Both link their own immutable index runs. |
| **Pipeline Architecture Graphs** | `GET /pipeline-configs/{id}/graph` renders the 14-node architecture DAG as JSON or deterministic Mermaid (`flowchart TD`) with distinct styling for disabled and planned nodes. |
| **Config-Aware Querying** | `POST /query` accepts `pipeline_config_id`. Baseline config enforces plain dense execution without router or structured redirection; recommended config activates hybrid/rerank and structured execution. |
| **Field-by-Field Diff** | `GET /pipeline-configs/compare?a={id}&b={id}` returns structured differences with rule attribution. |

---

## Strategy Recommender Rules (recommender-rules-v1)

> **Important**: All threshold values below are **prior heuristics**, not ground truth. They will be quantitatively benchmarked against RAGAS / Ground-Truth evaluation metrics in Phase 7. All chunk size and overlap values are in **characters**.

| Rule ID | Rule Name | Condition / Prior Threshold | Recommendation Effect |
|---|---|---|---|
| **R1** | `structured_present` | Structured source with &ge; 1 numeric column & &ge; 10 active rows | `structured_route_enabled = True` |
| **R2** | `identifier_present` | Identifier column in a structured source | `strategy_default = "hybrid"` |
| **R3** | `tiny_corpus` | Total corpus chunks &lt; 30 | `strategy_default = "dense"`, `use_rerank = False` |
| **R4** | `default_text` | Otherwise (chunks &ge; 30) | `strategy_default = "hybrid"` |
| **R5** | `rerank_policy` | Goal in `("qa", "comparison")` and corpus chunks &ge; 50 | `use_rerank = True` |
| **R6** | `chunk_sizing` | Avg words &lt; 300 &rarr; 500/75; 300–1500 &rarr; 800/120; &gt; 1500 &rarr; 1000/150 (in characters) | Sets `chunk_size`, `chunk_overlap`, `chunk_unit = "characters"` |
| **R7** | `stale_content` | Stale share &ge; 20% of dated chunks | Warning + `suggested_filters.freshness = ["fresh", "aging", "unknown"]` (never applied) |
| **R8** | `undated_documents` | &ge; 50% undated documents | Warning to set dates via overrides |
| **R9** | `ocr_quality` | OCR share &ge; 30% or mean confidence &lt; 70 | `filters_default.min_extraction_confidence = 60` plus warning |
| **R10** | `non_latin_script` | Non-Latin share &ge; 20% of characters | Warning only suggesting evaluating multilingual model (never switches models) |
| **R11** | `uncleaned_data` | Latest version 1 with duplicates or pending critical proposals | Warning that recommendation rests on uncleaned data |
| **R12** | `goal_adjustments` | Goal-specific adjustments: `search` &rarr; top_k=10, use_rerank=False; `comparison` &rarr; top_k=8; `analysis` &rarr; structured emphasized, warning if no structured source; `qa` &rarr; top_k=5 | Adjusts `top_k`, `use_rerank` |

---

## Offline Models & Simulated Clock Configuration

### Offline Transformer Operation
To avoid network overhead or Hugging Face Hub latency after initial download:
```bash
# In backend/.env:
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```
*Note: The first startup downloads SentenceTransformer and Cross-Encoder weights into local cache (`~/.cache/huggingface`). Subsequent runs operate completely offline when these flags are enabled.*

### Simulated Demo Clock
The environment variable `FRESHNESS_REFERENCE_DATE` enables deterministic time travel for demo scripts and test suites without modifying document timestamps on disk:
```bash
# Demos/Tests only (default 2024-09-01T00:00:00+00:00)
FRESHNESS_REFERENCE_DATE="2024-09-01T00:00:00+00:00"
```
*Production environments leave `FRESHNESS_REFERENCE_DATE` unset, defaulting to real-time `datetime.now(timezone.utc)`.*

---

## Phase 6B API Usage Examples (curl)

### 1 — Extract Knowledge Base Profile (POST /kb-profile)

```bash
curl -X POST http://localhost:8000/kb-profile \
  -H "Content-Type: application/json" \
  -d '{
    "source_ids": [1, 2, 3, 4]
  }'
```

---

### 2 — Generate Strategy Recommendation (POST /recommendations)

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "source_ids": [1, 2, 3, 4],
    "goal": "qa"
  }'
```

---

### 3 — Apply Recommendation with Background Indexing (POST /recommendations/{id}/apply)

```bash
# Approves recommendation first
curl -X POST http://localhost:8000/recommendations/1/approve

# Applies recommendation and indexes chunks for both configs
curl -X POST http://localhost:8000/recommendations/1/apply \
  -H "Content-Type: application/json" \
  -d '{
    "build_index": true
  }'
```

---

### 4 — Export Pipeline Architecture Graph in Mermaid Format (GET /pipeline-configs/{id}/graph)

```bash
curl http://localhost:8000/pipeline-configs/2/graph?format=mermaid
```

Returns valid `flowchart TD` text ready to paste directly into GitHub markdown or Mermaid Live Editor:
```mermaid
flowchart TD
    classDef default fill:#f8f9fa,stroke:#333,stroke-width:1.5px,color:#212529;
    classDef disabled fill:#f1f3f5,stroke:#adb5bd,stroke-width:1.5px,stroke-dasharray: 4 4,color:#868e96;
    classDef planned fill:#fff3bf,stroke:#fab005,stroke-width:1.5px,stroke-dasharray: 4 4,color:#495057;
    parser["Parser Engine"]
    quality_profiler["Quality Profiler"]
    cleaner["Cleaning Engine (Approved Proposals: 4)"]
    chunker["Chunker (500/75)"]
    embedder["Embedder (sentence-transformers/all-MiniLM-L6-v2)"]
    vector_store["Vector Store (pgvector HNSW)"]
    router["Query Router (Enabled)"]
    structured_executor["Structured Executor (Enabled)"]
    retriever["Retriever (hybrid, top_k=5)"]
    reranker["Cross-Encoder Reranker (Enabled)"]
    guardrails["Evidence Gate & Guardrails"]
    llm["LLM Generator (gemini:gemini-1.5-flash)"]
    evaluator["RAG Evaluator (Phase 7 Planned)"]
    class evaluator planned;
```

---

## Design Notes

- The profiler and quality checks are **read-only** — they never modify uploaded data.
- `json.dumps(..., default=str)` applied before every JSONB insert.
- Phase 4 Baseline RAG is preserved as the default `/query` path (`strategy="dense"`).
- Original document rows and record rows are strictly immutable.
- Document overrides only take effect on NEW index runs.
- If best retrieval score fails the evidence gate, the LLM is never called and status is `insufficient_evidence`.
- Structured aggregations execute with 0 LLM and 0 embedding calls. Column names are strictly whitelisted and SQL uses bound parameters for all inputs.