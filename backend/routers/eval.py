"""
routers/eval.py — REST API router for LOCUS Phase 7 Quantitative Evaluation Suite.

Endpoints:
- POST /eval/suites
- POST /eval/suites/{id}/items/import
- POST /eval/suites/{id}/clone
- GET  /eval/suites
- GET  /eval/suites/{id}
- PATCH /eval/items/{id}/review
- POST /eval/runs
- POST /eval/runs/{id}/cancel
- GET  /eval/runs/{id}
- GET  /eval/runs/{id}/report
- GET  /eval/runs/{id}/results
- GET  /eval/runs/{id}/export.csv
- POST /eval/matrix
- GET  /eval/compare
- GET  /eval/report.md
"""

import csv
import io
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import (
    get_db,
    SessionLocal,
    EvalSuite,
    EvalItem,
    EvalRun,
    EvalResult,
    Source,
    Document,
    Chunk,
    Record,
    safe_json,
)
from evaluation.engine import (
    create_eval_suite,
    import_suite_items,
    import_suite_items_csv,
    clone_eval_suite,
    is_suite_frozen,
    execute_eval_run,
    generate_run_report,
    generate_markdown_scorecard,
    lint_eval_suite,
    create_suite_item,
    update_suite_item,
    delete_suite_item,
    split_eval_suite,
)
from evaluation.matrix import generate_matrix_runs
from evaluation.stats import paired_bootstrap_comparison

router = APIRouter(prefix="/eval", tags=["evaluation"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateSuiteRequest(BaseModel):
    name: str
    description: Optional[str] = None
    source_ids: List[int]


class CloneSuiteRequest(BaseModel):
    new_name: str


class SplitSuiteRequest(BaseModel):
    holdout_fraction: float = Field(default=0.3, ge=0.0, le=1.0)
    seed: int = 42


class ItemCreateRequest(BaseModel):
    question: str
    item_type: str = "answerable"
    expected_facts: Optional[List[str]] = None
    reference_answer: Optional[str] = None
    expected_evidence: Optional[List[Dict[str, Any]]] = None
    expected_value: Optional[Any] = None
    expected_route: Optional[str] = None
    origin: Optional[str] = "hand"
    reviewed: Optional[bool] = False
    split: Optional[str] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None


class ItemUpdateRequest(BaseModel):
    question: Optional[str] = None
    item_type: Optional[str] = None
    expected_facts: Optional[List[str]] = None
    reference_answer: Optional[str] = None
    expected_evidence: Optional[List[Dict[str, Any]]] = None
    expected_value: Optional[Any] = None
    expected_route: Optional[str] = None
    origin: Optional[str] = None
    reviewed: Optional[bool] = None
    split: Optional[str] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None


class ReviewItemRequest(BaseModel):
    reviewed: bool


class CreateRunRequest(BaseModel):
    suite_id: int
    name: Optional[str] = None
    variant: Dict[str, Any] = Field(default_factory=dict)
    generate: bool = False
    judge: bool = False
    include_unreviewed: bool = False
    max_llm_calls: Optional[int] = None
    wait: bool = False


class MatrixRunRequest(BaseModel):
    suite_id: int
    base_variant: Dict[str, Any] = Field(default_factory=dict)
    vary: Dict[str, List[Any]] = Field(default_factory=dict)
    generate: bool = False
    judge: bool = False
    include_unreviewed: bool = False
    max_llm_calls: Optional[int] = None
    wait: bool = False


# ── Background Task Runner ───────────────────────────────────────────────────

def run_evaluation_background(run_id: int):
    """Background worker for asynchronous evaluation execution."""
    # Use get_db() so that dependency overrides (e.g. in test suites) are respected
    db = next(get_db())
    try:
        execute_eval_run(db, run_id)
    finally:
        db.close()


# ── Suites Endpoints ──────────────────────────────────────────────────────────

@router.post("/suites", status_code=201)
def create_suite_endpoint(req: CreateSuiteRequest, db: Session = Depends(get_db)):
    suite = create_eval_suite(
        db=db,
        name=req.name,
        source_ids=req.source_ids,
        description=req.description,
    )
    return {
        "id": suite.id,
        "name": suite.name,
        "description": suite.description,
        "source_ids": suite.source_ids,
        "suite_hash": suite.suite_hash,
        "created_at": suite.created_at.isoformat() if suite.created_at else None,
    }


@router.post("/suites/{id}/items/import")
def import_items_endpoint(
    id: int,
    items: Optional[List[Dict[str, Any]]] = None,
    db: Session = Depends(get_db),
):
    if items is None:
        raise HTTPException(status_code=400, detail="Missing items JSON body.")
    imported = import_suite_items(db=db, suite_id=id, items_data=items)
    return {
        "suite_id": id,
        "imported_count": len(imported),
        "status": "success",
    }


@router.post("/suites/{id}/items/upload-csv")
async def upload_items_csv_endpoint(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")
    imported = import_suite_items_csv(db=db, suite_id=id, csv_content=content)
    return {
        "suite_id": id,
        "imported_count": len(imported),
        "status": "success",
    }


@router.post("/suites/{id}/clone")
def clone_suite_endpoint(id: int, req: CloneSuiteRequest, db: Session = Depends(get_db)):
    cloned = clone_eval_suite(db=db, suite_id=id, new_name=req.new_name)
    return {
        "id": cloned.id,
        "name": cloned.name,
        "cloned_from": id,
        "suite_hash": cloned.suite_hash,
    }


@router.get("/suites")
def list_suites_endpoint(db: Session = Depends(get_db)):
    suites = db.query(EvalSuite).order_by(EvalSuite.id.desc()).all()
    out = []
    for s in suites:
        item_count = db.query(EvalItem).filter(EvalItem.suite_id == s.id).count()
        run_count = db.query(EvalRun).filter(EvalRun.suite_id == s.id).count()
        out.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "source_ids": s.source_ids,
            "suite_hash": s.suite_hash,
            "item_count": item_count,
            "run_count": run_count,
            "is_frozen": run_count > 0,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return out


@router.get("/suites/{id}")
def get_suite_endpoint(id: int, db: Session = Depends(get_db)):
    suite = db.query(EvalSuite).filter(EvalSuite.id == id).first()
    if not suite:
        raise HTTPException(status_code=404, detail=f"EvalSuite {id} not found.")

    items = db.query(EvalItem).filter(EvalItem.suite_id == id).order_by(EvalItem.position).all()
    run_count = db.query(EvalRun).filter(EvalRun.suite_id == id).count()

    return {
        "id": suite.id,
        "name": suite.name,
        "description": suite.description,
        "source_ids": suite.source_ids,
        "suite_hash": suite.suite_hash,
        "is_frozen": run_count > 0,
        "run_count": run_count,
        "items": [
            {
                "id": it.id,
                "position": it.position,
                "question": it.question,
                "item_type": it.item_type,
                "expected_facts": it.expected_facts,
                "reference_answer": it.reference_answer,
                "expected_evidence": it.expected_evidence,
                "expected_value": it.expected_value,
                "expected_route": it.expected_route,
                "origin": it.origin,
                "reviewed": it.reviewed,
                "split": it.split,
                "tags": it.tags,
            }
            for it in items
        ],
    }


@router.post("/suites/{id}/split")
def split_suite_endpoint(
    id: int,
    req: Optional[SplitSuiteRequest] = None,
    db: Session = Depends(get_db),
):
    frac = req.holdout_fraction if req is not None else 0.3
    sd = req.seed if req is not None else 42
    return split_eval_suite(db=db, suite_id=id, holdout_fraction=frac, seed=sd)


@router.post("/suites/{id}/items", status_code=201)
def create_suite_item_endpoint(
    id: int,
    req: ItemCreateRequest,
    db: Session = Depends(get_db),
):
    item = create_suite_item(db=db, suite_id=id, item_data=req.model_dump())
    return {
        "id": item.id,
        "suite_id": item.suite_id,
        "position": item.position,
        "question": item.question,
        "item_type": item.item_type,
        "expected_facts": item.expected_facts,
        "reference_answer": item.reference_answer,
        "expected_evidence": item.expected_evidence,
        "expected_value": item.expected_value,
        "expected_route": item.expected_route,
        "origin": item.origin,
        "reviewed": item.reviewed,
        "split": item.split,
        "tags": item.tags,
    }


@router.put("/suites/{id}/items/{item_id}")
def update_suite_item_endpoint(
    id: int,
    item_id: int,
    req: ItemUpdateRequest,
    db: Session = Depends(get_db),
):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    item = update_suite_item(db=db, suite_id=id, item_id=item_id, item_data=data)
    return {
        "id": item.id,
        "suite_id": item.suite_id,
        "position": item.position,
        "question": item.question,
        "item_type": item.item_type,
        "expected_facts": item.expected_facts,
        "reference_answer": item.reference_answer,
        "expected_evidence": item.expected_evidence,
        "expected_value": item.expected_value,
        "expected_route": item.expected_route,
        "origin": item.origin,
        "reviewed": item.reviewed,
        "split": item.split,
        "tags": item.tags,
    }


@router.delete("/suites/{id}/items/{item_id}")
def delete_suite_item_endpoint(
    id: int,
    item_id: int,
    db: Session = Depends(get_db),
):
    delete_suite_item(db=db, suite_id=id, item_id=item_id)
    return {"status": "deleted", "suite_id": id, "item_id": item_id}


@router.get("/sources/{id}/text-units")
def get_source_text_units_endpoint(
    id: int,
    version: Optional[int] = Query(None, description="Filter by version_no"),
    page: Optional[int] = Query(None, description="Filter by page_number"),
    db: Session = Depends(get_db),
):
    source = db.query(Source).filter(Source.id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {id} not found.")

    doc_q = db.query(Document).filter(Document.source_id == id)
    rec_q = db.query(Record).filter(Record.source_id == id, Record.status == "active")

    if version is not None:
        doc_q = doc_q.filter(Document.version_no == version)
        rec_q = rec_q.filter(Record.version_no == version)

    if page is not None:
        doc_q = doc_q.filter(Document.page_number == page)

    docs = doc_q.order_by(Document.page_number.asc().nulls_last(), Document.id.asc()).all()
    records = rec_q.order_by(Record.row_index.asc(), Record.id.asc()).all()

    units = []

    # Documents
    for d in docs:
        if d.page_number is not None:
            units.append({
                "unit_id": f"doc_{d.id}_p{d.page_number}",
                "source_id": id,
                "document_id": d.id,
                "page_number": d.page_number,
                "unit_type": "page",
                "title": d.title,
                "text": d.content or "",
            })
        else:
            chunks = db.query(Chunk).filter(Chunk.document_id == d.id).order_by(Chunk.chunk_index.asc()).all()
            if chunks:
                for ch in chunks:
                    units.append({
                        "unit_id": f"doc_{d.id}_chunk_{ch.chunk_index}",
                        "source_id": id,
                        "document_id": d.id,
                        "chunk_id": ch.id,
                        "chunk_index": ch.chunk_index,
                        "unit_type": "chunk",
                        "title": d.title,
                        "text": ch.content or "",
                    })
            else:
                paras = [p.strip() for p in (d.content or "").split("\n\n") if p.strip()]
                if not paras and d.content:
                    paras = [d.content.strip()]
                for p_idx, para in enumerate(paras):
                    units.append({
                        "unit_id": f"doc_{d.id}_p_{p_idx}",
                        "source_id": id,
                        "document_id": d.id,
                        "unit_type": "paragraph",
                        "title": d.title,
                        "text": para,
                    })

    # Records
    if page is None:
        for r in records:
            serialized = json.dumps(r.data) if isinstance(r.data, dict) else str(r.data or "")
            units.append({
                "unit_id": f"rec_{r.id}",
                "source_id": id,
                "record_id": r.id,
                "row_index": r.row_index,
                "row_key": str(r.id),
                "unit_type": "record",
                "text": serialized,
            })

    return units


@router.get("/suites/{id}/lint")
def lint_suite_endpoint(id: int, db: Session = Depends(get_db)):
    """
    Run comprehensive quality checks on gold evaluation suite labels:
    - best-match overlap of each expected span against corpus.
    - row_key presence in active records.
    - expected_facts occurrence in matched text.
    - duplicate question detection.
    - ambiguous spans matching 3+ documents.
    """
    return lint_eval_suite(db=db, suite_id=id)


@router.patch("/eval/items/{id}/review")
@router.patch("/items/{id}/review")
def review_item_endpoint(id: int, req: ReviewItemRequest, db: Session = Depends(get_db)):
    """Update item reviewed status. Allowed even when suite is frozen as reviewed is metadata."""
    item = db.query(EvalItem).filter(EvalItem.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"EvalItem {id} not found.")

    item.reviewed = req.reviewed
    db.commit()
    return {"id": item.id, "reviewed": item.reviewed}


# ── Runs Endpoints ────────────────────────────────────────────────────────────

@router.post("/runs")
def create_run_endpoint(
    req: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    suite = db.query(EvalSuite).filter(EvalSuite.id == req.suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail=f"EvalSuite {req.suite_id} not found.")

    run_name = req.name or f"Run: {req.variant.get('strategy', 'auto')} (top_k={req.variant.get('top_k', 5)})"

    run = EvalRun(
        suite_id=req.suite_id,
        name=run_name,
        variant=safe_json(req.variant),
        config_hash=suite.suite_hash or "",
        generate=req.generate,
        judge=req.judge,
        include_unreviewed=req.include_unreviewed,
        status="queued",
        progress={"status": "queued"},
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if req.wait:
        execute_eval_run(db, run.id)
        db.refresh(run)
    else:
        background_tasks.add_task(run_evaluation_background, run.id)

    return {
        "id": run.id,
        "suite_id": run.suite_id,
        "name": run.name,
        "status": run.status,
        "variant": run.variant,
        "generate": run.generate,
        "judge": run.judge,
        "include_unreviewed": run.include_unreviewed,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


@router.get("/runs")
def list_runs_endpoint(
    suite_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(EvalRun)
    if suite_id is not None:
        query = query.filter(EvalRun.suite_id == suite_id)
    runs = query.order_by(EvalRun.id.desc()).offset(offset).limit(limit).all()
    out = []
    for r in runs:
        out.append({
            "id": r.id,
            "suite_id": r.suite_id,
            "name": r.name,
            "status": r.status,
            "variant": r.variant,
            "generate": r.generate,
            "judge": r.judge,
            "include_unreviewed": r.include_unreviewed,
            "progress": r.progress,
            "error": r.error,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "seed": r.seed,
            "provenance": r.provenance,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return out


@router.post("/runs/{id}/cancel")
def cancel_run_endpoint(id: int, db: Session = Depends(get_db)):
    run = db.query(EvalRun).filter(EvalRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"EvalRun {id} not found.")

    if run.status in ("completed", "failed"):
        return {"id": run.id, "status": run.status, "message": "Run already finished."}

    run.status = "cancelled"
    db.commit()
    return {"id": run.id, "status": "cancelled"}


@router.get("/runs/{id}")
def get_run_endpoint(id: int, db: Session = Depends(get_db)):
    run = db.query(EvalRun).filter(EvalRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"EvalRun {id} not found.")

    return {
        "id": run.id,
        "suite_id": run.suite_id,
        "name": run.name,
        "status": run.status,
        "variant": run.variant,
        "generate": run.generate,
        "judge": run.judge,
        "include_unreviewed": run.include_unreviewed,
        "progress": run.progress,
        "error": run.error,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "seed": run.seed,
        "provenance": run.provenance,
    }


@router.get("/runs/{id}/report")
def get_run_report_endpoint(
    id: int,
    split: Optional[str] = Query("all", description="Filter by split: dev, holdout, or all"),
    db: Session = Depends(get_db),
):
    return generate_run_report(db, id, split=split)


@router.get("/runs/{id}/results")
def get_run_results_endpoint(
    id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    results = (
        db.query(EvalResult)
        .filter(EvalResult.run_id == id)
        .order_by(EvalResult.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(EvalResult).filter(EvalResult.run_id == id).count()

    out = []
    for r in results:
        out.append({
            "id": r.id,
            "run_id": r.run_id,
            "item_id": r.item_id,
            "route": r.route,
            "strategy": r.strategy,
            "status": r.status,
            "answer": r.answer,
            "citations": r.citations,
            "metrics": r.metrics,
            "latency_ms": r.latency_ms,
            "llm_calls": r.llm_calls,
            "judge_calls": r.judge_calls,
        })

    return {"total": total, "limit": limit, "offset": offset, "results": out}


@router.get("/runs/{id}/export.csv")
def export_run_csv_endpoint(id: int, db: Session = Depends(get_db)):
    run = db.query(EvalRun).filter(EvalRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"EvalRun {id} not found.")

    results = db.query(EvalResult).filter(EvalResult.run_id == id).order_by(EvalResult.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "item_id", "route", "strategy", "status",
        "hit@1", "hit@3", "hit@5", "recall@5", "recall@20",
        "precision@5", "ndcg@5", "mrr", "refusal_correct",
        "unsafe_answer", "false_refusal", "value_match", "latency_total_ms",
    ])

    for r in results:
        m = r.metrics or {}
        lat = r.latency_ms or {}
        writer.writerow([
            r.item_id,
            r.route,
            r.strategy,
            r.status,
            m.get("hit@1", ""),
            m.get("hit@3", ""),
            m.get("hit@5", ""),
            m.get("recall@5", ""),
            m.get("recall@20", ""),
            m.get("precision@5", ""),
            m.get("ndcg@5", ""),
            m.get("mrr", ""),
            m.get("refusal_correct", ""),
            m.get("unsafe_answer", ""),
            m.get("false_refusal", ""),
            m.get("value_match", ""),
            lat.get("total", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=eval_run_{id}_export.csv"},
    )


# ── Matrix & Report Endpoints ────────────────────────────────────────────────

@router.post("/matrix")
def matrix_sweep_endpoint(
    req: MatrixRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    runs = generate_matrix_runs(
        db=db,
        suite_id=req.suite_id,
        base_variant=req.base_variant,
        vary=req.vary,
        generate=req.generate,
        judge=req.judge,
        include_unreviewed=req.include_unreviewed,
        max_llm_calls=req.max_llm_calls,
        wait=req.wait,
    )

    if not req.wait:
        for r in runs:
            background_tasks.add_task(run_evaluation_background, r.id)

    return {
        "suite_id": req.suite_id,
        "runs_created": len(runs),
        "run_ids": [r.id for r in runs],
    }


@router.get("/compare")
def compare_runs_endpoint(
    a: int = Query(..., description="Run ID A"),
    b: int = Query(..., description="Run ID B"),
    split: Optional[str] = Query("all", description="dev, holdout, or all"),
    db: Session = Depends(get_db),
):
    res_a_q = db.query(EvalResult).filter(EvalResult.run_id == a)
    res_b_q = db.query(EvalResult).filter(EvalResult.run_id == b)

    if split in ("dev", "holdout"):
        res_a_q = res_a_q.join(EvalItem, EvalResult.item_id == EvalItem.id).filter(EvalItem.split == split)
        res_b_q = res_b_q.join(EvalItem, EvalResult.item_id == EvalItem.id).filter(EvalItem.split == split)

    res_a = res_a_q.all()
    res_b = res_b_q.all()

    map_a = {r.item_id: r for r in res_a}
    map_b = {r.item_id: r for r in res_b}
    common = sorted(set(map_a.keys()) & set(map_b.keys()))

    if not common:
        raise HTTPException(status_code=400, detail=f"No common items between the two runs for split='{split}'.")

    out: Dict[str, Any] = {
        "run_a": a,
        "run_b": b,
        "split": split,
        "common_items_count": len(common),
        "metrics": {},
        "route_slices": {},
    }

    metrics_list = ("hit@5", "recall@5", "precision@5", "mrr", "false_refusal")
    for mk in metrics_list:
        vals_a = []
        vals_b = []
        for iid in common:
            ma = map_a[iid].metrics or {}
            mb = map_b[iid].metrics or {}
            if mk in ma and mk in mb and ma[mk] is not None and mb[mk] is not None:
                vals_a.append(float(ma[mk]))
                vals_b.append(float(mb[mk]))

        if vals_a:
            out["metrics"][mk] = paired_bootstrap_comparison(vals_a, vals_b, n_resamples=2000, seed=42)

    # Route slices
    route_to_items: Dict[str, List[int]] = {}
    for iid in common:
        rt = map_a[iid].route or "semantic"
        route_to_items.setdefault(rt, []).append(iid)

    for rt, slice_iids in sorted(route_to_items.items()):
        slice_metrics: Dict[str, Any] = {}
        for mk in metrics_list:
            vals_a = [float(map_a[iid].metrics[mk]) for iid in slice_iids if mk in (map_a[iid].metrics or {}) and mk in (map_b[iid].metrics or {}) and map_a[iid].metrics[mk] is not None and map_b[iid].metrics[mk] is not None]
            vals_b = [float(map_b[iid].metrics[mk]) for iid in slice_iids if mk in (map_a[iid].metrics or {}) and mk in (map_b[iid].metrics or {}) and map_a[iid].metrics[mk] is not None and map_b[iid].metrics[mk] is not None]
            if vals_a:
                slice_metrics[mk] = paired_bootstrap_comparison(vals_a, vals_b, n_resamples=1000, seed=42)
        out["route_slices"][rt] = {
            "n": len(slice_iids),
            "metrics": slice_metrics,
        }

    return out


@router.get("/report.md", response_class=PlainTextResponse)
def get_report_markdown_endpoint(
    run_ids: str = Query(..., description="Comma-separated run IDs"),
    split: Optional[str] = Query("all", description="dev, holdout, or all"),
    db: Session = Depends(get_db),
):
    try:
        rids = [int(x.strip()) for x in run_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_ids format. Expected comma-separated integers.")

    if not rids:
        raise HTTPException(status_code=400, detail="No run_ids provided.")

    md_content = generate_markdown_scorecard(db, rids, split=split)
    return PlainTextResponse(md_content, media_type="text/markdown")
