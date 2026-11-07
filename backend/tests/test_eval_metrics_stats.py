"""
tests/test_eval_metrics_stats.py — Unit tests for Phase 7 deterministic metrics,
hand-computed mathematical proofs, and bootstrap statistics.
"""

import pytest
import math
from evaluation.metrics import (
    compute_mrr,
    compute_dcg_at_k,
    compute_ndcg_at_k,
    check_structured_value_match,
    compute_item_metrics,
)
from evaluation.stats import bootstrap_ci, paired_bootstrap_comparison


def test_hand_computed_mrr():
    # Rank 1 -> MRR = 1.0
    assert compute_mrr([1, 0, 0, 0]) == 1.0
    # Rank 2 -> MRR = 0.5
    assert compute_mrr([0, 1, 0, 0]) == 0.5
    # Rank 4 -> MRR = 0.25
    assert compute_mrr([0, 0, 0, 1]) == 0.25
    # No relevant item -> MRR = 0.0
    assert compute_mrr([0, 0, 0, 0]) == 0.0


def test_hand_computed_ndcg_at_3():
    """
    Hand-computed nDCG@3:
    Relevances: [1, 0, 1], total_relevant = 2.
    DCG@3 = 1 / log2(2) + 0 / log2(3) + 1 / log2(4) = 1.0 + 0.0 + 0.5 = 1.5
    IDCG@3 = 1 / log2(2) + 1 / log2(3) = 1.0 + 0.63092975357 = 1.63092975357
    nDCG@3 = 1.5 / 1.63092975357 = 0.919720789...
    """
    relevances = [1, 0, 1]
    total_rel = 2
    dcg = compute_dcg_at_k(relevances, 3)
    assert pytest.approx(dcg, abs=1e-5) == 1.5

    idcg = 1.0 + (1.0 / math.log2(3))
    expected_ndcg = 1.5 / idcg

    ndcg = compute_ndcg_at_k(relevances, total_rel, 3)
    assert pytest.approx(ndcg, abs=1e-5) == expected_ndcg
    assert round(ndcg, 4) == 0.9197


def test_precision_recall_hit_at_k():
    item_type = "answerable"
    expected_evidence = [
        {"span": "Leave policy allows 25 days annual leave."},
        {"span": "Carryover is limited to 5 days."},
    ]
    # 2 expected spans.
    # Chunk 1 covers span 1.
    # Chunk 2 is irrelevant.
    # Chunk 3 covers span 2.
    retrieved = [
        {
            "rank": 1,
            "chunk_id": 101,
            "content": "Full Leave policy allows 25 days annual leave without issue.",
            "relevant": True,
        },
        {
            "rank": 2,
            "chunk_id": 102,
            "content": "Cafeteria timings are 12 to 2.",
            "relevant": False,
        },
        {
            "rank": 3,
            "chunk_id": 103,
            "content": "Vacation carryover is limited to 5 days each calendar year.",
            "relevant": True,
        },
    ]

    metrics = compute_item_metrics(
        item_type=item_type,
        expected_evidence=expected_evidence,
        expected_facts=[],
        expected_value=None,
        expected_route="exact",
        retrieved=retrieved,
        answer="You get 25 days leave and can carry over 5 days.",
        status="success",
        citations=[101, 103],
        route="exact",
        generate=False,
    )

    # At k=1: 1 hit, precision = 1/1 = 1.0, recall = 1/2 = 0.5
    assert metrics["hit@1"] == 1.0
    assert metrics["precision@1"] == 1.0
    assert metrics["recall@1"] == 0.5

    # At k=2: 1 relevant out of 2 -> precision = 0.5, recall = 0.5
    assert metrics["hit@3"] == 1.0
    assert metrics["precision@3"] == pytest.approx(2 / 3, abs=1e-4)
    # At k=3: both spans covered -> recall = 2/2 = 1.0
    assert metrics["recall@3"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["route_accuracy"] == 1.0


def test_unanswerable_and_false_refusal_metrics():
    # 1. Correct refusal on unanswerable
    m1 = compute_item_metrics(
        item_type="unanswerable",
        expected_evidence=[],
        expected_facts=[],
        expected_value=None,
        expected_route="semantic",
        retrieved=[],
        answer=None,
        status="insufficient_evidence",
        citations=[],
        route="semantic",
    )
    assert m1["refusal_correct"] == 1.0
    assert m1["unsafe_answer"] == 0.0

    # 2. Unsafe answer on unanswerable
    m2 = compute_item_metrics(
        item_type="unanswerable",
        expected_evidence=[],
        expected_facts=[],
        expected_value=None,
        expected_route="semantic",
        retrieved=[],
        answer="The Mars budget is 50 billion.",
        status="success",
        citations=[],
        route="semantic",
    )
    assert m2["refusal_correct"] == 0.0
    assert m2["unsafe_answer"] == 1.0

    # 3. False refusal on answerable: relevant chunk was in top 3, but status is insufficient_evidence
    m3 = compute_item_metrics(
        item_type="answerable",
        expected_evidence=[{"span": "Valid policy"}],
        expected_facts=[],
        expected_value=None,
        expected_route="semantic",
        retrieved=[{"rank": 1, "relevant": True, "content": "Valid policy"}],
        answer=None,
        status="insufficient_evidence",
        citations=[],
        route="semantic",
    )
    assert m3["false_refusal"] == 1.0


def test_structured_tolerance_and_zero_llm_assertion():
    # Absolute tolerance match
    spec_abs = {"value": 100, "tolerance": 5, "tolerance_type": "absolute"}
    assert check_structured_value_match(104, spec_abs, llm_calls=0) == 1.0
    assert check_structured_value_match(106, spec_abs, llm_calls=0) == 0.0

    # Percentage tolerance match: 10% of 100 = 10
    spec_pct = {"value": 100, "tolerance": 10, "tolerance_type": "percentage"}
    assert check_structured_value_match(109, spec_pct, llm_calls=0) == 1.0
    assert check_structured_value_match(112, spec_pct, llm_calls=0) == 0.0

    # Zero LLM calls assertion: if llm_calls > 0, value_match fails strictly
    assert check_structured_value_match(100, spec_abs, llm_calls=1) == 0.0


def test_bootstrap_ci_determinism():
    data = [0.8, 0.9, 0.7, 0.85, 0.95, 0.6, 0.75, 0.88, 0.92, 0.81]
    res1 = bootstrap_ci(data, n_resamples=1000, seed=42)
    res2 = bootstrap_ci(data, n_resamples=1000, seed=42)

    assert res1["mean"] == res2["mean"]
    assert res1["ci_low"] == res2["ci_low"]
    assert res1["ci_high"] == res2["ci_high"]
    assert res1["n"] == 10
    assert res1["ci_low"] <= res1["mean"] <= res1["ci_high"]


def test_paired_bootstrap_comparison_known_delta():
    # Case 1: Variant A is strictly better than B by delta 0.2
    a = [0.8, 0.9, 0.85, 0.95]
    b = [0.6, 0.7, 0.65, 0.75]
    comp1 = paired_bootstrap_comparison(a, b, n_resamples=1000, seed=42)
    assert comp1["mean_delta"] == pytest.approx(0.2, abs=1e-4)
    assert comp1["wins"] == 4
    assert comp1["losses"] == 0
    assert comp1["ties"] == 0
    assert comp1["ci_low"] > 0
    assert "higher" in comp1["verdict"]

    # Case 2: Deltas cancel out so CI contains 0
    a2 = [0.8, 0.6, 0.7, 0.5]
    b2 = [0.6, 0.8, 0.5, 0.7]
    comp2 = paired_bootstrap_comparison(a2, b2, n_resamples=1000, seed=42)
    assert comp2["mean_delta"] == 0.0
    assert comp2["ci_low"] <= 0.0 <= comp2["ci_high"]
    assert comp2["verdict"] == "difference not distinguishable from zero"

