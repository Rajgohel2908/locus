"""
backend/evaluation/metrics.py — Deterministic metric computations for Sift evaluation runs.

Rules:
- Pure deterministic metrics; zero LLM calls.
- Retrieval always evaluates top 20 candidate pool.
- Answerable items: hit@k, recall@k, precision@k, nDCG@k, MRR for k in {1,3,5,10}, recall@20.
- Unanswerable items: refusal_correct (status insufficient_evidence), unsafe_answer.
- Answerable items: false_refusal (insufficient_evidence although a relevant chunk was in the top 3).
- Generation: fact_recall, answer_correct_strict, citation_precision, citation_recall, invalid_citation_rate.
- Structured items: value_match within tolerance + assert zero LLM calls.
- route_accuracy over items with expected_route.
"""

import math
from typing import Any, Dict, List, Optional
from evaluation.matching import normalize_text, union_covers_span


def compute_dcg_at_k(relevances: List[int], k: int) -> float:
    """Compute Discounted Cumulative Gain at rank k (1-based index)."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        if rel > 0:
            dcg += rel / math.log2(i + 1)
    return dcg


def compute_ndcg_at_k(relevances: List[int], total_relevant: int, k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain at rank k with binary relevance."""
    if total_relevant == 0:
        return 0.0

    dcg = compute_dcg_at_k(relevances, k)
    if dcg == 0.0:
        return 0.0

    ideal_k = min(k, total_relevant)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_k + 1))
    return dcg / idcg if idcg > 0.0 else 0.0


def compute_mrr(relevances: List[int]) -> float:
    """Mean Reciprocal Rank over binary relevances."""
    for i, rel in enumerate(relevances, start=1):
        if rel > 0:
            return 1.0 / i
    return 0.0


def check_structured_value_match(
    actual_output: Any,
    expected_value_spec: Optional[Dict[str, Any]],
    llm_calls: int = 0,
) -> float:
    """
    Check if structured execution output matches expected_value within tolerance.
    Asserts zero LLM calls (penalizes if LLM was invoked for a structured query).
    """
    if llm_calls > 0:
        return 0.0

    if expected_value_spec is None:
        return 1.0

    expected = expected_value_spec.get("value")
    tolerance = expected_value_spec.get("tolerance", 0.0) or 0.0
    tolerance_type = expected_value_spec.get("tolerance_type", "absolute")

    # If actual_output is dict or string, extract value
    actual = actual_output
    if isinstance(actual_output, dict):
        actual = actual_output.get("value", actual_output.get("answer"))

    # Try numeric conversion
    try:
        act_num = float(actual)
        exp_num = float(expected)

        if tolerance_type == "percentage":
            allowed_delta = abs(exp_num) * (tolerance / 100.0)
        else:
            allowed_delta = float(tolerance)

        if abs(act_num - exp_num) <= allowed_delta + 1e-9:
            return 1.0
        return 0.0
    except (ValueError, TypeError):
        # Fallback to string equality
        if normalize_text(str(actual)) == normalize_text(str(expected)):
            return 1.0
        return 0.0


def compute_item_metrics(
    item_type: str,
    expected_evidence: List[Dict[str, Any]],
    expected_facts: List[str],
    expected_value: Optional[Dict[str, Any]],
    expected_route: Optional[str],
    retrieved: List[Dict[str, Any]],
    answer: Optional[str],
    status: str,
    citations: List[Any],
    route: Optional[str],
    generate: bool = False,
    llm_calls: int = 0,
) -> Dict[str, Any]:
    """
    Compute all deterministic metrics for a single evaluation result.
    """
    metrics: Dict[str, Any] = {}

    # Extract binary relevances up to 20
    relevances = [1 if r.get("relevant", False) else 0 for r in retrieved[:20]]
    total_relevant = sum(relevances)

    # 1. Answerable Item Retrieval Metrics
    if item_type == "answerable":
        # R = number of expected spans/evidence items
        R = len(expected_evidence) if expected_evidence else 1

        for k in (1, 3, 5, 10):
            # hit@k
            metrics[f"hit@{k}"] = 1.0 if any(relevances[:k]) else 0.0

            # raw precision@k
            rel_k = sum(relevances[:k])
            metrics[f"precision@{k}"] = (
                rel_k / k if k > 0 else 0.0
            )

            # precision ceiling at k: min(1.0, R / k)
            precision_ceil = min(1.0, R / k) if k > 0 else 1.0
            metrics[f"precision_ceiling@{k}"] = precision_ceil

            # precision_norm@k = relevant chunks in top-k / min(k, R)
            denom_norm = min(k, R)
            metrics[f"precision_norm@{k}"] = min(1.0, rel_k / denom_norm) if denom_norm > 0 else 0.0

            # context_precision_tokens@k = share of tokens of top-k chunks that belong to relevant chunks
            top_k_items = retrieved[:k]
            chunk_tokens = [len(c.get("content", "").split()) for c in top_k_items]
            total_tokens = sum(chunk_tokens)
            rel_tokens = sum(chunk_tokens[idx] for idx, c in enumerate(top_k_items) if c.get("relevant", False))
            metrics[f"context_precision_tokens@{k}"] = (rel_tokens / total_tokens) if total_tokens > 0 else 0.0

            # nDCG@k
            metrics[f"ndcg@{k}"] = compute_ndcg_at_k(relevances, total_relevant, k)

            # recall@k (fraction of expected spans covered by union of top-k chunks)
            top_k_chunks = [r.get("content", "") for r in retrieved[:k]]
            if expected_evidence:
                spans_covered = sum(
                    1
                    for ev in expected_evidence
                    if union_covers_span(
                        top_k_chunks, ev.get("span", ""), ev.get("row_key")
                    )[0]
                )
                metrics[f"recall@{k}"] = spans_covered / len(expected_evidence)
            else:
                metrics[f"recall@{k}"] = 1.0 if metrics[f"hit@{k}"] > 0 else 0.0

        # recall@20
        top_20_chunks = [r.get("content", "") for r in retrieved[:20]]
        if expected_evidence:
            spans_cov_20 = sum(
                1
                for ev in expected_evidence
                if union_covers_span(
                    top_20_chunks, ev.get("span", ""), ev.get("row_key")
                )[0]
            )
            metrics["recall@20"] = spans_cov_20 / len(expected_evidence)
        else:
            metrics["recall@20"] = 1.0 if total_relevant > 0 else 0.0

        # MRR
        metrics["mrr"] = compute_mrr(relevances)

        # False refusal check
        # insufficient_evidence although a relevant chunk was in the top 3
        has_rel_in_top3 = any(relevances[:3])
        metrics["false_refusal"] = (
            1.0 if (status == "insufficient_evidence" and has_rel_in_top3) else 0.0
        )

    # 2. Unanswerable Items Metrics
    elif item_type == "unanswerable":
        metrics["refusal_correct"] = 1.0 if status == "insufficient_evidence" else 0.0
        is_unsafe = status in ("success", "unverified") or (
            answer is not None and len(answer.strip()) > 0
        )
        metrics["unsafe_answer"] = 1.0 if is_unsafe else 0.0

    # 3. Structured Items Metrics
    elif item_type == "structured":
        metrics["value_match"] = check_structured_value_match(
            answer, expected_value, llm_calls=llm_calls
        )

    # 4. Route Accuracy
    if expected_route:
        metrics["route_accuracy"] = 1.0 if route == expected_route else 0.0

    # 5. Generation Metrics (if generate=True and answer is provided)
    if generate:
        ans_norm = normalize_text(answer or "")

        # Fact Recall
        if expected_facts:
            matched_facts = sum(
                1 for f in expected_facts if normalize_text(f) in ans_norm
            )
            fact_rec = matched_facts / len(expected_facts)
            metrics["fact_recall"] = fact_rec
            metrics["answer_correct_strict"] = (
                1.0 if (fact_rec >= 1.0 and status != "insufficient_evidence") else 0.0
            )
        else:
            metrics["fact_recall"] = 1.0
            metrics["answer_correct_strict"] = (
                1.0 if status != "insufficient_evidence" else 0.0
            )

        # Citation Precision & Recall
        if citations:
            rel_by_id = {
                r.get("chunk_id"): r.get("relevant", False) for r in retrieved
            }
            retrieved_ids = {r.get("chunk_id") for r in retrieved}

            # Citation Precision: cited chunks that are relevant / total cited
            rel_cited = sum(1 for cid in citations if rel_by_id.get(cid, False))
            metrics["citation_precision"] = rel_cited / len(citations)

            # Citation Recall: spans covered by cited chunks / total expected spans
            cited_chunks = [
                r.get("content", "") for r in retrieved if r.get("chunk_id") in citations
            ]
            if expected_evidence:
                spans_cov_cited = sum(
                    1
                    for ev in expected_evidence
                    if union_covers_span(
                        cited_chunks, ev.get("span", ""), ev.get("row_key")
                    )[0]
                )
                metrics["citation_recall"] = spans_cov_cited / len(expected_evidence)
            else:
                metrics["citation_recall"] = 1.0

            # Invalid citation rate: cited chunks not in retrieved pool
            invalid_citations = sum(1 for cid in citations if cid not in retrieved_ids)
            metrics["invalid_citation_rate"] = invalid_citations / len(citations)
        else:
            metrics["citation_precision"] = 0.0
            metrics["citation_recall"] = 0.0 if expected_evidence else 1.0
            metrics["invalid_citation_rate"] = 0.0

    return metrics

