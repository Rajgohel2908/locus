"""
tests/test_eval_matching.py — Unit tests for Phase 7 pure evidence matching.
"""

import pytest
from evaluation.matching import (
    normalize_text,
    tokenize,
    chunk_matches_span,
    union_covers_span,
    match_retrieved_chunk,
)


def test_normalize_text():
    raw = "  Hello, World! This is a test... With \t tabs \n and newlines.  "
    norm = normalize_text(raw)
    assert norm == "hello world this is a test with tabs and newlines"


def test_tokenize():
    tokens = tokenize("Annual Leave Policy (2024): 25 days.")
    assert tokens == ["annual", "leave", "policy", "2024", "25", "days"]


def test_chunk_matches_span_exact_and_partial():
    span = "Employees are entitled to 25 days of annual leave per calendar year."
    
    # 1. Exact match in a larger chunk
    chunk_exact = "Under Section 3, employees are entitled to 25 days of annual leave per calendar year. Approvals must come from HR."
    is_rel, overlap = chunk_matches_span(chunk_exact, span)
    assert is_rel is True
    assert overlap == 1.0

    # 2. 80%+ overlap: 10 out of 11 tokens present (90.9%)
    chunk_partial_high = "Employees are entitled to 25 days of annual leave per calendar period."
    is_rel, overlap = chunk_matches_span(chunk_partial_high, span)
    assert is_rel is True
    assert overlap >= 0.80

    # 3. Under 80% overlap: only 7 out of 11 tokens present (63.6%)
    chunk_partial_low = "Employees get annual leave per calendar year."
    is_rel, overlap = chunk_matches_span(chunk_partial_low, span)
    assert is_rel is False
    assert overlap < 0.80


def test_chunk_matches_span_row_key():
    span = "Department Engineering Salary 120000"
    chunk_with_key = "Employee E1007 Department Engineering Salary 120000 Active"
    chunk_without_key = "Employee E9999 Department Engineering Salary 120000 Active"

    # With row_key present and in chunk -> matches
    is_rel, _ = chunk_matches_span(chunk_with_key, span, row_key="E1007")
    assert is_rel is True

    # With row_key present but NOT in chunk -> fails even if span tokens match
    is_rel, _ = chunk_matches_span(chunk_without_key, span, row_key="E1007")
    assert is_rel is False


def test_span_split_across_two_chunks():
    """
    Verify that when a gold span is fractured across two consecutive chunks:
    neither chunk meets the 80% threshold individually, but union_covers_span passes.
    """
    span = "The maximum carryover of unused annual leave into the subsequent calendar year is capped strictly at five days."
    # 17 tokens
    
    # Chunk 1 contains first 9 tokens (52.9%)
    chunk1 = "Regarding vacations: the maximum carryover of unused annual leave into the subsequent"
    # Chunk 2 contains remaining 8 tokens (47.1%)
    chunk2 = "calendar year is capped strictly at five days. Excess leave will lapse automatically."

    # Individually neither matches
    rel1, ov1 = chunk_matches_span(chunk1, span)
    rel2, ov2 = chunk_matches_span(chunk2, span)
    assert rel1 is False
    assert rel2 is False
    assert ov1 < 0.80
    assert ov2 < 0.80

    # Union covers span
    union_cov, union_ov = union_covers_span([chunk1, chunk2], span)
    assert union_cov is True
    assert union_ov == 1.0


def test_match_retrieved_chunk_helper():
    expected_evidence = [
        {"span": "Working hours are 9:00 AM to 5:00 PM Monday through Friday."},
        {"span": "Employees must punch in using the biometric scanner.", "row_key": None},
    ]

    chunk = "Daily schedule: working hours are 9:00 AM to 5:00 PM Monday through Friday without exception."
    is_rel, matched = match_retrieved_chunk(chunk, expected_evidence)
    assert is_rel is True
    assert len(matched) == 1
    assert "Working hours" in matched[0]

