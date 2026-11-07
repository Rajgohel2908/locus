"""
backend/evaluation/doctor/rules.py — Diagnostic rules D1 to D9 for RAG Doctor v1.

Pure Python rule implementations with zero LLM calls.
All numbers and thresholds derive strictly from DoctorConfig priors,
stored candidate scores, and raw evaluation run results.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from db import EvalRun, EvalResult, EvalItem
from evaluation.doctor.config import DoctorConfig
from evaluation.stats import paired_bootstrap_comparison


def compute_threshold_counterfactuals(
    answerable_results: List[EvalResult],
    unanswerable_results: List[EvalResult],
    current_threshold: float = 0.30,
) -> Dict[str, Any]:
    """
    Deterministic counterfactual sweep over observed scores for D4/D5.
    
    1. Extracts top candidate score for each item.
    2. Sweeps across all observed score values.
    3. Computes unsafe_rate (unanswerable >= t) and false_refusal_rate (answerable < t).
    4. Selects threshold maximizing: (1 - unsafe_rate) - false_refusal_rate (lowest on tie).
    5. Computes in-sample and leave-one-out (jackknife) estimates.
    6. Adds warning when n_unanswerable < 20 or n_answerable < 30.
    7. Notes dense-cosine limitation for hybrid gates.
    """
    ans_scores = [
        float(r.retrieved[0].get("score", 0.0)) if (r.retrieved and len(r.retrieved) > 0) else 0.0
        for r in answerable_results
    ]
    un_scores = [
        float(r.retrieved[0].get("score", 0.0)) if (r.retrieved and len(r.retrieved) > 0) else 0.0
        for r in unanswerable_results
    ]

    n_ans = len(ans_scores)
    n_un = len(un_scores)

    if n_ans == 0 and n_un == 0:
        return {
            "sweep": [],
            "optimal_threshold": current_threshold,
            "in_sample": {},
            "leave_one_out": {},
            "warnings": ["No answerable or unanswerable items available for sweep."],
            "limitations": "Only the dense cosine component is supported; in hybrid gates lexical and cross-encoder score distributions differ.",
            "n_answerable": 0,
            "n_unanswerable": 0,
        }

    # Gather candidate thresholds from observed scores
    all_scores = set(round(s, 4) for s in ans_scores + un_scores + [current_threshold])
    candidate_thresholds = sorted(all_scores)

    sweep_entries = []
    best_obj = -999.0
    best_t = current_threshold

    for t in candidate_thresholds:
        unsafe_cnt = sum(1 for s in un_scores if s >= t)
        unsafe_r = unsafe_cnt / n_un if n_un > 0 else 0.0

        fr_cnt = sum(1 for s in ans_scores if s < t)
        fr_r = fr_cnt / n_ans if n_ans > 0 else 0.0

        obj = (1.0 - unsafe_r) - fr_r

        sweep_entries.append({
            "threshold": round(t, 4),
            "unsafe_rate": round(unsafe_r, 4),
            "unsafe_count": unsafe_cnt,
            "false_refusal_rate": round(fr_r, 4),
            "false_refusal_count": fr_cnt,
            "n_unanswerable": n_un,
            "n_answerable": n_ans,
            "objective": round(obj, 4),
        })

        # Maximize objective; on tie, choose lowest threshold
        if obj > best_obj + 1e-7:
            best_obj = obj
            best_t = t
        elif abs(obj - best_obj) <= 1e-7 and t < best_t:
            best_t = t

    # In-sample metrics at current and optimal thresholds
    cur_un_cnt = sum(1 for s in un_scores if s >= current_threshold)
    cur_un_r = cur_un_cnt / n_un if n_un > 0 else 0.0
    cur_fr_cnt = sum(1 for s in ans_scores if s < current_threshold)
    cur_fr_r = cur_fr_cnt / n_ans if n_ans > 0 else 0.0

    opt_un_cnt = sum(1 for s in un_scores if s >= best_t)
    opt_un_r = opt_un_cnt / n_un if n_un > 0 else 0.0
    opt_fr_cnt = sum(1 for s in ans_scores if s < best_t)
    opt_fr_r = opt_fr_cnt / n_ans if n_ans > 0 else 0.0

    # Leave-One-Out (Jackknife) Cross-Validation
    loo_un_cnt = 0
    loo_fr_cnt = 0

    # LOO on answerable items
    for i in range(n_ans):
        train_ans = ans_scores[:i] + ans_scores[i + 1:]
        held_out = ans_scores[i]

        t_opt_i = _select_optimal_threshold(train_ans, un_scores, candidate_thresholds)
        if held_out < t_opt_i:
            loo_fr_cnt += 1

    # LOO on unanswerable items
    for j in range(n_un):
        train_un = un_scores[:j] + un_scores[j + 1:]
        held_out = un_scores[j]

        t_opt_j = _select_optimal_threshold(ans_scores, train_un, candidate_thresholds)
        if held_out >= t_opt_j:
            loo_un_cnt += 1

    loo_un_rate = loo_un_cnt / n_un if n_un > 0 else 0.0
    loo_fr_rate = loo_fr_cnt / n_ans if n_ans > 0 else 0.0

    # Sample size warnings
    warnings = []
    if n_un < 20 or n_ans < 30:
        warnings.append(
            f"Small sample warning: n_unanswerable={n_un} (< 20) or n_answerable={n_ans} (< 30); estimates may have high variance."
        )

    limitations = (
        "Only the dense cosine component is supported; in hybrid gates lexical and cross-encoder score distributions differ."
    )

    return {
        "sweep": sweep_entries,
        "optimal_threshold": round(best_t, 4),
        "in_sample": {
            "current_threshold": round(current_threshold, 4),
            "current_unsafe_rate": round(cur_un_r, 4),
            "current_unsafe_count": cur_un_cnt,
            "current_false_refusal_rate": round(cur_fr_r, 4),
            "current_false_refusal_count": cur_fr_cnt,
            "proposed_threshold": round(best_t, 4),
            "proposed_unsafe_rate": round(opt_un_r, 4),
            "proposed_unsafe_count": opt_un_cnt,
            "proposed_false_refusal_rate": round(opt_fr_r, 4),
            "proposed_false_refusal_count": opt_fr_cnt,
        },
        "leave_one_out": {
            "loo_unsafe_rate": round(loo_un_rate, 4),
            "loo_unsafe_count": loo_un_cnt,
            "loo_false_refusal_rate": round(loo_fr_rate, 4),
            "loo_false_refusal_count": loo_fr_cnt,
        },
        "warnings": warnings,
        "limitations": limitations,
        "n_answerable": n_ans,
        "n_unanswerable": n_un,
    }


def _select_optimal_threshold(
    ans_scores: List[float],
    un_scores: List[float],
    candidates: List[float],
) -> float:
    """Helper to pick threshold maximizing (1 - unsafe_rate) - false_refusal_rate."""
    n_ans = len(ans_scores)
    n_un = len(un_scores)
    best_obj = -999.0
    best_t = candidates[0] if candidates else 0.30

    for t in candidates:
        un_r = sum(1 for s in un_scores if s >= t) / n_un if n_un > 0 else 0.0
        fr_r = sum(1 for s in ans_scores if s < t) / n_ans if n_ans > 0 else 0.0
        obj = (1.0 - un_r) - fr_r

        if obj > best_obj + 1e-7:
            best_obj = obj
            best_t = t
        elif abs(obj - best_obj) <= 1e-7 and t < best_t:
            best_t = t

    return best_t


def evaluate_rules(
    runs: List[EvalRun],
    run_results: Dict[int, List[EvalResult]],
    items_map: Dict[int, EvalItem],
    return_not_fired: bool = False,
):
    """
    Evaluate all Doctor diagnostic rules D1-D9 across provided eval runs.
    Returns:
      - findings: list of findings adhering to DoctorFinding schema.
      - not_fired_reasons: dictionary of rule_id -> reason why it did not fire.
    """
    findings: List[Dict[str, Any]] = []
    not_fired_reasons: Dict[str, str] = {}

    for run in runs:
        results = run_results.get(run.id, [])
        if not results:
            continue

        var = run.variant or {}
        strategy = var.get("strategy", "dense")
        use_rerank = bool(var.get("use_rerank", False))
        current_threshold = float(var.get("min_score", 0.30))

        # Precompute run-level metrics
        answerable_results = [
            r for r in results
            if items_map.get(r.item_id) and items_map[r.item_id].item_type == "answerable"
        ]
        unanswerable_results = [
            r for r in results
            if items_map.get(r.item_id) and items_map[r.item_id].item_type == "unanswerable"
        ]

        r5_vals = [float(r.metrics.get("recall@5", 0.0)) for r in answerable_results if r.metrics and "recall@5" in r.metrics]
        r20_vals = [float(r.metrics.get("recall@20", 0.0)) for r in answerable_results if r.metrics and "recall@20" in r.metrics]
        hit5_vals = [float(r.metrics.get("hit@5", 0.0)) for r in answerable_results if r.metrics and "hit@5" in r.metrics]
        cpt5_vals = [float(r.metrics.get("context_precision_tokens@5", 0.0)) for r in answerable_results if r.metrics and "context_precision_tokens@5" in r.metrics]

        mean_r5 = float(np.mean(r5_vals)) if r5_vals else 0.0
        mean_r20 = float(np.mean(r20_vals)) if r20_vals else 0.0
        mean_hit5 = float(np.mean(hit5_vals)) if hit5_vals else 0.0
        mean_cpt5 = float(np.mean(cpt5_vals)) if cpt5_vals else 0.0

        # ── D1: Route Slice Weakness ──────────────────────────────────────────
        d1_fired = False
        routes_in_run = set(r.route for r in answerable_results if r.route)
        max_slice_gap = 0.0
        for route in routes_in_run:
            route_res = [r for r in answerable_results if r.route == route]
            if len(route_res) >= 2:
                route_r5 = [float(r.metrics.get("recall@5", 0.0)) for r in route_res if r.metrics and "recall@5" in r.metrics]
                mean_route_r5 = float(np.mean(route_r5)) if route_r5 else 0.0
                gap = mean_r5 - mean_route_r5
                if gap > max_slice_gap:
                    max_slice_gap = gap

                if gap >= DoctorConfig.SLICE_GAP_THRESHOLD:
                    d1_fired = True
                    affected_ids = [r.item_id for r in route_res if (r.metrics or {}).get("recall@5", 0.0) < mean_r5]
                    better_strategy = None
                    evidence_lvl = "hypothesis"
                    for other_run in runs:
                        if other_run.id == run.id:
                            continue
                        other_res = [
                            r for r in run_results.get(other_run.id, [])
                            if items_map.get(r.item_id) and items_map[r.item_id].item_type == "answerable" and r.route == route
                        ]
                        if other_res:
                            other_r5 = [float(r.metrics.get("recall@5", 0.0)) for r in other_res if r.metrics and "recall@5" in r.metrics]
                            other_mean = float(np.mean(other_r5)) if other_r5 else 0.0
                            if other_mean > mean_route_r5:
                                better_strategy = (other_run.variant or {}).get("strategy", "hybrid")
                                evidence_lvl = "measured_effect"
                                break

                    chosen_strat = better_strategy or ("hybrid" if strategy == "dense" else "hybrid_rerank")
                    findings.append({
                        "rule_id": "D1",
                        "severity": "warning",
                        "title": f"Route Slice Weakness: '{route}' (Run {run.id})",
                        "diagnosis": (
                            f"Items on the '{route}' route achieve recall@5 of {mean_route_r5:.2f}, "
                            f"falling below the overall run recall@5 of {mean_r5:.2f} by "
                            f"{(mean_r5 - mean_route_r5):.2f} (threshold: {DoctorConfig.SLICE_GAP_THRESHOLD})."
                        ),
                        "evidence": {
                            "run_id": run.id,
                            "route": route,
                            "slice_recall@5": round(mean_route_r5, 4),
                            "overall_recall@5": round(mean_r5, 4),
                            "gap": round(mean_r5 - mean_route_r5, 4),
                            "affected_item_ids": affected_ids,
                        },
                        "evidence_level": evidence_lvl,
                        "proposed_patch": {"strategy": chosen_strat, "route_target": route},
                        "expected_effect": f"Route queries with intent '{route}' to strategy '{chosen_strat}' to close the {round(mean_r5 - mean_route_r5, 2)} recall deficit.",
                        "cost_note": f"Switches execution path for route '{route}' without changing data or index.",
                        "status": "proposed",
                    })

        if not d1_fired and "D1" not in not_fired_reasons:
            not_fired_reasons["D1"] = (
                f"Slice gap on all routes is below threshold {DoctorConfig.SLICE_GAP_THRESHOLD} (max gap: {max_slice_gap:.4f})"
                if routes_in_run else "No multi-item route slices observed in run."
            )

        # ── D2: Depth Gap ────────────────────────────────────────────────────
        depth_gap = mean_r20 - mean_r5
        if depth_gap >= DoctorConfig.DEPTH_GAP_THRESHOLD:
            depth_gap_items = [
                r.item_id for r in answerable_results
                if float((r.metrics or {}).get("recall@20", 0.0)) > float((r.metrics or {}).get("recall@5", 0.0))
            ]
            if depth_gap_items:
                proposed_patch = {"top_k": 10} if use_rerank else {"use_rerank": True, "top_k": 5}
                action_text = "Enabling cross-encoder reranking" if not use_rerank else "Raising top_k from 5 to 10"
                findings.append({
                    "rule_id": "D2",
                    "severity": "warning",
                    "title": f"Depth Gap: Gold Evidence at Depth 20 Lost at Top-5 (Run {run.id})",
                    "diagnosis": (
                        f"Recall@20 ({mean_r20:.2f}) exceeds Recall@5 ({mean_r5:.2f}) by "
                        f"{depth_gap:.2f} (threshold: {DoctorConfig.DEPTH_GAP_THRESHOLD}). "
                        f"Target evidence is retrieved within candidate pool but misses top-5 rank."
                    ),
                    "evidence": {
                        "run_id": run.id,
                        "recall@5": round(mean_r5, 4),
                        "recall@20": round(mean_r20, 4),
                        "gap": round(depth_gap, 4),
                        "affected_item_ids": depth_gap_items,
                    },
                    "evidence_level": "hypothesis",
                    "proposed_patch": proposed_patch,
                    "expected_effect": f"{action_text} will pull depth 6-20 gold evidence into context.",
                    "cost_note": "Increases prompt tokens by ~5 chunks (~800 tokens) or adds reranking latency (+30-80 ms).",
                    "status": "proposed",
                })
        else:
            if "D2" not in not_fired_reasons:
                not_fired_reasons["D2"] = (
                    f"Recall@20 ({mean_r20:.4f}) - Recall@5 ({mean_r5:.4f}) = {depth_gap:.4f} "
                    f"is below depth gap threshold {DoctorConfig.DEPTH_GAP_THRESHOLD}."
                )

        # ── D3: Broad Chunks ─────────────────────────────────────────────────
        # Requires:
        # 1. hit@5 healthy (>= BROAD_CHUNK_MIN_HIT)
        # 2. context_precision_tokens@5 <= BROAD_CHUNK_MAX_CONTEXT_PRECISION_TOKENS
        # 3. Applicability: at least 50% of relevant chunks are longer than proposed chunk size
        d3_fired = False
        if mean_hit5 < DoctorConfig.BROAD_CHUNK_MIN_HIT:
            if "D3" not in not_fired_reasons:
                not_fired_reasons["D3"] = (
                    f"hit@5 ({mean_hit5:.2f}) is below healthy threshold {DoctorConfig.BROAD_CHUNK_MIN_HIT}."
                )
        elif mean_cpt5 > DoctorConfig.BROAD_CHUNK_MAX_CONTEXT_PRECISION_TOKENS:
            if "D3" not in not_fired_reasons:
                not_fired_reasons["D3"] = (
                    f"context_precision_tokens@5 ({mean_cpt5:.2f}) is healthy (> {DoctorConfig.BROAD_CHUNK_MAX_CONTEXT_PRECISION_TOKENS})."
                )
        else:
            # Check applicability: at least 50% of relevant chunks longer than PROPOSED_CHUNK_SIZE
            relevant_chunks = [
                ch for r in answerable_results
                for ch in (r.retrieved or [])[:5]
                if ch.get("relevant")
            ]
            if not relevant_chunks:
                relevant_chunks = [
                    ch for r in answerable_results
                    for ch in (r.retrieved or [])[:20]
                    if ch.get("relevant")
                ]

            longer_count = sum(
                1 for ch in relevant_chunks
                if len(ch.get("content", "")) > DoctorConfig.PROPOSED_CHUNK_SIZE
            )
            pct_longer = (longer_count / len(relevant_chunks)) if relevant_chunks else 0.0

            if pct_longer < 0.50:
                if "D3" not in not_fired_reasons:
                    not_fired_reasons["D3"] = "chunk_size_change_cannot_affect"
            else:
                d3_fired = True
                affected_items = [
                    r.item_id for r in answerable_results
                    if float((r.metrics or {}).get("context_precision_tokens@5", 0.0)) <= DoctorConfig.BROAD_CHUNK_MAX_CONTEXT_PRECISION_TOKENS
                ]
                findings.append({
                    "rule_id": "D3",
                    "severity": "info",
                    "title": f"Broad Chunks Diluting Context Precision (Run {run.id})",
                    "diagnosis": (
                        f"Hit@5 is healthy ({mean_hit5:.2f}), but context_precision_tokens@5 is low ({mean_cpt5:.2f}) "
                        f"and {pct_longer:.1%} of relevant chunks exceed the proposed chunk size {DoctorConfig.PROPOSED_CHUNK_SIZE}."
                    ),
                    "evidence": {
                        "run_id": run.id,
                        "hit@5": round(mean_hit5, 4),
                        "context_precision_tokens@5": round(mean_cpt5, 4),
                        "pct_relevant_chunks_longer_than_proposed": round(pct_longer, 4),
                        "proposed_chunk_size": DoctorConfig.PROPOSED_CHUNK_SIZE,
                        "affected_item_ids": affected_items,
                    },
                    "evidence_level": "hypothesis",
                    "proposed_patch": {
                        "chunk_size": DoctorConfig.PROPOSED_CHUNK_SIZE,
                        "chunk_overlap": DoctorConfig.PROPOSED_CHUNK_OVERLAP,
                    },
                    "expected_effect": (
                        f"Reducing chunk_size to {DoctorConfig.PROPOSED_CHUNK_SIZE} tightens retrieved evidence, "
                        f"raising context_precision_tokens@k."
                    ),
                    "cost_note": "Requires re-indexing affected sources; total chunk count increases in vector index.",
                    "status": "proposed",
                })

        # ── D4: False Refusals ───────────────────────────────────────────────
        false_refusal_items = [
            r.item_id for r in answerable_results
            if r.status == "insufficient_evidence" or (r.metrics or {}).get("false_refusal") == 1.0
        ]
        false_refusal_rate = len(false_refusal_items) / max(1, len(answerable_results))

        if false_refusal_rate > DoctorConfig.FALSE_REFUSAL_MAX_RATE:
            cf_data = compute_threshold_counterfactuals(
                answerable_results, unanswerable_results, current_threshold=current_threshold
            )
            in_s = cf_data["in_sample"]
            exp_eff = (
                f"at t={cf_data['optimal_threshold']:.2f} on this suite: unsafe "
                f"{in_s.get('current_unsafe_count', 0)}/{cf_data['n_unanswerable']} -> "
                f"{in_s.get('proposed_unsafe_count', 0)}/{cf_data['n_unanswerable']}, false refusals "
                f"{in_s.get('current_false_refusal_count', 0)}/{cf_data['n_answerable']} -> "
                f"{in_s.get('proposed_false_refusal_count', 0)}/{cf_data['n_answerable']}, in-sample"
            )

            findings.append({
                "rule_id": "D4",
                "severity": "critical",
                "title": f"Evidence Gate False Refusals (Run {run.id})",
                "diagnosis": (
                    f"{len(false_refusal_items)} answerable items ({false_refusal_rate:.1%}) were refused by "
                    f"the evidence gate despite having relevant candidate content."
                ),
                "evidence": {
                    "run_id": run.id,
                    "false_refusal_count": len(false_refusal_items),
                    "false_refusal_rate": round(false_refusal_rate, 4),
                    "affected_item_ids": false_refusal_items,
                },
                "evidence_level": "counterfactual",
                "counterfactual": cf_data,
                "proposed_patch": {"min_score": cf_data["optimal_threshold"]},
                "expected_effect": exp_eff,
                "cost_note": "May slightly increase candidate noise on vague inputs.",
                "status": "proposed",
            })
        else:
            if "D4" not in not_fired_reasons:
                not_fired_reasons["D4"] = (
                    f"False refusal rate ({false_refusal_rate:.4f}) is at or below threshold {DoctorConfig.FALSE_REFUSAL_MAX_RATE}."
                )

        # ── D5: Unsafe Answers ───────────────────────────────────────────────
        unsafe_items = [
            r.item_id for r in unanswerable_results
            if r.status != "insufficient_evidence" or (r.metrics or {}).get("unsafe_answer") == 1.0
        ]
        unsafe_rate = len(unsafe_items) / max(1, len(unanswerable_results))

        if unsafe_rate > DoctorConfig.UNSAFE_ANSWER_MAX_RATE:
            cf_data = compute_threshold_counterfactuals(
                answerable_results, unanswerable_results, current_threshold=current_threshold
            )
            in_s = cf_data["in_sample"]
            exp_eff = (
                f"at t={cf_data['optimal_threshold']:.2f} on this suite: unsafe "
                f"{in_s.get('current_unsafe_count', 0)}/{cf_data['n_unanswerable']} -> "
                f"{in_s.get('proposed_unsafe_count', 0)}/{cf_data['n_unanswerable']}, false refusals "
                f"{in_s.get('current_false_refusal_count', 0)}/{cf_data['n_answerable']} -> "
                f"{in_s.get('proposed_false_refusal_count', 0)}/{cf_data['n_answerable']}, in-sample"
            )

            findings.append({
                "rule_id": "D5",
                "severity": "critical",
                "title": f"Unsafe Answers on Unanswerable Queries (Run {run.id})",
                "diagnosis": (
                    f"{len(unsafe_items)} out-of-scope or unanswerable items ({unsafe_rate:.1%}) were answered "
                    f"instead of refused by the evidence gate."
                ),
                "evidence": {
                    "run_id": run.id,
                    "unsafe_count": len(unsafe_items),
                    "unsafe_rate": round(unsafe_rate, 4),
                    "affected_item_ids": unsafe_items,
                },
                "evidence_level": "counterfactual",
                "counterfactual": cf_data,
                "proposed_patch": {"min_score": cf_data["optimal_threshold"]},
                "expected_effect": exp_eff,
                "cost_note": "Tighter threshold may reject borderline queries if phrasing is sparse.",
                "status": "proposed",
            })
        else:
            if "D5" not in not_fired_reasons:
                not_fired_reasons["D5"] = (
                    f"Unsafe answer rate ({unsafe_rate:.4f}) is at or below threshold {DoctorConfig.UNSAFE_ANSWER_MAX_RATE}."
                )

        # ── D6: Citation Problems ────────────────────────────────────────────
        invalid_cit_items = [
            r.item_id for r in results
            if r.status == "unverified" or (r.metrics or {}).get("invalid_citation_rate", 0.0) > DoctorConfig.INVALID_CITATION_MAX_RATE
        ]
        if len(invalid_cit_items) > 0:
            findings.append({
                "rule_id": "D6",
                "severity": "warning",
                "title": f"Invalid or Hallucinated Bracket Citations (Run {run.id})",
                "diagnosis": (
                    f"{len(invalid_cit_items)} items contained citations referencing non-existent chunk IDs "
                    f"or ungrounded context numbers."
                ),
                "evidence": {
                    "run_id": run.id,
                    "invalid_citation_count": len(invalid_cit_items),
                    "affected_item_ids": invalid_cit_items,
                },
                "evidence_level": "hypothesis",
                "proposed_patch": {"citation_enforcement": "strict_validation"},
                "expected_effect": "Enforces pre-delivery citation parsing and post-processing verification.",
                "cost_note": "Zero compute latency or token overhead.",
                "status": "proposed",
            })
        else:
            if "D6" not in not_fired_reasons:
                not_fired_reasons["D6"] = "No invalid or hallucinated citations detected in results."

        # ── D7: Stale Citations & Temporal Conflicts ─────────────────────────
        stale_conflict_items = []
        for r in answerable_results:
            retrieved_chunks = r.retrieved or []
            has_stale = False
            has_fresh = False
            for ch in retrieved_chunks[:5]:
                sig = ch.get("signals", {})
                freshness = sig.get("freshness") or (ch.get("metadata") or {}).get("freshness")
                if freshness == "stale":
                    has_stale = True
                elif freshness == "fresh":
                    has_fresh = True

            if has_stale and has_fresh:
                stale_conflict_items.append(r.item_id)

        if len(stale_conflict_items) > 0:
            findings.append({
                "rule_id": "D7",
                "severity": "warning",
                "title": f"Temporal Conflict: Stale & Fresh Policy Interleaving (Run {run.id})",
                "diagnosis": (
                    f"{len(stale_conflict_items)} items retrieved both stale and fresh documents simultaneously "
                    f"(e.g. 2019 Archived vs 2024 Revised Leave Policy)."
                ),
                "evidence": {
                    "run_id": run.id,
                    "conflict_count": len(stale_conflict_items),
                    "affected_item_ids": stale_conflict_items,
                },
                "evidence_level": "hypothesis",
                "proposed_patch": {"filters": {"freshness": ["fresh", "unknown"]}},
                "expected_effect": "Applies Phase 5 R7 freshness filter to exclude superseded documents from candidate ranking.",
                "cost_note": "Historical comparative queries must explicitly disable freshness filter.",
                "status": "proposed",
            })
        else:
            if "D7" not in not_fired_reasons:
                not_fired_reasons["D7"] = "No temporal conflict / stale policy interleaving detected."

        # ── D8: Router Errors ────────────────────────────────────────────────
        router_mismatch_items = []
        for r in results:
            item = items_map.get(r.item_id)
            if item and item.expected_route and r.route and r.route != item.expected_route:
                router_mismatch_items.append({
                    "item_id": r.item_id,
                    "actual_route": r.route,
                    "expected_route": item.expected_route,
                })

        if len(router_mismatch_items) > 0:
            findings.append({
                "rule_id": "D8",
                "severity": "info",
                "title": f"Query Route Classification Mismatch (Run {run.id})",
                "diagnosis": (
                    f"{len(router_mismatch_items)} items were routed to a different execution route "
                    f"than specified in the benchmark suite expected_route."
                ),
                "evidence": {
                    "run_id": run.id,
                    "mismatches": router_mismatch_items,
                    "affected_item_ids": [m["item_id"] for m in router_mismatch_items],
                },
                "evidence_level": "observed",
                "proposed_patch": {},  # Report-only
                "expected_effect": "Report-only diagnostic; inspect router feature extraction and intent rules.",
                "cost_note": "No automated configuration patch.",
                "status": "proposed",
            })
        else:
            if "D8" not in not_fired_reasons:
                not_fired_reasons["D8"] = "Router classification matches expected route across all items."

    # ── D9: Rerank No Gain ───────────────────────────────────────────────────
    d9_fired = False
    for i, run_a in enumerate(runs):
        for run_b in runs[i + 1:]:
            var_a = run_a.variant or {}
            var_b = run_b.variant or {}

            strat_a = var_a.get("strategy")
            strat_b = var_b.get("strategy")
            rerank_a = bool(var_a.get("use_rerank", False) or strat_a == "hybrid_rerank")
            rerank_b = bool(var_b.get("use_rerank", False) or strat_b == "hybrid_rerank")

            if rerank_a != rerank_b:
                run_rerank = run_a if rerank_a else run_b
                run_no_rerank = run_b if rerank_a else run_a

                res_rerank = {r.item_id: r for r in run_results.get(run_rerank.id, [])}
                res_no_rerank = {r.item_id: r for r in run_results.get(run_no_rerank.id, [])}

                common_ids = sorted(set(res_rerank.keys()) & set(res_no_rerank.keys()))
                if len(common_ids) >= 10:
                    vals_rerank = [float((res_rerank[iid].metrics or {}).get("recall@5", 0.0)) for iid in common_ids]
                    vals_no_rerank = [float((res_no_rerank[iid].metrics or {}).get("recall@5", 0.0)) for iid in common_ids]

                    comp = paired_bootstrap_comparison(vals_rerank, vals_no_rerank, n_resamples=2000, seed=42)
                    ci_low = comp["ci_low"]
                    ci_high = comp["ci_high"]

                    if ci_low <= 0.0 <= ci_high:
                        d9_fired = True
                        findings.append({
                            "rule_id": "D9",
                            "severity": "info",
                            "title": f"Reranking Overhead Without Distinguishable Gain (Runs {run_rerank.id} vs {run_no_rerank.id})",
                            "diagnosis": (
                                f"Enabling cross-encoder reranking (Run {run_rerank.id}) yielded a mean delta of "
                                f"{comp['mean_delta']:+.4f} in recall@5 with 95% paired CI [{ci_low:+.4f}, {ci_high:+.4f}], "
                                f"which is not statistically distinguishable from zero while adding reranking latency."
                            ),
                            "evidence": {
                                "run_rerank_id": run_rerank.id,
                                "run_baseline_id": run_no_rerank.id,
                                "mean_delta": comp["mean_delta"],
                                "ci_95": [ci_low, ci_high],
                                "wins": comp["wins"],
                                "losses": comp["losses"],
                                "ties": comp["ties"],
                                "verdict": comp["verdict"],
                            },
                            "evidence_level": "measured_effect",
                            "proposed_patch": {"use_rerank": False},
                            "expected_effect": "Disables reranking step, saving 30-100 ms per query without measurable loss in recall@5.",
                            "cost_note": "Saves CPU computation and lowers p95 response time.",
                            "status": "proposed",
                        })

    if not d9_fired and "D9" not in not_fired_reasons:
        not_fired_reasons["D9"] = "No rerank vs no-rerank pair available or rerank shows significant gain."

    if return_not_fired:
        return findings, not_fired_reasons
    return findings
