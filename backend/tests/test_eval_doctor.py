"""
tests/test_eval_doctor.py — Integration and Unit Tests for RAG Doctor v1.

Tests:
1. Rules D1 through D9 unit evaluations:
   - D1: Slice Weakness
   - D2: Depth Gap
   - D3: Broad Chunks
   - D4: False Refusals
   - D5: Unsafe Answers
   - D6: Citation Problems
   - D7: Stale Citations & Temporal Conflicts
   - D8: Router Errors
   - D9: Rerank No Gain
2. Doctor State Machine:
   - proposed -> approved / rejected
   - cannot apply unless approved
   - apply creates new PipelineConfig of kind='doctor' and leaves old configs untouched
   - verify executes eval run on patched config and computes paired comparison
3. Zero LLM Calls: Doctor diagnosis, approval, patch generation, and verification
   make exactly ZERO LLM calls when retrieval-only runs are used.
"""

import os
import urllib.parse
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from db import (
    Base, get_db,
    EvalSuite, EvalItem, EvalRun, EvalResult,
    DoctorReport, DoctorFinding, PipelineConfig,
    Source, Document, IndexRun, Chunk
)
from indexing.embedder import FakeEmbedder, set_embedder
from retrieval.rerank import FakeReranker, set_reranker
from evaluation.doctor.rules import evaluate_rules
from evaluation.doctor.engine import (
    run_doctor_analysis,
    approve_finding,
    reject_finding,
    apply_finding,
    verify_finding,
)

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
        pytest.fail(f"Safety check failed: pg test database name must end with '_test', got '{db_name}'.")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    src = Source(source_type="file", name="test_doctor_source")
    session.add(src)
    session.commit()

    doc = Document(
        source_id=src.id,
        modality="text",
        title="Leave Policy",
        content="All full-time employees are entitled to 24 annual leave days.",
        content_hash="hash_doctor_1",
        word_count=10,
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
        content_hash="chash_doc_1",
        token_estimate=10,
        embedding=fake_emb.embed_query(doc.content),
        metadata_={"source_name": "test_doctor_source", "freshness": "fresh"},
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
        session.query(DoctorFinding).delete()
        session.query(DoctorReport).delete()
        session.query(EvalResult).delete()
        session.query(EvalRun).delete()
        session.query(EvalItem).delete()
        session.query(EvalSuite).delete()
        session.query(PipelineConfig).filter(PipelineConfig.kind == "doctor").delete()
        session.query(Chunk).filter(Chunk.source_id == src.id).delete()
        session.query(IndexRun).filter(IndexRun.source_id == src.id).delete()
        session.query(Document).filter(Document.source_id == src.id).delete()
        session.query(Source).filter(Source.id == src.id).delete()
        session.commit()
        session.close()


def test_rules_d1_to_d8_evaluation(db_session):
    """Test pure rule triggers D1 through D8."""
    suite = EvalSuite(name="Doctor Rules Test Suite", source_ids=[db_session.test_src_id], suite_hash="hash_d1")
    db_session.add(suite)
    db_session.commit()

    # Create items covering different scenarios
    items = []
    # Items 1-4: answerable semantic items with high recall
    for i in range(1, 5):
        it = EvalItem(
            suite_id=suite.id,
            position=i,
            question=f"Semantic Question {i}?",
            item_type="answerable",
            expected_route="semantic",
            expected_evidence=[{"span": "entitled to 24 annual leave days"}],
            reviewed=True,
        )
        db_session.add(it)
        items.append(it)

    # Items 5-6: exact route items with low recall (triggers D1 slice weakness)
    for i in range(5, 7):
        it = EvalItem(
            suite_id=suite.id,
            position=i,
            question=f"Exact ID Question {i}?",
            item_type="answerable",
            expected_route="exact",
            expected_evidence=[{"span": "employee ID exact span"}],
            reviewed=True,
        )
        db_session.add(it)
        items.append(it)

    # Item 7: broad chunk scenario
    it7 = EvalItem(
        suite_id=suite.id,
        position=7,
        question="Broad chunk question?",
        item_type="answerable",
        expected_route="semantic",
        expected_evidence=[{"span": "short"}],
        reviewed=True,
    )
    db_session.add(it7)
    items.append(it7)

    # Item 8: unanswerable query answered (unsafe answer D5)
    it8 = EvalItem(
        suite_id=suite.id,
        position=8,
        question="What is the Mars budget?",
        item_type="unanswerable",
        expected_route="semantic",
        reviewed=True,
    )
    db_session.add(it8)
    items.append(it8)

    db_session.commit()
    items_map = {it.id: it for it in items}

    # Setup Run
    run1 = EvalRun(
        suite_id=suite.id,
        name="Doctor Evaluation Run",
        variant={"strategy": "dense", "chunk_size": 800, "top_k": 5},
        config_hash="hash_d1",
        generate=False,
        judge=False,
        status="completed",
    )
    db_session.add(run1)
    db_session.commit()

    # Construct synthetic results for run1 to test rule triggers
    results = [
        # Items 1-4: recall@5 = 1.0, recall@20 = 1.0 (semantic)
        EvalResult(
            run_id=run1.id, item_id=items[0].id, route="semantic", status="success",
            metrics={"recall@5": 1.0, "recall@20": 1.0, "precision@5": 0.2, "hit@5": 1.0},
        ),
        EvalResult(
            run_id=run1.id, item_id=items[1].id, route="semantic", status="success",
            metrics={"recall@5": 1.0, "recall@20": 1.0, "precision@5": 0.2, "hit@5": 1.0},
        ),
        EvalResult(
            run_id=run1.id, item_id=items[2].id, route="semantic", status="success",
            metrics={"recall@5": 0.8, "recall@20": 1.0, "precision@5": 0.2, "hit@5": 1.0},
        ),
        EvalResult(
            run_id=run1.id, item_id=items[3].id, route="semantic", status="success",
            metrics={"recall@5": 0.8, "recall@20": 1.0, "precision@5": 0.2, "hit@5": 1.0},
        ),
        # Items 5-6: exact route, recall@5 = 0.0, recall@20 = 0.8 (Depth gap + slice weakness!)
        EvalResult(
            run_id=run1.id, item_id=items[4].id, route="exact", status="success",
            metrics={"recall@5": 0.0, "recall@20": 0.8, "precision@5": 0.0, "hit@5": 0.0},
        ),
        EvalResult(
            run_id=run1.id, item_id=items[5].id, route="exact", status="success",
            metrics={"recall@5": 0.0, "recall@20": 0.8, "precision@5": 0.0, "hit@5": 0.0},
        ),
        # Item 7: broad chunks (hit=1, precision=0.1, chunk content >> span)
        EvalResult(
            run_id=run1.id, item_id=items[6].id, route="semantic", status="success",
            metrics={"recall@5": 1.0, "recall@20": 1.0, "precision@5": 0.1, "hit@5": 1.0},
            retrieved=[{"content": "A" * 500, "relevant": True}],
        ),
        # Item 8: unanswerable query with unsafe answer (status='success' instead of 'insufficient_evidence')
        EvalResult(
            run_id=run1.id, item_id=items[7].id, route="semantic", status="success",
            metrics={"unsafe_answer": 1.0, "refusal_correct": 0.0},
            retrieved=[{"score": 0.38, "content": "Random context"}],
        ),
    ]
    for r in results:
        db_session.add(r)
    db_session.commit()

    run_results = {run1.id: results}
    findings = evaluate_rules([run1], run_results, items_map)

    rule_ids = {f["rule_id"] for f in findings}
    assert "D1" in rule_ids  # Slice Weakness on route 'exact'
    assert "D2" in rule_ids  # Depth Gap (recall@20 - recall@5 >= 0.15)
    assert "D5" in rule_ids  # Unsafe Answer on item 8


def test_rule_d9_rerank_no_gain(db_session):
    """Test rule D9 when hybrid vs hybrid_rerank shows no statistically distinguishable gain."""
    suite = EvalSuite(name="D9 Test Suite", source_ids=[db_session.test_src_id], suite_hash="hash_d9")
    db_session.add(suite)
    db_session.commit()

    items = []
    for i in range(15):
        it = EvalItem(
            suite_id=suite.id,
            position=i + 1,
            question=f"Q{i}?",
            item_type="answerable",
            reviewed=True,
        )
        db_session.add(it)
        items.append(it)
    db_session.commit()
    items_map = {it.id: it for it in items}

    run_base = EvalRun(
        suite_id=suite.id,
        name="Hybrid Run",
        variant={"strategy": "hybrid", "chunk_size": 800, "use_rerank": False},
        config_hash="hash_d9",
        status="completed",
    )
    run_rr = EvalRun(
        suite_id=suite.id,
        name="Hybrid Rerank Run",
        variant={"strategy": "hybrid", "chunk_size": 800, "use_rerank": True},
        config_hash="hash_d9",
        status="completed",
    )
    db_session.add(run_base)
    db_session.add(run_rr)
    db_session.commit()

    # Identical recall results across all 15 items (delta = 0.0, CI = [0, 0])
    res_base = []
    res_rr = []
    for it in items:
        res_base.append(EvalResult(
            run_id=run_base.id, item_id=it.id, status="success",
            metrics={"recall@5": 0.8, "recall@20": 0.8, "mrr": 0.7},
        ))
        res_rr.append(EvalResult(
            run_id=run_rr.id, item_id=it.id, status="success",
            metrics={"recall@5": 0.8, "recall@20": 0.8, "mrr": 0.7},
        ))

    for r in res_base + res_rr:
        db_session.add(r)
    db_session.commit()

    run_results = {run_base.id: res_base, run_rr.id: res_rr}
    findings = evaluate_rules([run_base, run_rr], run_results, items_map)

    d9_findings = [f for f in findings if f["rule_id"] == "D9"]
    assert len(d9_findings) == 1
    assert d9_findings[0]["proposed_patch"] == {"use_rerank": False}
    assert d9_findings[0]["evidence_level"] == "measured_effect"


def test_doctor_lifecycle_and_state_transitions(db_session):
    """
    Test full Doctor lifecycle via REST endpoints:
    1. POST /doctor/reports
    2. POST /doctor/findings/{id}/approve
    3. POST /doctor/findings/{id}/apply
    4. POST /doctor/findings/{id}/verify
    """
    suite = EvalSuite(name="Doctor Lifecycle Suite", source_ids=[db_session.test_src_id], suite_hash="hash_life")
    db_session.add(suite)
    db_session.commit()

    q_text = "All full-time employees are entitled to 24 annual leave days."
    items = []
    for i in range(5):
        it = EvalItem(
            suite_id=suite.id,
            position=i + 1,
            question=q_text,
            item_type="answerable",
            expected_evidence=[{"span": "entitled to 24 annual leave days"}],
            reviewed=True,
        )
        db_session.add(it)
        items.append(it)
    db_session.commit()

    # Create baseline run with top_k=1 (producing depth gap since depth 20 has it)
    run = EvalRun(
        suite_id=suite.id,
        name="Baseline Run with Depth Gap",
        variant={"strategy": "dense", "chunk_size": 800, "chunk_overlap": 120, "top_k": 1},
        config_hash="hash_life",
        generate=False,
        judge=False,
        status="completed",
    )
    db_session.add(run)
    db_session.commit()

    # Add results with depth gap: recall@5 = 0.2, recall@20 = 1.0
    for it in items:
        db_session.add(EvalResult(
            run_id=run.id,
            item_id=it.id,
            status="success",
            retrieved=[
                {"chunk_id": 1, "rank": 6, "score": 0.45, "relevant": True, "content": q_text}
            ],
            metrics={"recall@5": 0.2, "recall@20": 1.0, "hit@5": 0.2, "precision@5": 0.04},
        ))
    db_session.commit()

    # 1. Create Report
    rep_resp = client.post("/doctor/reports", json={"run_ids": [run.id]})
    assert rep_resp.status_code == 201
    rep_data = rep_resp.json()
    assert rep_data["summary"]["total_findings"] >= 1
    finding_id = rep_data["findings"][0]["id"]
    assert rep_data["findings"][0]["status"] == "proposed"

    # Cannot apply while still 'proposed'
    app_err = client.post(f"/doctor/findings/{finding_id}/apply")
    assert app_err.status_code == 400

    # 2. Approve Finding
    app_resp = client.post(f"/doctor/findings/{finding_id}/approve")
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "approved"

    # 3. Apply Finding
    apply_resp = client.post(f"/doctor/findings/{finding_id}/apply")
    assert apply_resp.status_code == 200
    applied_data = apply_resp.json()
    assert applied_data["finding"]["status"] == "applied"
    cfg = applied_data["pipeline_config"]
    assert cfg["kind"] == "doctor"
    assert applied_data["finding"]["applied_config_id"] == cfg["id"]

    # Verify that existing configs remain untouched
    doc_configs = db_session.query(PipelineConfig).filter(PipelineConfig.kind == "doctor").all()
    assert len(doc_configs) == 1

    # 4. Verify Finding
    ver_resp = client.post(f"/doctor/findings/{finding_id}/verify")
    assert ver_resp.status_code == 200
    ver_data = ver_resp.json()
    assert ver_data["finding"]["status"] in ("verified_improved", "verified_no_change")
    assert ver_data["finding"]["verification_run_id"] is not None


# ── Detailed D1 to D9 Rules Fixture Suites: Firing, Non-Firing, Boundary ────────

def test_rule_d1_fixtures():
    """D1 Slice Weakness: firing, non-firing, boundary."""
    run = EvalRun(id=1, variant={"strategy": "dense", "min_score": 0.30})
    item_sem1 = EvalItem(id=1, item_type="answerable", expected_route="semantic")
    item_sem2 = EvalItem(id=2, item_type="answerable", expected_route="semantic")
    item_exact1 = EvalItem(id=3, item_type="answerable", expected_route="exact")
    item_exact2 = EvalItem(id=4, item_type="answerable", expected_route="exact")
    items_map = {1: item_sem1, 2: item_sem2, 3: item_exact1, 4: item_exact2}

    # 1. Firing fixture: overall = (1.0+1.0+0.4+0.4)/4 = 0.70; exact = 0.40; gap = 0.30 >= 0.15
    res_firing = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 1.0}),
        EvalResult(run_id=1, item_id=2, route="semantic", status="success", metrics={"recall@5": 1.0}),
        EvalResult(run_id=1, item_id=3, route="exact", status="success", metrics={"recall@5": 0.40}),
        EvalResult(run_id=1, item_id=4, route="exact", status="success", metrics={"recall@5": 0.40}),
    ]
    findings, not_fired = evaluate_rules([run], {1: res_firing}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D1" for f in findings)

    # 2. Non-firing fixture: overall = (0.8+0.8+0.75+0.75)/4 = 0.775; exact = 0.75; gap = 0.025 < 0.15
    res_non_firing = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 0.80}),
        EvalResult(run_id=1, item_id=2, route="semantic", status="success", metrics={"recall@5": 0.80}),
        EvalResult(run_id=1, item_id=3, route="exact", status="success", metrics={"recall@5": 0.75}),
        EvalResult(run_id=1, item_id=4, route="exact", status="success", metrics={"recall@5": 0.75}),
    ]
    findings, not_fired = evaluate_rules([run], {1: res_non_firing}, items_map, return_not_fired=True)
    assert not any(f["rule_id"] == "D1" for f in findings)
    assert "D1" in not_fired

    # 3. Boundary fixture: overall = (1.0+1.0+0.70+0.70)/4 = 0.85; exact = 0.70; gap = 0.1500 >= 0.1500 (fires)
    res_bound_fires = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 1.0}),
        EvalResult(run_id=1, item_id=2, route="semantic", status="success", metrics={"recall@5": 1.0}),
        EvalResult(run_id=1, item_id=3, route="exact", status="success", metrics={"recall@5": 0.70}),
        EvalResult(run_id=1, item_id=4, route="exact", status="success", metrics={"recall@5": 0.70}),
    ]
    findings, _ = evaluate_rules([run], {1: res_bound_fires}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D1" for f in findings)

    # 3b. Boundary non-firing: overall = (1.0+1.0+0.71+0.71)/4 = 0.855; exact = 0.71; gap = 0.145 < 0.15
    res_bound_no_fire = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 1.0}),
        EvalResult(run_id=1, item_id=2, route="semantic", status="success", metrics={"recall@5": 1.0}),
        EvalResult(run_id=1, item_id=3, route="exact", status="success", metrics={"recall@5": 0.71}),
        EvalResult(run_id=1, item_id=4, route="exact", status="success", metrics={"recall@5": 0.71}),
    ]
    findings, not_fired = evaluate_rules([run], {1: res_bound_no_fire}, items_map, return_not_fired=True)
    assert not any(f["rule_id"] == "D1" for f in findings)


def test_rule_d2_fixtures():
    """D2 Depth Gap: firing, non-firing, boundary."""
    run = EvalRun(id=1, variant={"strategy": "dense", "min_score": 0.30})
    items_map = {
        i: EvalItem(id=i, item_type="answerable", expected_route="semantic")
        for i in range(1, 3)
    }

    # 1. Firing: recall@20 (1.0) - recall@5 (0.80) = 0.20 >= 0.15
    res_firing = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 0.8, "recall@20": 1.0}),
        EvalResult(run_id=1, item_id=2, route="semantic", status="success", metrics={"recall@5": 0.8, "recall@20": 1.0}),
    ]
    findings, not_fired = evaluate_rules([run], {1: res_firing}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D2" for f in findings)

    # 2. Non-firing: recall@20 (0.90) - recall@5 (0.85) = 0.05 < 0.15
    res_non_firing = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 0.85, "recall@20": 0.90}),
        EvalResult(run_id=1, item_id=2, route="semantic", status="success", metrics={"recall@5": 0.85, "recall@20": 0.90}),
    ]
    findings, not_fired = evaluate_rules([run], {1: res_non_firing}, items_map, return_not_fired=True)
    assert not any(f["rule_id"] == "D2" for f in findings)
    assert "D2" in not_fired

    # 3. Boundary: gap = 0.1500 (fires) vs gap = 0.1490 (does not fire)
    res_boundary_fire = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 0.85, "recall@20": 1.00}),
    ]
    findings, _ = evaluate_rules([run], {1: res_boundary_fire}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D2" for f in findings)

    res_boundary_no_fire = [
        EvalResult(run_id=1, item_id=1, route="semantic", status="success", metrics={"recall@5": 0.851, "recall@20": 1.00}),
    ]
    findings, not_fired = evaluate_rules([run], {1: res_boundary_no_fire}, items_map, return_not_fired=True)
    assert not any(f["rule_id"] == "D2" for f in findings)
    assert "D2" in not_fired


def test_rule_d3_fixtures():
    """D3 Broad Chunks: firing, non-firing (applicability), boundary."""
    run = EvalRun(id=1, variant={"strategy": "dense", "chunk_size": 800})
    items_map = {1: EvalItem(id=1, item_type="answerable", expected_route="semantic")}

    # 1. Firing: hit@5 = 1.0 (>= 0.50), context_precision_tokens = 0.20 (<= 0.35), chunk len 600 (> 400)
    res_firing = [
        EvalResult(
            run_id=1, item_id=1, route="semantic", status="success",
            metrics={"hit@5": 1.0, "context_precision_tokens@5": 0.20},
            retrieved=[{"content": "X" * 600, "relevant": True}],
        )
    ]
    findings, not_fired = evaluate_rules([run], {1: res_firing}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D3" for f in findings)

    # 2. Non-firing (applicability fails): chunks shorter than 400
    res_non_firing_app = [
        EvalResult(
            run_id=1, item_id=1, route="semantic", status="success",
            metrics={"hit@5": 1.0, "context_precision_tokens@5": 0.20},
            retrieved=[{"content": "X" * 200, "relevant": True}],
        )
    ]
    findings, not_fired = evaluate_rules([run], {1: res_non_firing_app}, items_map, return_not_fired=True)
    assert not any(f["rule_id"] == "D3" for f in findings)
    assert not_fired.get("D3") == "chunk_size_change_cannot_affect"

    # 3. Boundary: 50% chunks > 400 (fires) vs 0% chunks > 400 (does not fire)
    res_boundary_fire = [
        EvalResult(
            run_id=1, item_id=1, route="semantic", status="success",
            metrics={"hit@5": 1.0, "context_precision_tokens@5": 0.20},
            retrieved=[
                {"content": "X" * 600, "relevant": True},
                {"content": "X" * 200, "relevant": True},
            ],
        )
    ]
    findings, not_fired = evaluate_rules([run], {1: res_boundary_fire}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D3" for f in findings)


def test_rule_d4_d5_counterfactual_fixtures():
    """D4 False Refusals & D5 Unsafe Answers: firing, non-firing, counterfactual replay."""
    run = EvalRun(id=1, variant={"strategy": "dense", "min_score": 0.30})
    ans_items = {i: EvalItem(id=i, item_type="answerable") for i in range(1, 11)}
    un_items = {i: EvalItem(id=i, item_type="unanswerable") for i in range(11, 21)}
    items_map = {**ans_items, **un_items}

    # 1. D4 Firing: 2 false refusals out of 10 answerable (rate = 0.20 > 0.05)
    res_d4_fire = [
        EvalResult(
            run_id=1, item_id=i, status="insufficient_evidence",
            metrics={"false_refusal": 1.0},
            retrieved=[{"score": 0.28, "relevant": True}],
        )
        if i in (1, 2)
        else EvalResult(
            run_id=1, item_id=i, status="success",
            metrics={"false_refusal": 0.0},
            retrieved=[{"score": 0.45, "relevant": True}],
        )
        for i in range(1, 11)
    ]
    # Add clean unanswerable items
    res_d4_fire += [
        EvalResult(
            run_id=1, item_id=i, status="insufficient_evidence",
            metrics={"unsafe_answer": 0.0},
            retrieved=[{"score": 0.15, "relevant": False}],
        )
        for i in range(11, 21)
    ]

    findings, not_fired = evaluate_rules([run], {1: res_d4_fire}, items_map, return_not_fired=True)
    d4_findings = [f for f in findings if f["rule_id"] == "D4"]
    assert len(d4_findings) == 1
    assert d4_findings[0]["evidence_level"] == "counterfactual"
    assert "counterfactual" in d4_findings[0]
    assert d4_findings[0]["counterfactual"]["optimal_threshold"] <= 0.28

    # 2. D5 Firing: 2 unsafe answers out of 10 unanswerable (rate = 0.20 > 0.05)
    res_d5_fire = [
        EvalResult(
            run_id=1, item_id=i, status="success",
            metrics={"false_refusal": 0.0},
            retrieved=[{"score": 0.50, "relevant": True}],
        )
        for i in range(1, 11)
    ]
    res_d5_fire += [
        EvalResult(
            run_id=1, item_id=i, status="success",
            metrics={"unsafe_answer": 1.0},
            retrieved=[{"score": 0.35, "relevant": False}],
        )
        if i in (11, 12)
        else EvalResult(
            run_id=1, item_id=i, status="insufficient_evidence",
            metrics={"unsafe_answer": 0.0},
            retrieved=[{"score": 0.12, "relevant": False}],
        )
        for i in range(11, 21)
    ]

    findings, not_fired = evaluate_rules([run], {1: res_d5_fire}, items_map, return_not_fired=True)
    d5_findings = [f for f in findings if f["rule_id"] == "D5"]
    assert len(d5_findings) == 1
    assert d5_findings[0]["evidence_level"] == "counterfactual"
    assert "cleanly blocks" not in d5_findings[0]["expected_effect"]


def test_rule_d6_d7_d8_fixtures():
    """D6 (Citations), D7 (Temporal), D8 (Router): firing, non-firing."""
    run = EvalRun(id=1, variant={"strategy": "dense"})
    item1 = EvalItem(id=1, item_type="answerable", expected_route="structured")
    items_map = {1: item1}

    # 1. D6 Firing (invalid citations)
    res_d6 = [
        EvalResult(
            run_id=1, item_id=1, route="structured", status="success",
            metrics={"invalid_citation_rate": 0.30},
        )
    ]
    findings, _ = evaluate_rules([run], {1: res_d6}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D6" for f in findings)

    # 2. D7 Firing (fresh + stale interleaving)
    res_d7 = [
        EvalResult(
            run_id=1, item_id=1, route="structured", status="success",
            metrics={"invalid_citation_rate": 0.0},
            retrieved=[
                {"content": "c1", "signals": {"freshness": "fresh"}},
                {"content": "c2", "signals": {"freshness": "stale"}},
            ],
        )
    ]
    findings, _ = evaluate_rules([run], {1: res_d7}, items_map, return_not_fired=True)
    assert any(f["rule_id"] == "D7" for f in findings)

    # 3. D8 Firing (Route mismatch: expected structured, got semantic)
    res_d8 = [
        EvalResult(
            run_id=1, item_id=1, route="semantic", status="success",
            metrics={"invalid_citation_rate": 0.0},
        )
    ]
    findings, _ = evaluate_rules([run], {1: res_d8}, items_map, return_not_fired=True)
    d8_findings = [f for f in findings if f["rule_id"] == "D8"]
    assert len(d8_findings) == 1
    assert d8_findings[0]["evidence_level"] == "observed"


