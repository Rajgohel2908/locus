"""
backend/recommender/profile.py — KB profile builder from existing DB data.

Extracts:
- Source counts by type (file, web, structured), documents, records, chunks, avg words per doc/page.
- Structured: columns with roles, numeric column count, identifier columns, active row count.
- Text: freshness distribution (computed ONLY through existing check_freshness, honoring
  FRESHNESS_REFERENCE_DATE; uses document overrides), share of undated documents,
  near-duplicate pairs, injection suspects, short documents, OCR share and mean extraction confidence.
- Script share by Unicode ranges:
  - Latin (0000-024F)
  - Devanagari (0900-097F)
  - Gujarati (0A80-0AFF)
  - Other
- Quality state: latest version number, duplicate rows, pending critical cleaning proposals.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import (
    SessionLocal,
    Source,
    Document,
    Record,
    Chunk,
    IndexRun,
    ColumnRole,
    CleaningProposal,
    SourceVersion,
    DocumentOverride,
)
from profiler.text_quality import (
    check_freshness,
    check_near_duplicate,
    check_short_content,
    check_injection_suspect,
)


def compute_script_shares(texts: List[str]) -> Dict[str, Any]:
    """
    Compute share of characters across Unicode ranges:
    - Latin: 0x0000 - 0x024F
    - Devanagari: 0x0900 - 0x097F
    - Gujarati: 0x0A80 - 0x0AFF
    - Other: any remaining non-whitespace characters
    """
    latin_count = 0
    devanagari_count = 0
    gujarati_count = 0
    other_count = 0

    for text in texts:
        if not text:
            continue
        for char in text:
            if char.isspace():
                continue
            code = ord(char)
            if 0x0000 <= code <= 0x024F:
                latin_count += 1
            elif 0x0900 <= code <= 0x097F:
                devanagari_count += 1
            elif 0x0A80 <= code <= 0x0AFF:
                gujarati_count += 1
            else:
                other_count += 1

    total_chars = latin_count + devanagari_count + gujarati_count + other_count
    if total_chars == 0:
        return {
            "total_chars": 0,
            "latin_share": 1.0,
            "devanagari_share": 0.0,
            "gujarati_share": 0.0,
            "other_share": 0.0,
            "non_latin_share": 0.0,
            "char_counts": {
                "latin": 0,
                "devanagari": 0,
                "gujarati": 0,
                "other": 0,
            },
        }

    latin_share = round(latin_count / total_chars, 4)
    devanagari_share = round(devanagari_count / total_chars, 4)
    gujarati_share = round(gujarati_count / total_chars, 4)
    other_share = round(other_count / total_chars, 4)
    non_latin_share = round((devanagari_count + gujarati_count + other_count) / total_chars, 4)

    return {
        "total_chars": total_chars,
        "latin_share": latin_share,
        "devanagari_share": devanagari_share,
        "gujarati_share": gujarati_share,
        "other_share": other_share,
        "non_latin_share": non_latin_share,
        "char_counts": {
            "latin": latin_count,
            "devanagari": devanagari_count,
            "gujarati": gujarati_count,
            "other": other_count,
        },
    }


def build_kb_profile(*args, **kwargs) -> Dict[str, Any]:
    """
    Build KB profile from existing DB data only.
    Supports all calling conventions:
      - build_kb_profile(source_ids, version=None, db=None)
      - build_kb_profile(db, source_ids, version=None)
      - build_kb_profile(source_ids=..., version=..., db=...)
      - build_kb_profile(db=..., source_ids=..., version=...)
    """
    db_session = kwargs.get("db")
    s_ids = kwargs.get("source_ids")
    ver = kwargs.get("version")

    # Positional args resolution
    if len(args) == 1:
        if hasattr(args[0], "query"):
            db_session = args[0]
        else:
            s_ids = args[0]
    elif len(args) == 2:
        if hasattr(args[0], "query"):
            db_session = args[0]
            s_ids = args[1]
        else:
            s_ids = args[0]
            ver = args[1]
    elif len(args) >= 3:
        if hasattr(args[0], "query"):
            db_session = args[0]
            s_ids = args[1]
            ver = args[2]
        else:
            s_ids = args[0]
            ver = args[1]
            db_session = args[2]

    if db_session is not None:
        return _build_kb_profile_impl(db_session, s_ids or [], ver)
    with SessionLocal() as session:
        return _build_kb_profile_impl(session, s_ids or [], ver)


def _build_kb_profile_impl(
    db: Session,
    source_ids: List[int],
    target_version: Optional[int] = None,
) -> Dict[str, Any]:
    if not source_ids:
        return {
            "source_ids": [],
            "sources": {"total": 0, "by_type": {"file": 0, "web": 0, "structured": 0}},
            "documents": {"total": 0, "total_records": 0, "total_chunks": 0, "avg_words_per_doc": 0.0},
            "structured": {
                "columns": {},
                "numeric_columns": [],
                "numeric_columns_count": 0,
                "identifier_columns": [],
                "identifier_columns_count": 0,
                "active_row_count": 0,
            },
            "text": {
                "freshness_distribution": {"fresh": 0, "aging": 0, "stale": 0, "unknown": 0},
                "dated_count": 0,
                "stale_share": 0.0,
                "undated_share": 0.0,
                "near_duplicate_pairs": [],
                "near_duplicate_count": 0,
                "injection_suspects_count": 0,
                "short_documents_count": 0,
                "ocr_share": 0.0,
                "mean_extraction_confidence": 100.0,
            },
            "scripts": compute_script_shares([]),
            "quality_state": {
                "latest_version_no": 1,
                "duplicate_rows": 0,
                "pending_critical_proposals": 0,
            },
        }

    sources = db.query(Source).filter(Source.id.in_(source_ids)).all()
    sources_by_type = {"file": 0, "web": 0, "structured": 0}
    for s in sources:
        # Check if source is structured (contains records)
        rec_exists = db.query(Record.id).filter(Record.source_id == s.id).first() is not None
        if rec_exists:
            sources_by_type["structured"] = sources_by_type.get("structured", 0) + 1
        else:
            stype = s.source_type or "file"
            sources_by_type[stype] = sources_by_type.get(stype, 0) + 1

    # Resolve target version for each source
    source_versions_map = {}
    for s in sources:
        if target_version is not None:
            source_versions_map[s.id] = target_version
        else:
            latest_v = (
                db.query(func.max(SourceVersion.version_no))
                .filter(SourceVersion.source_id == s.id)
                .scalar()
            )
            source_versions_map[s.id] = latest_v if latest_v is not None else 1

    # Fetch active documents
    all_active_docs = []
    for s in sources:
        s_ver = source_versions_map[s.id]
        docs = (
            db.query(Document)
            .filter(
                Document.source_id == s.id,
                Document.version_no == s_ver,
                Document.status == "active",
            )
            .all()
        )
        all_active_docs.extend(docs)

    # Fetch active records
    all_active_records = []
    for s in sources:
        s_ver = source_versions_map[s.id]
        recs = (
            db.query(Record)
            .filter(
                Record.source_id == s.id,
                Record.version_no == s_ver,
                Record.status == "active",
            )
            .all()
        )
        all_active_records.extend(recs)

    total_docs = len(all_active_docs)
    total_records = len(all_active_records)

    # Total chunks from latest completed index run for each requested source
    total_chunks = 0
    for s in sources:
        latest_run = (
            db.query(IndexRun)
            .filter(IndexRun.source_id == s.id, IndexRun.status == "completed")
            .order_by(IndexRun.id.desc())
            .first()
        )
        if latest_run:
            total_chunks += latest_run.chunk_count

    # Average words per document/page
    total_words = 0
    for d in all_active_docs:
        w_cnt = d.word_count
        if w_cnt is None:
            w_cnt = len((d.content or "").split())
        total_words += w_cnt

    avg_words_per_doc = round(total_words / max(total_docs, 1), 2) if total_docs > 0 else 0.0

    # Structured details
    roles = db.query(ColumnRole).filter(ColumnRole.source_id.in_(source_ids)).all()
    columns_map = {r.column_name: r.role for r in roles}
    numeric_cols = [r.column_name for r in roles if r.role == "numeric"]
    identifier_cols = [r.column_name for r in roles if r.role == "identifier"]

    # Text details: Document Overrides & Freshness
    doc_ids = [d.id for d in all_active_docs]
    overrides = (
        db.query(DocumentOverride)
        .filter(DocumentOverride.document_id.in_(doc_ids))
        .all()
        if doc_ids else []
    )
    overrides_map = {o.document_id: o.published_at for o in overrides if o.published_at is not None}

    freshness_dist = {"fresh": 0, "aging": 0, "stale": 0, "unknown": 0}
    ocr_count = 0
    conf_scores = []
    short_docs_count = 0
    injection_suspects_count = 0
    doc_text_list = []

    for d in all_active_docs:
        content = d.content or ""
        doc_text_list.append(content)

        # Freshness via check_freshness (which honors FRESHNESS_REFERENCE_DATE)
        pub_dt = overrides_map.get(d.id, d.published_at)
        f_res = check_freshness(pub_dt)
        flag = f_res.get("flag", "unknown")
        freshness_dist[flag] = freshness_dist.get(flag, 0) + 1

        # OCR & extraction confidence
        meta = getattr(d, "metadata_", {}) or {}
        is_ocr = (d.modality == "image") or (isinstance(meta, dict) and meta.get("ocr") is True)
        if is_ocr:
            ocr_count += 1
        if d.extraction_confidence is not None:
            conf_scores.append(d.extraction_confidence)

        # Short documents
        if check_short_content(content)["flag"]:
            short_docs_count += 1

        # Injection suspects
        if check_injection_suspect(content)["flag"]:
            injection_suspects_count += 1

    dated_count = freshness_dist["fresh"] + freshness_dist["aging"] + freshness_dist["stale"]
    stale_share = round(freshness_dist["stale"] / max(dated_count, 1), 4) if dated_count > 0 else 0.0
    undated_share = round(freshness_dist["unknown"] / max(total_docs, 1), 4) if total_docs > 0 else 0.0
    ocr_share = round(ocr_count / max(total_docs, 1), 4) if total_docs > 0 else 0.0
    mean_confidence = round(sum(conf_scores) / len(conf_scores), 2) if conf_scores else 100.0

    # Near-duplicates via check_near_duplicate
    near_dup_input = [{"id": d.id, "content": d.content or ""} for d in all_active_docs]
    near_dup_res = check_near_duplicate(near_dup_input) if total_docs <= 50 else {"detail": {"near_duplicate_pairs": []}}
    near_dup_pairs = near_dup_res.get("detail", {}).get("near_duplicate_pairs", [])

    # Collect texts for script analysis (docs + record data strings)
    all_texts_for_script = list(doc_text_list)
    for rec in all_active_records:
        if isinstance(rec.data, dict):
            all_texts_for_script.append(" ".join(str(v) for v in rec.data.values() if v is not None))
    script_shares = compute_script_shares(all_texts_for_script)

    # Quality state
    all_vers = (
        db.query(SourceVersion.version_no)
        .filter(SourceVersion.source_id.in_(source_ids))
        .all()
    )
    latest_ver_no = max([v[0] for v in all_vers], default=1)

    # Duplicate rows count from cleaning proposals or quality reports
    dup_props = (
        db.query(CleaningProposal)
        .filter(
            CleaningProposal.source_id.in_(source_ids),
            CleaningProposal.kind == "drop_exact_duplicates",
        )
        .all()
    )
    duplicate_rows = 0
    for dp in dup_props:
        impact = dp.impact or {}
        duplicate_rows += impact.get("rows_affected", 0)

    # Pending critical cleaning proposals
    pending_critical = (
        db.query(CleaningProposal)
        .filter(
            CleaningProposal.source_id.in_(source_ids),
            CleaningProposal.status == "proposed",
            CleaningProposal.severity == "critical",
        )
        .count()
    )

    return {
        "source_ids": source_ids,
        "sources": {
            "total": len(sources),
            "by_type": sources_by_type,
        },
        "documents": {
            "total": total_docs,
            "total_records": total_records,
            "total_chunks": total_chunks,
            "avg_words_per_doc": avg_words_per_doc,
        },
        "structured": {
            "columns": columns_map,
            "numeric_columns": numeric_cols,
            "numeric_columns_count": len(numeric_cols),
            "identifier_columns": identifier_cols,
            "identifier_columns_count": len(identifier_cols),
            "active_row_count": total_records,
        },
        "text": {
            "freshness_distribution": freshness_dist,
            "dated_count": dated_count,
            "stale_share": stale_share,
            "undated_share": undated_share,
            "near_duplicate_pairs": near_dup_pairs,
            "near_duplicate_count": len(near_dup_pairs),
            "injection_suspects_count": injection_suspects_count,
            "short_documents_count": short_docs_count,
            "ocr_share": ocr_share,
            "mean_extraction_confidence": mean_confidence,
        },
        "scripts": script_shares,
        "quality_state": {
            "latest_version_no": latest_ver_no,
            "duplicate_rows": duplicate_rows,
            "pending_critical_proposals": pending_critical,
        },
    }
