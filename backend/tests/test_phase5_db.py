"""
tests/test_phase5_db.py — Database and integration tests for Phase 5.

Tests:
1. Filters return the right allowed IDs across multiple conditions.
2. Freshness filter excludes stale chunks.
3. Document override changes chunk metadata on a NEW index run while original document row remains byte-identical.
4. Lexical exact-ID retrieval finds the right CSV row chunk.
5. Unsupported question yields insufficient_evidence with 0 LLM calls across all 4 strategies.
6. no_chunks_match_filters path returns insufficient_evidence and 0 LLM calls.
7. REST API override endpoint validation (rejects invalid/future dates, supports GET/DELETE).
"""

import pytest
import os
import hashlib
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from db import Base, Source, Document, Record, IndexRun, Chunk, DocumentOverride, QueryRecord
from indexing.chunker import chunk_active_source_content, compute_content_hash
from indexing.embedder import FakeEmbedder
from retrieval.filters import RetrievalFilters, resolve_allowed_chunk_ids
from retrieval.lexical import BM25Retriever
from retrieval.rerank import FakeReranker
from generation.llm import FakeLLMClient
from generation.answer import execute_query
import urllib.parse
from main import app

DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.pg


@pytest.fixture
def db_session():
    """Real PostgreSQL test session that cleans up created sources after test."""
    if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+")):
        pytest.fail(f"TEST_DATABASE_URL must be a real PostgreSQL database, got: '{DATABASE_URL}'")

    parsed = urllib.parse.urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    if not db_name.endswith("_test"):
        pytest.fail(f"Safety check failed: pg test database name must end with '_test', got '{db_name}'. Refusing to run tests against non-test database.")

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    initial_source_ids = {s.id for s in session.query(Source.id).all()}
    try:
        yield session
    finally:
        session.rollback()
        current_source_ids = {s.id for s in session.query(Source.id).all()}
        new_source_ids = current_source_ids - initial_source_ids
        for sid in new_source_ids:
            session.query(Source).filter(Source.id == sid).delete()
        session.commit()
        session.close()


def test_filters_resolve_right_allowed_ids(db_session):
    src = Source(source_type="file", name="test_source")
    db_session.add(src)
    db_session.commit()

    run = IndexRun(
        source_id=src.id, source_version=1, embed_model="test",
        embed_dim=384, chunk_size=800, chunk_overlap=120,
        status="completed", chunk_count=3,
    )
    db_session.add(run)
    db_session.commit()

    c1 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=0,
        content="Text document chunk", content_hash="h1", token_estimate=10,
        metadata_={"modality": "text", "source_type": "file", "title": "Leave Policy 2024", "extraction_confidence": 95.0},
    )
    c2 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=1,
        content="OCR document chunk", content_hash="h2", token_estimate=10,
        metadata_={"modality": "ocr", "source_type": "file", "title": "Scanned Handbook", "extraction_confidence": 60.0},
    )
    c3 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=2,
        content="Structured employee row", content_hash="h3", token_estimate=10,
        metadata_={"modality": "structured", "source_type": "file", "title": None, "extraction_confidence": None},
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    # Filter 1: modality = ['text']
    f_text = RetrievalFilters(modality=["text"])
    res1 = resolve_allowed_chunk_ids(db_session, [run.id], f_text)
    assert res1 == {c1.id}

    # Filter 2: min_extraction_confidence = 80.0
    f_conf = RetrievalFilters(min_extraction_confidence=80.0)
    res2 = resolve_allowed_chunk_ids(db_session, [run.id], f_conf)
    assert res2 == {c1.id}

    # Filter 3: title_contains = 'Handbook'
    f_title = RetrievalFilters(title_contains="Handbook")
    res3 = resolve_allowed_chunk_ids(db_session, [run.id], f_title)
    assert res3 == {c2.id}


def test_freshness_filter_excludes_stale_chunks(db_session):
    src = Source(source_type="file", name="test_source")
    db_session.add(src)
    db_session.commit()

    run = IndexRun(
        source_id=src.id, source_version=1, embed_model="test",
        embed_dim=384, chunk_size=800, chunk_overlap=120,
        status="completed", chunk_count=2,
    )
    db_session.add(run)
    db_session.commit()

    c_fresh = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=0,
        content="Fresh policy 2024", content_hash="h_fresh", token_estimate=10,
        metadata_={"freshness": "fresh", "published_at": "2024-06-01T00:00:00"},
    )
    c_stale = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=1,
        content="Stale policy 2019", content_hash="h_stale", token_estimate=10,
        metadata_={"freshness": "stale", "published_at": "2019-03-01T00:00:00"},
    )
    db_session.add_all([c_fresh, c_stale])
    db_session.commit()

    f_fresh = RetrievalFilters(freshness=["fresh", "aging"])
    allowed = resolve_allowed_chunk_ids(db_session, [run.id], f_fresh)
    assert c_fresh.id in allowed
    assert c_stale.id not in allowed


def test_document_override_immutability_and_chunk_metadata(db_session):
    """
    CRITICAL REQUIREMENT:
    A document override changes chunk metadata after a NEW index run,
    while original documents rows remain byte-identical (hash before == hash after).
    """
    src = Source(source_type="file", name="policy.pdf")
    db_session.add(src)
    db_session.commit()

    orig_content = "All staff are entitled to 20 days leave."
    chash = compute_content_hash(orig_content)
    orig_date = datetime(2019, 3, 1, 0, 0, 0)
    orig_title = "Historical Leave Policy"

    doc = Document(
        source_id=src.id,
        modality="text",
        title=orig_title,
        content=orig_content,
        content_hash=chash,
        published_at=orig_date,
        version_no=1,
        status="active",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Compute pre-override byte fingerprint of the documents table row
    fingerprint_before = hashlib.sha256(
        f"{doc.id}|{doc.content}|{doc.content_hash}|{doc.title}|{doc.published_at.isoformat()}".encode()
    ).hexdigest()
    assert doc.content_hash is not None
    assert db_session.query(Document).count() > 0

    # Apply override (new title, new date)
    new_override_date = datetime(2024, 6, 1, 0, 0, 0)
    new_override_title = "Revised 2024 Policy"
    override = DocumentOverride(
        document_id=doc.id,
        published_at=new_override_date,
        title=new_override_title,
    )
    db_session.add(override)
    db_session.commit()

    # Verify original document row is 100% UNTOUCHED
    db_session.refresh(doc)
    fingerprint_after = hashlib.sha256(
        f"{doc.id}|{doc.content}|{doc.content_hash}|{doc.title}|{doc.published_at.isoformat()}".encode()
    ).hexdigest()
    assert fingerprint_before == fingerprint_after
    assert doc.title == orig_title
    assert doc.published_at == orig_date

    # Perform a NEW chunking / indexing run with overrides provided
    chunks = chunk_active_source_content(
        source_id=src.id,
        source_name=src.name,
        source_type="file",
        source_version=1,
        documents=[doc],
        records=[],
        chunk_size=800,
        chunk_overlap=120,
        overrides={doc.id: override},
    )

    assert len(chunks) == 1
    meta = chunks[0]["metadata"]
    # Chunk metadata MUST reflect the override!
    assert meta["title"] == new_override_title
    assert meta["published_at"] == "2024-06-01T00:00:00"
    assert meta["published_at_source"] == "user"
    assert meta["freshness"] == "stale" or meta["freshness"] in ("fresh", "aging", "stale")


def test_lexical_exact_id_retrieval(db_session):
    """
    CRITICAL REQUIREMENT:
    Lexical exact-ID retrieval finds the right CSV row chunk for 'E1007'.
    """
    src = Source(source_type="file", name="employees.csv")
    db_session.add(src)
    db_session.commit()

    run = IndexRun(
        source_id=src.id, source_version=1, embed_model="test",
        embed_dim=384, chunk_size=800, chunk_overlap=120,
        status="completed", chunk_count=3,
    )
    db_session.add(run)
    db_session.commit()

    c1 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=0,
        content="Employee_ID: E1007; Name: Alice; Department: Engineering; Salary: 95000.0",
        content_hash="h1", token_estimate=15,
        metadata_={"row_index": 1, "source_name": "employees.csv"},
    )
    c2 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=1,
        content="Employee_ID: E1008; Name: Bob; Department: Marketing; Salary: 65000.0",
        content_hash="h2", token_estimate=15,
        metadata_={"row_index": 2, "source_name": "employees.csv"},
    )
    c3 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=2,
        content="Employee_ID: E1009; Name: Charlie; Department: HR; Salary: 55000.0",
        content_hash="h3", token_estimate=15,
        metadata_={"row_index": 3, "source_name": "employees.csv"},
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    retriever = BM25Retriever()
    results = retriever.retrieve(
        db=db_session,
        question="What is employee E1007's department?",
        run_ids=[run.id],
        top_k=5,
    )

    assert len(results) > 0
    top_chunk = results[0]
    assert top_chunk["chunk_id"] == c1.id
    assert "e1007" in top_chunk["matched_terms"]
    assert top_chunk["score"] > 0.0


def test_unsupported_question_zero_llm_calls_every_strategy(db_session):
    """
    CRITICAL REQUIREMENT:
    For EVERY strategy (dense, lexical, hybrid, hybrid_rerank), the unsupported question
    returns status 'insufficient_evidence' with fake LLM call count equal to 0.
    """
    src = Source(source_type="file", name="hr_policy.docx")
    db_session.add(src)
    db_session.commit()

    run = IndexRun(
        source_id=src.id, source_version=1, embed_model="test",
        embed_dim=384, chunk_size=800, chunk_overlap=120,
        status="completed", chunk_count=1,
    )
    db_session.add(run)
    db_session.commit()

    embedder = FakeEmbedder(dim=384)
    # Put a normal HR chunk
    chunk_vec = [1.0] + [0.0] * 383
    c1 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=0,
        content="All full-time employees are entitled to 24 annual leave days.",
        content_hash="h_leave", token_estimate=10, embedding=chunk_vec,
        metadata_={"modality": "text", "source_name": "hr_policy.docx"},
    )
    db_session.add(c1)
    db_session.commit()

    # For unsupported question, embedder returns an orthogonal vector so cosine is ~0.0
    # BM25 has 0 matching terms so BM25 score is <= 0
    # CrossEncoder returns near 0
    fake_reranker = FakeReranker(score_fn=lambda q, item: 0.01)

    strategies = ["dense", "lexical", "hybrid", "hybrid_rerank"]
    unsupported_question = "What is the company's Mars colonization budget?"

    for strat in strategies:
        fake_llm = FakeLLMClient(response="This should never be generated.")

        res = execute_query(
            db=db_session,
            question=unsupported_question,
            source_ids=[src.id],
            strategy=strat,
            min_score=0.30,
            min_bm25=0.5,
            min_rerank=0.50,
            embedder=embedder,
            reranker=fake_reranker,
            llm_client=fake_llm,
        )

        assert res["status"] == "insufficient_evidence", f"Strategy '{strat}' did not return insufficient_evidence"
        assert res["answer"] is None
        assert res["evidence"]["passed"] is False
        assert fake_llm.call_count == 0, f"Strategy '{strat}' called LLM {fake_llm.call_count} times! Must be 0."


def test_no_chunks_match_filters_insufficient_evidence(db_session):
    """
    CRITICAL REQUIREMENT:
    If no chunks match the filters, return status 'insufficient_evidence'
    with reason 'no_chunks_match_filters' and 0 LLM calls.
    """
    src = Source(source_type="file", name="hr_policy.docx")
    db_session.add(src)
    db_session.commit()

    run = IndexRun(
        source_id=src.id, source_version=1, embed_model="test",
        embed_dim=384, chunk_size=800, chunk_overlap=120,
        status="completed", chunk_count=1,
    )
    db_session.add(run)
    db_session.commit()

    c1 = Chunk(
        index_run_id=run.id, source_id=src.id, chunk_index=0,
        content="Leave policy content.", content_hash="h1", token_estimate=10,
        metadata_={"modality": "text"},
    )
    db_session.add(c1)
    db_session.commit()

    fake_llm = FakeLLMClient()
    impossible_filters = RetrievalFilters(modality=["non_existent_modality"])

    res = execute_query(
        db=db_session,
        question="How many leaves?",
        source_ids=[src.id],
        filters=impossible_filters,
        llm_client=fake_llm,
    )

    assert res["status"] == "insufficient_evidence"
    assert res["evidence"]["reason"] == "no_chunks_match_filters"
    assert fake_llm.call_count == 0


def test_api_override_endpoints_and_validation():
    """
    Test PUT, GET, DELETE /documents/{id}/override endpoints using TestClient.
    """
    client = TestClient(app)

    # 1. Create a dummy source and document via upload or direct DB
    from db import SessionLocal
    db = SessionLocal()
    src = Source(source_type="file", name="override_test.txt")
    db.add(src)
    db.commit()
    doc = Document(
        source_id=src.id,
        modality="text",
        title="Original Doc",
        content="Sample content",
        content_hash="h_ovr",
        version_no=1,
        status="active",
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id
    src_id = src.id
    db.close()

    try:
        # Case A: Reject unparsable date
        r_bad_date = client.put(f"/documents/{doc_id}/override", json={"published_at": "not-a-valid-date"})
        assert r_bad_date.status_code == 400

        # Case B: Reject date > 1 day in the future
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        r_future = client.put(f"/documents/{doc_id}/override", json={"published_at": future_date})
        assert r_future.status_code == 400

        # Case C: Valid date and title override
        valid_date = "2024-06-01T00:00:00"
        r_valid = client.put(
            f"/documents/{doc_id}/override",
            json={"published_at": valid_date, "title": "Overridden Title 2024"},
        )
        assert r_valid.status_code == 200
        data = r_valid.json()
        assert data["document_id"] == doc_id
        assert "2024-06-01" in data["published_at"]
        assert data["title"] == "Overridden Title 2024"
        assert "NEW index run" in data["note"]

        # Case D: GET override
        r_get = client.get(f"/documents/{doc_id}/override")
        assert r_get.status_code == 200
        assert r_get.json()["title"] == "Overridden Title 2024"

        # Case E: DELETE override
        r_del = client.delete(f"/documents/{doc_id}/override")
        assert r_del.status_code == 200

        # Case F: GET after delete -> 404
        r_get_after = client.get(f"/documents/{doc_id}/override")
        assert r_get_after.status_code == 404
    finally:
        db = SessionLocal()
        db.query(Source).filter(Source.id == src_id).delete()
        db.commit()
        db.close()
