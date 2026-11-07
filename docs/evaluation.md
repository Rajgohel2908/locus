# Quantitative Evaluation Suite & RAG Doctor v1

Sift includes an internal quantitative evaluation harness and diagnostic engine designed for reproducible, offline verification of RAG retrieval quality, routing accuracy, and answer faithfulness without synthetic benchmarks or unverified claims.

---

## 1. Evaluation Architecture & Deterministic Foundations

### 1.1 Zero-LLM Retrieval-Only Mode
By default, evaluation operates at retrieval depth $k=20$. For retrieval-only runs (`generate=False`, `judge=False`), strictly **zero LLM calls** are made. All core ranking metrics (`hit@k`, `recall@k`, `precision@k`, `ndcg@k`, `mrr`) are evaluated deterministically from stored vector and lexical signals.

### 1.2 Canonical Benchmark Suite Hash
Every benchmark suite has a reproducible SHA-256 fingerprint (`suite_hash`) computed over its items sorted by position. Database auto-increment IDs and review state metadata are omitted from the hash. When a run executes against a suite, the suite is automatically frozen to guarantee that historical runs always correspond to an immutable set of questions and expected evidence.

---

## 2. Core Metrics & Mathematical Formulations

### 2.1 Precision Ceiling & Normalized Precision (`precision_norm@k`)
When an evaluation item has $R$ expected evidence spans, the standard precision at rank $k$ is capped:
$$\text{precision\_ceiling@k} = \min\left(1.0, \frac{R}{k}\right)$$

For instance, when an item specifies a single gold evidence span ($R=1$), at $k=5$ the maximum possible raw precision is $1/5 = 0.2000$. A raw precision of $0.2000$ in this context represents 100% relevant retrieval.

To prevent misinterpreting raw precision, Sift reports the mathematical ceiling alongside raw precision and computes **normalized precision**:
$$\text{precision\_norm@k} = \frac{\text{relevant chunks in top-}k}{\min(k, R)}$$

### 2.2 Token-Level Context Precision (`context_precision_tokens@k`)
Standard precision evaluates chunk counts regardless of chunk lengths. To detect context dilution caused by excessively large chunk windows, Sift measures token-level context precision:
$$\text{context\_precision\_tokens@k} = \frac{\sum_{c \in \text{relevant top-}k \text{ chunks}} \text{tokens}(c)}{\sum_{c \in \text{top-}k \text{ chunks}} \text{tokens}(c)}$$

Diagnostic rule **D3 (Broad Chunks)** uses `context_precision_tokens@5`. It requires that `hit@5` is healthy ($\ge 0.50$) and enforces an **applicability gate**: D3 fires only if at least 50% of the relevant chunks/documents in the corpus are longer than the proposed chunk size (400 chars). If not, D3 does not fire and persists the reason `"chunk_size_change_cannot_affect"`.

---

## 3. Evidence Levels in RAG Doctor v1

RAG Doctor findings are classified into four evidence levels to prevent presenting unverified hypotheses as measured facts:

| Evidence Level | Definition | Rules |
|---|---|---|
| `observed` | Deterministic metric measured directly on an executed run. | D8 (Route Mismatch) |
| `counterfactual` | Deterministic replay simulated from stored top-scoring signals without a new execution or LLM call. | D4 (False Refusals), D5 (Unsafe Answers) |
| `measured_effect` | Confirmed only after a verify run or an existing paired run on the same suite demonstrates empirical gain. | D9 (Rerank Overhead), Verified Findings |
| `hypothesis` | Heuristic recommendations requiring experimental confirmation before acceptance. | D1 (Slice Gap), D2 (Depth Gap), D3 (Broad Chunks), D6 (Citations), D7 (Temporal) |

---

## 4. Counterfactual Threshold Optimization (Rules D4 & D5)

When queries fail evidence gating (D4 false refusals or D5 unsafe answers), RAG Doctor performs a deterministic sweep across all observed candidate dense cosine scores without re-running retrieval or generation:

1. For every candidate threshold $t$ in the observed score set, it evaluates:
   $$\text{unsafe\_rate}(t) = \frac{\text{unanswerable items passing gate at } t}{N_{\text{unanswerable}}}$$
   $$\text{false\_refusal\_rate}(t) = \frac{\text{answerable items refused by gate at } t}{N_{\text{answerable}}}$$

2. It selects the optimal threshold $t^*$ maximizing:
   $$\text{Objective}(t) = (1 - \text{unsafe\_rate}(t)) - \text{false\_refusal\_rate}(t)$$
   *(Ties broken by selecting the lowest threshold).*

3. It reports both **in-sample** rates and **Leave-One-Out (jackknife)** cross-validation estimates:
   $$\text{loo\_unsafe\_rate} = \frac{1}{N_{un}} \sum_{i=1}^{N_{un}} \mathbb{I}(\text{query } i \text{ passes at optimal } t^*_{-i})$$

4. **Safety Warnings & Caveats**:
   - A warning is flagged if $N_{\text{unanswerable}} < 20$ or $N_{\text{answerable}} < 30$.
   - Supported strictly for the dense cosine component; in hybrid retrieval gates, lexical BM25 and cross-encoder score distributions behave differently.
   - Text descriptions state empirical numbers (e.g. `at t=0.57 on this suite: unsafe 4/6 -> 1/6, false refusals 0/15 -> 2/15, in-sample`); absolute claims like "cleanly blocks" are prohibited.

---

## 5. Label Lint Engine (`GET /eval/suites/{id}/lint`)

The label lint engine verifies ground-truth benchmark labels against the active corpus before runs are evaluated:

- **Duplicate Questions**: Flags duplicate questions normalized for punctuation and case.
- **Corpus Span Overlap**: Computes token overlap against all corpus chunks and documents; flags spans with $< 50\%$ best-match overlap.
- **Ambiguous Spans**: Flags expected spans that match 3 or more distinct documents in the knowledge base.
- **Structured Row Key Presence**: For tabular items, verifies that the specified `row_key` exists in active records (`status='active'`).
- **Expected Facts Verification**: Verifies that every required string in `expected_facts` occurs in the matched corpus text.

---

## 6. Non-Parametric Paired Bootstrap Method

### Why Paired Bootstrap is Required
When comparing two RAG configurations (e.g. Dense vs Hybrid), both configurations are evaluated on the exact same set of benchmark queries. Evaluating two runs as independent samples using two-sample t-tests or non-overlapping bootstrap resamples artificially inflates variance and destroys query-level covariance.

### Implementation
1. For common item pairs $i = 1, \dots, N$, Sift draws $B = 2,000$ bootstrap resamples with replacement.
2. For each resample $b$, it calculates the mean paired delta:
   $$\Delta^{(b)} = \frac{1}{N} \sum_{i=1}^N \left( \text{score}_{B, i}^{(b)} - \text{score}_{A, i}^{(b)} \right)$$
3. The empirical 95% confidence interval is $[Q_{0.025}, Q_{0.975}]$.
4. **Verdicts**:
   - $\text{CI lower} > 0$: **Distinguishable improvement**
   - $\text{CI upper} < 0$: **Distinguishable regression**
   - $\text{CI lower} \le 0 \le \text{CI upper}$: **No distinguishable difference**

---

## 7. Studio User Interface & Verification Screenshots

### 7.1 Benchmark Suites & Label Lint Drawer
Suites list showing items, reviewed count, suite hash, and active label lint drawer highlighting failing item #10 with missing corpus facts.

![Benchmark Suites & Label Lint Drawer](../frontend/SCREENSHOTS/eval_suites.png)

### 7.2 Parameter Sweep Matrix Launcher
Cartesian product generator previewing run counts across strategies, chunk sizes, and top-k with hard safety cap ($\le 24$).

![Parameter Sweep Matrix Launcher](../frontend/SCREENSHOTS/eval_matrix_launcher.png)

### 7.3 Quantitative Scorecard & Failure Drill-down
Full Markdown scorecard with provenance card, precision ceiling, route slices breakdown, and gold span highlight inside retrieved chunks.

![Evaluation Scorecard](../frontend/SCREENSHOTS/eval_scorecard.png)

### 7.4 Paired Statistical Bootstrap Comparison
Visual paired delta confidence interval bars across common items with win/loss/tie tallies and verdict chips.

![Paired Statistical Comparison](../frontend/SCREENSHOTS/eval_compare.png)

### 7.5 RAG Doctor Diagnostic Findings & Counterfactual Sweep
Doctor findings with evidence-level chips, D5 SVG counterfactual sweep chart, and collapsed not-fired rules with documented reasons.

![RAG Doctor Diagnostic Findings](../frontend/SCREENSHOTS/doctor_findings.png)

### 7.6 Finding Remediation Lifecycle & Verification
Automated patch lifecycle (Approved $\to$ Applied $\to$ Verify Run) showing pipeline configuration patch and verification card.

![Doctor Remediation Flow](../frontend/SCREENSHOTS/doctor_patch_flow.png)

