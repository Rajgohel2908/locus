"""
backend/evaluation/matrix.py — Automated parameter sweep matrix runner.

Rules:
- Matrix cap: maximum 24 combinations per matrix request.
- LLM budget check: refuses if estimated LLM calls exceed max_llm_calls.
- Combinations vary strategy, chunk_size, use_rerank, top_k, etc.
- Re-indexes sources with existing indexing function, reusing identical completed index runs.
"""

import itertools
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from db import EvalSuite, EvalItem, EvalRun, safe_json
from evaluation.engine import execute_eval_run


def generate_matrix_runs(
    db: Session,
    suite_id: int,
    base_variant: Dict[str, Any],
    vary: Dict[str, List[Any]],
    generate: bool = False,
    judge: bool = False,
    include_unreviewed: bool = False,
    max_llm_calls: Optional[int] = None,
    wait: bool = False,
) -> List[EvalRun]:
    """
    Generate and execute matrix combinations across variant parameters.
    """
    suite = db.query(EvalSuite).filter(EvalSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail=f"EvalSuite {suite_id} not found.")

    # Validate variation axes
    axes = list(vary.keys())
    values_list = [vary[ax] for ax in axes]

    if not axes:
        combinations = [{}]
    else:
        combinations = [
            dict(zip(axes, combo)) for combo in itertools.product(*values_list)
        ]

    if len(combinations) > 24:
        raise HTTPException(
            status_code=400,
            detail=f"Matrix parameter sweep produces {len(combinations)} combinations, exceeding the strict cap of 24.",
        )

    # Count applicable items
    items_query = db.query(EvalItem).filter(EvalItem.suite_id == suite_id)
    if not include_unreviewed:
        items_query = items_query.filter(EvalItem.reviewed.is_(True))
    item_count = items_query.count()

    # Estimate LLM calls
    calls_per_item = 0
    if generate:
        calls_per_item += 1
    if judge:
        calls_per_item += 2

    total_estimated_calls = len(combinations) * item_count * calls_per_item
    if max_llm_calls is not None and total_estimated_calls > max_llm_calls:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estimated LLM calls ({total_estimated_calls}) exceeds explicit budget cap "
                f"of {max_llm_calls} ({len(combinations)} runs x {item_count} items x {calls_per_item} calls/item)."
            ),
        )

    created_runs = []
    for combo in combinations:
        merged_variant = dict(base_variant)
        merged_variant.update(combo)

        # Build informative name
        combo_parts = [f"{k}={v}" for k, v in combo.items()]
        combo_str = ", ".join(combo_parts) if combo_parts else "base"
        run_name = f"Matrix: {combo_str}"

        config_hash = suite.suite_hash or "none"

        run = EvalRun(
            suite_id=suite_id,
            name=run_name,
            variant=safe_json(merged_variant),
            config_hash=config_hash,
            generate=generate,
            judge=judge,
            include_unreviewed=include_unreviewed,
            status="queued",
            progress={"total": item_count, "completed": 0, "status": "queued"},
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        if wait:
            # Execute synchronously
            execute_eval_run(db, run.id)
            db.refresh(run)

        created_runs.append(run)

    return created_runs

