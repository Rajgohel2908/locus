"""
backend/routers/doctor.py — FastAPI endpoints for RAG Doctor v1.

Endpoints:
  - POST /doctor/reports {run_ids: List[int]}
  - GET /doctor/reports/{id}
  - POST /doctor/findings/{id}/approve
  - POST /doctor/findings/{id}/reject
  - POST /doctor/findings/{id}/apply
  - POST /doctor/findings/{id}/verify
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db, DoctorReport, DoctorFinding, PipelineConfig, EvalRun
from evaluation.doctor.engine import (
    run_doctor_analysis,
    approve_finding,
    reject_finding,
    apply_finding,
    verify_finding,
)

router = APIRouter(prefix="/doctor", tags=["RAG Doctor"])


class DoctorReportRequest(BaseModel):
    run_ids: List[int] = Field(..., min_length=1, description="List of completed EvalRun IDs to diagnose")


def _finding_dict(f: DoctorFinding) -> Dict[str, Any]:
    return {
        "id": f.id,
        "report_id": f.report_id,
        "rule_id": f.rule_id,
        "severity": f.severity,
        "title": f.title,
        "diagnosis": f.diagnosis,
        "evidence": f.evidence,
        "evidence_level": f.evidence_level,
        "counterfactual": f.counterfactual,
        "proposed_patch": f.proposed_patch,
        "expected_effect": f.expected_effect,
        "cost_note": f.cost_note,
        "status": f.status,
        "applied_config_id": f.applied_config_id,
        "verification_run_id": f.verification_run_id,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.post("/reports", status_code=201)
def create_doctor_report(req: DoctorReportRequest, db: Session = Depends(get_db)):
    """Analyze eval runs with RAG Doctor rules D1-D9 and generate diagnoses and proposed patches."""
    report = run_doctor_analysis(db=db, run_ids=req.run_ids)
    findings = db.query(DoctorFinding).filter(DoctorFinding.report_id == report.id).order_by(DoctorFinding.id).all()

    return {
        "id": report.id,
        "run_ids": report.run_ids,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "summary": report.summary,
        "findings": [_finding_dict(f) for f in findings],
    }


@router.get("/reports")
def list_doctor_reports(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    reports = db.query(DoctorReport).order_by(DoctorReport.id.desc()).offset(offset).limit(limit).all()
    out = []
    for rep in reports:
        findings_count = db.query(DoctorFinding).filter(DoctorFinding.report_id == rep.id).count()
        out.append({
            "id": rep.id,
            "run_ids": rep.run_ids,
            "created_at": rep.created_at.isoformat() if rep.created_at else None,
            "summary": rep.summary,
            "findings_count": findings_count,
        })
    return out


@router.get("/reports/{id}")
def get_doctor_report(id: int, db: Session = Depends(get_db)):
    """Retrieve Doctor report and its associated findings."""
    report = db.query(DoctorReport).filter(DoctorReport.id == id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"DoctorReport {id} not found.")

    findings = db.query(DoctorFinding).filter(DoctorFinding.report_id == report.id).order_by(DoctorFinding.id).all()

    return {
        "id": report.id,
        "run_ids": report.run_ids,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "summary": report.summary,
        "findings": [_finding_dict(f) for f in findings],
    }


@router.post("/findings/{id}/approve")
def approve_doctor_finding(id: int, db: Session = Depends(get_db)):
    """Transition finding status to 'approved'."""
    finding = approve_finding(db, id)
    return _finding_dict(finding)


@router.post("/findings/{id}/reject")
def reject_doctor_finding(id: int, db: Session = Depends(get_db)):
    """Transition finding status to 'rejected'."""
    finding = reject_finding(db, id)
    return _finding_dict(finding)


@router.post("/findings/{id}/apply")
def apply_doctor_finding(id: int, db: Session = Depends(get_db)):
    """Apply approved finding: creates a new PipelineConfig (kind='doctor') and marks finding 'applied'."""
    finding, config = apply_finding(db, id)
    return {
        "finding": _finding_dict(finding),
        "pipeline_config": {
            "id": config.id,
            "name": config.name,
            "kind": config.kind,
            "source_ids": config.source_ids,
            "spec": config.spec,
            "spec_hash": config.spec_hash,
            "index_runs": config.index_runs,
        },
    }


@router.post("/findings/{id}/verify")
def verify_doctor_finding(id: int, db: Session = Depends(get_db)):
    """Execute evaluation on patched config, paired comparison against baseline, and update finding status."""
    finding, ver_run = verify_finding(db, id)
    return {
        "finding": _finding_dict(finding),
        "verification_run": {
            "id": ver_run.id,
            "name": ver_run.name,
            "status": ver_run.status,
            "variant": ver_run.variant,
        },
    }

