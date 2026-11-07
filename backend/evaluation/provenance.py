"""
backend/evaluation/provenance.py — Provenance capture for evaluation runs.

Tracks git commit, dirty working tree status, git diff SHA-256 with untracked files,
model usage flags (embedder/reranker used), versions of numpy, torch, sentence-transformers,
freshness reference date, and suite hash.
"""

import os
import sys
import hashlib
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import config


def get_git_provenance() -> Tuple[Optional[str], bool, str]:
    """
    Retrieve git commit hash, dirty flag, and SHA-256 of (git diff HEAD + untracked files).
    """
    commit = None
    dirty = False
    diff_sha256 = "n/a"

    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            commit = res.stdout.strip()
    except Exception:
        commit = None

    try:
        # Check dirty status (staged, unstaged, or untracked changes)
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if status_res.returncode == 0 and status_res.stdout.strip():
            dirty = True

        diff_res = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        untracked_res = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        combined = (diff_res.stdout or "") + "\n--- UNTRACKED ---\n" + (untracked_res.stdout or "")
        diff_sha256 = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    except Exception:
        diff_sha256 = "n/a"

    return commit, dirty, diff_sha256


def get_library_versions() -> Dict[str, str]:
    """Retrieve runtime versions of key scientific and ML libraries."""
    versions = {}
    try:
        import numpy as np
        versions["numpy"] = np.__version__
    except Exception:
        versions["numpy"] = "n/a"

    try:
        import torch
        versions["torch"] = torch.__version__
    except Exception:
        versions["torch"] = "n/a"

    try:
        import sentence_transformers
        versions["sentence_transformers"] = sentence_transformers.__version__
    except Exception:
        versions["sentence_transformers"] = "n/a"

    return versions


def capture_provenance(
    suite_hash: str,
    variant: Optional[Dict[str, Any]] = None,
    index_run_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Capture full provenance metadata for an evaluation run."""
    commit, dirty, diff_sha256 = get_git_provenance()
    versions = get_library_versions()

    var = variant or {}
    strategy = var.get("strategy", "dense")
    use_rerank = bool(var.get("use_rerank", False) or strategy == "hybrid_rerank")

    return {
        "git_commit": commit,
        "dirty": dirty,
        "diff_sha256": diff_sha256,
        "embedder": getattr(config, "EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        "embedder_used": True,
        "reranker": getattr(config, "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        "reranker_used": use_rerank,
        "python_version": sys.version.split()[0],
        "freshness_reference_date": os.getenv("FRESHNESS_REFERENCE_DATE", "none"),
        "index_run_ids": index_run_ids or [],
        "suite_hash": suite_hash,
        "numpy_version": versions.get("numpy", "n/a"),
        "torch_version": versions.get("torch", "n/a"),
        "sentence_transformers_version": versions.get("sentence_transformers", "n/a"),
    }
