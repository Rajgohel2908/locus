"""
retrieval/pipeline.py — Multi-strategy retrieval pipeline with metadata filtering,
evidence gates, explainability signals, and latency tracking.

Strategies supported:
1. 'dense'        — Baseline pgvector HNSW cosine similarity.
2. 'lexical'      — BM25 lexical retriever with LRU caching.
3. 'hybrid'       — Dense top N + BM25 top N fused via Reciprocal Rank Fusion (RRF).
4. 'hybrid_rerank'— Hybrid top RERANK_TOP_N reranked via CrossEncoder.

Every candidate carries:
signals = {
    "dense_rank": int | None,
    "dense_score": float | None,
    "lexical_rank": int | None,
    "lexical_score": float | None,
    "rrf_score": float | None,
    "rerank_score": float | None,
    "final_rank": int,
    "matched_terms": List[str],
}
"""

import time
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session

import config
from indexing.embedder import Embedder, get_embedder
from retrieval.dense import retrieve_dense, resolve_index_run_ids
from retrieval.lexical import LexicalRetriever, get_lexical_retriever
from retrieval.rerank import Reranker, get_reranker
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.filters import RetrievalFilters, resolve_allowed_chunk_ids

logger = logging.getLogger(__name__)


def evaluate_evidence_gate(
    strategy: str,
    candidates: List[Dict[str, Any]],
    min_score: float,
    min_bm25: float,
    min_rerank: float,
) -> Dict[str, Any]:
    """
    Evaluate explicit, per-strategy evidence gate:
    - dense: best cosine >= MIN_SCORE
    - lexical: best bm25 >= MIN_BM25
    - hybrid: best dense cosine >= MIN_SCORE OR best bm25 >= MIN_BM25 (reports which passed)
    - hybrid_rerank: best rerank score >= MIN_RERANK
    """
    if not candidates:
        return {
            "passed": False,
            "strategy": strategy,
            "signal": "none",
            "values": {},
            "thresholds": {
                "min_score": min_score,
                "min_bm25": min_bm25,
                "min_rerank": min_rerank,
            },
        }

    if strategy == "dense":
        best_cosine = max([c["score"] for c in candidates], default=0.0)
        passed = bool(best_cosine >= min_score)
        return {
            "passed": passed,
            "strategy": strategy,
            "signal": "cosine" if passed else "none",
            "values": {"cosine": best_cosine},
            "thresholds": {"min_score": min_score},
        }

    elif strategy == "lexical":
        best_bm25 = max([c["score"] for c in candidates], default=0.0)
        passed = bool(best_bm25 >= min_bm25)
        return {
            "passed": passed,
            "strategy": strategy,
            "signal": "bm25" if passed else "none",
            "values": {"bm25": best_bm25},
            "thresholds": {"min_bm25": min_bm25},
        }

    elif strategy == "hybrid":
        dense_scores = [
            c["signals"]["dense_score"]
            for c in candidates
            if c.get("signals", {}).get("dense_score") is not None
        ]
        lexical_scores = [
            c["signals"]["lexical_score"]
            for c in candidates
            if c.get("signals", {}).get("lexical_score") is not None
        ]

        best_dense = max(dense_scores, default=0.0)
        best_bm25 = max(lexical_scores, default=0.0)

        dense_passed = bool(best_dense >= min_score)
        bm25_passed = bool(best_bm25 >= min_bm25)
        passed = bool(dense_passed or bm25_passed)

        if dense_passed and bm25_passed:
            sig = "dense_and_bm25"
        elif dense_passed:
            sig = "dense"
        elif bm25_passed:
            sig = "bm25"
        else:
            sig = "none"

        return {
            "passed": passed,
            "strategy": strategy,
            "signal": sig,
            "values": {"dense_cosine": best_dense, "bm25": best_bm25},
            "thresholds": {"min_score": min_score, "min_bm25": min_bm25},
        }

    elif strategy == "hybrid_rerank":
        rerank_scores = [
            c.get("signals", {}).get("rerank_score", c.get("score", 0.0))
            for c in candidates
        ]
        best_rerank = max(rerank_scores, default=0.0)
        passed = bool(best_rerank >= min_rerank)
        return {
            "passed": passed,
            "strategy": strategy,
            "signal": "rerank" if passed else "none",
            "values": {"rerank": best_rerank},
            "thresholds": {"min_rerank": min_rerank},
        }

    else:
        raise ValueError(f"Unknown retrieval strategy: {strategy}")


def execute_pipeline(
    db: Session,
    question: str,
    source_ids: List[int],
    index_run_id: Optional[int] = None,
    strategy: str = "dense",
    filters: Optional[RetrievalFilters] = None,
    top_k: Optional[int] = None,
    candidates_n: Optional[int] = None,
    min_score: Optional[float] = None,
    min_bm25: Optional[float] = None,
    min_rerank: Optional[float] = None,
    embedder: Optional[Embedder] = None,
    lexical_retriever: Optional[LexicalRetriever] = None,
    reranker: Optional[Reranker] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, float], List[int]]:
    """
    Execute end-to-end multi-strategy retrieval pipeline.

    Returns:
        (retrieved_chunks, evidence_gate, latency_ms, resolved_run_ids)
    """
    valid_strategies = ("dense", "lexical", "hybrid", "hybrid_rerank")
    if strategy not in valid_strategies:
        raise ValueError(f"Invalid strategy '{strategy}'. Must be one of {valid_strategies}.")

    k = top_k if top_k is not None else config.TOP_K
    n = candidates_n if candidates_n is not None else config.CANDIDATES_N
    th_score = min_score if min_score is not None else config.MIN_SCORE
    th_bm25 = min_bm25 if min_bm25 is not None else config.MIN_BM25
    th_rerank = min_rerank if min_rerank is not None else config.MIN_RERANK

    t_pipeline_start = time.perf_counter()
    latency_ms = {
        "filter": 0.0,
        "dense": 0.0,
        "lexical": 0.0,
        "fuse": 0.0,
        "rerank": 0.0,
    }

    # 1. Resolve index runs
    run_ids = resolve_index_run_ids(db, source_ids=source_ids, index_run_id=index_run_id)
    if not run_ids:
        evidence = {
            "passed": False,
            "strategy": strategy,
            "signal": "none",
            "values": {},
            "thresholds": {"min_score": th_score, "min_bm25": th_bm25, "min_rerank": th_rerank},
        }
        return [], evidence, latency_ms, []

    # 2. Stage 1: Metadata Filtering
    t0 = time.perf_counter()
    allowed_chunk_ids = resolve_allowed_chunk_ids(db, run_ids=run_ids, filters=filters)
    latency_ms["filter"] = round((time.perf_counter() - t0) * 1000, 2)

    # Fast-fail if filters active but 0 chunks matched
    if allowed_chunk_ids is not None and len(allowed_chunk_ids) == 0:
        evidence = {
            "passed": False,
            "strategy": strategy,
            "signal": "none",
            "reason": "no_chunks_match_filters",
            "values": {},
            "thresholds": {"min_score": th_score, "min_bm25": th_bm25, "min_rerank": th_rerank},
        }
        return [], evidence, latency_ms, run_ids

    candidates: List[Dict[str, Any]] = []

    # 3. Strategy Execution
    if strategy == "dense":
        t0 = time.perf_counter()
        dense_results, _, _ = retrieve_dense(
            db=db,
            question=question,
            source_ids=source_ids,
            index_run_id=index_run_id,
            top_k=k,
            embedder=embedder,
            allowed_chunk_ids=allowed_chunk_ids,
        )
        latency_ms["dense"] = round((time.perf_counter() - t0) * 1000, 2)

        for c in dense_results:
            item = dict(c)
            signals = {
                "dense_rank": item["rank"],
                "dense_score": item["score"],
                "lexical_rank": None,
                "lexical_score": None,
                "rrf_score": None,
                "rerank_score": None,
                "final_rank": item["rank"],
                "matched_terms": [],
            }
            item["signals"] = signals
            candidates.append(item)

    elif strategy == "lexical":
        t0 = time.perf_counter()
        retriever = lexical_retriever or get_lexical_retriever()
        lex_results = retriever.retrieve(
            db=db,
            question=question,
            run_ids=run_ids,
            top_k=n,
            allowed_chunk_ids=allowed_chunk_ids,
        )
        latency_ms["lexical"] = round((time.perf_counter() - t0) * 1000, 2)

        for rank, c in enumerate(lex_results[:k], start=1):
            item = dict(c)
            item["rank"] = rank
            signals = {
                "dense_rank": None,
                "dense_score": None,
                "lexical_rank": c["rank"],
                "lexical_score": c["score"],
                "rrf_score": None,
                "rerank_score": None,
                "final_rank": rank,
                "matched_terms": c.get("matched_terms", []),
            }
            item["signals"] = signals
            candidates.append(item)

    elif strategy in ("hybrid", "hybrid_rerank"):
        # Dense top N
        t0 = time.perf_counter()
        dense_results, _, _ = retrieve_dense(
            db=db,
            question=question,
            source_ids=source_ids,
            index_run_id=index_run_id,
            top_k=n,
            embedder=embedder,
            allowed_chunk_ids=allowed_chunk_ids,
        )
        latency_ms["dense"] = round((time.perf_counter() - t0) * 1000, 2)

        # Lexical top N
        t0 = time.perf_counter()
        retriever = lexical_retriever or get_lexical_retriever()
        lex_results = retriever.retrieve(
            db=db,
            question=question,
            run_ids=run_ids,
            top_k=n,
            allowed_chunk_ids=allowed_chunk_ids,
        )
        latency_ms["lexical"] = round((time.perf_counter() - t0) * 1000, 2)

        dense_map = {c["chunk_id"]: c for c in dense_results}
        lex_map = {c["chunk_id"]: c for c in lex_results}

        # Reciprocal Rank Fusion
        t0 = time.perf_counter()
        fused = reciprocal_rank_fusion([dense_results, lex_results], k=config.RRF_K)
        latency_ms["fuse"] = round((time.perf_counter() - t0) * 1000, 2)

        if strategy == "hybrid":
            for rank, item in enumerate(fused[:k], start=1):
                cid = item["chunk_id"]
                dense_item = dense_map.get(cid)
                lex_item = lex_map.get(cid)
                signals = {
                    "dense_rank": dense_item["rank"] if dense_item else None,
                    "dense_score": dense_item["score"] if dense_item else None,
                    "lexical_rank": lex_item["rank"] if lex_item else None,
                    "lexical_score": lex_item["score"] if lex_item else None,
                    "rrf_score": item["rrf_score"],
                    "rerank_score": None,
                    "final_rank": rank,
                    "matched_terms": lex_item.get("matched_terms", []) if lex_item else [],
                }
                candidate = dict(item)
                candidate["score"] = item["rrf_score"]
                candidate["rank"] = rank
                candidate["signals"] = signals
                candidates.append(candidate)

        else:  # hybrid_rerank
            top_candidates_for_rerank = fused[:config.RERANK_TOP_N]

            t0 = time.perf_counter()
            rerank_engine = reranker or get_reranker()
            reranked = rerank_engine.rerank(query=question, chunks=top_candidates_for_rerank)
            latency_ms["rerank"] = round((time.perf_counter() - t0) * 1000, 2)

            for rank, item in enumerate(reranked[:k], start=1):
                cid = item["chunk_id"]
                dense_item = dense_map.get(cid)
                lex_item = lex_map.get(cid)
                signals = {
                    "dense_rank": dense_item["rank"] if dense_item else None,
                    "dense_score": dense_item["score"] if dense_item else None,
                    "lexical_rank": lex_item["rank"] if lex_item else None,
                    "lexical_score": lex_item["score"] if lex_item else None,
                    "rrf_score": item.get("rrf_score"),
                    "rerank_score": item.get("rerank_score"),
                    "final_rank": rank,
                    "matched_terms": lex_item.get("matched_terms", []) if lex_item else [],
                }
                candidate = dict(item)
                candidate["score"] = item.get("rerank_score", item.get("score", 0.0))
                candidate["rank"] = rank
                candidate["signals"] = signals
                candidates.append(candidate)

    # 4. Evidence Gate Evaluation
    evidence = evaluate_evidence_gate(
        strategy=strategy,
        candidates=candidates,
        min_score=th_score,
        min_bm25=th_bm25,
        min_rerank=th_rerank,
    )

    return candidates, evidence, latency_ms, run_ids
