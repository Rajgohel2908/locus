"""
backend/evaluation/engine.py — Core execution engine for evaluation suites, runs, and reporting.

Rules:
- Internal execution: calls internal query/retrieval functions, not HTTP.
- Depth 20 retrieval: every cutoff comes from the same ranking.
- Frozen suites: HTTP 409 on item edits once any run exists; clone to edit.
- Reviewed flag is metadata, excluded from suite_hash.
- Resumable runs: skips items that already have results.
- Zero LLM calls for retrieval-only runs.
- Budget cap enforcement: clean exit with status='failed', error='budget'.
- Completed runs and results are immutable.
"""

import csv
import io
import json
import math
import os
import re
import time
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

import config
from db import (
    get_db,
    EvalSuite,
    EvalItem,
    EvalRun,
    EvalResult,
    Source,
    Document,
    Record,
    SourceVersion,
    IndexRun,
    Chunk,
    PipelineConfig,
    safe_json,
)
from indexing.chunker import chunk_active_source_content
from indexing.embedder import get_embedder
from retrieval.pipeline import execute_pipeline
from retrieval.filters import RetrievalFilters
from routing.context import build_schema_context
from routing.features import extract_features
from routing.router import decide_route
from structured.executor import execute_aggregation
from structured.render import render_answer
from generation.answer import build_rag_prompt, parse_and_validate_citations
from generation.llm import get_llm_client, FakeLLMClient, LLMClient
from evaluation.matching import (
    normalize_text,
    match_retrieved_chunk,
    union_covers_span,
)
from evaluation.metrics import compute_item_metrics
from evaluation.stats import bootstrap_ci, paired_bootstrap_comparison
from evaluation.judge import (
    JudgeClient,
    FakeJudgeClient,
    GeminiJudgeClient,
    CallBudgetTracker,
    BudgetExceededException,
)
from evaluation.provenance import capture_provenance


def compute_suite_hash(items: List[Dict[str, Any]]) -> str:
    """
    Compute deterministic SHA-256 hash of suite test cases.
    The reviewed flag and database IDs are strictly excluded.
    """
    canonical_items = []
    # Sort items by position then question
    sorted_items = sorted(
        items,
        key=lambda it: (it.get("position", 0), it.get("question", "")),
    )
    for it in sorted_items:
        canonical_items.append({
            "position": it.get("position", 0),
            "question": it.get("question", "").strip(),
            "item_type": it.get("item_type", "answerable"),
            "expected_facts": it.get("expected_facts", []),
            "reference_answer": it.get("reference_answer"),
            "expected_evidence": it.get("expected_evidence", []),
            "expected_value": it.get("expected_value"),
            "expected_route": it.get("expected_route"),
            "origin": it.get("origin", "agent_drafted"),
            "tags": it.get("tags", []),
        })

    canonical_json = json.dumps(canonical_items, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]


def is_suite_frozen(db: Session, suite_id: int) -> bool:
    """A suite is frozen once any run exists for it."""
    run_count = db.query(EvalRun).filter(EvalRun.suite_id == suite_id).count()
    return run_count > 0


def create_eval_suite(
    db: Session,
    name: str,
    source_ids: List[int],
    description: Optional[str] = None,
) -> EvalSuite:
    suite = EvalSuite(
        name=name,
        description=description,
        source_ids=source_ids,
        suite_hash="",
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite


def import_suite_items(
    db: Session,
    suite_id: int,
    items_data: List[Dict[str, Any]],
) -> List[EvalItem]:
    suite = db.query(EvalSuite).filter(EvalSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail=f"EvalSuite {suite_id} not found.")

    if is_suite_frozen(db, suite_id):
        raise HTTPException(
            status_code=409,
            detail="Suite is frozen because evaluation runs exist. Clone suite to edit items.",
        )

    created_items = []
    start_pos = (
        db.query(func.max(EvalItem.position))
        .filter(EvalItem.suite_id == suite_id)
        .scalar()
        or 0
    )

    for i, it in enumerate(items_data):
        item = EvalItem(
            suite_id=suite_id,
            position=it.get("position", start_pos + i + 1),
            question=it["question"].strip(),
            item_type=it.get("item_type", "answerable"),
            expected_facts=it.get("expected_facts", []),
            reference_answer=it.get("reference_answer"),
            expected_evidence=it.get("expected_evidence", []),
            expected_value=it.get("expected_value"),
            expected_route=it.get("expected_route"),
            origin=it.get("origin", "agent_drafted"),
            reviewed=bool(it.get("reviewed", False)),
            tags=it.get("tags", []),
        )
        db.add(item)
        created_items.append(item)

    db.commit()

    # Recompute suite_hash
    all_items = (
        db.query(EvalItem)
        .filter(EvalItem.suite_id == suite_id)
        .order_by(EvalItem.position)
        .all()
    )
    item_dicts = [
        {
            "position": item.position,
            "question": item.question,
            "item_type": item.item_type,
            "expected_facts": item.expected_facts,
            "reference_answer": item.reference_answer,
            "expected_evidence": item.expected_evidence,
            "expected_value": item.expected_value,
            "expected_route": item.expected_route,
            "origin": item.origin,
            "tags": item.tags,
        }
        for item in all_items
    ]
    suite.suite_hash = compute_suite_hash(item_dicts)
    db.commit()
    return created_items


def import_suite_items_csv(db: Session, suite_id: int, csv_content: str) -> List[EvalItem]:
    """
    Parse CSV format and import items into an evaluation suite.
    Documented columns:
      question, item_type, expected_facts (pipe-separated), expected_span,
      document_title, page_number, row_key, expected_route, tags (pipe-separated)
    Defaults: origin="hand", reviewed=False.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    items_data = []
    for row in reader:
        question = (row.get("question") or "").strip()
        if not question:
            continue

        item_type = (row.get("item_type") or "answerable").strip()

        # expected_facts: pipe-separated string or JSON list
        raw_facts = row.get("expected_facts", "")
        if raw_facts.startswith("["):
            try:
                facts = json.loads(raw_facts)
            except Exception:
                facts = [f.strip() for f in raw_facts.split("|") if f.strip()]
        else:
            facts = [f.strip() for f in raw_facts.split("|") if f.strip()] if raw_facts else []

        # expected_evidence from expected_span, document_title, page_number, row_key, or expected_evidence JSON
        evidence = []
        expected_span = row.get("expected_span", "").strip()
        doc_title = row.get("document_title", "").strip() or None
        page_raw = row.get("page_number", "").strip()
        page_num = int(page_raw) if page_raw.isdigit() else None
        row_key = row.get("row_key", "").strip() or None

        if expected_span or doc_title or row_key or page_num is not None:
            evidence.append({
                "span": expected_span,
                "document_title": doc_title,
                "page_number": page_num,
                "row_key": row_key,
            })
        elif row.get("expected_evidence"):
            try:
                evidence = json.loads(row["expected_evidence"])
            except Exception:
                evidence = []

        # expected_value
        exp_val = None
        if row.get("expected_value"):
            try:
                exp_val = json.loads(row["expected_value"])
            except Exception:
                exp_val = {"value": row["expected_value"].strip()}

        # tags: pipe-separated or comma-separated or JSON
        raw_tags = row.get("tags", "")
        if raw_tags.startswith("["):
            try:
                tags = json.loads(raw_tags)
            except Exception:
                tags = [t.strip() for t in raw_tags.split("|") if t.strip()]
        else:
            tags = [t.strip() for t in raw_tags.replace(",", "|").split("|") if t.strip()] if raw_tags else []

        expected_route = row.get("expected_route", "").strip() or None

        # defaults to origin="hand", reviewed=False
        origin = row.get("origin", "").strip() or "hand"
        reviewed_raw = row.get("reviewed", "").strip().lower()
        reviewed = reviewed_raw in ("true", "1", "yes")

        items_data.append({
            "position": int(row["position"]) if row.get("position", "").strip().isdigit() else None,
            "question": question,
            "item_type": item_type,
            "expected_facts": facts,
            "reference_answer": row.get("reference_answer"),
            "expected_evidence": evidence,
            "expected_value": exp_val,
            "expected_route": expected_route,
            "origin": origin,
            "reviewed": reviewed,
            "tags": tags,
        })
    return import_suite_items(db, suite_id, items_data)


def clone_eval_suite(db: Session, suite_id: int, new_name: str) -> EvalSuite:
    """Clone an existing suite so it can be modified without altering frozen runs."""
    src_suite = db.query(EvalSuite).filter(EvalSuite.id == suite_id).first()
    if not src_suite:
        raise HTTPException(status_code=404, detail=f"Suite {suite_id} not found.")

    new_suite = EvalSuite(
        name=new_name,
        description=f"Cloned from suite {suite_id} ({src_suite.name})",
        source_ids=list(src_suite.source_ids or []),
        suite_hash=src_suite.suite_hash,
    )
    db.add(new_suite)
    db.commit()
    db.refresh(new_suite)

    items = db.query(EvalItem).filter(EvalItem.suite_id == suite_id).all()
    for item in items:
        new_item = EvalItem(
            suite_id=new_suite.id,
            position=item.position,
            question=item.question,
            item_type=item.item_type,
            expected_facts=item.expected_facts,
            reference_answer=item.reference_answer,
            expected_evidence=item.expected_evidence,
            expected_value=item.expected_value,
            expected_route=item.expected_route,
            origin=item.origin,
            reviewed=item.reviewed,
            tags=item.tags,
        )
        db.add(new_item)
    db.commit()
    return new_suite


def lint_eval_suite(db: Session, suite_id: int) -> Dict[str, Any]:
    """
    Performs label quality linting on an evaluation suite:
    - best-match overlap of each expected span against corpus (matching document and page).
    - whether the row_key exists in active records.
    - whether expected_facts occur in the matched text.
    - duplicate questions.
    - spans matching 3 or more documents (ambiguous).
    - items that fail get lint_failed=True.
    """
    suite = db.query(EvalSuite).filter(EvalSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail=f"EvalSuite {suite_id} not found.")

    items = db.query(EvalItem).filter(EvalItem.suite_id == suite_id).order_by(EvalItem.position).all()
    source_ids = suite.source_ids or []

    docs = db.query(Document).filter(Document.source_id.in_(source_ids)).all() if source_ids else []
    chunks = db.query(Chunk).filter(Chunk.source_id.in_(source_ids)).all() if source_ids else []
    records = db.query(Record).filter(Record.source_id.in_(source_ids), Record.status == "active").all() if source_ids else []

    active_row_keys = set()
    for r in records:
        active_row_keys.add(str(r.id))
        if r.row_index is not None:
            active_row_keys.add(str(r.row_index))
        if isinstance(r.data, dict):
            for v in r.data.values():
                if isinstance(v, (str, int, float)):
                    active_row_keys.add(str(v))
    doc_by_id = {d.id: d for d in docs}

    # 1. Duplicate questions count
    question_counts: Dict[str, int] = {}
    for it in items:
        norm_q = normalize_text(it.question)
        question_counts[norm_q] = question_counts.get(norm_q, 0) + 1

    items_lint = []
    total_failing = 0

    for it in items:
        failures = []
        norm_q = normalize_text(it.question)

        # Check duplicate question
        is_dup = question_counts.get(norm_q, 0) > 1
        if is_dup:
            failures.append("duplicate_question")

        span_checks = []
        all_matched_texts = []

        if it.expected_evidence:
            for ev in it.expected_evidence:
                span = ev.get("span", "")
                norm_span = normalize_text(span) if span else ""
                row_key = ev.get("row_key")
                doc_title = ev.get("document_title")
                page_num = ev.get("page_number")

                matching_docs = set()
                best_overlap = 0.0

                if norm_span:
                    for ch in chunks:
                        norm_content = normalize_text(ch.content or "")
                        if norm_span in norm_content:
                            matching_docs.add(ch.document_id)
                            best_overlap = 1.0
                            all_matched_texts.append(norm_content)
                        else:
                            span_toks = set(norm_span.split())
                            ch_toks = set(norm_content.split())
                            if span_toks and ch_toks:
                                overlap = len(span_toks & ch_toks) / len(span_toks)
                                if overlap > best_overlap:
                                    best_overlap = overlap
                                    if overlap >= 0.85:
                                        matching_docs.add(ch.document_id)
                                        all_matched_texts.append(norm_content)

                    # Also check whole docs if chunks had lower match
                    if best_overlap < 1.0:
                        for d in docs:
                            norm_doc_content = normalize_text(d.content or "")
                            if norm_span in norm_doc_content:
                                matching_docs.add(d.id)
                                best_overlap = 1.0
                                all_matched_texts.append(norm_doc_content)

                    is_ambiguous = len(matching_docs) >= 3
                    if is_ambiguous:
                        failures.append("ambiguous_span_in_3_or_more_documents")

                    if best_overlap < 0.50 and not row_key:
                        failures.append("expected_span_not_found_in_corpus")

                    # Check page number if specified
                    if page_num is not None:
                        page_matched = False
                        for ch in chunks:
                            if ch.document_id in matching_docs:
                                ch_meta = ch.metadata or {}
                                if ch_meta.get("page_number") == page_num or ch_meta.get("page") == page_num:
                                    page_matched = True
                                    break
                        if matching_docs and not page_matched and len(chunks) > 0:
                            doc_obj = doc_by_id.get(list(matching_docs)[0])
                            if doc_obj and (doc_obj.metadata or {}).get("page_count", 1) < page_num:
                                failures.append(f"page_number_{page_num}_out_of_bounds")

                    span_checks.append({
                        "span": span[:100] + ("..." if len(span) > 100 else ""),
                        "best_overlap": round(best_overlap, 4),
                        "matching_doc_count": len(matching_docs),
                        "ambiguous": is_ambiguous,
                    })

                # Check row_key in active records
                if row_key:
                    if str(row_key) not in active_row_keys and len(active_row_keys) > 0:
                        failures.append(f"row_key_missing_in_active_records: {row_key}")

        # Check expected_facts occur in matched text
        if it.expected_facts and all_matched_texts:
            combined_corpus_text = " ".join(all_matched_texts)
            missing_facts = [
                f for f in it.expected_facts
                if normalize_text(f) not in combined_corpus_text
            ]
            if missing_facts:
                failures.append(f"expected_facts_missing_in_matched_text: {', '.join(missing_facts)}")

        lint_failed = len(failures) > 0
        if lint_failed:
            total_failing += 1

        items_lint.append({
            "item_id": it.id,
            "position": it.position,
            "question": it.question,
            "item_type": it.item_type,
            "lint_failed": lint_failed,
            "duplicate_question": is_dup,
            "span_checks": span_checks,
            "failures": failures,
        })

    return {
        "suite_id": suite.id,
        "suite_name": suite.name,
        "total_items": len(items),
        "lint_failed_count": total_failing,
        "items": items_lint,
    }


def resolve_variant_index_runs(
    db: Session,
    source_ids: List[int],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    pipeline_config_id: Optional[int] = None,
) -> Dict[str, int]:
    """
    Resolve or trigger index runs for a variant.
    Reuses identical completed index runs. Overlap = 15% of chunk_size unless given.
    """
    from routers.indexing import perform_indexing

    if pipeline_config_id is not None:
        pcfg = db.query(PipelineConfig).filter(PipelineConfig.id == pipeline_config_id).first()
        if pcfg and pcfg.index_runs:
            return {str(k): int(v) for k, v in pcfg.index_runs.items() if v}

    c_size = chunk_size or config.CHUNK_SIZE
    c_overlap = chunk_overlap if chunk_overlap is not None else round(c_size * 0.15)

    index_runs_map = {}
    for sid in source_ids:
        # Check if identical completed index run exists
        existing = (
            db.query(IndexRun)
            .filter(
                IndexRun.source_id == sid,
                IndexRun.chunk_size == c_size,
                IndexRun.chunk_overlap == c_overlap,
                IndexRun.status == "completed",
            )
            .order_by(IndexRun.id.desc())
            .first()
        )
        if existing:
            index_runs_map[str(sid)] = existing.id
        else:
            # Trigger index run
            new_run = perform_indexing(
                db=db,
                source_id=sid,
                chunk_size=c_size,
                chunk_overlap=c_overlap,
            )
            index_runs_map[str(sid)] = new_run.id

    return index_runs_map


def execute_eval_run(
    db: Session,
    run_id: int,
    llm_client: Optional[LLMClient] = None,
    judge_client: Optional[JudgeClient] = None,
    budget_tracker: Optional[CallBudgetTracker] = None,
) -> EvalRun:
    """
    Execute an evaluation run item by item.
    Resumable: skips items that already have results.
    Enforces call budgets and records full telemetry.
    """
    run = db.query(EvalRun).filter(EvalRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"EvalRun {run_id} not found.")

    if run.status in ("completed", "failed", "cancelled"):
        return run

    suite = db.query(EvalSuite).filter(EvalSuite.id == run.suite_id).first()
    if not suite:
        run.status = "failed"
        run.error = "Suite not found"
        db.commit()
        return run

    run.status = "running"
    run.started_at = run.started_at or datetime.utcnow()
    db.commit()

    # Capture provenance
    run.provenance = capture_provenance(
        suite_hash=suite.suite_hash or "",
        variant=run.variant or {},
        index_run_ids=run.index_run_ids,
    )
    db.commit()

    # Determine items to evaluate
    items_query = db.query(EvalItem).filter(EvalItem.suite_id == run.suite_id)
    if not run.include_unreviewed:
        items_query = items_query.filter(EvalItem.reviewed.is_(True))
    items = items_query.order_by(EvalItem.position).all()

    total_items = len(items)
    run.progress = {"total": total_items, "completed": 0, "status": "running"}
    db.commit()

    # Resolve variant parameters
    var = run.variant or {}
    strategy = var.get("strategy", "dense")
    top_k = var.get("top_k", 5)
    chunk_size = var.get("chunk_size")
    chunk_overlap = var.get("chunk_overlap")
    pipeline_config_id = var.get("pipeline_config_id")

    # Resolve index runs
    source_ids = list(suite.source_ids or [])
    index_runs_map = resolve_variant_index_runs(
        db=db,
        source_ids=source_ids,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        pipeline_config_id=pipeline_config_id,
    )
    run.index_run_ids = index_runs_map
    db.commit()

    resolved_index_runs_list = [int(v) for v in index_runs_map.values()]

    # Setup clients
    active_llm = llm_client
    if run.generate and active_llm is None:
        active_llm = get_llm_client()

    active_judge = judge_client
    if run.judge and active_judge is None:
        judge_provider = run.judge_llm.get("provider", "gemini")
        if judge_provider == "gemini":
            active_judge = GeminiJudgeClient(
                model_name=run.judge_llm.get("model", "gemini-2.0-flash"),
                budget_tracker=budget_tracker,
            )
        else:
            active_judge = FakeJudgeClient(budget_tracker=budget_tracker)

    completed_count = 0

    try:
        for idx, item in enumerate(items, start=1):
            # Check for cancellation
            db.refresh(run)
            if run.status == "cancelled":
                break

            # Resumable: check if result already exists
            existing_res = (
                db.query(EvalResult)
                .filter(EvalResult.run_id == run.id, EvalResult.item_id == item.id)
                .first()
            )
            if existing_res is not None:
                completed_count += 1
                continue

            t0 = time.perf_counter()
            item_llm_calls = 0
            item_judge_calls = 0

            route_name = item.expected_route or "semantic"
            actual_strategy = strategy
            actual_answer = None
            actual_status = "retrieved"
            retrieved_data = []
            citations = []
            latency_ms = {}

            # 1. Structured Route Execution
            if item.item_type == "structured" or strategy == "auto":
                # Check router
                context = build_schema_context(db=db, source_ids=source_ids)
                features = extract_features(item.question, context)
                decision = decide_route(features)
                route_name = decision.route

                if decision.route == "structured":
                    t_struct_start = time.perf_counter()
                    try:
                        table_schema = context.tables.get(features.target_source_id)
                        if table_schema and features.aggregation_intent:
                            op = features.aggregation_intent.op
                            col = features.target_column
                            grp = features.group_by_hint
                            filts = [(f.column, f.value) for f in features.filter_values if f.source_id == features.target_source_id]
                            template_req = "top_n" if features.row_identity_request else None

                            sv = (
                                db.query(SourceVersion)
                                .filter(SourceVersion.source_id == features.target_source_id, SourceVersion.is_current.is_(True))
                                .first()
                            )
                            version_no = sv.version_no if sv else 1

                            exec_res = execute_aggregation(
                                db=db,
                                table_schema=table_schema,
                                op=op,
                                column=col,
                                group_by=grp,
                                filters=filts,
                                version=version_no,
                                template=template_req,
                                top_n=features.top_n,
                            )
                            rendered_ans = render_answer(exec_res)
                            t_struct_end = time.perf_counter()
                            latency_ms = {
                                "route": round((t_struct_end - t_struct_start) * 1000, 2),
                                "total": round((t_struct_end - t_struct_start) * 1000, 2),
                            }
                            actual_answer = rendered_ans
                            actual_status = "answered"
                            actual_strategy = "auto"
                        else:
                            actual_status = "insufficient_evidence"
                            actual_answer = None
                    except Exception as e:
                        actual_status = "insufficient_evidence"
                        actual_answer = None

            # 2. Retrieval Pipeline Execution (Depth 20)
            if actual_answer is None and item.item_type != "structured":
                if strategy == "auto":
                    actual_strategy = "hybrid" if var.get("use_rerank") else "dense"
                else:
                    actual_strategy = strategy

                chunks_pool, evidence, stage_latencies, _ = execute_pipeline(
                    db=db,
                    question=item.question,
                    source_ids=source_ids,
                    index_run_id=None,
                    index_run_ids=resolved_index_runs_list,
                    strategy=actual_strategy,
                    filters=None,
                    top_k=20,  # Always fetch depth 20
                    candidates_n=max(20, config.CANDIDATES_N),
                    min_score=config.MIN_SCORE,
                    min_bm25=config.MIN_BM25,
                    min_rerank=config.MIN_RERANK,
                )

                latency_ms = stage_latencies

                # Evaluate relevance of each candidate chunk
                retrieved_data = []
                for r_idx, ch in enumerate(chunks_pool[:20], start=1):
                    content = ch.get("content", "")
                    is_rel, matched_spans = match_retrieved_chunk(
                        content, item.expected_evidence
                    )
                    retrieved_data.append({
                        "rank": r_idx,
                        "chunk_id": ch.get("chunk_id"),
                        "score": ch.get("score"),
                        "signals": ch.get("signals", {}),
                        "relevant": is_rel,
                        "matched_spans": matched_spans,
                        "content": content,
                    })

                # Check evidence gate
                if not evidence.get("passed", False):
                    actual_status = "insufficient_evidence"
                    actual_answer = None
                else:
                    actual_status = "success"

                    # 3. Generation (if requested)
                    if run.generate and active_llm:
                        if budget_tracker:
                            budget_tracker.record_generation_call()
                        item_llm_calls += 1

                        top_chunks = chunks_pool[:top_k]
                        prompt = build_rag_prompt(item.question, top_chunks)
                        t_gen_start = time.perf_counter()
                        try:
                            gen_resp = active_llm.generate(prompt)
                            t_gen_end = time.perf_counter()
                            latency_ms["generate"] = round((t_gen_end - t_gen_start) * 1000, 2)
                            actual_answer = gen_resp.text if hasattr(gen_resp, "text") else str(gen_resp)
                            # Citation validation
                            cit_res = parse_and_validate_citations(actual_answer, top_chunks)
                            citations = list(cit_res["valid_ids"])
                            if cit_res["invalid_citations"]:
                                actual_status = "unverified"
                        except Exception as e:
                            actual_status = "failed"
                            actual_answer = f"LLM error: {str(e)}"

            t_total = time.perf_counter() - t0
            latency_ms["total"] = round(t_total * 1000, 2)

            # Compute deterministic metrics
            item_metrics = compute_item_metrics(
                item_type=item.item_type,
                expected_evidence=item.expected_evidence,
                expected_facts=item.expected_facts,
                expected_value=item.expected_value,
                expected_route=item.expected_route,
                retrieved=retrieved_data,
                answer=actual_answer,
                status=actual_status,
                citations=citations,
                route=route_name,
                generate=run.generate,
                llm_calls=item_llm_calls,
            )

            # 4. Optional LLM Judge
            if run.judge and active_judge and actual_answer and actual_status != "insufficient_evidence":
                top_contexts = [r["content"] for r in retrieved_data[:top_k]]
                faith_res = active_judge.evaluate_faithfulness(
                    item.question, actual_answer, top_contexts
                )
                rel_res = active_judge.evaluate_answer_relevance(
                    item.question, actual_answer
                )
                item_metrics["faithfulness"] = faith_res.get("score", 0.0)
                item_metrics["answer_relevance"] = rel_res.get("score", 0.0)
                item_judge_calls += 2

            # Persist EvalResult
            eval_res = EvalResult(
                run_id=run.id,
                item_id=item.id,
                query_id=None,
                route=route_name,
                strategy=actual_strategy,
                retrieved=safe_json(retrieved_data),
                answer=actual_answer,
                status=actual_status,
                citations=safe_json(citations),
                metrics=safe_json(item_metrics),
                latency_ms=safe_json(latency_ms),
                llm_calls=item_llm_calls,
                judge_calls=item_judge_calls,
                error=None,
            )
            db.add(eval_res)
            completed_count += 1
            run.progress = {
                "total": total_items,
                "completed": completed_count,
                "current_item_id": item.id,
                "status": "running",
            }
            db.commit()

        if run.status != "cancelled":
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.progress = {
                "total": total_items,
                "completed": completed_count,
                "status": "completed",
            }
            db.commit()

    except BudgetExceededException:
        db.rollback()
        run.status = "failed"
        run.error = "budget"
        run.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        run.status = "failed"
        run.error = str(e)
        run.finished_at = datetime.utcnow()
        db.commit()

    return run


def generate_run_report(db: Session, run_id: int) -> Dict[str, Any]:
    """
    Generate aggregated evaluation report with 95% bootstrap CIs,
    per-slice route breakdowns, and top failure classifications.
    """
    run = db.query(EvalRun).filter(EvalRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"EvalRun {run_id} not found.")

    results = db.query(EvalResult).filter(EvalResult.run_id == run_id).all()
    if not results:
        return {
            "run_id": run.id,
            "name": run.name,
            "status": run.status,
            "n": 0,
            "metrics": {},
            "slices": {},
            "failures": [],
        }

    # Collect metric vectors
    all_metric_keys = set()
    for r in results:
        all_metric_keys.update((r.metrics or {}).keys())

    aggregated_metrics: Dict[str, Any] = {}
    for k in sorted(all_metric_keys):
        vals = [
            float(r.metrics[k])
            for r in results
            if r.metrics and k in r.metrics and r.metrics[k] is not None
        ]
        if vals:
            aggregated_metrics[k] = bootstrap_ci(vals, n_resamples=2000, seed=run.seed)

    # Add latency aggregations
    for lat_key in ("total", "dense", "lexical", "rerank", "generate"):
        lat_vals = [
            float(r.latency_ms[lat_key])
            for r in results
            if r.latency_ms and lat_key in r.latency_ms and r.latency_ms[lat_key] is not None
        ]
        if lat_vals:
            arr = np.array(lat_vals)
            aggregated_metrics[f"latency_{lat_key}_p50"] = {
                "value": round(float(np.percentile(arr, 50)), 2),
                "n": len(lat_vals),
            }
            aggregated_metrics[f"latency_{lat_key}_p95"] = {
                "value": round(float(np.percentile(arr, 95)), 2),
                "n": len(lat_vals),
            }

    # Slice breakdown by route
    slices: Dict[str, Dict[str, Any]] = {}
    routes = set(r.route for r in results if r.route)
    for rt in sorted(routes):
        rt_results = [r for r in results if r.route == rt]
        rt_metrics = {}
        for k in ("hit@5", "recall@5", "precision@5", "mrr"):
            vals = [
                float(r.metrics[k])
                for r in rt_results
                if r.metrics and k in r.metrics and r.metrics[k] is not None
            ]
            if vals:
                rt_metrics[k] = bootstrap_ci(vals, n_resamples=1000, seed=run.seed)
        slices[rt] = {"n": len(rt_results), "metrics": rt_metrics}

    # Top failures categorization
    failures = []
    for r in results:
        m = r.metrics or {}
        reasons = []

        # 1. Gold missing from top-5 on answerable
        if m.get("recall@5", 1.0) < 1.0 and m.get("hit@5", 1.0) == 0.0:
            reasons.append("gold_missing_from_top_k")

        # 2. False refusal
        if m.get("false_refusal", 0.0) > 0.0:
            reasons.append("false_refusal")

        # 3. Unsafe answer
        if m.get("unsafe_answer", 0.0) > 0.0:
            reasons.append("unsafe_answer")

        # 4. Bad citations
        if m.get("invalid_citation_rate", 0.0) > 0.0:
            reasons.append("bad_citations")

        if reasons:
            failures.append({
                "item_id": r.item_id,
                "reasons": reasons,
                "status": r.status,
                "route": r.route,
                "strategy": r.strategy,
                "answer": r.answer,
                "metrics": r.metrics,
            })

    # Flag mock generation metrics as INVALID
    is_mock = bool((run.llm or {}).get("mock", False))

    # In retrieval-only runs, map unsafe_answer to gate_pass_unanswerable
    if not run.generate:
        if "unsafe_answer" in aggregated_metrics:
            aggregated_metrics["gate_pass_unanswerable"] = aggregated_metrics["unsafe_answer"]

    return {
        "run_id": run.id,
        "name": run.name,
        "status": run.status,
        "variant": run.variant,
        "generate": bool(run.generate),
        "is_mock": is_mock,
        "include_unreviewed": run.include_unreviewed,
        "provenance": run.provenance,
        "n": len(results),
        "metrics": aggregated_metrics,
        "slices": slices,
        "failures": failures,
    }


def generate_markdown_scorecard(db: Session, run_ids: List[int]) -> str:
    """
    Generate Markdown scorecard across multiple runs with provenance,
    banners, metrics tables with CI and n, paired comparisons, and top failures.
    """
    reports = [generate_run_report(db, rid) for rid in run_ids]
    if not reports:
        return "# Evaluation Report\n\nNo valid runs specified."

    md = []
    md.append("# Sift Reproducible Evaluation Scorecard\n")

    # Banners
    any_mock = any(rep.get("is_mock") for rep in reports)
    if any_mock:
        md.append("> [!WARNING]\n> **MOCK LLM RUN DETECTED:** Generation metrics for mock LLM runs are **INVALID** and must not be used for production calibration.\n")

    any_unreviewed = any(rep.get("include_unreviewed") for rep in reports)
    if any_unreviewed:
        md.append("> [!NOTE]\n> **UNREVIEWED ITEMS INCLUDED:** Run includes items with `reviewed=false`.\n")

    any_dirty = any((rep.get("provenance") or {}).get("dirty") for rep in reports)
    if any_dirty:
        md.append("> [!WARNING]\n> **DIRTY WORKING TREE: results not reproducible from the commit hash alone**\n")

    any_small_n = any(rep.get("n", 0) < 30 for rep in reports)
    if any_small_n:
        md.append("> [!NOTE]\n> **SMALL SAMPLE SIZE (n < 30, labeled heuristic):** Results have wider confidence intervals and high sample sensitivity.\n")

    if len(reports) >= 2:
        metrics_compared_count = 5  # recall@5, precision@5, mrr, hit@5, false_refusal
        md.append(f"> [!NOTE]\n> **EXPLORATORY COMPARISONS:** Evaluated {metrics_compared_count} metric comparisons without multiple-testing correction (e.g. Bonferroni/FDR). Interpret exploratory deltas with caution.\n")

    md.append("> [!IMPORTANT]\n> **LLM-JUDGED METRICS:** Faithfulness and Answer Relevance are **LLM-judged, uncalibrated**.\n")

    # Provenance Table
    md.append("## 1. Provenance & Run Configuration\n")
    md.append("| Run ID | Name | Strategy | Chunk Size | Top K | Git Commit | Dirty Tree | Diff SHA | Embedder (Used) | Reranker (Used) | Python | Suite Hash |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for rep in reports:
        var = rep.get("variant", {})
        prov = rep.get("provenance", {})
        git_c = str(prov.get("git_commit", "n/a"))[:8]
        dirty_str = "YES (DIRTY)" if prov.get("dirty") else "CLEAN"
        diff_sha = str(prov.get("diff_sha256", "n/a"))[:8]
        emb_used = "Yes" if prov.get("embedder_used", True) else "No"
        rerank_used = "Yes" if prov.get("reranker_used", False) else "No"
        md.append(
            f"| {rep['run_id']} | {rep['name']} | {var.get('strategy', 'auto')} | "
            f"{var.get('chunk_size', 'default')} | {var.get('top_k', 5)} | "
            f"`{git_c}` | {dirty_str} | `{diff_sha}` | {prov.get('embedder', 'default')} ({emb_used}) | {prov.get('reranker', 'default')} ({rerank_used}) | "
            f"{prov.get('python_version', '3.12')} | `{prov.get('suite_hash', 'n/a')}` |"
        )
    md.append("\n---\n")

    # Metrics Table
    md.append("## 2. Core Quantitative Metrics (95% Bootstrap CI)\n")
    display_keys = [
        "hit@1", "hit@3", "hit@5", "hit@10",
        "recall@1", "recall@3", "recall@5", "recall@10", "recall@20",
        "precision@1", "precision@3", "precision@5", "precision@10",
        "precision_norm@1", "precision_norm@3", "precision_norm@5", "precision_norm@10",
        "context_precision_tokens@1", "context_precision_tokens@3", "context_precision_tokens@5", "context_precision_tokens@10",
        "ndcg@1", "ndcg@3", "ndcg@5", "ndcg@10", "mrr",
        "refusal_correct", "gate_pass_unanswerable", "unsafe_answer", "false_refusal",
        "value_match", "route_accuracy",
        "fact_recall", "answer_correct_strict", "citation_precision", "citation_recall", "invalid_citation_rate",
        "faithfulness", "answer_relevance",
    ]

    header = "| Metric | " + " | ".join(f"Run {rep['run_id']} ({rep['name']})" for rep in reports) + " |"
    sep = "| :--- | " + " | ".join(":---:" for _ in reports) + " |"
    md.append(header)
    md.append(sep)

    for mk in display_keys:
        row_vals = []
        has_any_val = False
        for rep in reports:
            effective_key = mk
            if not rep.get("generate", False) and mk == "unsafe_answer":
                effective_key = "gate_pass_unanswerable"
            elif rep.get("generate", False) and mk == "gate_pass_unanswerable":
                effective_key = "unsafe_answer"

            m_data = rep["metrics"].get(effective_key)
            if m_data and isinstance(m_data, dict) and "mean" in m_data:
                has_any_val = True
                mean = m_data["mean"]
                ci_l = m_data["ci_low"]
                ci_h = m_data["ci_high"]
                n = m_data["n"]

                # If raw precision, display ceiling next to raw precision
                if mk in ("precision@1", "precision@3", "precision@5", "precision@10"):
                    k_str = mk.split("@")[1]
                    ceil_data = rep["metrics"].get(f"precision_ceiling@{k_str}")
                    if ceil_data and isinstance(ceil_data, dict) and "mean" in ceil_data:
                        ceil_val = ceil_data["mean"]
                        row_vals.append(f"{mean:.4f} `(ceiling: {ceil_val:.4f})` `[{ci_l:.4f}, {ci_h:.4f}]` *(n={n})*")
                    else:
                        row_vals.append(f"{mean:.4f} `[{ci_l:.4f}, {ci_h:.4f}]` *(n={n})*")
                else:
                    row_vals.append(f"{mean:.4f} `[{ci_l:.4f}, {ci_h:.4f}]` *(n={n})*")
            else:
                row_vals.append("—")

        if has_any_val:
            md.append(f"| **{mk}** | " + " | ".join(row_vals) + " |")

    # Latencies
    md.append("\n### Stage Latencies (p50 / p95)\n")
    md.append("| Stage | " + " | ".join(f"Run {rep['run_id']} p50 / p95" for rep in reports) + " |")
    md.append("| :--- | " + " | ".join(":---:" for _ in reports) + " |")
    for stage in ("total", "dense", "lexical", "rerank", "generate"):
        row_vals = []
        for rep in reports:
            p50 = rep["metrics"].get(f"latency_{stage}_p50", {}).get("value", "—")
            p95 = rep["metrics"].get(f"latency_{stage}_p95", {}).get("value", "—")
            row_vals.append(f"{p50} ms / {p95} ms")
        md.append(f"| **{stage}** | " + " | ".join(row_vals) + " |")

    # Route Slices Breakdown
    all_slices = set()
    for rep in reports:
        all_slices.update(rep.get("slices", {}).keys())

    if all_slices:
        md.append("\n### Route Slices Breakdown\n")
        md.append("| Route | Run | Items (n) | Recall@5 (95% CI) | Hit@5 (95% CI) | Precision@5 | MRR |")
        md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
        for rt in sorted(all_slices):
            for rep in reports:
                sl = rep.get("slices", {}).get(rt)
                if sl:
                    n_sl = sl["n"]
                    m = sl["metrics"]
                    r5 = m.get("recall@5", {})
                    r5_str = f"{r5.get('mean', 0.0):.4f} `[{r5.get('ci_low', 0.0):.4f}, {r5.get('ci_high', 0.0):.4f}]`" if "mean" in r5 else "—"
                    h5 = m.get("hit@5", {})
                    h5_str = f"{h5.get('mean', 0.0):.4f} `[{h5.get('ci_low', 0.0):.4f}, {h5.get('ci_high', 0.0):.4f}]`" if "mean" in h5 else "—"
                    p5 = m.get("precision@5", {})
                    p5_str = f"{p5.get('mean', 0.0):.4f}" if "mean" in p5 else "—"
                    mrr = m.get("mrr", {})
                    mrr_str = f"{mrr.get('mean', 0.0):.4f}" if "mean" in mrr else "—"
                    md.append(f"| **{rt}** | Run {rep['run_id']} | {n_sl} | {r5_str} | {h5_str} | {p5_str} | {mrr_str} |")

    # Paired Comparisons (if 2 runs)
    if len(reports) >= 2:
        md.append("\n---\n")
        md.append("## 3. Paired Comparisons (Variant A vs Variant B)\n")
        run_a_id = reports[0]["run_id"]
        run_b_id = reports[1]["run_id"]
        comp_md = generate_paired_comparison_md(db, run_a_id, run_b_id)
        md.append(comp_md)

    # Diagnostic Failures Summary
    md.append("\n---\n")
    md.append("## 4. Diagnostic Failures Summary\n")
    for rep in reports:
        fails = rep.get("failures", [])
        md.append(f"### Run {rep['run_id']} ({rep['name']}) — Total Failures: {len(fails)}\n")
        if not fails:
            md.append("No failures recorded for this run.\n")
        else:
            for f in fails:
                md.append(f"- **Item ID `{f['item_id']}`** | Status: `{f['status']}` | Reasons: `{', '.join(f['reasons'])}`")
                if f.get("answer"):
                    md.append(f"  *Answer snippet:* {f['answer'][:160]}...")
            md.append("\n")

    return "\n".join(md)

    return "\n".join(md)


def generate_paired_comparison_md(db: Session, run_a_id: int, run_b_id: int) -> str:
    """Compute paired delta comparisons for two runs."""
    res_a = db.query(EvalResult).filter(EvalResult.run_id == run_a_id).all()
    res_b = db.query(EvalResult).filter(EvalResult.run_id == run_b_id).all()

    map_a = {r.item_id: r for r in res_a}
    map_b = {r.item_id: r for r in res_b}
    common_item_ids = sorted(set(map_a.keys()) & set(map_b.keys()))

    if not common_item_ids:
        return "No common items between the two runs."

    metrics_to_compare = ["recall@5", "precision@5", "mrr", "hit@5", "false_refusal"]
    md = [f"Paired evaluation over **{len(common_item_ids)} common items**:\n"]
    md.append("| Metric | Mean A | Mean B | Mean Δ (A - B) | 95% Paired CI | W / L / T | Verdict |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :--- |")

    for mk in metrics_to_compare:
        vals_a = []
        vals_b = []
        for iid in common_item_ids:
            ma = map_a[iid].metrics or {}
            mb = map_b[iid].metrics or {}
            if mk in ma and mk in mb:
                vals_a.append(float(ma[mk]))
                vals_b.append(float(mb[mk]))

        if vals_a:
            comp = paired_bootstrap_comparison(vals_a, vals_b, n_resamples=2000, seed=42)
            ci_str = f"[{comp['ci_low']:.4f}, {comp['ci_high']:.4f}]"
            wlt = f"{comp['wins']} / {comp['losses']} / {comp['ties']}"
            md.append(
                f"| **{mk}** | {comp['mean_a']:.4f} | {comp['mean_b']:.4f} | "
                f"{comp['mean_delta']:+.4f} | `{ci_str}` | {wlt} | {comp['verdict']} |"
            )

    return "\n".join(md)
