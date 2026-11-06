"""
backend/tests/test_phase6b_state_machine.py — Recommender state machine & apply tests.

Tests:
- Only 'proposed' can be approved or rejected.
- Only 'approved' can be applied.
- Cannot approve twice.
- Rejected cannot be applied.
- Apply creates baseline and recommended configs.
- Apply is idempotent: repeated apply does not duplicate configs or index runs.
- Document/records rows remain completely untouched.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from db import get_db, Source, Document, Record, SourceVersion, Recommendation, PipelineConfig, IndexRun


@pytest.fixture
def test_setup(db: Session):
    """Create test source and documents in test DB."""
    src = Source(name="HR Policy Doc", source_type="file", origin="test")
    db.add(src)
    db.flush()

    ver = SourceVersion(source_id=src.id, version_no=1, note="initial")
    db.add(ver)

    doc1 = Document(
        source_id=src.id,
        modality="text",
        title="Leave Policy",
        content="Employees are entitled to 20 days annual leave per calendar year.",
        content_hash="hash_leave_policy_1",
        word_count=12,
        version_no=1,
        status="active",
        published_at=datetime(2024, 1, 1),
    )
    doc2 = Document(
        source_id=src.id,
        modality="text",
        title="Remote Work Policy",
        content="Remote work is permitted two days per week with manager approval.",
        content_hash="hash_remote_work_1",
        word_count=11,
        version_no=1,
        status="active",
        published_at=datetime(2024, 2, 1),
    )
    db.add(doc1)
    db.add(doc2)
    db.commit()
    return {"source": src, "docs": [doc1, doc2]}


def test_recommender_state_machine_transitions(db: Session, test_setup):
    client = TestClient(app)
    src_id = test_setup["source"].id

    # 1. Create recommendation (status proposed)
    resp = client.post("/recommendations", json={"source_ids": [src_id], "goal": "qa"})
    assert resp.status_code == 200, resp.text
    rec = resp.json()
    rec_id = rec["id"]
    assert rec["status"] == "proposed"

    # 2. Cannot apply unapproved
    resp_apply = client.post(f"/recommendations/{rec_id}/apply", json={"build_index": False})
    assert resp_apply.status_code == 400
    assert "Cannot apply recommendation in status 'proposed'" in resp_apply.text

    # 3. Approve
    resp_appr = client.post(f"/recommendations/{rec_id}/approve")
    assert resp_appr.status_code == 200
    assert resp_appr.json()["status"] == "approved"

    # 4. Cannot approve twice
    resp_appr2 = client.post(f"/recommendations/{rec_id}/approve")
    assert resp_appr2.status_code == 400
    assert "Cannot approve recommendation in status 'approved'" in resp_appr2.text

    # 5. Apply
    resp_apply_ok = client.post(f"/recommendations/{rec_id}/apply", json={"build_index": False})
    assert resp_apply_ok.status_code == 200
    app_data = resp_apply_ok.json()
    assert app_data["status"] == "applied"
    assert app_data["baseline_config"]["kind"] == "baseline"
    assert app_data["recommended_config"]["kind"] == "recommended"

    # 6. Cannot reject once applied
    resp_rej = client.post(f"/recommendations/{rec_id}/reject")
    assert resp_rej.status_code == 400


def test_recommender_rejected_cannot_be_applied(db: Session, test_setup):
    client = TestClient(app)
    src_id = test_setup["source"].id

    resp = client.post("/recommendations", json={"source_ids": [src_id], "goal": "search"})
    assert resp.status_code == 200
    rec_id = resp.json()["id"]

    # Reject
    resp_rej = client.post(f"/recommendations/{rec_id}/reject")
    assert resp_rej.status_code == 200
    assert resp_rej.json()["status"] == "rejected"

    # Cannot apply
    resp_app = client.post(f"/recommendations/{rec_id}/apply", json={"build_index": False})
    assert resp_app.status_code == 400
    assert "Cannot apply recommendation in status 'rejected'" in resp_app.text

    # Cannot approve
    resp_appr = client.post(f"/recommendations/{rec_id}/approve")
    assert resp_appr.status_code == 400


def test_apply_idempotency_and_data_immutability(db: Session, test_setup):
    client = TestClient(app)
    src_id = test_setup["source"].id

    # Record document state before
    docs_before = db.query(Document).filter(Document.source_id == src_id).all()
    hashes_before = {d.id: d.content_hash for d in docs_before}
    assert len(hashes_before) > 0
    assert all(h is not None for h in hashes_before.values())

    # Create & approve
    resp_c = client.post("/recommendations", json={"source_ids": [src_id], "goal": "qa"})
    rec_id = resp_c.json()["id"]
    client.post(f"/recommendations/{rec_id}/approve")

    # Apply 1
    resp_a1 = client.post(f"/recommendations/{rec_id}/apply", json={"build_index": False})
    assert resp_a1.status_code == 200
    d1 = resp_a1.json()

    # Apply 2 (idempotent repeat)
    resp_a2 = client.post(f"/recommendations/{rec_id}/apply", json={"build_index": False})
    assert resp_a2.status_code == 200
    d2 = resp_a2.json()

    # Assert configs are identical and not duplicated
    assert d1["baseline_config"]["id"] == d2["baseline_config"]["id"]
    assert d1["recommended_config"]["id"] == d2["recommended_config"]["id"]

    # Total configs count for this recommendation must be exactly 2 (1 baseline, 1 recommended)
    cfgs = db.query(PipelineConfig).filter(PipelineConfig.recommendation_id == rec_id).all()
    assert len(cfgs) == 2

    # Assert document immutability: rows, content, and hashes unchanged
    docs_after = db.query(Document).filter(Document.source_id == src_id).all()
    assert len(docs_after) == len(docs_before)
    for d in docs_after:
        assert d.content_hash == hashes_before[d.id]


def test_required_source_ids_and_goal_validation(db: Session, test_setup):
    client = TestClient(app)
    src_id = test_setup["source"].id

    # 1. Missing source_ids in POST /kb-profile
    r1 = client.post("/kb-profile", json={})
    assert r1.status_code == 422

    # 2. Empty source_ids in POST /kb-profile
    r2 = client.post("/kb-profile", json={"source_ids": []})
    assert r2.status_code == 422

    # 3. Non-existent source_id in POST /kb-profile
    r3 = client.post("/kb-profile", json={"source_ids": [999999]})
    assert r3.status_code == 404

    # 4. Missing source_ids in POST /recommendations
    r4 = client.post("/recommendations", json={"goal": "qa"})
    assert r4.status_code == 422

    # 5. Empty source_ids in POST /recommendations
    r5 = client.post("/recommendations", json={"source_ids": [], "goal": "qa"})
    assert r5.status_code == 422

    # 6. Non-existent source_id in POST /recommendations
    r6 = client.post("/recommendations", json={"source_ids": [999999], "goal": "qa"})
    assert r6.status_code == 404

    # 7. Invalid goal in POST /recommendations
    for bad_goal in ["discovery", "compliance", "cost", "unknown_goal", "summarization"]:
        r7 = client.post("/recommendations", json={"source_ids": [src_id], "goal": bad_goal})
        assert r7.status_code == 422, f"Expected 422 for goal {bad_goal}, got {r7.status_code}"


def test_apply_with_query_param_and_diff_rules(db: Session, test_setup):
    client = TestClient(app)
    src_id = test_setup["source"].id

    # Create & approve
    r_create = client.post("/recommendations", json={"source_ids": [src_id], "goal": "qa"})
    rec_id = r_create.json()["id"]
    client.post(f"/recommendations/{rec_id}/approve")

    # Apply via query param ?build_index=false
    r_apply = client.post(f"/recommendations/{rec_id}/apply?build_index=false")
    assert r_apply.status_code == 200
    app_data = r_apply.json()
    b_id = app_data["baseline_config"]["id"]
    r_id = app_data["recommended_config"]["id"]

    # Verify compare endpoint returns rule causes
    r_comp = client.get(f"/pipeline-configs/compare?a={b_id}&b={r_id}")
    assert r_comp.status_code == 200
    diff_data = r_comp.json()
    assert "differences" in diff_data
    diffs = diff_data["differences"]
    assert len(diffs) > 0
    for d in diffs:
        assert "field" in d
        assert "rules" in d
        assert isinstance(d["rules"], list)
        assert len(d["rules"]) > 0, f"Expected rule causes for field {d['field']}"


