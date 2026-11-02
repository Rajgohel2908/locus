"""
retrieval/filters.py — Whitelisted metadata filtering and allowed chunk ID resolution.

Enforces:
- Strict Pydantic model with whitelisted fields only (extra="forbid", rejecting unknown keys with 422).
- Single parameterized SQL query builder over chunks.metadata (JSONB).
- Whitelisted SQL fragments and bound parameters only — zero string interpolation.
- Fallback for SQLite in test environments.
- Returns allowed chunk IDs (or None if no filters active).
"""

from typing import Optional, List, Set, Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from db import Chunk

logger = logging.getLogger(__name__)


class RetrievalFilters(BaseModel):
    """
    Whitelisted metadata filters for chunk retrieval.
    Any unknown keys are rejected with validation error (HTTP 422).
    """
    model_config = ConfigDict(extra="forbid")

    modality: Optional[List[str]] = Field(
        default=None,
        description="Filter by document modality: 'text', 'ocr', 'web', 'structured', etc.",
    )
    source_type: Optional[List[str]] = Field(
        default=None,
        description="Filter by source type: 'file', 'web', etc.",
    )
    freshness: Optional[List[str]] = Field(
        default=None,
        description="Filter by freshness level: 'fresh', 'aging', 'stale', 'unknown'.",
    )
    published_after: Optional[datetime] = Field(
        default=None,
        description="Only chunks published on or after this timestamp.",
    )
    published_before: Optional[datetime] = Field(
        default=None,
        description="Only chunks published on or before this timestamp.",
    )
    min_extraction_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Minimum extraction/OCR confidence score (0-100).",
    )
    title_contains: Optional[str] = Field(
        default=None,
        description="Case-insensitive substring search in document title.",
    )

    def is_empty(self) -> bool:
        """Returns True if all filter fields are None."""
        return all(
            getattr(self, f) is None
            for f in self.__dict__.keys()
        )


def build_filter_sql(run_ids: List[int], filters: RetrievalFilters) -> Tuple[str, Dict[str, Any]]:
    """
    Pure SQL builder that generates parameterized PostgreSQL query with bound parameters only.
    Guaranteed zero string interpolation of user values.
    """
    clauses = ["index_run_id = ANY(:run_ids)"]
    params: Dict[str, Any] = {"run_ids": run_ids}

    if filters.modality is not None:
        clauses.append("metadata->>'modality' = ANY(:modalities)")
        params["modalities"] = list(filters.modality)

    if filters.source_type is not None:
        clauses.append("metadata->>'source_type' = ANY(:source_types)")
        params["source_types"] = list(filters.source_type)

    if filters.freshness is not None:
        clauses.append("metadata->>'freshness' = ANY(:freshness_list)")
        params["freshness_list"] = list(filters.freshness)

    if filters.published_after is not None:
        clauses.append(
            "(CASE WHEN metadata->>'published_at' IS NOT NULL "
            "THEN (metadata->>'published_at')::timestamp >= :published_after "
            "ELSE FALSE END)"
        )
        dt = filters.published_after
        params["published_after"] = dt.replace(tzinfo=None) if dt.tzinfo else dt

    if filters.published_before is not None:
        clauses.append(
            "(CASE WHEN metadata->>'published_at' IS NOT NULL "
            "THEN (metadata->>'published_at')::timestamp <= :published_before "
            "ELSE FALSE END)"
        )
        dt = filters.published_before
        params["published_before"] = dt.replace(tzinfo=None) if dt.tzinfo else dt

    if filters.min_extraction_confidence is not None:
        clauses.append(
            "(CASE WHEN metadata->>'extraction_confidence' IS NOT NULL "
            "THEN (metadata->>'extraction_confidence')::float >= :min_extraction_confidence "
            "ELSE FALSE END)"
        )
        params["min_extraction_confidence"] = float(filters.min_extraction_confidence)

    if filters.title_contains is not None:
        clauses.append("metadata->>'title' ILIKE :title_contains")
        params["title_contains"] = f"%{filters.title_contains}%"

    query_str = "SELECT id FROM chunks WHERE " + " AND ".join(clauses)
    return query_str, params


def resolve_allowed_chunk_ids(
    db: Session,
    run_ids: List[int],
    filters: Optional[RetrievalFilters],
) -> Optional[Set[int]]:
    """
    Resolve allowed chunk IDs across given index runs based on metadata filters.

    Returns:
        - None if filters is None or empty (indicating all chunks are allowed).
        - A set of chunk IDs (may be empty if no chunk matches).
    """
    if filters is None or filters.is_empty():
        return None

    if not run_ids:
        return set()

    bind_engine = db.get_bind()
    is_postgres = (bind_engine.dialect.name == "postgresql")

    if is_postgres:
        sql_query, params = build_filter_sql(run_ids, filters)
        rows = db.execute(text(sql_query), params).fetchall()
        return {r[0] for r in rows}
    else:
        # SQLite / in-memory testing fallback: evaluate criteria in Python
        chunks = db.query(Chunk).filter(Chunk.index_run_id.in_(run_ids)).all()
        allowed = set()
        for ch in chunks:
            meta = ch.metadata_ if isinstance(ch.metadata_, dict) else {}

            if filters.modality is not None:
                if meta.get("modality") not in filters.modality:
                    continue

            if filters.source_type is not None:
                if meta.get("source_type") not in filters.source_type:
                    continue

            if filters.freshness is not None:
                if meta.get("freshness") not in filters.freshness:
                    continue

            if filters.published_after is not None:
                pub_str = meta.get("published_at")
                if not pub_str:
                    continue
                try:
                    dt = datetime.fromisoformat(str(pub_str).replace("Z", "+00:00"))
                    dt = dt.replace(tzinfo=None) if dt.tzinfo else dt
                    after_dt = filters.published_after.replace(tzinfo=None) if filters.published_after.tzinfo else filters.published_after
                    if dt < after_dt:
                        continue
                except Exception:
                    continue

            if filters.published_before is not None:
                pub_str = meta.get("published_at")
                if not pub_str:
                    continue
                try:
                    dt = datetime.fromisoformat(str(pub_str).replace("Z", "+00:00"))
                    dt = dt.replace(tzinfo=None) if dt.tzinfo else dt
                    before_dt = filters.published_before.replace(tzinfo=None) if filters.published_before.tzinfo else filters.published_before
                    if dt > before_dt:
                        continue
                except Exception:
                    continue

            if filters.min_extraction_confidence is not None:
                conf = meta.get("extraction_confidence")
                if conf is None or float(conf) < filters.min_extraction_confidence:
                    continue

            if filters.title_contains is not None:
                title = meta.get("title") or ""
                if filters.title_contains.lower() not in title.lower():
                    continue

            allowed.add(ch.id)

        return allowed
