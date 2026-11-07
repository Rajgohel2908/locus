"""
backend/evaluation/doctor/engine.py — Core engine and state machine for RAG Doctor v1.

Provides:
  - run_doctor_analysis: evaluates D1-D9 rules across eval runs, persists report & findings.
  - approve_finding / reject_finding: state transitions for findings.
  - apply_finding: applies patch by creating a new PipelineConfig (kind='doctor').
  - verify_finding: executes evaluation on patched config, computes paired comparison,
    and transitions finding status to verified_improved / verified_no_change / verified_regressed.
"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException

from db import (
    DoctorReport,
    DoctorFinding,
    EvalSuite,
    EvalRun,
    EvalResult,
    EvalItem,
    PipelineConfig,
    Source,
    IndexRun,
    safe_json,
)
from evaluation.doctor.rules import evaluate_rules
from evaluation.engine import execute_eval_run, resolve_variant_index_runs
from evaluation.stats import paired_bootstrap_comparison


def run_doctor_analysis(db: Session, run_ids: List[int]) -> DoctorReport:
    """
    Run diagnostic rules across one or more completed eval runs.
    Persists DoctorReport and associated DoctorFinding rows.
    """
    if not run_ids:
        raise HTTPException(status_code=400, detail="run_ids list cannot be empty.")

    runs = db.query(EvalRun).filter(EvalRun.id.in_(run_ids)).all()
    if len(runs) != len(run_ids):
        found_ids = {r.id for r in runs}
        missing = set(run_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"EvalRuns {missing} not found.")

    # Collect all results and items
    run_results: Dict[int, List[EvalResult]] = {}
    item_ids = set()

    for r in runs:
        res = db.query(EvalResult).filter(EvalResult.run_id == r.id).all()
        run_results[r.id] = res
        for item_res in res:
            item_ids.add(item_res.item_id)

    items = db.query(EvalItem).filter(EvalItem.id.in_(list(item_ids))).all() if item_ids else []
    items_map = {item.id: item for item in items}

    # Evaluate rules
    raw_findings, not_fired_reasons = evaluate_rules(runs, run_results, items_map, return_not_fired=True)

    # Build summary
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for f in raw_findings:
        sev = f.get("severity", "info")
        if sev in severity_counts:
            severity_counts[sev] += 1

    summary = {
        "runs_analyzed": run_ids,
        "total_findings": len(raw_findings),
        "severities": severity_counts,
        "rules_evaluated": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"],
        "not_fired_reasons": not_fired_reasons,
    }

    report = DoctorReport(
        run_ids=run_ids,
        summary=safe_json(summary),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Persist findings
    for f in raw_findings:
        finding = DoctorFinding(
            report_id=report.id,
            rule_id=f["rule_id"],
            severity=f["severity"],
            title=f["title"],
            diagnosis=f["diagnosis"],
            evidence=safe_json(f.get("evidence", {})),
            evidence_level=f.get("evidence_level", "hypothesis"),
            counterfactual=safe_json(f.get("counterfactual", {})),
            proposed_patch=safe_json(f.get("proposed_patch", {})),
            expected_effect=f.get("expected_effect", ""),
            cost_note=f.get("cost_note", ""),
            status="proposed",
        )
        db.add(finding)

    db.commit()
    return report


def approve_finding(db: Session, finding_id: int) -> DoctorFinding:
    """Approve a proposed finding."""
    finding = db.query(DoctorFinding).filter(DoctorFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"DoctorFinding {finding_id} not found.")

    if finding.status not in ("proposed", "rejected"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve finding with status '{finding.status}'. Finding must be in 'proposed' or 'rejected'.",
        )

    finding.status = "approved"
    db.commit()
    db.refresh(finding)
    return finding


def reject_finding(db: Session, finding_id: int) -> DoctorFinding:
    """Reject a proposed finding."""
    finding = db.query(DoctorFinding).filter(DoctorFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"DoctorFinding {finding_id} not found.")

    if finding.status not in ("proposed", "approved"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject finding with status '{finding.status}'. Finding must be in 'proposed' or 'approved'.",
        )

    finding.status = "rejected"
    db.commit()
    db.refresh(finding)
    return finding


def apply_finding(db: Session, finding_id: int) -> Tuple[DoctorFinding, PipelineConfig]:
    """
    Apply an approved finding by creating a new PipelineConfig (kind='doctor').
    Existing configs remain strictly untouched.
    """
    finding = db.query(DoctorFinding).filter(DoctorFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"DoctorFinding {finding_id} not found.")

    if finding.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply finding with status '{finding.status}'. Finding must be approved first.",
        )

    report = db.query(DoctorReport).filter(DoctorReport.id == finding.report_id).first()
    if not report or not report.run_ids:
        raise HTTPException(status_code=400, detail="Associated doctor report has no runs.")

    # Base on original run
    base_run = db.query(EvalRun).filter(EvalRun.id == report.run_ids[0]).first()
    if not base_run:
        raise HTTPException(status_code=404, detail=f"Base EvalRun {report.run_ids[0]} not found.")

    suite = db.query(EvalSuite).filter(EvalSuite.id == base_run.suite_id).first()
    source_ids = list(suite.source_ids) if suite and suite.source_ids else []

    # Merge patch into base spec
    base_spec = dict(base_run.variant or {})
    patch = finding.proposed_patch or {}
    patched_spec = dict(base_spec)
    patched_spec.update(patch)

    spec_json = json.dumps(patched_spec, sort_keys=True)
    spec_hash = hashlib.sha256(spec_json.encode("utf-8")).hexdigest()[:16]

    # Resolve index runs for new chunk parameters
    chunk_size = patched_spec.get("chunk_size", 800)
    chunk_overlap = patched_spec.get("chunk_overlap", 120)
    index_runs_map = resolve_variant_index_runs(
        db=db,
        source_ids=source_ids,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    config_name = f"Doctor Patch [{finding.rule_id}]: {finding.title[:40]}"
    config = PipelineConfig(
        name=config_name,
        kind="doctor",
        source_ids=source_ids,
        spec=safe_json(patched_spec),
        spec_hash=spec_hash,
        recommendation_id=None,
        index_runs=safe_json(index_runs_map),
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    finding.status = "applied"
    finding.applied_config_id = config.id
    db.commit()
    db.refresh(finding)

    return finding, config


def verify_finding(db: Session, finding_id: int) -> Tuple[DoctorFinding, EvalRun]:
    """
    Verify an applied finding by executing an evaluation run on the patched configuration
    and performing a paired bootstrap comparison against the original run.
    """
    finding = db.query(DoctorFinding).filter(DoctorFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail=f"DoctorFinding {finding_id} not found.")

    if finding.status != "applied" or not finding.applied_config_id:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot verify finding with status '{finding.status}'. Finding must be applied first.",
        )

    config = db.query(PipelineConfig).filter(PipelineConfig.id == finding.applied_config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"PipelineConfig {finding.applied_config_id} not found.")

    report = db.query(DoctorReport).filter(DoctorReport.id == finding.report_id).first()
    orig_run_id = report.run_ids[0]
    orig_run = db.query(EvalRun).filter(EvalRun.id == orig_run_id).first()
    if not orig_run:
        raise HTTPException(status_code=404, detail=f"Original EvalRun {orig_run_id} not found.")

    # Create verification run
    suite_id = orig_run.suite_id
    ver_variant = dict(config.spec or {})
    ver_variant["pipeline_config_id"] = config.id

    ver_run = EvalRun(
        suite_id=suite_id,
        name=f"Verify Doctor Patch [{finding.rule_id}] on Config {config.id}",
        variant=safe_json(ver_variant),
        config_hash=orig_run.config_hash,
        generate=orig_run.generate,
        judge=orig_run.judge,
        include_unreviewed=orig_run.include_unreviewed,
        status="queued",
    )
    db.add(ver_run)
    db.commit()
    db.refresh(ver_run)

    # Execute verification run synchronously
    execute_eval_run(db, ver_run.id)
    db.refresh(ver_run)

    # Execute paired comparison between verification run and original run
    res_orig = {r.item_id: r for r in db.query(EvalResult).filter(EvalResult.run_id == orig_run_id).all()}
    res_ver = {r.item_id: r for r in db.query(EvalResult).filter(EvalResult.run_id == ver_run.id).all()}

    common_ids = sorted(set(res_orig.keys()) & set(res_ver.keys()))
    if not common_ids:
        finding.status = "verified_no_change"
        finding.verification_run_id = ver_run.id
        db.commit()
        db.refresh(finding)
        return finding, ver_run

    # Target comparison metric: recall@5 (or false_refusal if D4)
    target_metric = "false_refusal" if finding.rule_id == "D4" else "recall@5"
    vals_orig = [float((res_orig[i].metrics or {}).get(target_metric, 0.0)) for i in common_ids]
    vals_ver = [float((res_ver[i].metrics or {}).get(target_metric, 0.0)) for i in common_ids]

    comp = paired_bootstrap_comparison(vals_ver, vals_orig, n_resamples=2000, seed=42)
    ci_low = comp["ci_low"]
    ci_high = comp["ci_high"]

    # Determine status from CI
    if finding.rule_id == "D4":
        # For false_refusal, a decrease is an improvement (lower delta)
        if ci_high < 0:
            finding.status = "verified_improved"
        elif ci_low > 0:
            finding.status = "verified_regressed"
        else:
            finding.status = "verified_no_change"
    else:
        # Standard: higher recall is improvement
        if ci_low > 0:
            finding.status = "verified_improved"
        elif ci_high < 0:
            finding.status = "verified_regressed"
        else:
            finding.status = "verified_no_change"

    finding.verification_run_id = ver_run.id
    db.commit()
    db.refresh(finding)

    return finding, ver_run

