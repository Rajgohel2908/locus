"""
backend/evaluation/doctor — RAG Doctor v1 package.
"""

from evaluation.doctor.config import DoctorConfig
from evaluation.doctor.rules import evaluate_rules
from evaluation.doctor.engine import (
    run_doctor_analysis,
    approve_finding,
    reject_finding,
    apply_finding,
    verify_finding,
)

__all__ = [
    "DoctorConfig",
    "evaluate_rules",
    "run_doctor_analysis",
    "approve_finding",
    "reject_finding",
    "apply_finding",
    "verify_finding",
]

