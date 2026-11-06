"""
backend/recommender/rules.py — Deterministic rule-based strategy recommender.

RULES_VERSION = "recommender-rules-v1"
All thresholds are priors stored in RECOMMENDER_THRESHOLDS.
No LLM, no tuning, no confidence score.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple

RULES_VERSION = "recommender-rules-v1"

RECOMMENDER_THRESHOLDS = {
    "structured_min_numeric_cols": 1,
    "structured_min_active_rows": 10,
    "tiny_corpus_chunk_limit": 30,         # < 30 -> tiny
    "rerank_min_chunks": 50,               # >= 50 and goal in (qa, comparison) -> rerank
    "chunk_sizing_small_threshold": 300,   # < 300 words -> 500/75
    "chunk_sizing_large_threshold": 1500,  # > 1500 words -> 1000/150
    "stale_share_threshold": 0.20,          # >= 20% of dated items -> stale warning
    "undated_share_threshold": 0.50,        # >= 50% undated -> warning
    "ocr_share_threshold": 0.30,            # >= 30% OCR -> filter + warning
    "ocr_confidence_threshold": 70.0,       # < 70 mean confidence -> filter + warning
    "non_latin_script_threshold": 0.20,     # >= 20% non-Latin -> warning
}

VALID_GOALS = {"qa", "search", "comparison", "analysis"}


def get_baseline_spec() -> Dict[str, Any]:
    """Phase 4 baseline pipeline specification."""
    return {
        "chunk_size": 800,
        "chunk_overlap": 120,
        "chunk_unit": "characters",
        "strategy_default": "dense",
        "use_rerank": False,
        "top_k": 5,
        "candidates_n": 20,
        "filters_default": {},
        "structured_route_enabled": False,
        "router_enabled": False,
        "suggested_filters": {},
        "notes": ["Phase 4 baseline configuration. Chunk size and overlap are in characters."],
        "basis": "Phase 4 baseline behavior",
    }


def compute_spec_hash(spec: Dict[str, Any]) -> str:
    """Deterministic hash of a pipeline spec."""
    serialized = json.dumps(spec, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def evaluate_rules(profile: Dict[str, Any], goal: str) -> Dict[str, Any]:
    """
    Evaluate rules R1 through R12 against the KB profile and goal.

    Returns:
        {
            "rules_version": "recommender-rules-v1",
            "goal": goal,
            "pipeline_spec": dict,
            
            "rules_fired": list,
            "rules_not_fired": list,
            "warnings": list,
        }
    """
    if goal not in VALID_GOALS:
        raise ValueError(
            f"Invalid goal '{goal}'. Supported goals: {sorted(list(VALID_GOALS))} "
            f"(summarization is not supported yet)."
        )

    t = RECOMMENDER_THRESHOLDS
    rules_fired = []
    rules_not_fired = []
    warnings = []
    notes = []

    # Default spec initial values
    chunk_size = 800
    chunk_overlap = 120
    strategy_default = "hybrid"
    use_rerank = False
    top_k = 5
    candidates_n = 20
    filters_default: Dict[str, Any] = {}
    suggested_filters: Dict[str, Any] = {}
    structured_route_enabled = False

    # Extract metrics from profile
    sources_struct_count = profile.get("sources", {}).get("by_type", {}).get("structured", 0)
    num_cols = profile.get("structured", {}).get("numeric_columns_count", 0)
    active_rows = profile.get("structured", {}).get("active_row_count", 0)
    id_cols = profile.get("structured", {}).get("identifier_columns", [])
    total_chunks = profile.get("documents", {}).get("total_chunks", 0)
    total_docs = profile.get("documents", {}).get("total", 0)
    avg_words = profile.get("documents", {}).get("avg_words_per_doc", 0.0)
    stale_share = profile.get("text", {}).get("stale_share", 0.0)
    dated_count = profile.get("text", {}).get("dated_count", 0)
    undated_share = profile.get("text", {}).get("undated_share", 0.0)
    ocr_share = profile.get("text", {}).get("ocr_share", 0.0)
    mean_conf = profile.get("text", {}).get("mean_extraction_confidence", 100.0)
    non_latin_share = profile.get("scripts", {}).get("non_latin_share", 0.0)
    latest_ver = profile.get("quality_state", {}).get("latest_version_no", 1)
    dup_rows = profile.get("quality_state", {}).get("duplicate_rows", 0)
    pending_crit = profile.get("quality_state", {}).get("pending_critical_proposals", 0)

    # ─────────────────────────────────────────────────────────────────────────
    # R1: structured_present
    # a structured source with >= 1 numeric column and >= 10 active rows
    # ─────────────────────────────────────────────────────────────────────────
    r1_cond = (sources_struct_count >= 1 and num_cols >= t["structured_min_numeric_cols"] and active_rows >= t["structured_min_active_rows"])
    if r1_cond:
        structured_route_enabled = True
        rules_fired.append({
            "id": "R1",
            "name": "structured_present",
            "fired": True,
            "effect": "structured_route_enabled=True",
            "reason": (
                f"Structured source found with {num_cols} numeric column(s) "
                f"(threshold >= {t['structured_min_numeric_cols']}) and {active_rows} active row(s) "
                f"(threshold >= {t['structured_min_active_rows']})."
            ),
        })
    else:
        structured_route_enabled = False
        rules_not_fired.append({
            "id": "R1",
            "name": "structured_present",
            "fired": False,
            "effect": "structured_route_enabled=False",
            "reason": (
                f"No qualifying structured source: structured sources={sources_struct_count}, "
                f"numeric columns={num_cols} (< {t['structured_min_numeric_cols']}), "
                f"active rows={active_rows} (< {t['structured_min_active_rows']})."
            ),
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R2: identifier_present
    # identifier column in a structured source -> strategy_default="hybrid",
    # note that exact-ID queries benefit from lexical retrieval
    # ─────────────────────────────────────────────────────────────────────────
    if len(id_cols) >= 1:
        strategy_default = "hybrid"
        note_text = "Exact-ID queries benefit from lexical retrieval."
        if note_text not in notes:
            notes.append(note_text)
        rules_fired.append({
            "id": "R2",
            "name": "identifier_present",
            "fired": True,
            "effect": "strategy_default='hybrid', note added",
            "reason": f"Identifier column(s) present ({', '.join(id_cols)}); exact-ID queries benefit from lexical retrieval.",
        })
    else:
        rules_not_fired.append({
            "id": "R2",
            "name": "identifier_present",
            "fired": False,
            "effect": "none",
            "reason": "No identifier column found in structured sources.",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R3: tiny_corpus
    # total chunks of requested sources < 30 -> strategy_default="dense", use_rerank=false
    # ─────────────────────────────────────────────────────────────────────────
    if total_chunks < t["tiny_corpus_chunk_limit"]:
        strategy_default = "dense"
        use_rerank = False
        rules_fired.append({
            "id": "R3",
            "name": "tiny_corpus",
            "fired": True,
            "effect": "strategy_default='dense', use_rerank=False",
            "reason": (
                f"Total corpus chunks is {total_chunks} (< {t['tiny_corpus_chunk_limit']}); "
                f"BM25 statistics are unreliable on tiny corpora."
            ),
        })
    else:
        rules_not_fired.append({
            "id": "R3",
            "name": "tiny_corpus",
            "fired": False,
            "effect": "none",
            "reason": (
                f"Total corpus chunks is {total_chunks} (>= {t['tiny_corpus_chunk_limit']}); "
                f"corpus size is sufficient for lexical/hybrid indexing."
            ),
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R4: default_text
    # otherwise strategy_default="hybrid"
    # ─────────────────────────────────────────────────────────────────────────
    if total_chunks >= t["tiny_corpus_chunk_limit"]:
        strategy_default = "hybrid"
        rules_fired.append({
            "id": "R4",
            "name": "default_text",
            "fired": True,
            "effect": "strategy_default='hybrid'",
            "reason": (
                f"Corpus chunks {total_chunks} >= {t['tiny_corpus_chunk_limit']}; "
                f"hybrid retrieval balances semantic and lexical recall."
            ),
        })
    else:
        rules_not_fired.append({
            "id": "R4",
            "name": "default_text",
            "fired": False,
            "effect": "none",
            "reason": f"Corpus is tiny ({total_chunks} chunks < {t['tiny_corpus_chunk_limit']}), R3 took precedence.",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R5: rerank_policy
    # use_rerank=true only if goal in (qa, comparison) AND total chunks >= 50; else false
    # ─────────────────────────────────────────────────────────────────────────
    r5_cond = (goal in ("qa", "comparison") and total_chunks >= t["rerank_min_chunks"])
    if r5_cond:
        use_rerank = True
        rules_fired.append({
            "id": "R5",
            "name": "rerank_policy",
            "fired": True,
            "effect": "use_rerank=True",
            "reason": (
                f"Goal is '{goal}' and total corpus chunks is {total_chunks} "
                f"(threshold >= {t['rerank_min_chunks']}); cross-encoder reranking active."
            ),
        })
    else:
        use_rerank = False
        rules_not_fired.append({
            "id": "R5",
            "name": "rerank_policy",
            "fired": False,
            "effect": "use_rerank=False",
            "reason": (
                f"Reranking criteria not met: goal '{goal}' in ('qa','comparison')={goal in ('qa', 'comparison')}, "
                f"total chunks {total_chunks} >= {t['rerank_min_chunks']} is {total_chunks >= t['rerank_min_chunks']}."
            ),
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R6: chunk_sizing
    # from average words per document/page:
    # < 300 -> 500/75; 300-1500 -> 800/120; > 1500 -> 1000/150
    # ─────────────────────────────────────────────────────────────────────────
    if avg_words < t["chunk_sizing_small_threshold"]:
        chunk_size = 500
        chunk_overlap = 75
        size_reason = (
            f"Average words per document/page is {avg_words:.1f} (< {t['chunk_sizing_small_threshold']}); "
            f"assigned compact chunks 500/75."
        )
    elif avg_words <= t["chunk_sizing_large_threshold"]:
        chunk_size = 800
        chunk_overlap = 120
        size_reason = (
            f"Average words per document/page is {avg_words:.1f} "
            f"({t['chunk_sizing_small_threshold']} to {t['chunk_sizing_large_threshold']}); "
            f"assigned standard chunks 800/120."
        )
    else:
        chunk_size = 1000
        chunk_overlap = 150
        size_reason = (
            f"Average words per document/page is {avg_words:.1f} (> {t['chunk_sizing_large_threshold']}); "
            f"assigned large chunks 1000/150."
        )

    rules_fired.append({
        "id": "R6",
        "name": "chunk_sizing",
        "fired": True,
        "effect": f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}, chunk_unit='characters'",
        "reason": size_reason,
    })
    notes.append("Chunk size and overlap are measured in characters.")

    # ─────────────────────────────────────────────────────────────────────────
    # R7: stale_content
    # stale share >= 20% of dated chunks/docs -> warning plus OPTIONAL suggested filter
    # freshness in [fresh, aging, unknown]; never applied silently
    # ─────────────────────────────────────────────────────────────────────────
    if dated_count > 0 and stale_share >= t["stale_share_threshold"]:
        suggested_filters["freshness"] = ["fresh", "aging", "unknown"]
        warn_msg = (
            f"Stale content share is {stale_share:.1%} of dated items (threshold >= {t['stale_share_threshold']:.1%}). "
            f"Suggested freshness filter ['fresh', 'aging', 'unknown'] recommended."
        )
        warnings.append(warn_msg)
        rules_fired.append({
            "id": "R7",
            "name": "stale_content",
            "fired": True,
            "effect": "suggested_filters.freshness=['fresh', 'aging', 'unknown'], warning emitted",
            "reason": f"Stale content share is {stale_share:.1%} (>= {t['stale_share_threshold']:.1%} of {dated_count} dated items).",
        })
    else:
        rules_not_fired.append({
            "id": "R7",
            "name": "stale_content",
            "fired": False,
            "effect": "none",
            "reason": f"Stale share is {stale_share:.1%} (< {t['stale_share_threshold']:.1%} of {dated_count} dated items).",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R8: undated_documents
    # >= 50% undated -> warning to set document dates via overrides
    # ─────────────────────────────────────────────────────────────────────────
    if total_docs > 0 and undated_share >= t["undated_share_threshold"]:
        warn_msg = (
            f"Undated documents share is {undated_share:.1%} (threshold >= {t['undated_share_threshold']:.1%}). "
            f"Recommend setting document dates via overrides."
        )
        warnings.append(warn_msg)
        rules_fired.append({
            "id": "R8",
            "name": "undated_documents",
            "fired": True,
            "effect": "warning emitted to set document dates via overrides",
            "reason": f"Undated document share is {undated_share:.1%} (>= {t['undated_share_threshold']:.1%} of {total_docs} docs).",
        })
    else:
        rules_not_fired.append({
            "id": "R8",
            "name": "undated_documents",
            "fired": False,
            "effect": "none",
            "reason": f"Undated document share is {undated_share:.1%} (< {t['undated_share_threshold']:.1%} of {total_docs} docs).",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R9: ocr_quality
    # OCR share >= 30% or mean confidence < 70 -> filters_default.min_extraction_confidence=60 plus warning
    # ─────────────────────────────────────────────────────────────────────────
    r9_cond = (ocr_share >= t["ocr_share_threshold"] or mean_conf < t["ocr_confidence_threshold"])
    if r9_cond:
        filters_default["min_extraction_confidence"] = 60
        warn_msg = (
            f"OCR quality issue: OCR share={ocr_share:.1%} (threshold >= {t['ocr_share_threshold']:.1%}) "
            f"or mean extraction confidence={mean_conf:.1f} (threshold < {t['ocr_confidence_threshold']:.1f}). "
            f"Applied default filter min_extraction_confidence=60."
        )
        warnings.append(warn_msg)
        rules_fired.append({
            "id": "R9",
            "name": "ocr_quality",
            "fired": True,
            "effect": "filters_default.min_extraction_confidence=60, warning emitted",
            "reason": f"OCR share is {ocr_share:.1%} (>= 30.0%) or mean confidence is {mean_conf:.1f} (< 70.0).",
        })
    else:
        rules_not_fired.append({
            "id": "R9",
            "name": "ocr_quality",
            "fired": False,
            "effect": "none",
            "reason": f"OCR share is {ocr_share:.1%} (< 30.0%) and mean confidence is {mean_conf:.1f} (>= 70.0).",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R10: non_latin_script
    # non-Latin share >= 20% of characters -> warning that default English-centric
    # embedder and reranker are weak for this content; suggest multilingual model
    # with 384-dim output; never switch automatically
    # ─────────────────────────────────────────────────────────────────────────
    if non_latin_share >= t["non_latin_script_threshold"]:
        warn_msg = (
            f"Non-Latin script share is {non_latin_share:.1%} (threshold >= {t['non_latin_script_threshold']:.1%}). "
            f"Default English-centric embedder and reranker are weak for this content; "
            f"suggest evaluating a multilingual model with 384-dim output (user must verify)."
        )
        warnings.append(warn_msg)
        rules_fired.append({
            "id": "R10",
            "name": "non_latin_script",
            "fired": True,
            "effect": "warning emitted to evaluate multilingual model",
            "reason": f"Non-Latin script share is {non_latin_share:.1%} (>= {t['non_latin_script_threshold']:.1%} of characters).",
        })
    else:
        rules_not_fired.append({
            "id": "R10",
            "name": "non_latin_script",
            "fired": False,
            "effect": "none",
            "reason": f"Non-Latin script share is {non_latin_share:.1%} (< {t['non_latin_script_threshold']:.1%}).",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R11: uncleaned_data
    # latest version is 1 with duplicates or pending critical proposals -> warning
    # ─────────────────────────────────────────────────────────────────────────
    r11_cond = (latest_ver == 1 and (dup_rows > 0 or pending_crit > 0))
    if r11_cond:
        warn_msg = (
            f"Recommendation rests on uncleaned data (version {latest_ver}, {dup_rows} duplicate row(s), "
            f"{pending_crit} pending critical cleaning proposal(s)). Cleaning should be approved first."
        )
        warnings.append(warn_msg)
        rules_fired.append({
            "id": "R11",
            "name": "uncleaned_data",
            "fired": True,
            "effect": "warning emitted that recommendation rests on uncleaned data",
            "reason": f"Latest version is {latest_ver} with {dup_rows} duplicate rows and {pending_crit} pending critical proposals.",
        })
    else:
        rules_not_fired.append({
            "id": "R11",
            "name": "uncleaned_data",
            "fired": False,
            "effect": "none",
            "reason": f"Data is cleaned or clean (version {latest_ver}, {dup_rows} duplicates, {pending_crit} pending critical proposals).",
        })

    # ─────────────────────────────────────────────────────────────────────────
    # R12: goal_adjustments
    # search -> top_k=10 and use_rerank=false; comparison -> top_k=8;
    # analysis -> structured_route_enabled emphasized, warning if no structured source;
    # qa -> top_k=5
    # ─────────────────────────────────────────────────────────────────────────
    if goal == "search":
        top_k = 10
        use_rerank = False
        goal_reason = "Goal 'search': increased top_k=10 for broad retrieval recall, reranking disabled."
    elif goal == "comparison":
        top_k = 8
        goal_reason = "Goal 'comparison': top_k=8 for multi-document synthesis."
    elif goal == "analysis":
        top_k = 5
        goal_reason = "Goal 'analysis': structured route emphasized."
        if sources_struct_count == 0:
            analysis_warn = "Goal is analysis but no structured source is present."
            warnings.append(analysis_warn)
    else:  # qa
        top_k = 5
        goal_reason = "Goal 'qa': top_k=5 for precise answer extraction."

    rules_fired.append({
        "id": "R12",
        "name": "goal_adjustments",
        "fired": True,
        "effect": f"top_k={top_k}, use_rerank={use_rerank}",
        "reason": goal_reason,
    })

    pipeline_spec = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "chunk_unit": "characters",
        "strategy_default": strategy_default,
        "use_rerank": use_rerank,
        "top_k": top_k,
        "candidates_n": candidates_n,
        "filters_default": filters_default,
        "structured_route_enabled": structured_route_enabled,
        "router_enabled": True,
        "suggested_filters": suggested_filters,
        "notes": notes,
        "basis": "rule-based priors, not validated; compare with evaluation in Phase 7",
    }

    return {
        "rules_version": RULES_VERSION,
        "goal": goal,
        "pipeline_spec": pipeline_spec,
        "rules_fired": rules_fired,
        "rules_not_fired": rules_not_fired,
        "warnings": warnings,
    }
