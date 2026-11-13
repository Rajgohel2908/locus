"""
tests/test_eval_phase8_1.py — Comprehensive tests for Phase 8.1 Backend Patch:
1. Unmeasured is not zero: metrics not computed report n/a with reason, router_bypassed exclusion for value_match.
2. Suite composition breakdown & 60% route skew banner boundary (> 0.60 vs <= 0.60).
3. Paired comparisons reported per route slice with n.
4. Non-atomic facts linting failure and suggestions.
5. Dev/holdout split determinism, item_type stratification, and immutability after first run (409).
6. Gold builder API: item CRUD on draft suites, frozen-suite 409, text-units endpoint.
7. Verbatim span validation (422) and active row_key check (422).
8. Holdout-only verification and verified_inconclusive_small_n status when holdout n is small.
"""

import os
import json
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
    Source, Document, IndexRun, Chunk, Record,
)
from indexing.embedder import FakeEmbedder, set_embedder
from retrieval.rerank import FakeReranker, set_reranker
from evaluation.metrics import compute_item_metrics, check_structured_value_match
from evaluation.engine import (
    create_eval_suite,
    split_eval_suite,
    is_suite_frozen,
    create_suite_item,
    update_suite_item,
    delete_suite_item,
    lint_eval_suite,
    generate_run_report,
    generate_markdown_scorecard,
    generate_paired_comparison_md,
)
from evaluation.doctor.engine import run_doctor_analysis, approve_finding, apply_finding, verify_finding

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
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        app.dependency_overrides.pop(get_db, None)


# ── 1. Unmeasured is not zero & router_bypassed ──────────────────────────────

def test_unmeasured_is_not_zero_and_router_bypassed(db_session):
    """
    When router is bypassed (explicit retrieval strategy), value_match is excluded
    with reason 'router_bypassed' and never reported as 0 with an n.
    """
    # Case A: structured path did NOT run -> value_match must be excluded with reason 'router_bypassed'
    metrics_no_router = compute_item_metrics(
        item_type="answerable",
        expected_evidence=[],
        expected_facts=[],
        expected_value={"value": 75000},
        expected_route="structured",
        retrieved=[],
        answer="75000",
        status="success",
        citations=[],
        route="semantic",
        generate=False,
        structured_path_ran=False,
    )
    assert metrics_no_router["value_match"] is None
    assert metrics_no_router.get("value_match_reason") == "router_bypassed"

    # Case B: structured path DID run -> value_match is computed
    metrics_with_router = compute_item_metrics(
        item_type="answerable",
        expected_evidence=[],
        expected_facts=[],
        expected_value={"value": 75000},
        expected_route="structured",
        retrieved=[],
        answer="75000",
        status="success",
        citations=[],
        route="structured",
        generate=False,
        structured_path_ran=True,
    )
    assert metrics_with_router["value_match"] == 1.0


# ── 2. Suite Composition & 60% Route Skew Banner Boundary ───────────────────

def test_suite_composition_and_skew_banner_boundary(db_session):
    """
    Reports show suite composition: counts by item_type, expected_route, source type,
    and answerable items per route.
    Tests the exact 60% boundary:
    - > 60% (e.g. 7/10 = 70%): banner appears.
    - <= 60% (e.g. 6/10 = 60%): banner does NOT appear.
    """
    # Create suite 1: 7 exact out of 10 answerable (70% > 60%) -> skewed
    suite_skewed = EvalSuite(name="Skewed Suite", source_ids=[], suite_hash="hash_skewed_123")
    db_session.add(suite_skewed)
    db_session.commit()

    for i in range(10):
        route = "exact" if i < 7 else "semantic"
        item = EvalItem(
            suite_id=suite_skewed.id,
            position=i + 1,
            question=f"Question {i}?",
            item_type="answerable",
            expected_route=route,
        )
        db_session.add(item)
    db_session.commit()

    run_skewed = EvalRun(
        suite_id=suite_skewed.id,
        name="Run Skewed",
        variant={"strategy": "dense", "top_k": 5},
        status="completed",
        config_hash="hash_skewed_123",
        provenance={"git_commit": "abc"},
    )
    db_session.add(run_skewed)
    db_session.commit()

    for item in db_session.query(EvalItem).filter(EvalItem.suite_id == suite_skewed.id).all():
        res = EvalResult(
            run_id=run_skewed.id,
            item_id=item.id,
            route=item.expected_route,
            strategy="dense",
            status="success",
            metrics={"hit@5": 1.0, "recall@5": 1.0, "mrr": 1.0},
        )
        db_session.add(res)
    db_session.commit()

    rep_skewed = generate_run_report(db_session, run_skewed.id)
    comp_skewed = rep_skewed.get("composition", {})
    assert comp_skewed["answerable_by_route"]["exact"] == 7
    assert comp_skewed["answerable_by_route"]["semantic"] == 3
    assert comp_skewed["skew_banner"] is not None
    assert "suite skewed toward exact" in comp_skewed["skew_banner"]

    md_skewed = generate_markdown_scorecard(db_session, [run_skewed.id])
    assert "suite skewed toward exact; strategy comparisons reflect this mix" in md_skewed

    # Create suite 2: exactly 6 exact out of 10 answerable (60% <= 60%) -> NOT skewed
    suite_balanced = EvalSuite(name="Balanced Suite", source_ids=[], suite_hash="hash_bal_123")
    db_session.add(suite_balanced)
    db_session.commit()

    for i in range(10):
        route = "exact" if i < 6 else "semantic"
        item = EvalItem(
            suite_id=suite_balanced.id,
            position=i + 1,
            question=f"Question {i}?",
            item_type="answerable",
            expected_route=route,
        )
        db_session.add(item)
    db_session.commit()

    run_balanced = EvalRun(
        suite_id=suite_balanced.id,
        name="Run Balanced",
        variant={"strategy": "dense", "top_k": 5},
        status="completed",
        config_hash="hash_bal_123",
        provenance={"git_commit": "abc"},
    )
    db_session.add(run_balanced)
    db_session.commit()

    for item in db_session.query(EvalItem).filter(EvalItem.suite_id == suite_balanced.id).all():
        res = EvalResult(
            run_id=run_balanced.id,
            item_id=item.id,
            route=item.expected_route,
            strategy="dense",
            status="success",
            metrics={"hit@5": 1.0, "recall@5": 1.0, "mrr": 1.0},
        )
        db_session.add(res)
    db_session.commit()

    rep_balanced = generate_run_report(db_session, run_balanced.id)
    comp_balanced = rep_balanced.get("composition", {})
    assert comp_balanced["skew_banner"] is None

    md_balanced = generate_markdown_scorecard(db_session, [run_balanced.id])
    assert "suite skewed toward" not in md_balanced


# ── 3. Per-Slice Paired Comparisons ─────────────────────────────────────────

def test_per_slice_paired_comparisons(db_session):
    """Paired comparisons are reported per route slice with sample size n."""
    suite = EvalSuite(name="Slice Comp Suite", source_ids=[], suite_hash="hash_slice_123")
    db_session.add(suite)
    db_session.commit()

    items = []
    for i in range(6):
        route = "semantic" if i < 3 else "exact"
        it = EvalItem(
            suite_id=suite.id,
            position=i + 1,
            question=f"Q {i}?",
            item_type="answerable",
            expected_route=route,
        )
        db_session.add(it)
        items.append(it)
    db_session.commit()

    run_a = EvalRun(suite_id=suite.id, name="Run A", variant={"strategy": "dense"}, status="completed", config_hash="hash_slice_123")
    run_b = EvalRun(suite_id=suite.id, name="Run B", variant={"strategy": "hybrid"}, status="completed", config_hash="hash_slice_123")
    db_session.add_all([run_a, run_b])
    db_session.commit()

    for it in items:
        db_session.add(EvalResult(
            run_id=run_a.id, item_id=it.id, route=it.expected_route,
            strategy="dense", status="success", metrics={"recall@5": 0.8, "precision@5": 0.4, "mrr": 0.8, "hit@5": 1.0}
        ))
        db_session.add(EvalResult(
            run_id=run_b.id, item_id=it.id, route=it.expected_route,
            strategy="hybrid", status="success", metrics={"recall@5": 1.0, "precision@6": 0.6, "mrr": 1.0, "hit@5": 1.0}
        ))
    db_session.commit()

    comp_md = generate_paired_comparison_md(db_session, run_a.id, run_b.id)
    assert "Paired Comparisons per Route Slice" in comp_md
    assert "Route Slice `exact` (n = 3)" in comp_md
    assert "Route Slice `semantic` (n = 3)" in comp_md

    resp = client.get(f"/eval/compare?a={run_a.id}&b={run_b.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "route_slices" in data
    assert "exact" in data["route_slices"]
    assert data["route_slices"]["exact"]["n"] == 3


# ── 4. Non-Atomic Facts Linting ──────────────────────────────────────────────

def test_lint_atomic_facts_failure_and_suggestion(db_session):
    """
    expected_facts must be atomic (a number, a name, or <= 3 tokens).
    Otherwise lint fails with fact_not_atomic and a suggestion.
    """
    suite = EvalSuite(name="Lint Facts Suite", source_ids=[], suite_hash="hash_lint_123")
    db_session.add(suite)
    db_session.commit()

    # Item with atomic facts (numbers, <= 3 tokens)
    item_good = EvalItem(
        suite_id=suite.id,
        position=1,
        question="What is the entitlement?",
        item_type="answerable",
        expected_facts=["20", "24", "40 hours", "$125,000"],
    )
    # Item with non-atomic fact (> 3 tokens and not a number)
    item_bad = EvalItem(
        suite_id=suite.id,
        position=2,
        question="What are the remote work rules?",
        item_type="answerable",
        expected_facts=["employees may work remotely up to two days per week"],
    )
    db_session.add_all([item_good, item_bad])
    db_session.commit()

    lint_res = lint_eval_suite(db_session, suite.id)
    assert lint_res["lint_failed_count"] >= 1

    bad_lint = next(it for it in lint_res["items"] if it["item_id"] == item_bad.id)
    assert bad_lint["lint_failed"] is True
    assert any("fact_not_atomic" in f for f in bad_lint["failures"])
    assert any("suggestion: 'employees may work'" in f for f in bad_lint["failures"])

    good_lint = next(it for it in lint_res["items"] if it["item_id"] == item_good.id)
    assert not any("fact_not_atomic" in f for f in good_lint["failures"])


# ── 5. Dev/Holdout Split Determinism & Immutability ──────────────────────────

def test_split_determinism_stratification_and_immutability(db_session):
    """
    Deterministic hash-based split stratified by item_type.
    Allowed only before the first run (409 if frozen).
    """
    suite = EvalSuite(name="Split Suite", source_ids=[], suite_hash="hash_split_123")
    db_session.add(suite)
    db_session.commit()

    for i in range(10):
        it_type = "answerable" if i < 7 else "unanswerable"
        db_session.add(EvalItem(
            suite_id=suite.id,
            position=i + 1,
            question=f"Q {i}?",
            item_type=it_type,
        ))
    db_session.commit()

    # First split call
    res1 = split_eval_suite(db_session, suite.id, holdout_fraction=0.3, seed=42)
    assert res1["dev_count"] + res1["holdout_count"] == 10
    assert res1["holdout_count"] > 0

    items_run1 = {
        it.id: it.split
        for it in db_session.query(EvalItem).filter(EvalItem.suite_id == suite.id).all()
    }

    # Second split call with same seed -> deterministic identical assignment
    res2 = split_eval_suite(db_session, suite.id, holdout_fraction=0.3, seed=42)
    items_run2 = {
        it.id: it.split
        for it in db_session.query(EvalItem).filter(EvalItem.suite_id == suite.id).all()
    }
    assert items_run1 == items_run2

    # Verify item_type stratification
    holdout_items = db_session.query(EvalItem).filter(
        EvalItem.suite_id == suite.id, EvalItem.split == "holdout"
    ).all()
    holdout_types = {it.item_type for it in holdout_items}
    assert "answerable" in holdout_types

    # Add a run to freeze the suite
    run = EvalRun(suite_id=suite.id, name="Freezer Run", status="completed", config_hash="hash_split_123")
    db_session.add(run)
    db_session.commit()
    assert is_suite_frozen(db_session, suite.id) is True

    # Splitting after first run must return 409 Conflict
    resp = client.post(f"/eval/suites/{suite.id}/split", json={"holdout_fraction": 0.3, "seed": 42})
    assert resp.status_code == 409


# ── 6. Gold Builder API: Item CRUD & Frozen Suite 409 ────────────────────────

def test_gold_builder_crud_and_frozen_suite_409(db_session):
    """
    POST/PUT/DELETE /eval/suites/{id}/items on draft suites.
    409 Conflict when suite is frozen.
    """
    suite = EvalSuite(name="Builder Suite", source_ids=[], suite_hash="hash_builder_123")
    db_session.add(suite)
    db_session.commit()

    # 1. Create item
    post_resp = client.post(
        f"/eval/suites/{suite.id}/items",
        json={
            "question": "What is the policy?",
            "item_type": "answerable",
            "expected_facts": ["24 days"],
            "expected_route": "exact",
        },
    )
    assert post_resp.status_code == 201
    item_id = post_resp.json()["id"]

    # 2. Update item
    put_resp = client.put(
        f"/eval/suites/{suite.id}/items/{item_id}",
        json={"question": "What is the updated policy?"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["question"] == "What is the updated policy?"

    # 3. Freeze suite by adding an EvalRun
    run = EvalRun(suite_id=suite.id, name="Freezer Run", status="completed", config_hash="hash_builder_123")
    db_session.add(run)
    db_session.commit()

    # 4. Attempting POST, PUT, DELETE on frozen suite -> 409
    assert client.post(f"/eval/suites/{suite.id}/items", json={"question": "New?"}).status_code == 409
    assert client.put(f"/eval/suites/{suite.id}/items/{item_id}", json={"question": "Edit?"}).status_code == 409
    assert client.delete(f"/eval/suites/{suite.id}/items/{item_id}").status_code == 409


# ── 7. Verbatim Span and Active Record Validation (422) ──────────────────────

def test_verbatim_span_and_record_validation_422(db_session):
    """
    On item creation, server verifies:
    - Every expected_span occurs verbatim (after normalization) in the corpus.
    - Every row_key exists in active records.
    Otherwise raises 422 Unprocessable Entity.
    """
    source = Source(source_type="file", name="test_doc.pdf")
    db_session.add(source)
    db_session.commit()

    doc = Document(
        source_id=source.id,
        title="Test Document",
        content="Employees are entitled to 24 annual leave days per year.",
        page_number=1,
    )
    rec = Record(
        source_id=source.id,
        row_index=1,
        data={"name": "Alice", "salary": 90000},
        status="active",
    )
    db_session.add_all([doc, rec])
    db_session.commit()

    suite = EvalSuite(name="Validation Suite", source_ids=[source.id], suite_hash="hash_val_123")
    db_session.add(suite)
    db_session.commit()

    # Case A: Valid verbatim span -> 201
    resp_ok = client.post(
        f"/eval/suites/{suite.id}/items",
        json={
            "question": "How many days?",
            "item_type": "answerable",
            "expected_evidence": [{"span": "24 annual leave days per year"}],
        },
    )
    assert resp_ok.status_code == 201

    # Case B: Non-existent span -> 422
    resp_bad_span = client.post(
        f"/eval/suites/{suite.id}/items",
        json={
            "question": "How many days?",
            "item_type": "answerable",
            "expected_evidence": [{"span": "unlimited vacation days without notice"}],
        },
    )
    assert resp_bad_span.status_code == 422
    assert "does not occur verbatim" in resp_bad_span.json()["detail"]

    # Case C: Non-existent row_key -> 422
    resp_bad_key = client.post(
        f"/eval/suites/{suite.id}/items",
        json={
            "question": "Who is employee 99999?",
            "item_type": "answerable",
            "expected_evidence": [{"row_key": "99999"}],
        },
    )
    assert resp_bad_key.status_code == 422
    assert "does not exist in active records" in resp_bad_key.json()["detail"]


# ── 8. Text Units Endpoint ───────────────────────────────────────────────────

def test_source_text_units_endpoint(db_session):
    """GET /eval/sources/{id}/text-units returns stored text units with stable unit_ids."""
    source = Source(source_type="file", name="handbook.pdf")
    db_session.add(source)
    db_session.commit()

    doc = Document(
        source_id=source.id,
        title="Handbook",
        content="Standard hours are 40 hours per week.",
        page_number=3,
    )
    db_session.add(doc)
    db_session.commit()

    resp = client.get(f"/eval/sources/{source.id}/text-units")
    assert resp.status_code == 200
    units = resp.json()
    assert len(units) >= 1
    unit = units[0]
    assert unit["unit_id"] == f"doc_{doc.id}_p3"
    assert unit["page_number"] == 3
    assert "40 hours" in unit["text"]


# ── 9. Holdout Verification & Small-N Status ─────────────────────────────────

def test_holdout_verification_and_small_n_status(db_session):
    """
    Verification of D4/D5 runs on holdout.
    When holdout has < 10 unanswerable or < 15 answerable items, status becomes
    verified_inconclusive_small_n (never verified_improved).
    """
    suite = EvalSuite(name="Doctor Holdout Suite", source_ids=[], suite_hash="hash_doc_123")
    db_session.add(suite)
    db_session.commit()

    # Small sample: 4 answerable items, 2 unanswerable items on holdout
    for i in range(4):
        db_session.add(EvalItem(
            suite_id=suite.id,
            position=i + 1,
            question=f"Answerable {i}?",
            item_type="answerable",
            expected_route="semantic",
            split="holdout",
            reviewed=True,
        ))
    for j in range(2):
        db_session.add(EvalItem(
            suite_id=suite.id,
            position=j + 5,
            question=f"Unanswerable {j}?",
            item_type="unanswerable",
            expected_route="semantic",
            split="holdout",
            reviewed=True,
        ))
    db_session.commit()

    run = EvalRun(
        suite_id=suite.id,
        name="Baseline Run",
        variant={"strategy": "dense", "top_k": 5},
        status="completed",
        config_hash="hash_doc_123",
        include_unreviewed=True,
    )
    db_session.add(run)
    db_session.commit()

    for item in db_session.query(EvalItem).filter(EvalItem.suite_id == suite.id).all():
        db_session.add(EvalResult(
            run_id=run.id,
            item_id=item.id,
            route="semantic",
            strategy="dense",
            status="success",
            metrics={"recall@5": 0.5, "hit@5": 1.0, "false_refusal": 0.0, "unsafe_answer": 0.5},
        ))
    db_session.commit()

    report = DoctorReport(run_ids=[run.id], summary={})
    db_session.add(report)
    db_session.commit()

    finding = DoctorFinding(
        report_id=report.id,
        rule_id="D5",
        severity="critical",
        title="Unsafe Answer Gate Leakage",
        diagnosis="Unsafe rate too high.",
        evidence={"run_id": run.id},
        evidence_level="counterfactual",
        proposed_patch={"min_score": 0.65},
        expected_effect="Filters leakage.",
        cost_note="Zero additional latency or compute cost.",
        status="proposed",
    )
    db_session.add(finding)
    db_session.commit()

    approve_finding(db_session, finding.id)
    apply_finding(db_session, finding.id)

    # Verify finding on holdout -> small n heuristic (< 10 unanswerable, < 15 answerable)
    finding_obj, ver_run = verify_finding(db_session, finding.id)
    assert finding_obj.status == "verified_inconclusive_small_n"
    assert finding.status == "verified_inconclusive_small_n"
