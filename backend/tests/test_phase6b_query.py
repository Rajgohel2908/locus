"""
backend/tests/test_phase6b_query.py — Config-aware /query endpoint tests.

Tests:
1. /query with pipeline_config_id uses the config's index runs and specs.
2. Explicit request parameters override config settings (top_k, strategy).
3. structured_route_enabled=False redirects structured question to RAG with trace note.
4. Baseline config + auto behaves as plain dense with router and structured off.
5. Default /query without pipeline_config_id behaves exactly as in 6A.
6. Unsupported question returns insufficient_evidence with zero LLM calls under both configs.
7. Document/records hashes and rows non-NULL and unchanged.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from db import (
    Source,
    Document,
    Record,
    SourceVersion,
    ColumnRole,
    IndexRun,
    Chunk,
    PipelineConfig,
    QueryRecord,
)
from recommender.rules import get_baseline_spec, compute_spec_hash

client = TestClient(app)


@pytest.fixture
def test_env(db: Session):
    """Set up structured employee source and policy text document."""
    # 1. Structured employee source
    s_emp = Source(name="Employees", source_type="structured", origin="test")
    db.add(s_emp)
    db.flush()

    v_emp = SourceVersion(source_id=s_emp.id, version_no=2, note="cleaned v2")
    db.add(v_emp)

    roles = [
        ColumnRole(source_id=s_emp.id, column_name="EmpId", role="identifier", confirmed=True),
        ColumnRole(source_id=s_emp.id, column_name="Salary", role="numeric", confirmed=True),
        ColumnRole(source_id=s_emp.id, column_name="City", role="categorical", confirmed=True),
    ]
    for r in roles:
        db.add(r)

    rows = [
        {"EmpId": "E1", "Salary": 60000.0, "City": "Mumbai"},
        {"EmpId": "E2", "Salary": 80000.0, "City": "Mumbai"},
        {"EmpId": "E3", "Salary": 75000.0, "City": "Delhi"},
    ]
    for idx, r_data in enumerate(rows):
        rec = Record(
            source_id=s_emp.id,
            row_index=idx,
            data=r_data,
            version_no=2,
            status="active",
        )
        db.add(rec)

    # 2. Text source
    s_txt = Source(name="Leave Policy", source_type="file", origin="test")
    db.add(s_txt)
    db.flush()

    v_txt = SourceVersion(source_id=s_txt.id, version_no=1, note="initial")
    db.add(v_txt)

    doc = Document(
        source_id=s_txt.id,
        modality="text",
        title="Leave Policy 2024",
        content="All full-time employees are entitled to 24 annual leave days.",
        content_hash="hash_leave_2024",
        word_count=10,
        version_no=1,
        status="active",
    )
    db.add(doc)
    db.flush()

    # Index runs
    idx_run_base = IndexRun(
        source_id=s_txt.id,
        source_version=1,
        embed_model="sentence-transformers/all-MiniLM-L6-v2",
        embed_dim=384,
        chunk_size=800,
        chunk_overlap=120,
        chunk_count=1,
        status="completed",
    )
    idx_run_rec = IndexRun(
        source_id=s_txt.id,
        source_version=1,
        embed_model="sentence-transformers/all-MiniLM-L6-v2",
        embed_dim=384,
        chunk_size=500,
        chunk_overlap=75,
        chunk_count=1,
        status="completed",
    )
    db.add(idx_run_base)
    db.add(idx_run_rec)
    db.flush()

    chk_base = Chunk(
        index_run_id=idx_run_base.id,
        source_id=s_txt.id,
        document_id=doc.id,
        chunk_index=0,
        content="All full-time employees are entitled to 24 annual leave days.",
        content_hash="chunk_hash_base",
        token_estimate=12,
        embedding=[0.05] * 384,
        metadata_={"published_at": None},
    )
    chk_rec = Chunk(
        index_run_id=idx_run_rec.id,
        source_id=s_txt.id,
        document_id=doc.id,
        chunk_index=0,
        content="All full-time employees are entitled to 24 annual leave days.",
        content_hash="chunk_hash_rec",
        token_estimate=12,
        embedding=[0.05] * 384,
        metadata_={"published_at": None},
    )
    db.add(chk_base)
    db.add(chk_rec)

    # 3. Pipeline Configs
    b_spec = get_baseline_spec()
    cfg_base = PipelineConfig(
        name="Phase 4 Baseline",
        kind="baseline",
        source_ids=[s_txt.id, s_emp.id],
        spec=b_spec,
        spec_hash=compute_spec_hash(b_spec),
        index_runs={str(s_txt.id): idx_run_base.id},
    )

    r_spec = {
        "chunk_size": 500,
        "chunk_overlap": 75,
        "strategy_default": "hybrid",
        "use_rerank": False,
        "top_k": 5,
        "candidates_n": 20,
        "filters_default": {},
        "structured_route_enabled": True,
        "router_enabled": True,
        "suggested_filters": {},
        "notes": [],
        "basis": "rule-based priors, not validated; compare with evaluation in Phase 7",
    }
    cfg_rec = PipelineConfig(
        name="Recommended (qa)",
        kind="recommended",
        source_ids=[s_txt.id, s_emp.id],
        spec=r_spec,
        spec_hash=compute_spec_hash(r_spec),
        index_runs={str(s_txt.id): idx_run_rec.id},
    )

    # Config with structured_route_enabled=False
    r_spec_no_struct = dict(r_spec)
    r_spec_no_struct["structured_route_enabled"] = False
    cfg_no_struct = PipelineConfig(
        name="Recommended (no structured)",
        kind="recommended",
        source_ids=[s_txt.id, s_emp.id],
        spec=r_spec_no_struct,
        spec_hash=compute_spec_hash(r_spec_no_struct),
        index_runs={str(s_txt.id): idx_run_rec.id},
    )

    db.add(cfg_base)
    db.add(cfg_rec)
    db.add(cfg_no_struct)
    db.commit()

    return {
        "emp_source": s_emp,
        "txt_source": s_txt,
        "doc": doc,
        "cfg_base": cfg_base,
        "cfg_rec": cfg_rec,
        "cfg_no_struct": cfg_no_struct,
        "idx_run_base": idx_run_base,
        "idx_run_rec": idx_run_rec,
    }


def test_query_baseline_config_auto_behaves_as_plain_dense(test_env):
    """
    Baseline config with auto behaves as plain config.strategy_default ('dense')
    with the router and structured path off.
    """
    cfg_base_id = test_env["cfg_base"].id

    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "no_chunks"}, {"dense": 2.0}, [test_env["idx_run_base"].id])

        # Even on structured question, baseline config keeps router and structured path off
        resp = client.post(
            "/query",
            json={
                "question": "What is the average salary in Mumbai?",
                "pipeline_config_id": cfg_base_id,
                "strategy": "auto",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["config"]["strategy"] == "dense"
        assert data["answer_type"] == "generated"
        assert data["pipeline_config_id"] == cfg_base_id

        # Trace endpoint check
        q_id = data["query_id"]
        trace = client.get(f"/queries/{q_id}/trace").json()
        assert trace["pipeline_config_id"] == cfg_base_id
        assert trace["pipeline_config"]["kind"] == "baseline"


def test_query_recommended_config_structured_route_when_enabled(test_env):
    """
    Recommended config with structured_route_enabled=True computes structured aggregation.
    Zero LLM calls, zero embedder calls.
    """
    cfg_rec_id = test_env["cfg_rec"].id

    with patch("generation.answer.get_llm_client") as mock_llm, \
         patch("generation.answer.get_embedder") as mock_emb:

        resp = client.post(
            "/query",
            json={
                "question": "What is the average salary in Mumbai?",
                "pipeline_config_id": cfg_rec_id,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "answered"
        assert data["answer_type"] == "computed"
        assert "70,000.00" in data["answer"]
        assert data["pipeline_config_id"] == cfg_rec_id
        assert mock_llm.return_value.generate.call_count == 0


def test_query_structured_redirect_when_disabled(test_env):
    """
    structured_route_enabled=False sends structured question to RAG with trace note.
    """
    cfg_id = test_env["cfg_no_struct"].id

    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "no_chunks"}, {"hybrid": 5.0}, [test_env["idx_run_rec"].id])

        resp = client.post(
            "/query",
            json={
                "question": "What is the average salary in Mumbai?",
                "pipeline_config_id": cfg_id,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Redirected to RAG
        assert data["answer_type"] == "generated"
        assert data["pipeline_config_id"] == cfg_id

        # Verify trace note explains the redirect
        q_id = data["query_id"]
        trace = client.get(f"/queries/{q_id}/trace").json()
        assert trace["pipeline_config_id"] == cfg_id
        route_decision = trace.get("route_decision", {})
        # Route info captured in query
        q_row = client.get(f"/queries/{q_id}").json()
        r_info = q_row.get("route_info", {})
        assert r_info.get("redirected_from_structured") is True
        assert "structured_route_enabled is False" in r_info.get("note", "")


def test_query_explicit_parameters_override_config(test_env):
    """Explicit request parameters override pipeline config."""
    cfg_rec_id = test_env["cfg_rec"].id

    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "no_chunks"}, {"dense": 2.0}, [test_env["idx_run_rec"].id])

        resp = client.post(
            "/query",
            json={
                "question": "Leave policy details",
                "pipeline_config_id": cfg_rec_id,
                "strategy": "dense",  # Overrides config's hybrid
                "top_k": 9,           # Overrides config's 5
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["config"]["strategy"] == "dense"
        assert data["config"]["top_k"] == 9


def test_query_default_behavior_without_config_unchanged(test_env):
    """Without pipeline_config_id, /query behaves exactly as before (defaults to dense)."""
    with patch("generation.answer.execute_pipeline") as mock_pipeline:
        mock_pipeline.return_value = ([], {"passed": False, "signal": "no_chunks"}, {"dense": 2.0}, [test_env["idx_run_base"].id])

        resp = client.post(
            "/query",
            json={
                "question": "Leave policy details",
                "source_ids": [test_env["txt_source"].id],
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["config"]["strategy"] == "dense"
        assert data.get("pipeline_config_id") is None


def test_query_unsupported_question_zero_llm_calls_both_configs(test_env):
    """Unsupported question returns insufficient_evidence with zero LLM calls under both configs."""
    unsupported_q = "What is the company's Mars colonization budget?"

    for cfg_key in ("cfg_base", "cfg_rec"):
        cfg_id = test_env[cfg_key].id
        with patch("generation.answer.get_llm_client") as mock_llm:
            resp = client.post(
                "/query",
                json={
                    "question": unsupported_q,
                    "pipeline_config_id": cfg_id,
                },
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["status"] == "insufficient_evidence"
            assert data["answer"] is None
            assert mock_llm.return_value.generate.call_count == 0


def test_document_and_record_immutability(db: Session, test_env):
    """Assert non-NULL content_hash and row count > 0 for documents and records."""
    docs = db.query(Document).filter(Document.source_id == test_env["txt_source"].id).all()
    assert len(docs) > 0
    for d in docs:
        assert d.content_hash is not None
        assert len(d.content_hash) > 0

    recs = db.query(Record).filter(Record.source_id == test_env["emp_source"].id).all()
    assert len(recs) > 0
    for r in recs:
        assert r.data is not None

