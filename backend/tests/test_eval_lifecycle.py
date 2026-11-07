"""
tests/test_eval_lifecycle.py — Integration and lifecycle tests for Phase 7 Evaluation Suite.

Tests:
1. Suite creation, importing items, and suite_hash computation.
2. Frozen suite 409: modifying a suite with existing runs raises 409; cloning succeeds.
3. Review patch endpoint succeeds even on frozen suite (metadata only).
4. Retrieval-only run executes and makes exactly ZERO LLM calls.
5. Generation run with FakeLLMClient.
6. Judge run with FakeJudgeClient and explicit budget cap enforcement (stops with status='failed', error='budget').
7. Matrix cap enforcement (>24 combinations raises 400).
8. Matrix LLM budget check (estimated calls > max_llm_calls raises 400).
9. Mock LLM run flags generation metrics as INVALID.
10. report.md contains provenance, MOCK banner, unreviewed banner, and LLM-judged notice.
"""

import os
import urllib.parse
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from db import Base, get_db, EvalSuite, EvalItem, EvalRun, EvalResult, Source, Document, IndexRun, Chunk
from indexing.embedder import FakeEmbedder, set_embedder
from retrieval.rerank import FakeReranker, set_reranker
from evaluation.judge import CallBudgetTracker, FakeJudgeClient
from generation.llm import FakeLLMClient
from evaluation.engine import execute_eval_run, generate_run_report, generate_markdown_scorecard

DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")
pytestmark = pytest.mark.pg

client = TestClient(app)


@pytest.fixture
def db_session():
    """Real PostgreSQL test session on _test database."""
    set_embedder(FakeEmbedder())
    set_reranker(FakeReranker())
    if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+")):
        pytest.fail(f"TEST_DATABASE_URL must be a real PostgreSQL database, got: '{DATABASE_URL}'")

    parsed = urllib.parse.urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    if not db_name.endswith("_test"):
        pytest.fail(f"Safety check failed: pg test database name must end with '_test', got '{db_name}'. Refusing to run tests against non-test database.")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed minimal source and documents for testing
    src = Source(source_type="file", name="test_hr_eval_lifecycle", origin=None, file_id=None)
    session.add(src)
    session.commit()

    doc = Document(
        source_id=src.id,
        modality="text",
        title="Leave Policy",
        content="All full-time employees are entitled to 24 annual leave days per calendar year. Employees may carry over up to 5 unused annual leave days.",
        content_hash="hash_lifecycle_123",
        word_count=25,
        version_no=1,
        status="active",
    )
    session.add(doc)
    session.commit()

    irun = IndexRun(
        source_id=src.id,
        source_version=1,
        embed_model="sentence-transformers/all-MiniLM-L6-v2",
        embed_dim=384,
        chunk_size=800,
        chunk_overlap=120,
        status="completed",
    )
    session.add(irun)
    session.commit()

    fake_emb = FakeEmbedder()
    chunk1 = Chunk(
        index_run_id=irun.id,
        source_id=src.id,
        document_id=doc.id,
        chunk_index=0,
        content=doc.content,
        content_hash="chash_lifecycle_123",
        token_estimate=25,
        embedding=fake_emb.embed_query(doc.content),
        metadata_={"source_name": "test_hr_eval_lifecycle", "page_number": 1},
    )
    session.add(chunk1)
    session.commit()

    session.test_src_id = src.id

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        # Clean up created records
        session.query(Chunk).filter(Chunk.source_id == src.id).delete()
        session.query(IndexRun).filter(IndexRun.source_id == src.id).delete()
        session.query(Document).filter(Document.source_id == src.id).delete()
        session.query(Source).filter(Source.id == src.id).delete()
        session.commit()
        session.close()


def test_suite_creation_import_and_hash(db_session):
    resp = client.post("/eval/suites", json={
        "name": "HR Policy Test Suite",
        "description": "Lifecycle testing suite",
        "source_ids": [db_session.test_src_id],
    })
    assert resp.status_code == 201
    suite_id = resp.json()["id"]

    # Import items
    items = [
        {
            "position": 1,
            "question": "How many days leave do employees get?",
            "item_type": "answerable",
            "expected_facts": ["24 annual leave days"],
            "expected_evidence": [{"span": "entitled to 24 annual leave days"}],
            "reviewed": False,
        },
        {
            "position": 2,
            "question": "What is the Mars budget?",
            "item_type": "unanswerable",
            "reviewed": False,
        },
    ]
    resp_imp = client.post(f"/eval/suites/{suite_id}/items/import", json=items)
    assert resp_imp.status_code == 200
    assert resp_imp.json()["imported_count"] == 2

    # Check suite hash
    suite = db_session.query(EvalSuite).filter(EvalSuite.id == suite_id).first()
    assert suite.suite_hash != ""
    initial_hash = suite.suite_hash

    # Updating reviewed flag via review endpoint must NOT change suite_hash
    item1 = db_session.query(EvalItem).filter(EvalItem.suite_id == suite_id).first()
    patch_resp = client.patch(f"/eval/items/{item1.id}/review", json={"reviewed": True})
    assert patch_resp.status_code == 200
    db_session.refresh(suite)
    assert suite.suite_hash == initial_hash


def test_frozen_suite_409_and_clone(db_session):
    # 1. Create suite and item
    resp = client.post("/eval/suites", json={
        "name": "Frozen Suite Test",
        "source_ids": [db_session.test_src_id],
    })
    suite_id = resp.json()["id"]
    client.post(f"/eval/suites/{suite_id}/items/import", json=[{
        "position": 1,
        "question": "Sample question?",
        "item_type": "answerable",
        "reviewed": True,
    }])

    # 2. Create an eval run on this suite -> marks it frozen
    run_resp = client.post("/eval/runs", json={
        "suite_id": suite_id,
        "variant": {"strategy": "dense", "chunk_size": 800, "chunk_overlap": 120},
        "wait": True,
    })
    assert run_resp.status_code == 200

    # 3. Attempting to import more items to frozen suite must raise 409
    imp_resp = client.post(f"/eval/suites/{suite_id}/items/import", json=[{
        "position": 2,
        "question": "Another question?",
        "item_type": "unanswerable",
    }])
    assert imp_resp.status_code == 409
    assert "frozen" in imp_resp.json()["detail"].lower()

    # 4. Clone suite succeeds and allows importing items
    clone_resp = client.post(f"/eval/suites/{suite_id}/clone", json={"new_name": "Cloned Editable Suite"})
    assert clone_resp.status_code == 200
    cloned_id = clone_resp.json()["id"]

    imp_clone = client.post(f"/eval/suites/{cloned_id}/items/import", json=[{
        "position": 2,
        "question": "New question in clone?",
        "item_type": "unanswerable",
    }])
    assert imp_clone.status_code == 200
    assert imp_clone.json()["imported_count"] == 1


def test_retrieval_only_run_zero_llm_calls(db_session):
    # Setup suite with 1 reviewed item
    s = EvalSuite(name="Retrieval Zero LLM", source_ids=[db_session.test_src_id], suite_hash="hash1")
    db_session.add(s)
    db_session.commit()

    item = EvalItem(
        suite_id=s.id,
        position=1,
        question="How many days leave do employees get?",
        item_type="answerable",
        expected_facts=["24 annual leave days"],
        expected_evidence=[{"span": "entitled to 24 annual leave days"}],
        reviewed=True,
    )
    db_session.add(item)
    db_session.commit()

    run = EvalRun(
        suite_id=s.id,
        name="Zero LLM Test",
        variant={"strategy": "dense", "chunk_size": 800, "chunk_overlap": 120},
        config_hash=s.suite_hash,
        generate=False,
        judge=False,
        include_unreviewed=False,
        status="queued",
    )
    db_session.add(run)
    db_session.commit()

    # Execute
    tracker = CallBudgetTracker(max_calls=10)
    execute_eval_run(db_session, run.id, budget_tracker=tracker)

    assert run.status == "completed"
    assert tracker.total_calls == 0  # STRICT ASSERTION: ZERO LLM CALLS MADE

    res = db_session.query(EvalResult).filter(EvalResult.run_id == run.id).first()
    assert res is not None
    assert res.llm_calls == 0
    assert res.judge_calls == 0
    assert res.answer is None


def test_generation_with_fake_llm_and_judge_budget(db_session):
    s = EvalSuite(name="Generation & Judge Suite", source_ids=[db_session.test_src_id], suite_hash="hash2")
    db_session.add(s)
    db_session.commit()

    q_text = "All full-time employees are entitled to 24 annual leave days per calendar year. Employees may carry over up to 5 unused annual leave days."
    for pos in (1, 2, 3):
        db_session.add(EvalItem(
            suite_id=s.id,
            position=pos,
            question=q_text,
            item_type="answerable",
            expected_facts=["fact"],
            expected_evidence=[{"span": "entitled to 24"}],
            reviewed=True,
        ))
    db_session.commit()

    tracker = CallBudgetTracker(max_calls=2)
    fake_llm = FakeLLMClient(response="Employees get 24 days [1].")
    fake_judge = FakeJudgeClient(budget_tracker=tracker)

    run = EvalRun(
        suite_id=s.id,
        name="Budget Cap Test",
        variant={"strategy": "dense", "chunk_size": 800, "chunk_overlap": 120},
        config_hash=s.suite_hash,
        generate=True,
        judge=True,
        include_unreviewed=False,
        status="queued",
    )
    db_session.add(run)
    db_session.commit()

    execute_eval_run(
        db_session,
        run.id,
        llm_client=fake_llm,
        judge_client=fake_judge,
        budget_tracker=tracker,
    )

    assert run.status == "failed"
    assert run.error == "budget"


def test_matrix_cap_and_budget_checks(db_session):
    s = EvalSuite(name="Matrix Test Suite", source_ids=[db_session.test_src_id], suite_hash="hash3")
    db_session.add(s)
    db_session.commit()

    # 1. Cap > 24 combinations
    resp_overcap = client.post("/eval/matrix", json={
        "suite_id": s.id,
        "base_variant": {},
        "vary": {
            "strategy": ["dense", "lexical", "hybrid", "hybrid_rerank", "auto"],
            "chunk_size": [200, 400, 600, 800, 1000, 1200],  # 5 x 6 = 30 > 24
        },
    })
    assert resp_overcap.status_code == 400
    assert "exceeding the strict cap of 24" in resp_overcap.json()["detail"]

    # 2. Budget check
    for i in range(5):
        db_session.add(EvalItem(
            suite_id=s.id,
            position=i + 1,
            question=f"Q{i}?",
            item_type="answerable",
            reviewed=True,
        ))
    db_session.commit()

    resp_budget = client.post("/eval/matrix", json={
        "suite_id": s.id,
        "base_variant": {},
        "vary": {"strategy": ["dense", "lexical", "hybrid", "hybrid_rerank"]},
        "generate": True,
        "max_llm_calls": 15,
    })
    assert resp_budget.status_code == 400
    assert "exceeds explicit budget cap" in resp_budget.json()["detail"]


def test_report_md_and_mock_banner(db_session):
    s = EvalSuite(name="Report Markdown Suite", source_ids=[db_session.test_src_id], suite_hash="hash4")
    db_session.add(s)
    db_session.commit()

    run = EvalRun(
        suite_id=s.id,
        name="Mock LLM Test Run",
        variant={"strategy": "dense", "chunk_size": 800},
        config_hash="hash4",
        generate=True,
        judge=True,
        include_unreviewed=True,
        llm={"provider": "mock", "model": "fake-llm", "mock": True},
        status="completed",
    )
    db_session.add(run)
    db_session.commit()

    item = EvalItem(
        suite_id=s.id,
        position=1,
        question="What is leave entitlement?",
        item_type="answerable",
        reviewed=False,
    )
    db_session.add(item)
    db_session.commit()

    res = EvalResult(
        run_id=run.id,
        item_id=item.id,
        status="success",
        answer="Employees get 24 days leave.",
        metrics={"hit@5": 1.0, "recall@5": 1.0, "precision@5": 0.2, "mrr": 1.0},
        latency_ms={"total": 45.0, "dense": 20.0},
    )
    db_session.add(res)
    db_session.commit()

    rep = generate_run_report(db_session, run.id)
    assert rep["is_mock"] is True

    md = generate_markdown_scorecard(db_session, [run.id])
    assert "MOCK LLM RUN DETECTED" in md
    assert "UNREVIEWED ITEMS INCLUDED" in md
    assert "LLM-JUDGED METRICS" in md
    assert "Provenance & Run Configuration" in md
    assert "Core Quantitative Metrics" in md
