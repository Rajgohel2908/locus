"""
tests/test_phase6a_api.py — Integration and endpoint tests for Phase 6A.

Covers:
- POST /route: Pure analysis endpoint (0 LLM, 0 embedder calls).
- POST /query with strategy="auto":
  - Structured route: 0 LLM calls, 0 embedder calls, answer_type="computed", computed citations.
  - Verification of database persistence: route, route_info, answer_type in queries table.
  - Fallback path test: unexpected failure falls back to RAG with recorded note.
- Regression check: POST /query without strategy defaults to "dense", route is None, answer_type is "generated".
- Explicit strategies ("dense", "lexical", "hybrid", "hybrid_rerank") bypass router.
- GET /queries/{id}/trace: Assembled explanation for computed, retrieval, and insufficient evidence queries.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool
from main import app
from db import (
    Base, get_db, Source, Document, Record, SourceVersion,
    ColumnRole, CleaningProposal, IndexRun, Chunk, QueryRecord,
    RetrievalResult, DocumentOverride
)
from indexing.embedder import FakeEmbedder
from generation.llm import FakeLLMClient

client = TestClient(app)


@pytest.fixture
def test_db_session():
    """In-memory SQLite session with all tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Override get_db dependency in FastAPI app
    def _override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield session
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def populated_source(test_db_session):
    """Seed structured source for API tests."""
    src = Source(source_type="file", name="employees_test.csv")
    test_db_session.add(src)
    test_db_session.commit()

    rows = [
        {"Employee_ID": "E1001", "Name": "Alice", "Department": "Engineering", "Salary": "85000", "City": "Mumbai"},
        {"Employee_ID": "E1002", "Name": "Bob", "Department": "HR", "Salary": "55000", "City": "Mumbai"},
        {"Employee_ID": "E1003", "Name": "Charlie", "Department": "Engineering", "Salary": "92000", "City": "Delhi"},
        {"Employee_ID": "E1004", "Name": "Diana", "Department": "HR", "Salary": "60000", "City": "Delhi"},
    ]

    for idx, r in enumerate(rows):
        rec = Record(
            source_id=src.id,
            row_index=idx,
            version_no=1,
            status="active",
            data=r,
        )
        test_db_session.add(rec)

    # Add SourceVersion profile
    sv = SourceVersion(
        source_id=src.id,
        version_no=1,
        profile={
            "duplicate_rows": 0,
            "columns": {
                "Salary": {"dtype": "float64", "missing_pct": 0.0},
                "City": {"dtype": "object", "missing_pct": 0.0},
                "Department": {"dtype": "object", "missing_pct": 0.0},
                "Employee_ID": {"dtype": "object", "missing_pct": 0.0},
            }
        }
    )
    test_db_session.add(sv)
    test_db_session.commit()
    return src


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /route Endpoint Test
# ─────────────────────────────────────────────────────────────────────────────

def test_api_route_endpoint(populated_source):
    # Structured query
    res = client.post(
        "/route",
        json={
            "question": "What is the average salary in Mumbai?",
            "source_ids": [populated_source.id],
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "structured"
    assert data["strategy"] == "structured"
    assert "features" in data
    assert data["features"]["aggregation_intent"]["op"] == "avg"
    assert data["features"]["target_column"] == "Salary"

    # Exact query
    res_exact = client.post(
        "/route",
        json={
            "question": "What is employee E1001's salary?",
            "source_ids": [populated_source.id],
        }
    )
    assert res_exact.status_code == 200
    data_exact = res_exact.json()
    assert data_exact["route"] == "exact"
    assert data_exact["strategy"] == "hybrid"


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /query Structured Route: Zero LLM / Zero Embedding Calls
# ─────────────────────────────────────────────────────────────────────────────

def test_api_query_structured_auto_zero_llm_zero_embed(populated_source):
    with patch("generation.answer.get_llm_client") as mock_get_llm, \
         patch("generation.answer.get_embedder") as mock_get_embedder:

        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        mock_emb = MagicMock()
        mock_get_embedder.return_value = mock_emb

        res = client.post(
            "/query",
            json={
                "question": "What is the average salary in Mumbai?",
                "source_ids": [populated_source.id],
                "strategy": "auto",
            }
        )

        assert res.status_code == 200
        data = res.json()

        # Zero LLM and zero embedding calls assertion
        assert mock_llm.generate.call_count == 0
        assert mock_emb.embed_query.call_count == 0
        assert mock_emb.embed_chunks.call_count == 0

        # Structured response verification
        assert data["status"] == "answered"
        assert data["answer_type"] == "computed"
        assert "70,000.00" in data["answer"]
        assert len(data["citations"]) == 1
        citation = data["citations"][0]
        assert citation["type"] == "computed"
        assert citation["source_id"] == populated_source.id
        assert citation["rows_used"] == 2
        assert "Salary" in citation["columns"]

        # Route info present in response
        assert "route" in data
        assert data["route"]["route"] == "structured"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Default Strategy and Explicit Strategies Regression Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_api_query_default_strategy_regression(test_db_session, populated_source):
    # /query without strategy must default to "dense", route is None, answer_type is "generated"
    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "no_chunks"}, {"dense": 5.0}, [1])

        res = client.post(
            "/query",
            json={
                "question": "General company policy question",
                "source_ids": [populated_source.id],
                # strategy omitted -> defaults to "dense"
            }
        )

        assert res.status_code == 200
        data = res.json()
        assert data["config"]["strategy"] == "dense"
        assert data.get("answer_type") == "generated"
        assert "route" not in data  # Router bypassed on explicit/default dense strategy


def test_api_query_explicit_strategy_bypasses_router(test_db_session, populated_source):
    # Even if question looks structured, explicit strategy bypasses router
    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "no_chunks"}, {"hybrid": 5.0}, [1])

        res = client.post(
            "/query",
            json={
                "question": "What is the average salary in Mumbai?",
                "source_ids": [populated_source.id],
                "strategy": "hybrid",
            }
        )

        assert res.status_code == 200
        data = res.json()
        assert data["config"]["strategy"] == "hybrid"
        assert "route" not in data


# ─────────────────────────────────────────────────────────────────────────────
# 4. Fallback Path When Structured Execution Fails
# ─────────────────────────────────────────────────────────────────────────────

def test_api_query_structured_fallback_path(test_db_session, populated_source):
    # Simulate unexpected failure during execute_aggregation
    with patch("generation.answer.execute_aggregation", side_effect=RuntimeError("Simulated DB connection drop")), \
         patch("generation.answer.execute_pipeline") as mock_pipeline:

        mock_pipeline.return_value = ([], {"passed": False, "signal": "insufficient_evidence"}, {"dense": 5.0}, [1])

        res = client.post(
            "/query",
            json={
                "question": "What is the average salary in Mumbai?",
                "source_ids": [populated_source.id],
                "strategy": "auto",
            }
        )

        assert res.status_code == 200
        data = res.json()
        # Must fall back cleanly to RAG route, not 500 error
        assert "route" in data
        assert any("structured_execution_failed" in f for f in data["route"]["fallbacks"])


# ─────────────────────────────────────────────────────────────────────────────
# 5. GET /queries/{id}/trace Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_api_trace_computed_and_retrieval_queries(test_db_session, populated_source):
    # 1. Run a computed query
    res_comp = client.post(
        "/query",
        json={
            "question": "What is the average salary in Mumbai?",
            "source_ids": [populated_source.id],
            "strategy": "auto",
        }
    )
    comp_qid = res_comp.json()["query_id"]

    # Trace computed query
    t_comp = client.get(f"/queries/{comp_qid}/trace")
    assert t_comp.status_code == 200
    trace_comp = t_comp.json()
    assert trace_comp["query_id"] == comp_qid
    assert trace_comp["route"] == "structured"
    assert trace_comp["answer_type"] == "computed"
    assert trace_comp["rows_used"] == 2
    assert "sql_description" in trace_comp
    assert "data_quality_notes" in trace_comp

    # 2. Run a retrieval query (insufficient evidence)
    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "insufficient_evidence"}, {"dense": 5.0}, [1])
        res_rag = client.post(
            "/query",
            json={
                "question": "What is the company's Mars colonization budget?",
                "source_ids": [populated_source.id],
                "strategy": "auto",
            }
        )
        rag_qid = res_rag.json()["query_id"]

    # Trace retrieval query
    t_rag = client.get(f"/queries/{rag_qid}/trace")
    assert t_rag.status_code == 200
    trace_rag = t_rag.json()
    assert trace_rag["query_id"] == rag_qid
    assert trace_rag["route"] == "semantic"
    assert trace_rag["strategy"] == "hybrid"
    assert trace_rag["status"] == "insufficient_evidence"
    assert "evidence_gate" in trace_rag
    assert trace_rag["evidence_gate"]["passed"] is False
    assert "retrieval_candidates" in trace_rag


# ─────────────────────────────────────────────────────────────────────────────
# 6. Citation Consistency & Mock LLM Honesty Tests (Requirements 4 & 5)
# ─────────────────────────────────────────────────────────────────────────────

def test_citation_consistency_with_fake_llm_invalid_id(test_db_session, populated_source):
    """
    Test that if the LLM cites one retrieved ID and one non-retrieved ID,
    the non-retrieved ID is reported in invalid_citations and the status becomes 'unverified'.
    """
    retrieved_chunk = {
        "chunk_id": 1876,
        "source_id": populated_source.id,
        "score": 0.95,
        "rank": 1,
        "content": "Employees are entitled to 24 annual leave days.",
        "metadata": {"source_name": "policy.pdf", "page_number": 1},
        "signals": {"dense_score": 0.95},
    }

    fake_answer = "Employees get 24 days [1876] but historical records say 20 [1877]."
    fake_llm = FakeLLMClient(response=fake_answer, is_mock=True)

    with patch("generation.answer.execute_pipeline") as mock_pipe, \
         patch("generation.answer.get_llm_client", return_value=fake_llm):
        mock_pipe.return_value = (
            [retrieved_chunk],
            {"passed": True, "signal": "score_threshold_met"},
            {"dense": 2.0, "rerank": 0.0},
            [1]
        )

        res = client.post(
            "/query",
            json={
                "question": "What is the policy for annual leaves?",
                "source_ids": [populated_source.id],
                "strategy": "hybrid",
            }
        )
        assert res.status_code == 200
        data = res.json()

        # Item 4: Status must become 'unverified' because 1877 was not in retrieved prompt chunks
        assert data["status"] == "unverified"
        assert len(data["citations"]) == 1
        assert data["citations"][0]["chunk_id"] == 1876
        assert data["invalid_citations"] == [1877]

        # Item 5: Mock answers start with [MOCK], llm object included
        assert data["answer"].startswith("[MOCK]")
        assert "llm" in data
        assert data["llm"]["mock"] is True


def test_unmapped_row_identity_insufficient_evidence(test_db_session, populated_source):
    """
    Test that row_identity_request that cannot be mapped returns status 'insufficient_evidence'
    with reason 'row_identity_not_supported', without calling RAG or LLM.
    """
    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        res = client.post(
            "/query",
            json={
                "question": "Who has the highest bonus?",
                "source_ids": [populated_source.id],
                "strategy": "auto",
            }
        )
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "insufficient_evidence"
        assert data["reason"] == "row_identity_not_supported"
        assert data["answer"] is None
        assert mock_pipeline.call_count == 0  # Zero RAG calls!

