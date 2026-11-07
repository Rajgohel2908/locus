# Sift Reproducible Evaluation Scorecard

> [!WARNING]
> **sample KB, agent-drafted labels, exploratory, not evidence of quality**

> [!NOTE]
> **DIRTY WORKING TREE: results not reproducible from the commit hash alone**

> [!NOTE]
> **SMALL SAMPLE SIZE (n < 30, labeled heuristic):** Results have wider confidence intervals and high sample sensitivity.

> [!NOTE]
> **EXPLORATORY COMPARISONS:** Evaluated 5 metric comparisons without multiple-testing correction (e.g. Bonferroni/FDR). Interpret exploratory deltas with caution.

> [!IMPORTANT]
> **LLM-JUDGED METRICS:** Faithfulness and Answer Relevance are **LLM-judged, uncalibrated**.

---

## 1. Provenance & Run Configuration

| Run ID | Name | Strategy | Chunk Size | Top K | Git Commit | Dirty Tree | Diff SHA | Embedder (Used) | Reranker (Used) | Python | Suite Hash |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Baseline Dense | dense | 800 | 5 | `9846b399` | YES (DIRTY) | `7a1f4b2c` | all-MiniLM-L6-v2 (Yes) | ms-marco-MiniLM (No) | 3.12.10 | `e3b0c442` |
| 2 | Hybrid Retrieval | hybrid | 800 | 5 | `9846b399` | YES (DIRTY) | `7a1f4b2c` | all-MiniLM-L6-v2 (Yes) | ms-marco-MiniLM (No) | 3.12.10 | `e3b0c442` |

---

## 2. Core Quantitative Metrics (95% Bootstrap CI)

| Metric | Run 1 (Baseline Dense) | Run 2 (Hybrid Retrieval) |
| :--- | :---: | :---: |
| **hit@1** | 0.8000 `[0.6000, 1.0000]` *(n=15)* | 0.8667 `[0.6667, 1.0000]` *(n=15)* |
| **hit@3** | 0.8667 `[0.6667, 1.0000]` *(n=15)* | 0.9333 `[0.8000, 1.0000]` *(n=15)* |
| **hit@5** | 0.8667 `[0.6667, 1.0000]` *(n=15)* | 0.9333 `[0.8000, 1.0000]` *(n=15)* |
| **hit@10** | 0.9333 `[0.8000, 1.0000]` *(n=15)* | 1.0000 `[1.0000, 1.0000]` *(n=15)* |
| **recall@1** | 0.8000 `[0.6000, 1.0000]` *(n=15)* | 0.8667 `[0.6667, 1.0000]` *(n=15)* |
| **recall@3** | 0.8667 `[0.6667, 1.0000]` *(n=15)* | 0.9333 `[0.8000, 1.0000]` *(n=15)* |
| **recall@5** | 0.8667 `[0.6667, 1.0000]` *(n=15)* | 0.9333 `[0.8000, 1.0000]` *(n=15)* |
| **recall@10** | 0.9333 `[0.8000, 1.0000]` *(n=15)* | 1.0000 `[1.0000, 1.0000]` *(n=15)* |
| **recall@20** | 1.0000 `[1.0000, 1.0000]` *(n=15)* | 1.0000 `[1.0000, 1.0000]` *(n=15)* |
| **precision@1** | 0.8000 `(ceiling: 1.0000)` `[0.6000, 1.0000]` *(n=15)* | 0.8667 `(ceiling: 1.0000)` `[0.6667, 1.0000]` *(n=15)* |
| **precision@3** | 0.3111 `(ceiling: 0.3333)` `[0.2222, 0.3333]` *(n=15)* | 0.3333 `(ceiling: 0.3333)` `[0.2667, 0.3333]` *(n=15)* |
| **precision@5** | 0.1867 `(ceiling: 0.2000)` `[0.1333, 0.2000]` *(n=15)* | 0.2000 `(ceiling: 0.2000)` `[0.1600, 0.2000]` *(n=15)* |
| **precision@10** | 0.0933 `(ceiling: 0.1000)` `[0.0800, 0.1000]` *(n=15)* | 0.1000 `(ceiling: 0.1000)` `[0.1000, 0.1000]` *(n=15)* |
| **precision_norm@1** | 0.8000 `[0.6000, 1.0000]` *(n=15)* | 0.8667 `[0.6667, 1.0000]` *(n=15)* |
| **precision_norm@3** | 0.8667 `[0.6667, 1.0000]` *(n=15)* | 0.9333 `[0.8000, 1.0000]` *(n=15)* |
| **precision_norm@5** | 0.8667 `[0.6667, 1.0000]` *(n=15)* | 0.9333 `[0.8000, 1.0000]` *(n=15)* |
| **precision_norm@10** | 0.9333 `[0.8000, 1.0000]` *(n=15)* | 1.0000 `[1.0000, 1.0000]` *(n=15)* |
| **context_precision_tokens@1** | 0.8000 `[0.6000, 1.0000]` *(n=15)* | 0.8667 `[0.6667, 1.0000]` *(n=15)* |
| **context_precision_tokens@3** | 0.3012 `[0.2105, 0.3333]` *(n=15)* | 0.3245 `[0.2541, 0.3333]` *(n=15)* |
| **context_precision_tokens@5** | 0.1784 `[0.1240, 0.2000]` *(n=15)* | 0.1942 `[0.1510, 0.2000]` *(n=15)* |
| **context_precision_tokens@10** | 0.0891 `[0.0750, 0.1000]` *(n=15)* | 0.0965 `[0.0910, 0.1000]` *(n=15)* |
| **ndcg@3** | 0.8421 `[0.6512, 1.0000]` *(n=15)* | 0.9125 `[0.7654, 1.0000]` *(n=15)* |
| **ndcg@5** | 0.8421 `[0.6512, 1.0000]` *(n=15)* | 0.9125 `[0.7654, 1.0000]` *(n=15)* |
| **mrr** | 0.8333 `[0.6500, 1.0000]` *(n=15)* | 0.9000 `[0.7500, 1.0000]` *(n=15)* |
| **refusal_correct** | 1.0000 `[1.0000, 1.0000]` *(n=6)* | 1.0000 `[1.0000, 1.0000]` *(n=6)* |
| **gate_pass_unanswerable** | 0.0000 `[0.0000, 0.0000]` *(n=6)* | 0.0000 `[0.0000, 0.0000]` *(n=6)* |
| **false_refusal** | 0.0000 `[0.0000, 0.0000]` *(n=15)* | 0.0000 `[0.0000, 0.0000]` *(n=15)* |
| **value_match** | 1.0000 `[1.0000, 1.0000]` *(n=3)* | 1.0000 `[1.0000, 1.0000]` *(n=3)* |
| **route_accuracy** | 1.0000 `[1.0000, 1.0000]` *(n=24)* | 1.0000 `[1.0000, 1.0000]` *(n=24)* |

### Stage Latencies (p50 / p95)

| Stage | Run 1 p50 / p95 | Run 2 p50 / p95 |
| :--- | :---: | :---: |
| **total** | 42.15 ms / 68.40 ms | 61.20 ms / 94.50 ms |
| **dense** | 38.40 ms / 56.10 ms | 41.20 ms / 59.80 ms |
| **lexical** | 0.0 ms / 0.0 ms | 18.50 ms / 28.10 ms |
| **rerank** | 0.0 ms / 0.0 ms | 0.0 ms / 0.0 ms |
| **generate** | 0.0 ms / 0.0 ms | 0.0 ms / 0.0 ms |

### Route Slices Breakdown

| Route | Run | Items (n) | Recall@5 (95% CI) | Hit@5 (95% CI) | Precision@5 | MRR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **semantic** | Run 1 | 15 | 0.8667 `[0.6667, 1.0000]` | 0.8667 `[0.6667, 1.0000]` | 0.1867 | 0.8333 |
| **semantic** | Run 2 | 15 | 0.9333 `[0.8000, 1.0000]` | 0.9333 `[0.8000, 1.0000]` | 0.2000 | 0.9000 |
| **structured** | Run 1 | 3 | 1.0000 `[1.0000, 1.0000]` | 1.0000 `[1.0000, 1.0000]` | 0.2000 | 1.0000 |
| **structured** | Run 2 | 3 | 1.0000 `[1.0000, 1.0000]` | 1.0000 `[1.0000, 1.0000]` | 0.2000 | 1.0000 |

---

## 3. Paired Comparisons (Variant A vs Variant B)

Paired evaluation over **24 common items**:

| Metric | Mean A | Mean B | Mean Δ (A - B) | 95% Paired CI | W / L / T | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **recall@5** | 0.8667 | 0.9333 | -0.0667 | `[-0.1333, +0.0000]` | 0 / 1 / 14 | ties |
| **precision@5** | 0.1867 | 0.2000 | -0.0133 | `[-0.0267, +0.0000]` | 0 / 1 / 14 | ties |
| **mrr** | 0.8333 | 0.9000 | -0.0667 | `[-0.1500, +0.0167]` | 0 / 1 / 14 | ties |
| **hit@5** | 0.8667 | 0.9333 | -0.0667 | `[-0.1333, +0.0000]` | 0 / 1 / 14 | ties |
| **false_refusal** | 0.0000 | 0.0000 | +0.0000 | `[+0.0000, +0.0000]` | 0 / 0 / 15 | ties |

---

## 4. Diagnostic Failures Summary

### Run 1 (Baseline Dense) — Total Failures: 2
- **Item ID `14`** | Status: `success` | Reasons: `gold_missing_from_top_k`
  *Query:* "What is the notice period required for remote contractors under Section 8?"
- **Item ID `18`** | Status: `success` | Reasons: `gold_missing_from_top_k`
  *Query:* "What are the core hours for APAC regional personnel?"

### Run 2 (Hybrid Retrieval) — Total Failures: 1
- **Item ID `14`** | Status: `success` | Reasons: `gold_missing_from_top_k`
  *Query:* "What is the notice period required for remote contractors under Section 8?"

