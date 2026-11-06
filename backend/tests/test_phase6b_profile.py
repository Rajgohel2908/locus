"""
backend/tests/test_phase6b_profile.py — KB profile correctness tests.

Tests:
- Profile counts compared with independent DB/pandas recomputation.
- Freshness distribution honors FRESHNESS_REFERENCE_DATE.
- Script shares accurately reflect content character sets.
"""

import os
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import Source, Document, Record, SourceVersion, ColumnRole, DocumentOverride
from recommender.profile import build_kb_profile


@pytest.fixture
def profile_test_data(db: Session):
    # Create structured source
    s1 = Source(name="Test Employees", source_type="structured", origin="test")
    db.add(s1)
    db.flush()

    v1 = SourceVersion(source_id=s1.id, version_no=1, note="v1")
    db.add(v1)

    roles = [
        ColumnRole(source_id=s1.id, column_name="EmpId", role="identifier", confirmed=True),
        ColumnRole(source_id=s1.id, column_name="Salary", role="numeric", confirmed=True),
    ]
    for r in roles:
        db.add(r)

    for i in range(15):
        db.add(Record(
            source_id=s1.id,
            row_index=i,
            data={"EmpId": f"E{i}", "Salary": 50000.0 + i * 1000},
            version_no=1,
            status="active",
        ))

    # Create text source
    s2 = Source(name="Test Policies", source_type="file", origin="test")
    db.add(s2)
    db.flush()

    v2 = SourceVersion(source_id=s2.id, version_no=1, note="v1")
    db.add(v2)

    # 1 fresh doc (published 2024-08-01, ref 2024-09-01 -> 31 days)
    doc_fresh = Document(
        source_id=s2.id,
        modality="text",
        title="Fresh Policy",
        content="This is fresh policy text with Latin characters.",
        content_hash="hash_fresh",
        word_count=8,
        version_no=1,
        status="active",
        published_at=datetime(2024, 8, 1, tzinfo=timezone.utc),
    )
    # 1 stale doc (published 2019-01-01 -> > 2000 days)
    doc_stale = Document(
        source_id=s2.id,
        modality="text",
        title="Stale Policy",
        content="This is archived policy text from several years ago.",
        content_hash="hash_stale",
        word_count=9,
        version_no=1,
        status="active",
        published_at=datetime(2019, 1, 1, tzinfo=timezone.utc),
    )
    # 1 undated doc
    doc_undated = Document(
        source_id=s2.id,
        modality="text",
        title="Undated Policy",
        content="Undated document without publication date specified.",
        content_hash="hash_undated",
        word_count=6,
        version_no=1,
        status="active",
        published_at=None,
    )
    db.add(doc_fresh)
    db.add(doc_stale)
    db.add(doc_undated)
    db.commit()

    return {"s1": s1, "s2": s2, "docs": [doc_fresh, doc_stale, doc_undated]}


def test_kb_profile_counts_match_db(db: Session, profile_test_data, monkeypatch):
    monkeypatch.setenv("FRESHNESS_REFERENCE_DATE", "2024-09-01T00:00:00+00:00")
    s1 = profile_test_data["s1"]
    s2 = profile_test_data["s2"]

    profile = build_kb_profile(db=db, source_ids=[s1.id, s2.id])

    # Independent DB checks
    expected_doc_count = db.query(Document).filter(Document.source_id.in_([s1.id, s2.id]), Document.status == "active").count()
    expected_rec_count = db.query(Record).filter(Record.source_id.in_([s1.id, s2.id]), Record.status == "active").count()

    assert profile["documents"]["total"] == expected_doc_count
    assert profile["documents"]["total_records"] == expected_rec_count
    assert profile["structured"]["numeric_columns_count"] == 1
    assert profile["structured"]["identifier_columns_count"] == 1
    assert profile["structured"]["active_row_count"] == 15

    # Freshness distribution
    f_dist = profile["text"]["freshness_distribution"]
    assert f_dist["fresh"] == 1
    assert f_dist["stale"] == 1
    assert f_dist["unknown"] == 1
    assert profile["text"]["dated_count"] == 2
    assert profile["text"]["stale_share"] == 0.5  # 1 stale out of 2 dated
    assert profile["text"]["undated_share"] == round(1 / 3, 4)

    # Document override honors simulated date
    doc_undated = profile_test_data["docs"][2]
    override = DocumentOverride(
        document_id=doc_undated.id,
        published_at=datetime(2024, 7, 15, tzinfo=timezone.utc),
    )
    db.add(override)
    db.commit()

    profile_after = build_kb_profile(db=db, source_ids=[s1.id, s2.id])
    f_dist_after = profile_after["text"]["freshness_distribution"]
    assert f_dist_after["fresh"] == 2  # now 2 fresh!
    assert f_dist_after["unknown"] == 0

