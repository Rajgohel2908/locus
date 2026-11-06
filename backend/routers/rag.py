"""
routers/rag.py — RAG Query, comparison, and evaluation endpoints.

Phases 4 & 5 endpoints:
POST /query            — Execute retrieval (dense, lexical, hybrid, hybrid_rerank) + LLM generation
POST /retrieve/compare — Multi-strategy retrieval comparison without calling LLM
GET  /queries/{id}     — Retrieve details of a past query, cited chunks, strategy, and signals
GET  /queries          — List recent queries
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db, QueryRecord, RetrievalResult, Chunk
from retrieval.filters import RetrievalFilters
from retrieval.pipeline import execute_pipeline
from generation.answer import execute_query

from routing.context import build_schema_context
from routing.features import extract_features
from routing.router import decide_route

router = APIRouter()


class RouteRequest(BaseModel):
    question: str
    source_ids: Optional[List[int]] = None
    version: Optional[int] = None


class QueryRequest(BaseModel):
    question: str
    source_ids: Optional[List[int]] = None
    index_run_id: Optional[int] = None
    top_k: Optional[int] = None
    min_score: Optional[float] = None
    # Phase 5 additions
    strategy: Optional[str] = None
    filters: Optional[RetrievalFilters] = None
    candidates_n: Optional[int] = None
    min_bm25: Optional[float] = None
    min_rerank: Optional[float] = None
    # Phase 6 additions
    version: Optional[int] = None
    # Phase 6B additions
    pipeline_config_id: Optional[int] = None


@router.post("/route", summary="Analyze query and return deterministic routing decision")
def route_query_endpoint(
    req: RouteRequest,
    db: Session = Depends(get_db),
):
    """
    Pure rule-based query analyzer and router.
    Evaluates schema context, extracts features, and decides execution route (structured, exact, complex, semantic).
    CRITICAL: Does NOT call LLM, does NOT call embedding model, and does NOT execute query.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    context = build_schema_context(db=db, source_ids=req.source_ids, version=req.version)
    features = extract_features(req.question.strip(), context)
    decision = decide_route(features)
    return {
        "route": decision.route,
        "strategy": decision.strategy,
        "reasons": decision.reasons,
        "signals": decision.signals,
        "fallbacks": decision.fallbacks,
        "rules_version": decision.rules_version,
        "features": features.model_dump(),
    }


class CompareRequest(BaseModel):
    question: str
    source_ids: Optional[List[int]] = None
    index_run_id: Optional[int] = None
    filters: Optional[RetrievalFilters] = None
    top_k: Optional[int] = None
    candidates_n: Optional[int] = None
    min_score: Optional[float] = None
    min_bm25: Optional[float] = None
    min_rerank: Optional[float] = None
    strategies: Optional[List[str]] = None


@router.post("/query", summary="Execute RAG search and grounded generation or structured computation")
def query_endpoint(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    Search indexed content and generate a grounded, cited answer or compute deterministic aggregation.
    - Selectable strategies: 'dense' (baseline), 'lexical', 'hybrid', 'hybrid_rerank', and 'auto'.
    - With 'auto': analyzes query with rule-based router. Structured route computes deterministic template
      without LLM or embeddings. Other routes execute RAG pipeline with chosen strategy.
    - If evidence gate fails: returns status 'insufficient_evidence' (LLM is NOT called).
    - If answers lack valid citations: returns status 'unverified'.
    - If citations are valid: returns status 'answered'.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not req.source_ids and req.index_run_id is None and req.pipeline_config_id is None:
        raise HTTPException(status_code=400, detail="Must provide at least one source_id, index_run_id, or pipeline_config_id.")

    if req.pipeline_config_id is not None:
        strategy = req.strategy or "auto"
    else:
        strategy = req.strategy or "dense"

    valid_strategies = ("dense", "lexical", "hybrid", "hybrid_rerank", "auto")
    if strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy '{strategy}'. Must be one of {valid_strategies}.",
        )

    result = execute_query(
        db=db,
        question=req.question.strip(),
        source_ids=req.source_ids or [],
        index_run_id=req.index_run_id,
        top_k=req.top_k,
        min_score=req.min_score,
        strategy=strategy,
        filters=req.filters,
        candidates_n=req.candidates_n,
        min_bm25=req.min_bm25,
        min_rerank=req.min_rerank,
        version=req.version,
        pipeline_config_id=req.pipeline_config_id,
    )
    return result


@router.post("/retrieve/compare", summary="Compare multiple retrieval strategies side-by-side")
def compare_retrieval_strategies(
    req: CompareRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluate multiple retrieval strategies side-by-side on the same query and filters.
    CRITICAL: Does NOT call the LLM.
    Returns per-strategy ranked chunks with explainability signals, evidence gate outcomes,
    stage latencies, and an overlap summary comparing rank changes against dense baseline.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not req.source_ids and req.index_run_id is None:
        raise HTTPException(status_code=400, detail="Must provide at least one source_id or index_run_id.")

    strategies_to_run = req.strategies or ["dense", "lexical", "hybrid", "hybrid_rerank"]
    valid_strategies = {"dense", "lexical", "hybrid", "hybrid_rerank"}
    for s in strategies_to_run:
        if s not in valid_strategies:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy '{s}'. Must be one of {sorted(valid_strategies)}.",
            )

    results_by_strategy: Dict[str, Any] = {}
    dense_ranks_by_chunk: Dict[int, int] = {}
    chunk_strategies_map: Dict[int, List[str]] = {}

    for strat in strategies_to_run:
        chunks, evidence, latencies, _ = execute_pipeline(
            db=db,
            question=req.question.strip(),
            source_ids=req.source_ids or [],
            index_run_id=req.index_run_id,
            strategy=strat,
            filters=req.filters,
            top_k=req.top_k,
            candidates_n=req.candidates_n,
            min_score=req.min_score,
            min_bm25=req.min_bm25,
            min_rerank=req.min_rerank,
        )

        formatted_chunks = []
        for c in chunks:
            cid = c["chunk_id"]
            if cid not in chunk_strategies_map:
                chunk_strategies_map[cid] = []
            chunk_strategies_map[cid].append(strat)

            if strat == "dense":
                dense_ranks_by_chunk[cid] = c["rank"]

            meta = c.get("metadata", {})
            content = c.get("content", "")
            snippet = (content[:150] + "...") if len(content) > 150 else content

            formatted_chunks.append({
                "rank": c["rank"],
                "chunk_id": cid,
                "score": c["score"],
                "snippet": snippet,
                "metadata": meta,
                "signals": c.get("signals", {}),
            })

        results_by_strategy[strat] = {
            "chunks": formatted_chunks,
            "evidence": evidence,
            "latency_ms": latencies,
        }

    # Build overlap summary
    rank_changes: Dict[str, Any] = {}
    all_seen_cids = sorted(chunk_strategies_map.keys())

    for cid in all_seen_cids:
        dense_rank = dense_ranks_by_chunk.get(cid)
        strat_ranks = {}
        for s in strategies_to_run:
            s_chunks = results_by_strategy[s]["chunks"]
            found_rank = next((c["rank"] for c in s_chunks if c["chunk_id"] == cid), None)
            strat_ranks[f"{s}_rank"] = found_rank

        deltas = {}
        if dense_rank is not None:
            for s in strategies_to_run:
                if s != "dense":
                    s_rank = strat_ranks.get(f"{s}_rank")
                    deltas[f"delta_{s}_vs_dense"] = (s_rank - dense_rank) if s_rank is not None else None

        rank_changes[str(cid)] = {
            "dense_rank": dense_rank,
            **strat_ranks,
            **deltas,
        }

    overlap_summary = {
        "chunk_strategies": {str(cid): strats for cid, strats in chunk_strategies_map.items()},
        "rank_changes_vs_dense": rank_changes,
        "unique_chunk_count": len(all_seen_cids),
    }

    return {
        "question": req.question.strip(),
        "strategies": strategies_to_run,
        "results": results_by_strategy,
        "overlap_summary": overlap_summary,
    }


@router.get("/queries/{query_id}/trace", summary="Get assembled trace explanation for a query")
def get_query_trace(
    query_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns an assembled explanation for a past query:
    - Route decision and rules evaluated
    - Strategy and filters
    - Per-stage latency
    - For computed answers: template, SQL-level description (bound placeholders, no raw values), rows_used, and data_quality_notes
    - For retrieval answers: candidates with explainability signals, evidence gate outcome, valid/dropped citations
    """
    q = db.query(QueryRecord).filter(QueryRecord.id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found.")

    route_info = q.route_info or {}
    res_summary = route_info.get("result_summary", {})
    spec = route_info.get("spec", {})
    decision = route_info.get("decision", {})
    chosen_strategy = decision.get("strategy") if decision else getattr(q, "strategy", "dense")

    trace: Dict[str, Any] = {
        "query_id": q.id,
        "question": q.question,
        "route": q.route,
        "route_decision": decision,
        "strategy": chosen_strategy,
        "answer_type": getattr(q, "answer_type", "generated"),
        "status": q.status,
        "answer": q.answer,
        "filters": getattr(q, "filters", {}),
        "latency_ms": q.latency_ms or {},
        "created_at": str(q.created_at),
    }

    if getattr(q, "answer_type", "generated") == "computed" or q.route == "structured":
        trace["template"] = res_summary.get("template") or spec.get("template")
        trace["column"] = spec.get("column")
        trace["group_by"] = spec.get("group_by")
        trace["sql_description"] = res_summary.get("sql_description")
        trace["rows_used"] = res_summary.get("rows_used")
        trace["rows_considered"] = res_summary.get("rows_considered")
        trace["rows_excluded_non_numeric"] = res_summary.get("rows_excluded_non_numeric")
        trace["rows_null"] = res_summary.get("rows_null")
        trace["data_quality_notes"] = res_summary.get("data_quality_notes", [])
        trace["structured_spec"] = {**spec, **res_summary}
        trace["citations"] = [
            {
                "type": "computed",
                "columns": spec.get("column") or spec.get("group_by"),
                "filters": spec.get("filters"),
                "rows_used": res_summary.get("rows_used"),
            }
        ]
    else:
        results = (
            db.query(RetrievalResult)
            .filter(RetrievalResult.query_id == query_id)
            .order_by(RetrievalResult.rank.asc())
            .all()
        )
        candidate_items = []
        for r in results:
            chunk = db.query(Chunk).filter(Chunk.id == r.chunk_id).first()
            candidate_items.append({
                "rank": r.rank,
                "chunk_id": r.chunk_id,
                "score": r.score,
                "used_in_prompt": r.used_in_prompt,
                "cited": r.cited,
                "signals": r.signals if hasattr(r, "signals") and r.signals else {},
                "metadata": chunk.metadata_ if chunk else {},
                "snippet": (chunk.content[:150] + "...") if chunk and len(chunk.content) > 150 else (chunk.content if chunk else ""),
            })

        trace["retrieval_candidates"] = candidate_items
        trace["evidence_gate"] = {
            "passed": (q.status != "insufficient_evidence"),
            "status": q.status,
        }
        trace["citations_valid"] = [c for c in candidate_items if c["cited"]]
        trace["citations_dropped"] = [c for c in candidate_items if not c["cited"]]

    if getattr(q, "pipeline_config_id", None) is not None:
        from db import PipelineConfig
        cfg = db.query(PipelineConfig).filter(PipelineConfig.id == q.pipeline_config_id).first()
        trace["pipeline_config_id"] = q.pipeline_config_id
        if cfg:
            trace["pipeline_config"] = {
                "id": cfg.id,
                "name": cfg.name,
                "kind": cfg.kind,
                "spec": cfg.spec,
            }

    return trace


@router.get("/queries/{query_id}", summary="Get query details and retrieval results")
def get_query_details(
    query_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve details of a past query including retrieved chunks, scores, signals, route, and citation status."""
    q = db.query(QueryRecord).filter(QueryRecord.id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found.")

    results = (
        db.query(RetrievalResult)
        .filter(RetrievalResult.query_id == query_id)
        .order_by(RetrievalResult.rank.asc())
        .all()
    )

    retrieved_items = []
    for r in results:
        chunk = db.query(Chunk).filter(Chunk.id == r.chunk_id).first()
        retrieved_items.append({
            "rank": r.rank,
            "chunk_id": r.chunk_id,
            "score": r.score,
            "used_in_prompt": r.used_in_prompt,
            "cited": r.cited,
            "signals": r.signals if hasattr(r, "signals") and r.signals else {},
            "metadata": chunk.metadata_ if chunk else {},
            "snippet": (chunk.content[:150] + "...") if chunk and len(chunk.content) > 150 else (chunk.content if chunk else ""),
        })

    return {
        "id": q.id,
        "question": q.question,
        "source_ids": q.source_ids,
        "index_run_ids": q.index_run_ids,
        "pipeline_config_id": getattr(q, "pipeline_config_id", None),
        "top_k": q.top_k,
        "min_score": q.min_score,
        "strategy": getattr(q, "strategy", "dense"),
        "route": getattr(q, "route", None),
        "route_info": getattr(q, "route_info", {}),
        "answer_type": getattr(q, "answer_type", "generated"),
        "filters": getattr(q, "filters", {}),
        "status": q.status,
        "answer": q.answer,
        "latency_ms": q.latency_ms,
        "created_at": str(q.created_at),
        "retrieval_results": retrieved_items,
    }


@router.get("/queries", summary="List recent queries")
def list_queries(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent search queries."""
    queries = (
        db.query(QueryRecord)
        .order_by(QueryRecord.id.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": q.id,
            "question": q.question,
            "source_ids": q.source_ids,
            "index_run_ids": q.index_run_ids,
            "pipeline_config_id": getattr(q, "pipeline_config_id", None),
            "top_k": q.top_k,
            "min_score": q.min_score,
            "strategy": getattr(q, "strategy", "dense"),
            "route": getattr(q, "route", None),
            "answer_type": getattr(q, "answer_type", "generated"),
            "filters": getattr(q, "filters", {}),
            "status": q.status,
            "answer": q.answer,
            "created_at": str(q.created_at),
        }
        for q in queries
    ]
