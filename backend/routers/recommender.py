"""
backend/routers/recommender.py — Phase 6B Recommender endpoints and pipeline configs.

Endpoints:
- POST /kb-profile
- POST /recommendations
- GET  /recommendations/{id}
- GET  /recommendations
- POST /recommendations/{id}/approve
- POST /recommendations/{id}/reject
- POST /recommendations/{id}/apply
- GET  /pipeline-configs
- GET  /pipeline-configs/{id}
- GET  /pipeline-configs/compare
- GET  /pipeline-configs/{id}/graph
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import (
    get_db,
    Recommendation,
    PipelineConfig,
    Source,
    SourceVersion,
    IndexRun,
    safe_json,
)
from recommender.profile import build_kb_profile
from recommender.rules import (
    evaluate_rules,
    get_baseline_spec,
    compute_spec_hash,
    RULES_VERSION,
    VALID_GOALS,
)
from recommender.graph import build_pipeline_graph, render_mermaid_graph
from routers.indexing import perform_indexing

router = APIRouter()


class KBProfileRequest(BaseModel):
    source_ids: List[int]
    version: Optional[int] = None


class RecommendationCreateRequest(BaseModel):
    source_ids: List[int]
    goal: str


class ApplyRequest(BaseModel):
    build_index: Optional[bool] = None


def _format_recommendation(rec: Recommendation) -> Dict[str, Any]:
    return {
        "id": rec.id,
        "source_ids": rec.source_ids,
        "goal": rec.goal,
        "rules_version": rec.rules_version,
        "data_profile": rec.data_profile,
        "pipeline_spec": rec.pipeline_spec,
        "rules_fired": rec.rules_fired,
        "rules_not_fired": rec.rules_not_fired,
        "warnings": rec.warnings,
        "status": rec.status,
        "created_at": str(rec.created_at) if rec.created_at else None,
        "decided_at": str(rec.decided_at) if rec.decided_at else None,
    }


def _format_config(cfg: PipelineConfig) -> Dict[str, Any]:
    return {
        "id": cfg.id,
        "name": cfg.name,
        "kind": cfg.kind,
        "source_ids": cfg.source_ids,
        "spec": cfg.spec,
        "spec_hash": cfg.spec_hash,
        "recommendation_id": cfg.recommendation_id,
        "index_runs": cfg.index_runs,
        "created_at": str(cfg.created_at) if cfg.created_at else None,
    }


@router.post("/kb-profile", summary="Extract read-only data profile from sources")
def get_kb_profile(
    req: KBProfileRequest,
    db: Session = Depends(get_db),
):
    """
    Build KB profile from existing DB data only.
    No network calls, no model execution.
    """
    if not req.source_ids:
        raise HTTPException(status_code=422, detail="source_ids list cannot be empty.")
    existing_rows = db.query(Source.id).filter(Source.id.in_(req.source_ids)).all()
    existing_ids = set(r[0] for r in existing_rows)
    missing = [sid for sid in req.source_ids if sid not in existing_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Source ID(s) not found: {missing}")

    profile = build_kb_profile(db=db, source_ids=req.source_ids, version=req.version)
    return profile


@router.post("/recommendations", summary="Generate a rule-based pipeline recommendation")
def create_recommendation(
    req: RecommendationCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Compute KB profile and evaluate deterministic rules R1-R12.
    Stores recommendation in status 'proposed'.
    """
    if not req.source_ids:
        raise HTTPException(status_code=422, detail="source_ids list cannot be empty.")
    existing_rows = db.query(Source.id).filter(Source.id.in_(req.source_ids)).all()
    existing_ids = set(r[0] for r in existing_rows)
    missing = [sid for sid in req.source_ids if sid not in existing_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Source ID(s) not found: {missing}")

    if req.goal not in VALID_GOALS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid goal '{req.goal}'. Supported goals: {sorted(list(VALID_GOALS))} (summarization is not supported yet).",
        )

    profile = build_kb_profile(db=db, source_ids=req.source_ids)
    rule_eval = evaluate_rules(profile=profile, goal=req.goal)

    rec = Recommendation(
        source_ids=req.source_ids,
        goal=req.goal,
        rules_version=rule_eval["rules_version"],
        data_profile=safe_json(profile),
        pipeline_spec=safe_json(rule_eval["pipeline_spec"]),
        rules_fired=safe_json(rule_eval["rules_fired"]),
        rules_not_fired=safe_json(rule_eval["rules_not_fired"]),
        warnings=safe_json(rule_eval["warnings"]),
        status="proposed",
        created_at=datetime.utcnow(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return _format_recommendation(rec)


@router.get("/recommendations/{rec_id}", summary="Get recommendation by ID")
def get_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    return _format_recommendation(rec)


@router.get("/recommendations", summary="List recommendations")
def list_recommendations(
    source_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Recommendation)
    recs = query.order_by(Recommendation.id.desc()).all()
    if source_id is not None:
        recs = [r for r in recs if source_id in (r.source_ids or [])]
    return [_format_recommendation(r) for r in recs]


@router.post("/recommendations/{rec_id}/approve", summary="Approve recommendation")
def approve_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    if rec.status != "proposed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve recommendation in status '{rec.status}'. Only 'proposed' recommendations can be approved.",
        )

    rec.status = "approved"
    rec.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return _format_recommendation(rec)


@router.post("/recommendations/{rec_id}/reject", summary="Reject recommendation")
def reject_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")
    if rec.status != "proposed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject recommendation in status '{rec.status}'. Only 'proposed' recommendations can be rejected.",
        )

    rec.status = "rejected"
    rec.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return _format_recommendation(rec)


@router.post("/recommendations/{rec_id}/apply", summary="Apply approved recommendation")
def apply_recommendation(
    rec_id: int,
    req: Optional[ApplyRequest] = None,
    build_index: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Apply an approved recommendation.
    Creates or reuses baseline config (Phase 4 baseline) and recommended config.
    Builds/reuses index runs matching chunking specs if build_index is True.
    Idempotent: repeated apply does not duplicate configs or index runs.
    Accepts build_index in JSON body or as a query parameter.
    """
    should_build_index = True
    if build_index is not None:
        should_build_index = build_index
    elif req is not None and req.build_index is not None:
        should_build_index = req.build_index

    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found.")

    if rec.status not in ("approved", "applied"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply recommendation in status '{rec.status}'. Only 'approved' recommendations can be applied.",
        )

    # 1. Baseline Config
    b_spec = get_baseline_spec()
    b_hash = compute_spec_hash(b_spec)
    baseline_cfg = (
        db.query(PipelineConfig)
        .filter(
            PipelineConfig.kind == "baseline",
            PipelineConfig.spec_hash == b_hash,
            PipelineConfig.source_ids == rec.source_ids,
        )
        .first()
    )
    if not baseline_cfg:
        baseline_cfg = PipelineConfig(
            name="Phase 4 Baseline",
            kind="baseline",
            source_ids=rec.source_ids,
            spec=safe_json(b_spec),
            spec_hash=b_hash,
            recommendation_id=rec.id,
            index_runs={},
        )
        db.add(baseline_cfg)
        db.flush()

    # 2. Recommended Config
    r_spec = rec.pipeline_spec
    r_hash = compute_spec_hash(r_spec)
    recommended_cfg = (
        db.query(PipelineConfig)
        .filter(
            PipelineConfig.kind == "recommended",
            PipelineConfig.spec_hash == r_hash,
            PipelineConfig.source_ids == rec.source_ids,
        )
        .first()
    )
    if not recommended_cfg:
        recommended_cfg = PipelineConfig(
            name=f"Recommended ({rec.goal})",
            kind="recommended",
            source_ids=rec.source_ids,
            spec=safe_json(r_spec),
            spec_hash=r_hash,
            recommendation_id=rec.id,
            index_runs={},
        )
        db.add(recommended_cfg)
        db.flush()

    # 3. Build or Reuse Index Runs
    if should_build_index:
        for cfg in (baseline_cfg, recommended_cfg):
            runs_map = dict(cfg.index_runs or {})
            for sid in rec.source_ids:
                s_ver = (
                    db.query(func.max(SourceVersion.version_no))
                    .filter(SourceVersion.source_id == sid)
                    .scalar()
                ) or 1
                c_size = cfg.spec.get("chunk_size", 800)
                c_overlap = cfg.spec.get("chunk_overlap", 120)

                # Check for existing completed run with identical parameters
                existing_run = (
                    db.query(IndexRun)
                    .filter(
                        IndexRun.source_id == sid,
                        IndexRun.source_version == s_ver,
                        IndexRun.chunk_size == c_size,
                        IndexRun.chunk_overlap == c_overlap,
                        IndexRun.status == "completed",
                    )
                    .order_by(IndexRun.id.desc())
                    .first()
                )
                if existing_run:
                    runs_map[str(sid)] = existing_run.id
                else:
                    new_run = perform_indexing(
                        db=db,
                        source_id=sid,
                        version=s_ver,
                        chunk_size=c_size,
                        chunk_overlap=c_overlap,
                    )
                    runs_map[str(sid)] = new_run.id

            cfg.index_runs = safe_json(runs_map)

    # 4. Mark applied
    rec.status = "applied"
    if not rec.decided_at:
        rec.decided_at = datetime.utcnow()

    db.commit()
    db.refresh(baseline_cfg)
    db.refresh(recommended_cfg)
    db.refresh(rec)

    return {
        "status": "applied",
        "recommendation_id": rec.id,
        "baseline_config": _format_config(baseline_cfg),
        "recommended_config": _format_config(recommended_cfg),
    }


@router.get("/pipeline-configs", summary="List pipeline configs")
def list_pipeline_configs(db: Session = Depends(get_db)):
    cfgs = db.query(PipelineConfig).order_by(PipelineConfig.id.asc()).all()
    return [_format_config(c) for c in cfgs]


@router.get("/pipeline-configs/compare", summary="Compare two pipeline configs field-by-field")
def compare_pipeline_configs(
    a: int = Query(..., description="First pipeline config ID"),
    b: int = Query(..., description="Second pipeline config ID"),
    db: Session = Depends(get_db),
):
    cfg_a = db.query(PipelineConfig).filter(PipelineConfig.id == a).first()
    cfg_b = db.query(PipelineConfig).filter(PipelineConfig.id == b).first()
    if not cfg_a:
        raise HTTPException(status_code=404, detail=f"Pipeline config {a} not found.")
    if not cfg_b:
        raise HTTPException(status_code=404, detail=f"Pipeline config {b} not found.")

    rec_target = None
    if cfg_b.recommendation_id:
        rec_target = db.query(Recommendation).filter(Recommendation.id == cfg_b.recommendation_id).first()
    elif cfg_a.recommendation_id:
        rec_target = db.query(Recommendation).filter(Recommendation.id == cfg_a.recommendation_id).first()

    field_to_rules: Dict[str, List[str]] = {}
    if rec_target and rec_target.rules_fired:
        for rf in rec_target.rules_fired:
            rid = rf.get("id") or rf.get("rule_id")
            effect = str(rf.get("effect", ""))
            name = str(rf.get("name", ""))
            if "chunk_size" in effect or name == "chunk_sizing":
                field_to_rules.setdefault("chunk_size", []).append(rid)
                field_to_rules.setdefault("chunk_overlap", []).append(rid)
                field_to_rules.setdefault("chunk_unit", []).append(rid)
            if "strategy_default" in effect or name in ("identifier_present", "tiny_corpus", "default_text"):
                field_to_rules.setdefault("strategy_default", []).append(rid)
            if "use_rerank" in effect or name in ("tiny_corpus", "rerank_policy", "goal_adjustments"):
                field_to_rules.setdefault("use_rerank", []).append(rid)
            if "top_k" in effect or name == "goal_adjustments":
                field_to_rules.setdefault("top_k", []).append(rid)
            if "structured_route_enabled" in effect or name == "structured_present":
                field_to_rules.setdefault("structured_route_enabled", []).append(rid)
            if "min_extraction_confidence" in effect or name == "ocr_quality":
                field_to_rules.setdefault("filters_default", []).append(rid)
            if "suggested_filters" in effect or name == "stale_content":
                field_to_rules.setdefault("suggested_filters", []).append(rid)

    fallback_causes = {
        "chunk_size": ["R6"],
        "chunk_overlap": ["R6"],
        "chunk_unit": ["R6"],
        "strategy_default": ["R2", "R3", "R4"],
        "use_rerank": ["R3", "R5", "R12"],
        "top_k": ["R12"],
        "candidates_n": ["default"],
        "filters_default": ["R9"],
        "structured_route_enabled": ["R1"],
        "router_enabled": ["baseline_mode"],
        "suggested_filters": ["R7"],
    }

    spec_a = cfg_a.spec or {}
    spec_b = cfg_b.spec or {}

    all_keys = [
        "chunk_size",
        "chunk_overlap",
        "chunk_unit",
        "strategy_default",
        "use_rerank",
        "top_k",
        "candidates_n",
        "filters_default",
        "structured_route_enabled",
        "router_enabled",
        "suggested_filters",
    ]

    differences = []
    for k in all_keys:
        val_a = spec_a.get(k)
        val_b = spec_b.get(k)
        if val_a != val_b:
            active_rules = field_to_rules.get(k) or fallback_causes.get(k, ["default"])
            seen = set()
            deduped_rules = [r for r in active_rules if not (r in seen or seen.add(r))]
            differences.append({
                "field": k,
                "a": val_a,
                "b": val_b,
                "rules": deduped_rules,
            })

    return {
        "config_a": {"id": cfg_a.id, "name": cfg_a.name, "kind": cfg_a.kind},
        "config_b": {"id": cfg_b.id, "name": cfg_b.name, "kind": cfg_b.kind},
        "differences": differences,
    }


@router.get("/pipeline-configs/{cfg_id}/graph", summary="Get pipeline graph in JSON or Mermaid")
def get_pipeline_graph_endpoint(
    cfg_id: int,
    format: str = Query("json", pattern="^(json|mermaid)$"),
    db: Session = Depends(get_db),
):
    cfg = db.query(PipelineConfig).filter(PipelineConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Pipeline config {cfg_id} not found.")

    graph_data = build_pipeline_graph(db=db, pipeline_config_row=cfg)

    if format == "mermaid":
        mermaid_text = render_mermaid_graph(graph_data)
        return Response(content=mermaid_text, media_type="text/plain")

    return graph_data


@router.get("/pipeline-configs/{cfg_id}", summary="Get pipeline config by ID")
def get_pipeline_config(
    cfg_id: int,
    db: Session = Depends(get_db),
):
    cfg = db.query(PipelineConfig).filter(PipelineConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Pipeline config {cfg_id} not found.")
    return _format_config(cfg)
