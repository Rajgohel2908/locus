"""
routers/documents.py — Document endpoints and Phase 5 document metadata overrides.

GET    /documents/{doc_id}          — Full document including content
PUT    /documents/{doc_id}/override — Set or update document metadata overrides (published_at, title)
GET    /documents/{doc_id}/override — Retrieve active override for a document
DELETE /documents/{doc_id}/override — Remove active override for a document
"""

from typing import Optional, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db, Document, DocumentOverride

router = APIRouter()


class DocumentOverrideRequest(BaseModel):
    published_at: Optional[Any] = None
    title: Optional[str] = None


@router.get("/documents/{doc_id}", summary="Get a full document including content")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    """
    Return a single document by ID, including its full text content.
    For a list without content, use GET /sources/{source_id}/documents.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    return {
        "id":                    doc.id,
        "source_id":             doc.source_id,
        "modality":              doc.modality,
        "title":                 doc.title,
        "url":                   doc.url,
        "page_number":           doc.page_number,
        "word_count":            doc.word_count,
        "content_hash":          doc.content_hash,
        "extraction_confidence": doc.extraction_confidence,
        "published_at":          str(doc.published_at) if doc.published_at else None,
        "fetched_at":            str(doc.fetched_at),
        "metadata":              doc.metadata_,
        "quality":               doc.quality,
        "content":               doc.content,
    }


@router.put("/documents/{doc_id}/override", summary="Set or update metadata overrides for a document")
def set_document_override(
    doc_id: int,
    req: DocumentOverrideRequest,
    db: Session = Depends(get_db),
):
    """
    Set user metadata overrides (published_at, title) for a document.
    - Original document row remains strictly untouched (immutability preserved).
    - Rejects unparsable dates and dates more than 1 day in the future.
    - Overrides take effect only for a NEW index run.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    parsed_date = None
    if req.published_at is not None:
        if isinstance(req.published_at, str):
            clean_str = req.published_at.strip()
            if clean_str.lower() in ("null", "none", ""):
                parsed_date = None
            else:
                try:
                    clean_str = clean_str.replace("Z", "+00:00")
                    parsed_date = datetime.fromisoformat(clean_str)
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail="Unparsable date format for published_at. Expected ISO 8601 string.",
                    )
        elif isinstance(req.published_at, datetime):
            parsed_date = req.published_at
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid data type for published_at. Expected ISO 8601 string or null.",
            )

        if parsed_date is not None:
            now_utc = datetime.now(timezone.utc)
            check_dt = parsed_date if parsed_date.tzinfo else parsed_date.replace(tzinfo=timezone.utc)
            if check_dt > now_utc + timedelta(days=1):
                raise HTTPException(
                    status_code=400,
                    detail="published_at date cannot be more than 1 day in the future.",
                )
            if parsed_date.tzinfo is not None:
                parsed_date = parsed_date.astimezone(timezone.utc).replace(tzinfo=None)

    override = db.query(DocumentOverride).filter(DocumentOverride.document_id == doc_id).first()
    if not override:
        override = DocumentOverride(
            document_id=doc_id,
            published_at=parsed_date,
            title=req.title,
            set_at=datetime.utcnow(),
        )
        db.add(override)
    else:
        override.published_at = parsed_date
        override.title = req.title
        override.set_at = datetime.utcnow()

    db.commit()
    db.refresh(override)

    return {
        "id": override.id,
        "document_id": override.document_id,
        "published_at": override.published_at.isoformat() if override.published_at else None,
        "title": override.title,
        "set_at": override.set_at.isoformat() if override.set_at else None,
        "note": "Overrides take effect only for a NEW index run.",
    }


@router.get("/documents/{doc_id}/override", summary="Get metadata overrides for a document")
def get_document_override(doc_id: int, db: Session = Depends(get_db)):
    """Retrieve the current metadata overrides for a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    override = db.query(DocumentOverride).filter(DocumentOverride.document_id == doc_id).first()
    if not override:
        raise HTTPException(status_code=404, detail=f"No override found for document {doc_id}.")

    return {
        "id": override.id,
        "document_id": override.document_id,
        "published_at": override.published_at.isoformat() if override.published_at else None,
        "title": override.title,
        "set_at": override.set_at.isoformat() if override.set_at else None,
        "note": "Overrides take effect only for a NEW index run.",
    }


@router.delete("/documents/{doc_id}/override", summary="Delete metadata overrides for a document")
def delete_document_override(doc_id: int, db: Session = Depends(get_db)):
    """Delete metadata overrides for a document. Original document remains unchanged."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    override = db.query(DocumentOverride).filter(DocumentOverride.document_id == doc_id).first()
    if not override:
        raise HTTPException(status_code=404, detail=f"No override found for document {doc_id}.")

    db.delete(override)
    db.commit()

    return {
        "detail": f"Override for document {doc_id} deleted successfully.",
        "document_id": doc_id,
        "note": "Overrides take effect only for a NEW index run.",
    }
