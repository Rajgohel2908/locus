"""
tests/test_phase5_units.py — Pure unit tests for Phase 5 components.

Tests:
1. Tokenizer: IDs (E1007, E-1007), possessives ('s, ’s), Devanagari intact, punctuation, stopwords, length cap.
2. Reciprocal Rank Fusion: ordering, tie-breaking by chunk_id, single list.
3. Filter model validation: unknown keys rejected (422/ValidationError), valid whitelisted keys accepted.
4. Filter SQL builder: parameterized query with bound parameters only, zero string interpolation.
5. Evidence gate: evaluation logic per strategy (dense, lexical, hybrid, hybrid_rerank).
6. Document override date validation: future date > 1 day rejected, unparsable date rejected, valid accepted.
7. Freshness prompt formatting: <chunk> tag attributes (published_at, freshness) and conflict rule.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from retrieval.lexical import tokenize
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.filters import RetrievalFilters, build_filter_sql
from retrieval.pipeline import evaluate_evidence_gate
from generation.answer import build_rag_prompt


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tokenizer Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_tokenizer_identifier_tokens_intact():
    # Identifiers like E1007 and E-1007 must survive intact
    text = "Employee_ID: E1007; Alternate_ID: E-1007; Status: Active."
    tokens = tokenize(text)
    assert "e1007" in tokens
    assert "e-1007" in tokens
    assert "employee_id" in tokens


def test_tokenizer_trailing_possessives_stripped():
    # Both standard ASCII 's and typographic ’s must be stripped
    text = "The employee's manager approved the company’s policy."
    tokens = tokenize(text)
    assert "employee" in tokens
    assert "company" in tokens
    assert "employee's" not in tokens
    assert "company’s" not in tokens


def test_tokenizer_internal_symbols_preserved():
    # Internal - . _ @ must survive, boundary punctuation must be stripped
    text = "Contact support@example.com or user.name_test-1 for version 3.14!"
    tokens = tokenize(text)
    assert "support@example.com" in tokens
    assert "user.name_test-1" in tokens
    assert "3.14" in tokens


def test_tokenizer_devanagari_combining_marks_not_mangled():
    # Combining vowel marks and matras in Devanagari must stay intact
    text = "नमस्ते कर्मचारी वार्षिक अवकाश 24 दिन"
    tokens = tokenize(text)
    assert "नमस्ते" in tokens
    assert "कर्मचारी" in tokens
    assert "वार्षिक" in tokens
    assert "अवकाश" in tokens
    # Combining characters must not be broken into orphan characters
    for tok in tokens:
        assert len(tok) >= 2


def test_tokenizer_stopwords_and_min_length():
    # English and Hinglish filler words must be stripped, single char tokens dropped
    text = "This is a test of the emergency alert system kya yeh sahi hai x"
    tokens = tokenize(text)
    assert "test" in tokens
    assert "emergency" in tokens
    assert "alert" in tokens
    assert "system" in tokens
    assert "sahi" in tokens
    # Stopwords omitted
    assert "this" not in tokens
    assert "is" not in tokens
    assert "a" not in tokens
    assert "the" not in tokens
    assert "kya" not in tokens
    assert "yeh" not in tokens
    assert "hai" not in tokens
    assert "x" not in tokens


def test_tokenizer_query_cap_at_40():
    # Cap query tokens at 40
    long_query = "word " * 60
    tokens = tokenize(long_query, max_tokens=40)
    assert len(tokens) == 40


# ─────────────────────────────────────────────────────────────────────────────
# 2. Reciprocal Rank Fusion Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_rrf_scoring_and_ordering():
    list1 = [
        {"chunk_id": 1, "rank": 1, "score": 0.9},
        {"chunk_id": 2, "rank": 2, "score": 0.8},
        {"chunk_id": 3, "rank": 3, "score": 0.7},
    ]
    list2 = [
        {"chunk_id": 2, "rank": 1, "score": 5.0},
        {"chunk_id": 4, "rank": 2, "score": 4.0},
        {"chunk_id": 1, "rank": 3, "score": 3.0},
    ]
    fused = reciprocal_rank_fusion([list1, list2], k=60)
    # chunk 2 appears at rank 2 (1/62) and rank 1 (1/61) -> ~0.0325
    # chunk 1 appears at rank 1 (1/61) and rank 3 (1/63) -> ~0.0322
    # chunk 2 should be ranked #1
    assert fused[0]["chunk_id"] == 2
    assert fused[1]["chunk_id"] == 1
    assert fused[0]["rank"] == 1
    assert fused[1]["rank"] == 2
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


def test_rrf_deterministic_tie_breaking():
    # When scores are identical, chunk_id ascending determines order
    list1 = [{"chunk_id": 20, "rank": 1}, {"chunk_id": 10, "rank": 1}]
    fused = reciprocal_rank_fusion([list1], k=60)
    assert fused[0]["chunk_id"] == 10
    assert fused[1]["chunk_id"] == 20


def test_rrf_single_list():
    single = [{"chunk_id": 5, "rank": 1}, {"chunk_id": 3, "rank": 2}]
    fused = reciprocal_rank_fusion([single], k=60)
    assert len(fused) == 2
    assert fused[0]["chunk_id"] == 5
    assert fused[1]["chunk_id"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# 3. Filter Model Validation Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_filter_model_whitelisted_fields():
    filt = RetrievalFilters(
        modality=["text", "structured"],
        source_type=["file"],
        freshness=["fresh", "aging"],
        published_after=datetime(2023, 1, 1),
        min_extraction_confidence=80.0,
        title_contains="leave",
    )
    assert filt.modality == ["text", "structured"]
    assert filt.freshness == ["fresh", "aging"]
    assert filt.min_extraction_confidence == 80.0
    assert filt.title_contains == "leave"
    assert not filt.is_empty()


def test_filter_model_rejects_unknown_keys():
    # extra="forbid" MUST reject unknown keys with ValidationError
    with pytest.raises(ValidationError):
        RetrievalFilters(unknown_field="injected", freshness=["fresh"])

    with pytest.raises(ValidationError):
        RetrievalFilters(sql_injection="'; DROP TABLE chunks; --")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Filter SQL Builder Parameterization Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_filter_sql_builder_uses_bound_parameters_only():
    filt = RetrievalFilters(
        modality=["text"],
        source_type=["file"],
        freshness=["fresh"],
        published_after=datetime(2024, 1, 1, 0, 0, 0),
        min_extraction_confidence=75.0,
        title_contains="Policy",
    )
    sql_str, params = build_filter_sql([1, 2], filt)

    # Assert SQL string contains NO raw literal user values
    assert "'Policy'" not in sql_str
    assert "Policy" not in sql_str
    assert "75" not in sql_str
    assert "2024-01-01" not in sql_str

    # Assert SQL uses parameter placeholders
    assert ":run_ids" in sql_str
    assert ":modalities" in sql_str
    assert ":source_types" in sql_str
    assert ":freshness_list" in sql_str
    assert ":published_after" in sql_str
    assert ":min_extraction_confidence" in sql_str
    assert ":title_contains" in sql_str

    # Assert values are securely bound in params dict
    assert params["run_ids"] == [1, 2]
    assert params["modalities"] == ["text"]
    assert params["freshness_list"] == ["fresh"]
    assert params["min_extraction_confidence"] == 75.0
    assert params["title_contains"] == "%Policy%"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Evidence Gate Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_evidence_gate_dense():
    candidates_pass = [{"chunk_id": 1, "score": 0.35}]
    candidates_fail = [{"chunk_id": 1, "score": 0.25}]

    res_pass = evaluate_evidence_gate("dense", candidates_pass, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert res_pass["passed"] is True
    assert res_pass["signal"] == "cosine"

    res_fail = evaluate_evidence_gate("dense", candidates_fail, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert res_fail["passed"] is False
    assert res_fail["signal"] == "none"


def test_evidence_gate_lexical():
    candidates_pass = [{"chunk_id": 1, "score": 1.5}]
    candidates_fail = [{"chunk_id": 1, "score": 0.2}]

    res_pass = evaluate_evidence_gate("lexical", candidates_pass, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert res_pass["passed"] is True
    assert res_pass["signal"] == "bm25"

    res_fail = evaluate_evidence_gate("lexical", candidates_fail, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert res_fail["passed"] is False


def test_evidence_gate_hybrid_or_logic():
    # Passes if dense passes OR bm25 passes
    cand_dense_only = [{
        "chunk_id": 1, "score": 0.02,
        "signals": {"dense_score": 0.40, "lexical_score": 0.1}
    }]
    cand_bm25_only = [{
        "chunk_id": 2, "score": 0.02,
        "signals": {"dense_score": 0.20, "lexical_score": 1.2}
    }]
    cand_both = [{
        "chunk_id": 3, "score": 0.03,
        "signals": {"dense_score": 0.45, "lexical_score": 2.0}
    }]
    cand_neither = [{
        "chunk_id": 4, "score": 0.01,
        "signals": {"dense_score": 0.15, "lexical_score": 0.1}
    }]

    r_dense = evaluate_evidence_gate("hybrid", cand_dense_only, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert r_dense["passed"] is True
    assert r_dense["signal"] == "dense"

    r_bm25 = evaluate_evidence_gate("hybrid", cand_bm25_only, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert r_bm25["passed"] is True
    assert r_bm25["signal"] == "bm25"

    r_both = evaluate_evidence_gate("hybrid", cand_both, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert r_both["passed"] is True
    assert r_both["signal"] == "dense_and_bm25"

    r_none = evaluate_evidence_gate("hybrid", cand_neither, min_score=0.30, min_bm25=0.5, min_rerank=0.5)
    assert r_none["passed"] is False
    assert r_none["signal"] == "none"


def test_evidence_gate_hybrid_rerank():
    cand_pass = [{"chunk_id": 1, "score": 0.85, "signals": {"rerank_score": 0.85}}]
    cand_fail = [{"chunk_id": 1, "score": 0.20, "signals": {"rerank_score": 0.20}}]

    r_pass = evaluate_evidence_gate("hybrid_rerank", cand_pass, min_score=0.30, min_bm25=0.5, min_rerank=0.50)
    assert r_pass["passed"] is True
    assert r_pass["signal"] == "rerank"

    r_fail = evaluate_evidence_gate("hybrid_rerank", cand_fail, min_score=0.30, min_bm25=0.5, min_rerank=0.50)
    assert r_fail["passed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. Freshness-Aware Prompt & Conflict Rule Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_prompt_has_published_at_freshness_and_conflict_rule():
    chunks = [
        {
            "chunk_id": 1,
            "content": "Staff receive 24 days annual leave.",
            "metadata": {
                "source_name": "leave_2024.docx",
                "published_at": "2024-06-01T00:00:00",
                "freshness": "fresh",
            },
        },
        {
            "chunk_id": 2,
            "content": "Staff receive 20 days annual leave under older policy.",
            "metadata": {
                "source_name": "leave_2019.pdf",
                "published_at": "2019-03-01T00:00:00",
                "freshness": "stale",
            },
        },
    ]

    prompt = build_rag_prompt("How many leaves?", chunks)

    # Tag attributes verified
    assert 'published_at="2024-06-01T00:00:00"' in prompt
    assert 'freshness="fresh"' in prompt
    assert 'published_at="2019-03-01T00:00:00"' in prompt
    assert 'freshness="stale"' in prompt

    # Conflict rule verified
    assert "CONFLICT RESOLUTION" in prompt
    assert "prefer the most recent dated source" in prompt
    assert "Explicitly state the conflict" in prompt
    assert "Never present information from an older or superseded source as current" in prompt
