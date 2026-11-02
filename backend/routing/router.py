"""
routing/router.py — Pure deterministic query router.

Decides the execution route and retrieval strategy based on QueryFeatures:
1. structured: aggregation_intent AND NOT row_identity_request AND mappable
   AND exactly one structured source resolved.
2. exact: identifier_hits or identifier_candidates present -> strategy "hybrid".
3. complex: comparison_intent or multi_part -> strategy "hybrid_rerank"
   (falls back to "hybrid" if cross-encoder unavailable).
4. semantic: everything else -> strategy "hybrid".

Every decision records rules that fired and rules considered but rejected.
Outputs ROUTER_RULES_VERSION = "router-rules-v1".
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from routing.features import QueryFeatures

ROUTER_RULES_VERSION = "router-rules-v1"


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    route: str                 # "structured" | "exact" | "complex" | "semantic"
    strategy: str              # "structured" | "hybrid" | "hybrid_rerank"
    reasons: List[str] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    fallbacks: List[str] = Field(default_factory=list)
    rules_version: str = ROUTER_RULES_VERSION


def decide_route(
    features: QueryFeatures,
    availability: Optional[Dict[str, Any]] = None,
) -> RouteDecision:
    """
    Pure deterministic route decider.
    Decision priority:
      a) structured
      b) exact
      c) complex
      d) semantic
    """
    reasons: List[str] = []
    fallbacks: List[str] = []

    # Signals summary
    signals: Dict[str, Any] = {
        "aggregation_intent": features.aggregation_intent.model_dump() if features.aggregation_intent else None,
        "row_identity_request": features.row_identity_request,
        "identifier_candidates": features.identifier_candidates,
        "identifier_hits": features.identifier_hits,
        "comparison_intent": features.comparison_intent,
        "multi_part": features.multi_part,
        "group_by_hint": features.group_by_hint,
        "mapped_columns": [c.model_dump() for c in features.mapped_columns],
        "filter_values": [f.model_dump() for f in features.filter_values],
        "mappable": features.mappable,
        "mappable_reason": features.mappable_reason,
        "target_source_id": features.target_source_id,
        "target_column": features.target_column,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # a) Rule: structured
    # ─────────────────────────────────────────────────────────────────────────
    is_structured = (
        features.aggregation_intent is not None
        and features.mappable
        and features.target_source_id is not None
        and (not features.row_identity_request or (features.row_identity_request and features.target_column is not None))
    )

    if is_structured:
        op = features.aggregation_intent.op
        if features.row_identity_request:
            reasons.append(
                f"rule_structured_fired: op='{op}', target_col='{features.target_column}', "
                f"template='top_n', top_n={features.top_n}, filters={len(features.filter_values)}, "
                f"source_id={features.target_source_id}"
            )
        else:
            reasons.append(
                f"rule_structured_fired: op='{op}', target_col='{features.target_column}', "
                f"group_by='{features.group_by_hint}', filters={len(features.filter_values)}, "
                f"source_id={features.target_source_id}"
            )
        return RouteDecision(
            route="structured",
            strategy="structured",
            reasons=reasons,
            signals=signals,
            fallbacks=fallbacks,
            rules_version=ROUTER_RULES_VERSION,
        )
    else:
        # Record why structured was considered and rejected
        if features.aggregation_intent is None:
            reasons.append("rule_structured_rejected: no_aggregation_intent")
        elif features.mappable_reason.startswith("unmapped_terms"):
            reasons.append(f"rule_structured_rejected: {features.mappable_reason}")
        elif features.row_identity_request:
            reasons.append(f"rule_structured_rejected: {features.mappable_reason}")
        elif not features.mappable:
            reasons.append(f"rule_structured_rejected: not_mappable ({features.mappable_reason})")
        elif features.target_source_id is None:
            reasons.append("rule_structured_rejected: no_single_structured_source_resolved")

    # ─────────────────────────────────────────────────────────────────────────
    # b) Rule: exact
    # ─────────────────────────────────────────────────────────────────────────
    has_exact = (len(features.identifier_hits) > 0) or (len(features.identifier_candidates) > 0)
    if has_exact:
        detail = (
            f"identifier_hits={features.identifier_hits}"
            if features.identifier_hits
            else f"identifier_candidates={features.identifier_candidates}"
        )
        reasons.append(f"rule_exact_fired: {detail} -> strategy hybrid")
        return RouteDecision(
            route="exact",
            strategy="hybrid",
            reasons=reasons,
            signals=signals,
            fallbacks=fallbacks,
            rules_version=ROUTER_RULES_VERSION,
        )
    else:
        reasons.append("rule_exact_rejected: no_identifier_hits_or_candidates")

    # ─────────────────────────────────────────────────────────────────────────
    # c) Rule: complex
    # ─────────────────────────────────────────────────────────────────────────
    has_complex = features.comparison_intent or features.multi_part
    if has_complex:
        cross_encoder_ok = True
        if availability is not None:
            cross_encoder_ok = availability.get("cross_encoder_available", True)

        if cross_encoder_ok:
            chosen_strat = "hybrid_rerank"
        else:
            chosen_strat = "hybrid"
            fallbacks.append("cross_encoder_unavailable: fallback from hybrid_rerank to hybrid")

        reasons.append(
            f"rule_complex_fired: comparison={features.comparison_intent}, "
            f"multi_part={features.multi_part} -> strategy {chosen_strat}"
        )
        return RouteDecision(
            route="complex",
            strategy=chosen_strat,
            reasons=reasons,
            signals=signals,
            fallbacks=fallbacks,
            rules_version=ROUTER_RULES_VERSION,
        )
    else:
        reasons.append("rule_complex_rejected: neither comparison nor multi_part query")

    # ─────────────────────────────────────────────────────────────────────────
    # d) Rule: semantic
    # ─────────────────────────────────────────────────────────────────────────
    reasons.append("rule_semantic_fired: default RAG retrieval path -> strategy hybrid")
    return RouteDecision(
        route="semantic",
        strategy="hybrid",
        reasons=reasons,
        signals=signals,
        fallbacks=fallbacks,
        rules_version=ROUTER_RULES_VERSION,
    )
