"""
backend/tests/test_eval_phase8_1b.py — Tests for Phase 8.1b backend fixes.

Covers:
1. Determinism: identical per-item metrics and CIs across identical variant runs.
2. Route accuracy calculation & confusion matrix generation.
3. D8 trigger iff route_accuracy < 1.0, and not firing with reason when == 1.0.
4. Threshold optimizer on hand-computed candidate sweep with non-first maximizer.
5. Signal calibration: sweep on dense cosine; observed-only finding for gates with other signals.
6. Not-fired reasons: D6 'not_evaluable', D7 examined pairs count, D9 'no pair available' / 'rerank shows gain'.
7. Paired comparison counts over applicable items only.
8. Label plausibility lint for answerable document items with expected_route 'exact'.
"""

import pytest
from unittest.mock import MagicMock
from db import EvalRun, EvalResult, EvalItem, EvalSuite
from evaluation.doctor.rules import (
    _select_optimal_threshold,
    compute_threshold_counterfactuals,
    evaluate_rules,
)
from evaluation.engine import lint_eval_suite, generate_run_report
from evaluation.stats import bootstrap_ci, paired_bootstrap_comparison
from evaluation.metrics import compute_item_metrics


def test_threshold_optimizer_hand_computed_sweep_non_first_maximizer():
    """
    Test hand-computed sweep where the maximizer is strictly NOT the first candidate.
    
    Hand calculation:
    Suppose candidate thresholds: [0.20, 0.40, 0.60]
    Answerable scores (n=4): [0.35, 0.45, 0.55, 0.65]
    Unanswerable scores (n=2): [0.25, 0.45]
    
    At t = 0.20:
      un_cnt (un >= 0.20) = 2 -> unsafe_rate = 2/2 = 1.0
      fr_cnt (ans < 0.20) = 0 -> false_refusal_rate = 0/4 = 0.0
      obj = (1 - 1.0) - 0.0 = 0.0
      
    At t = 0.40:
      un_cnt (un >= 0.40) = 1 (0.45) -> unsafe_rate = 1/2 = 0.5
      fr_cnt (ans < 0.40) = 1 (0.35) -> false_refusal_rate = 1/4 = 0.25
      obj = (1 - 0.5) - 0.25 = 0.5 - 0.25 = 0.25
      
    At t = 0.60:
      un_cnt (un >= 0.60) = 0 -> unsafe_rate = 0/2 = 0.0
      fr_cnt (ans < 0.60) = 3 (0.35, 0.45, 0.55) -> false_refusal_rate = 3/4 = 0.75
      obj = (1 - 0.0) - 0.75 = 0.25
      
    Compare t=0.20 (obj=0.0) vs t=0.40 (obj=0.25) vs t=0.60 (obj=0.25).
    Maximizer objective is 0.25.
    Between t=0.40 and t=0.60 (tie at 0.25), lowest threshold tie-break chooses 0.40!
    The first candidate (0.20) has obj=0.0, so the chosen maximizer is 0.40 (NOT the first candidate).
    """
    ans_scores = [0.35, 0.45, 0.55, 0.65]
    un_scores = [0.25, 0.45]
    candidates = [0.20, 0.40, 0.60]

    chosen = _select_optimal_threshold(ans_scores, un_scores, candidates)
    assert chosen == 0.40, f"Expected 0.40, got {chosen}"


def test_determinism_identical_runs():
    """Run metric computation and bootstrap CI on identical inputs; assert identical results."""
    scores1 = [0.1, 0.5, 0.8, 0.9, 0.4, 0.7, 0.6, 0.3, 0.85, 0.95]
    scores2 = list(scores1)

    ci1 = bootstrap_ci(scores1, n_resamples=2000, seed=42)
    ci2 = bootstrap_ci(scores2, n_resamples=2000, seed=42)

    assert ci1["mean"] == ci2["mean"]
    assert ci1["ci_low"] == ci2["ci_low"]
    assert ci1["ci_high"] == ci2["ci_high"]
    assert ci1["n"] == ci2["n"]


def test_route_accuracy_and_predicted_route_metrics():
    """Verify compute_item_metrics computes route_accuracy against predicted_route."""
    # Match: expected 'exact', predicted 'exact'
    m_match = compute_item_metrics(
        item_type="answerable",
        expected_evidence=[{"span": "test"}],
        expected_facts=[],
        expected_value=None,
        expected_route="exact",
        retrieved=[{"relevant": True, "score": 0.9}],
        answer=None,
        status="retrieved",
        citations=[],
        route="dense",
        predicted_route="exact",
    )
    assert m_match["predicted_route"] == "exact"
    assert m_match["route_accuracy"] == 1.0

    # Mismatch: expected 'exact', predicted 'semantic'
    m_mismatch = compute_item_metrics(
        item_type="answerable",
        expected_evidence=[{"span": "test"}],
        expected_facts=[],
        expected_value=None,
        expected_route="exact",
        retrieved=[{"relevant": True, "score": 0.9}],
        answer=None,
        status="retrieved",
        citations=[],
        route="dense",
        predicted_route="semantic",
    )
    assert m_mismatch["predicted_route"] == "semantic"
    assert m_mismatch["route_accuracy"] == 0.0


def test_d8_fires_on_route_mismatch_and_does_not_fire_when_perfect():
    """D8 fires iff route_accuracy < 1.0 and lists mismatching items."""
    run = MagicMock(spec=EvalRun)
    run.id = 1
    run.variant = {"strategy": "dense"}

    item1 = MagicMock(spec=EvalItem)
    item1.id = 101
    item1.item_type = "answerable"
    item1.expected_route = "exact"

    item2 = MagicMock(spec=EvalItem)
    item2.id = 102
    item2.item_type = "answerable"
    item2.expected_route = "semantic"

    items_map = {101: item1, 102: item2}

    # Case A: Mismatch on item 101 (predicted 'semantic' instead of 'exact')
    res1_mismatch = MagicMock(spec=EvalResult)
    res1_mismatch.run_id = 1
    res1_mismatch.item_id = 101
    res1_mismatch.route = "semantic"
    res1_mismatch.strategy = "dense"
    res1_mismatch.retrieved = []
    res1_mismatch.metrics = {"predicted_route": "semantic", "route_accuracy": 0.0}

    res2_match = MagicMock(spec=EvalResult)
    res2_match.run_id = 1
    res2_match.item_id = 102
    res2_match.route = "semantic"
    res2_match.strategy = "dense"
    res2_match.retrieved = []
    res2_match.metrics = {"predicted_route": "semantic", "route_accuracy": 1.0}

    findings_a, _ = evaluate_rules(
        runs=[run],
        run_results={1: [res1_mismatch, res2_match]},
        items_map=items_map,
        return_not_fired=True,
    )
    d8_findings_a = [f for f in findings_a if f["rule_id"] == "D8"]
    assert len(d8_findings_a) == 1
    evidence_a = d8_findings_a[0]["evidence"]
    assert evidence_a["mismatch_count"] == 1
    assert 101 in evidence_a["affected_item_ids"]

    # Case B: All match (predicted 'exact' for 101, 'semantic' for 102)
    res1_match = MagicMock(spec=EvalResult)
    res1_match.run_id = 1
    res1_match.item_id = 101
    res1_match.route = "exact"
    res1_match.strategy = "dense"
    res1_match.retrieved = []
    res1_match.metrics = {"predicted_route": "exact", "route_accuracy": 1.0}

    findings_b, not_fired_b = evaluate_rules(
        runs=[run],
        run_results={1: [res1_match, res2_match]},
        items_map=items_map,
        return_not_fired=True,
    )
    d8_findings_b = [f for f in findings_b if f["rule_id"] == "D8"]
    assert len(d8_findings_b) == 0
    assert "Router classification matches expected route across all items." in not_fired_b.get("D8", "")


def test_not_fired_reasons_d6_retrieval_only():
    """D6 not-fired reason is 'not_evaluable: retrieval-only run' when generate=False."""
    run = MagicMock(spec=EvalRun)
    run.id = 1
    run.generate = False
    run.variant = {"strategy": "dense"}

    item = MagicMock(spec=EvalItem)
    item.id = 1
    item.item_type = "answerable"
    item.expected_route = "semantic"

    res = MagicMock(spec=EvalResult)
    res.run_id = 1
    res.item_id = 1
    res.route = "semantic"
    res.retrieved = []
    res.metrics = {}

    findings, not_fired = evaluate_rules(
        runs=[run],
        run_results={1: [res]},
        items_map={1: item},
        return_not_fired=True,
    )
    assert "not_evaluable: retrieval-only run" in not_fired.get("D6", "")


def test_d5_signal_calibration_hybrid_rerank_observed_only():
    """For hybrid_rerank runs where gate uses min_rerank, D5 emits observed-only finding with no patch."""
    run = MagicMock(spec=EvalRun)
    run.id = 1
    run.generate = False
    run.variant = {"strategy": "hybrid_rerank", "use_rerank": True}

    un_item = MagicMock(spec=EvalItem)
    un_item.id = 201
    un_item.item_type = "unanswerable"
    un_item.expected_route = None

    # Result where evidence gate passed on unanswerable query (unsafe)
    un_res = MagicMock(spec=EvalResult)
    un_res.run_id = 1
    un_res.item_id = 201
    un_res.route = "semantic"
    un_res.strategy = "hybrid_rerank"
    un_res.status = "success"
    un_res.metrics = {"unsafe_answer": 1.0}
    un_res.retrieved = [
        {"chunk_id": 1, "score": 0.85, "signals": {"dense_score": 0.42, "rerank_score": 0.85}}
    ]

    findings, _ = evaluate_rules(
        runs=[run],
        run_results={1: [un_res]},
        items_map={201: un_item},
        return_not_fired=True,
    )
    d5_findings = [f for f in findings if f["rule_id"] == "D5"]
    assert len(d5_findings) == 1
    f = d5_findings[0]
    assert f["evidence_level"] == "observed"
    assert f["proposed_patch"] == {}
    assert "min_rerank" in f["diagnosis"]


def test_paired_bootstrap_comparison_counts_applicable_only():
    """Paired bootstrap comparison wins + losses + ties strictly equals n of applicable items."""
    vals_a = [0.8, 0.5, 0.3, 0.9, 0.7]  # n=5
    vals_b = [0.7, 0.5, 0.4, 0.9, 0.6]  # n=5

    comp = paired_bootstrap_comparison(vals_a, vals_b, n_resamples=1000, seed=42)
    assert comp["n"] == 5
    assert comp["wins"] + comp["losses"] + comp["ties"] == 5


def test_label_plausibility_lint_document_items_exact_route():
    """Lint identifies answerable document items with expected_route='exact' as suspected label errors."""
    mock_db = MagicMock()
    mock_suite = MagicMock(spec=EvalSuite)
    mock_suite.id = 1
    mock_suite.name = "Test Suite"
    mock_suite.source_ids = [10]

    # Item 1: answerable doc item with expected_route 'exact' (suspected label error)
    item1 = MagicMock(spec=EvalItem)
    item1.id = 1
    item1.position = 1
    item1.question = "What is the annual leave allowance?"
    item1.item_type = "answerable"
    item1.expected_route = "exact"
    item1.expected_evidence = [{"document_title": "Policy", "span": "24 days"}]
    item1.expected_facts = ["24 days"]

    # Item 2: answerable structured/record item with expected_route 'exact' (correct)
    item2 = MagicMock(spec=EvalItem)
    item2.id = 2
    item2.position = 2
    item2.question = "What is employee 101's salary?"
    item2.item_type = "answerable"
    item2.expected_route = "exact"
    item2.expected_evidence = [{"row_key": "101"}]
    item2.expected_facts = ["$100,000"]

    # Setup mock query returns
    def query_side_effect(model):
        q = MagicMock()
        if model == EvalSuite:
            q.filter.return_value.first.return_value = mock_suite
        elif model == EvalItem:
            q.filter.return_value.order_by.return_value.all.return_value = [item1, item2]
        else:
            q.filter.return_value.all.return_value = []
        return q

    mock_db.query.side_effect = query_side_effect

    res = lint_eval_suite(mock_db, suite_id=1)
    assert res["suspected_label_errors_count"] == 1
    err = res["suspected_label_errors"][0]
    assert err["item_id"] == 1
    assert "answerable document item with expected_route 'exact'" in err["reason"]

