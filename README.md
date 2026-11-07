# Sift — Verifiable Enterprise RAG & Data Quality Platform

Sift is a production-grade, verifiable RAG and data quality system featuring deterministic data profiling, transactional tabular cleaning, multi-strategy vector search, rule-based routing, and a comprehensive quantitative evaluation harness with **RAG Doctor v1** for automated diagnostic analysis and verified remediation.

---

## 1. System Overview

```
                      ┌──────────────────────────────────────────────┐
                      │              Raw User / API Query            │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │     Rule-Based Router     │
                               │     (router-rules-v1)     │
                               └─────────────┬─────────────┘
                                             │
                ┌────────────────────────────┼───────────────────────────┐
                ▼                            ▼                           ▼
     [Structured Route]             [Exact / Complex]           [Semantic Route]
     No-RAG Fast Path              Hybrid RRF + Overrides       Dense Cosine HNSW
     0 LLM / 0 Embeddings          0.6 Dense + 0.4 BM25         Calibrated Threshold
                │                            │                           │
                └────────────────────────────┼───────────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   Evidence Quality Gate   │
                               │ (Relevance & Freshness)   │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   Grounded Generation     │
                               │   + Verifiable Citations  │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │    RAG Doctor Analysis    │
                               │    (Rules D1 through D9)  │
                               └───────────────────────────┘
```

---

## 2. Evaluation Suite & RAG Doctor v1 (Phase 7 & 8)

Sift provides an internal, reproducible evaluation suite designed for quantitative benchmarking without unverified claims:

### 2.1 Mathematical Precision Ceiling & Normalized Metrics
When an item has $R$ gold expected evidence spans, standard precision at depth $k$ is bounded by:
$$\text{precision\_ceiling@k} = \min\left(1.0, \frac{R}{k}\right)$$

For $R=1$ at $k=5$, raw precision cannot exceed $0.2000$. Sift reports this ceiling alongside raw precision and calculates normalized precision:
$$\text{precision\_norm@k} = \frac{\text{relevant chunks in top-}k}{\min(k, R)}$$

### 2.2 Token-Level Context Precision
Measures the share of top-$k$ retrieved tokens belonging to relevant chunks:
$$\text{context\_precision\_tokens@k} = \frac{\sum_{c \in \text{relevant top-}k} \text{tokens}(c)}{\sum_{c \in \text{top-}k} \text{tokens}(c)}$$

Diagnostic rule **D3 (Broad Chunks)** evaluates `context_precision_tokens@5` and applies only when $\ge 50\%$ of relevant source chunks exceed the proposed chunk size (400 chars).

### 2.3 RAG Doctor Evidence Levels
Doctor findings are rigorously segregated into four evidence levels:
1. `observed`: Measured directly on an executed run (e.g., Rule D8 query routing mismatch).
2. `counterfactual`: Deterministic replay simulated from stored signals without new executions or LLM calls (e.g., Rules D4 & D5 threshold sweep).
3. `measured_effect`: Validated only after a verify run or paired execution confirms empirical gain (e.g., Rule D9 rerank gain/overhead).
4. `hypothesis`: Empirical heuristics requiring verification before acceptance (e.g., Rules D1, D2, D3, D6, D7).

### 2.4 Counterfactual Threshold Optimization
Rules D4 and D5 sweep observed candidate dense cosine scores to optimize:
$$\text{Objective}(t) = (1 - \text{unsafe\_rate}(t)) - \text{false\_refusal\_rate}(t)$$
Estimates are reported both **in-sample** and using **Leave-One-Out (jackknife)** cross-validation with sample size warnings ($N_{un} < 20, N_{ans} < 30$).

### 2.5 Label Lint Engine
`GET /eval/suites/{id}/lint` inspects ground-truth labels against the corpus before evaluation:
- Flags ambiguous spans matching 3+ documents.
- Verifies best token overlap against corpus chunks ($\ge 50\%$).
- Confirms structured `row_key` presence in active table records.
- Verifies that all `expected_facts` strings occur in the matched corpus text.
- Detects duplicate questions across the benchmark suite.

### 2.6 Non-Parametric Paired Bootstrap
Comparing two retrieval strategies on the same benchmark queries introduces correlation across runs. Sift uses paired bootstrap resampling ($B=2,000$ resamples) to compute paired delta distributions $\Delta = \text{score}_B - \text{score}_A$ and 95% confidence intervals $[Q_{0.025}, Q_{0.975}]$. When the interval crosses zero, the result is reported strictly as `"No distinguishable difference"`.

---

## 3. Studio Interface & Screenshots

### Benchmark Suites & Label Lint
Suites list, items review status, reproducible SHA-256 suite hash, and label lint drawer highlighting failing items.
![Suites & Label Lint](frontend/SCREENSHOTS/eval_suites.png)

### Parameter Sweep Matrix Launcher
Cartesian product generator for multi-axis variant sweeps with hard safety cap ($\le 24$).
![Matrix Launcher](frontend/SCREENSHOTS/eval_matrix_launcher.png)

### Quantitative Evaluation Scorecard
Full Markdown scorecard with execution provenance, dirty tree warning, precision ceiling, and failure drill-down.
![Evaluation Scorecard](frontend/SCREENSHOTS/eval_scorecard.png)

### Paired Bootstrap Comparison
Visual paired delta confidence interval bars across common benchmark items.
![Paired Comparison](frontend/SCREENSHOTS/eval_compare.png)

### RAG Doctor Diagnostic Findings
Findings with evidence level chips, D5 SVG threshold sweep polyline chart, and collapsed not-fired rules.
![Doctor Findings](frontend/SCREENSHOTS/doctor_findings.png)

### Finding Remediation Lifecycle
Automated patch workflow (Approve $\to$ Apply $\to$ Verify Run) with paired CI verification card.
![Patch Lifecycle](frontend/SCREENSHOTS/doctor_patch_flow.png)

---

## 4. Quickstart & Verification Commands

### 4.1 Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 16 with pgvector (running at `localhost:8887` or configured via `DATABASE_URL`)

### 4.2 Backend Setup & Tests
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run full test suite (336 tests, 100% pass)
.\venv\Scripts\pytest.exe backend/tests backend/security_tests -v

# Run PostgreSQL-backed tests against ragstudio_test
$env:TEST_DATABASE_URL="postgresql://postgres:raj1818@localhost:8887/ragstudio_test"
.\venv\Scripts\pytest.exe -m pg -v

# Run slow-marked tests
$env:RUN_SLOW="1"
.\venv\Scripts\pytest.exe -m slow -v
```

### 4.3 Run Phase 7 End-to-End Evaluation Demo
```bash
$env:DEMO_DATABASE_URL="postgresql://postgres:raj1818@localhost:8887/ragstudio_demo"
.\venv\Scripts\python.exe backend/scripts/demo_phase7.py --standalone
```

### 4.4 Frontend Build & Start
```bash
cd frontend
npm run build
npm run lint
npm start
```

---

## 5. Documentation Links
- [Detailed Evaluation Architecture & Formulas](docs/evaluation.md)
- [Example Evaluation Markdown Scorecard](docs/examples/phase7_scorecard_example.md)
- [Database Migrations Log](backend/migrations/README.md)

