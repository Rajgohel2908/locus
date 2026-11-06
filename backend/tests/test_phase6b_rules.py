"""
backend/tests/test_phase6b_rules.py — Table-driven rule tests for Phase 6B recommender.

Tests:
- R1 structured_present: at, below, and above thresholds (numeric cols, active rows)
- R2 identifier_present: identifier column present vs absent
- R3 tiny_corpus: chunks < 30 vs >= 30
- R4 default_text: chunks >= 30
- R5 rerank_policy: goal in (qa, comparison) and chunks >= 50 vs < 50 or other goals
- R6 chunk_sizing: avg words < 300, 300-1500, > 1500 (boundaries 299, 300, 1500, 1501)
- R7 stale_content: stale share 0.19, 0.20, 0.21
- R8 undated_documents: undated share 0.49, 0.50, 0.51
- R9 ocr_quality: OCR share 0.29, 0.30; mean confidence 69.9, 70.0
- R10 non_latin_script: non-Latin share 0.19, 0.20, 0.21; script detection fixtures
- R11 uncleaned_data: v1 with duplicates/pending vs v1 clean vs v2
- R12 goal_adjustments: qa, search, comparison, analysis; invalid goal raises ValueError
"""

import pytest
from recommender.rules import (
    evaluate_rules,
    get_baseline_spec,
    compute_spec_hash,
    RULES_VERSION,
    RECOMMENDER_THRESHOLDS,
)
from recommender.profile import compute_script_shares


def _base_profile():
    return {
        "source_ids": [1],
        "sources": {"total": 1, "by_type": {"file": 1, "web": 0, "structured": 0}},
        "documents": {"total": 10, "total_records": 0, "total_chunks": 40, "avg_words_per_doc": 500.0},
        "structured": {
            "columns": {},
            "numeric_columns": [],
            "numeric_columns_count": 0,
            "identifier_columns": [],
            "identifier_columns_count": 0,
            "active_row_count": 0,
        },
        "text": {
            "freshness_distribution": {"fresh": 10, "aging": 0, "stale": 0, "unknown": 0},
            "dated_count": 10,
            "stale_share": 0.0,
            "undated_share": 0.0,
            "near_duplicate_pairs": [],
            "near_duplicate_count": 0,
            "injection_suspects_count": 0,
            "short_documents_count": 0,
            "ocr_share": 0.0,
            "mean_extraction_confidence": 100.0,
        },
        "scripts": {
            "total_chars": 1000,
            "latin_share": 1.0,
            "devanagari_share": 0.0,
            "gujarati_share": 0.0,
            "other_share": 0.0,
            "non_latin_share": 0.0,
        },
        "quality_state": {
            "latest_version_no": 1,
            "duplicate_rows": 0,
            "pending_critical_proposals": 0,
        },
    }


# ── R1: structured_present ───────────────────────────────────────────────────

@pytest.mark.parametrize("struct_count,num_cols,rows,expected_fired", [
    (0, 2, 50, False),  # No structured source
    (1, 0, 50, False),  # Below numeric threshold (0 < 1)
    (1, 1, 9, False),   # Below active rows threshold (9 < 10)
    (1, 1, 10, True),   # Exactly at boundary (1 col, 10 rows)
    (1, 3, 200, True),  # Well above boundary
])
def test_r1_structured_present(struct_count, num_cols, rows, expected_fired):
    p = _base_profile()
    p["sources"]["by_type"]["structured"] = struct_count
    p["structured"]["numeric_columns_count"] = num_cols
    p["structured"]["active_row_count"] = rows
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R1" in fired_ids) == expected_fired
    assert res["pipeline_spec"]["structured_route_enabled"] == expected_fired


# ── R2: identifier_present ───────────────────────────────────────────────────

def test_r2_identifier_present():
    p = _base_profile()
    p["structured"]["identifier_columns"] = ["employee_id"]
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert "R2" in fired_ids
    assert res["pipeline_spec"]["strategy_default"] == "hybrid"
    assert any("Exact-ID" in note for note in res["pipeline_spec"]["notes"])

    # Without identifier
    p2 = _base_profile()
    p2["structured"]["identifier_columns"] = []
    res2 = evaluate_rules(p2, goal="qa")
    not_fired_ids = [r["id"] for r in res2["rules_not_fired"]]
    assert "R2" in not_fired_ids


# ── R3 & R4: tiny_corpus vs default_text ─────────────────────────────────────

@pytest.mark.parametrize("chunks,expected_r3,expected_r4,expected_strat", [
    (10, True, False, "dense"),
    (29, True, False, "dense"),
    (30, False, True, "hybrid"),
    (100, False, True, "hybrid"),
])
def test_r3_r4_corpus_size_boundaries(chunks, expected_r3, expected_r4, expected_strat):
    p = _base_profile()
    p["documents"]["total_chunks"] = chunks
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R3" in fired_ids) == expected_r3
    assert ("R4" in fired_ids) == expected_r4
    assert res["pipeline_spec"]["strategy_default"] == expected_strat


# ── R5: rerank_policy ────────────────────────────────────────────────────────

@pytest.mark.parametrize("goal,chunks,expected_rerank", [
    ("qa", 49, False),         # Boundary below (49 < 50)
    ("qa", 50, True),          # Boundary exactly (50 >= 50)
    ("qa", 100, True),         # Above
    ("comparison", 50, True),  # Comparison at 50
    ("comparison", 49, False), # Comparison below 50
    ("search", 100, False),    # Search never reranks
    ("analysis", 100, False),  # Analysis never reranks
])
def test_r5_rerank_policy(goal, chunks, expected_rerank):
    p = _base_profile()
    p["documents"]["total_chunks"] = chunks
    res = evaluate_rules(p, goal=goal)
    assert res["pipeline_spec"]["use_rerank"] == expected_rerank


# ── R6: chunk_sizing ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("avg_words,expected_size,expected_overlap", [
    (150.0, 500, 75),
    (299.9, 500, 75),
    (300.0, 800, 120),
    (750.0, 800, 120),
    (1500.0, 800, 120),
    (1500.1, 1000, 150),
    (2500.0, 1000, 150),
])
def test_r6_chunk_sizing_boundaries(avg_words, expected_size, expected_overlap):
    p = _base_profile()
    p["documents"]["avg_words_per_doc"] = avg_words
    res = evaluate_rules(p, goal="qa")
    assert res["pipeline_spec"]["chunk_size"] == expected_size
    assert res["pipeline_spec"]["chunk_overlap"] == expected_overlap


# ── R7: stale_content ────────────────────────────────────────────────────────

@pytest.mark.parametrize("stale_share,dated_count,expected_fired", [
    (0.19, 10, False),
    (0.20, 10, True),
    (0.50, 10, True),
    (0.50, 0, False),  # No dated items
])
def test_r7_stale_content(stale_share, dated_count, expected_fired):
    p = _base_profile()
    p["text"]["dated_count"] = dated_count
    p["text"]["stale_share"] = stale_share
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R7" in fired_ids) == expected_fired
    if expected_fired:
        assert res["pipeline_spec"]["suggested_filters"].get("freshness") == ["fresh", "aging", "unknown"]
        assert len(res["warnings"]) > 0


# ── R8: undated_documents ────────────────────────────────────────────────────

@pytest.mark.parametrize("undated_share,total_docs,expected_fired", [
    (0.49, 10, False),
    (0.50, 10, True),
    (0.75, 10, True),
    (0.75, 0, False),
])
def test_r8_undated_documents(undated_share, total_docs, expected_fired):
    p = _base_profile()
    p["documents"]["total"] = total_docs
    p["text"]["undated_share"] = undated_share
    p["text"]["freshness_distribution"]["unknown"] = int(undated_share * total_docs)
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R8" in fired_ids) == expected_fired


# ── R9: ocr_quality ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("ocr_share,mean_conf,expected_fired", [
    (0.29, 70.0, False),
    (0.30, 70.0, True),
    (0.10, 69.9, True),
    (0.50, 60.0, True),
])
def test_r9_ocr_quality(ocr_share, mean_conf, expected_fired):
    p = _base_profile()
    p["text"]["ocr_share"] = ocr_share
    p["text"]["mean_extraction_confidence"] = mean_conf
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R9" in fired_ids) == expected_fired
    if expected_fired:
        assert res["pipeline_spec"]["filters_default"].get("min_extraction_confidence") == 60


# ── R10: non_latin_script & Script Detection ─────────────────────────────────

@pytest.mark.parametrize("non_latin_share,expected_fired", [
    (0.19, False),
    (0.20, True),
    (0.50, True),
])
def test_r10_non_latin_script(non_latin_share, expected_fired):
    p = _base_profile()
    p["scripts"]["non_latin_share"] = non_latin_share
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R10" in fired_ids) == expected_fired


def test_script_detection_fixtures():
    # Latin fixture
    latin_text = ["Employee policy handbook. Leave entitlement is 24 days per year."]
    res_lat = compute_script_shares(latin_text)
    assert res_lat["latin_share"] > 0.95
    assert res_lat["non_latin_share"] < 0.05

    # Devanagari fixture
    dev_text = ["कर्मचारी नीति विवरण। वार्षिक अवकाश २४ दिन हैं।"]
    res_dev = compute_script_shares(dev_text)
    assert res_dev["devanagari_share"] > 0.80
    assert res_dev["non_latin_share"] > 0.80

    # Gujarati fixture
    guj_text = ["કર્મચારી નીતિ પુસ્તિકા. વાર્ષિક રજાઓ ૨૪ દિવસ છે."]
    res_guj = compute_script_shares(guj_text)
    assert res_guj["gujarati_share"] > 0.80
    assert res_guj["non_latin_share"] > 0.80


# ── R11: uncleaned_data ──────────────────────────────────────────────────────

@pytest.mark.parametrize("ver,dups,crits,expected_fired", [
    (1, 5, 0, True),
    (1, 0, 2, True),
    (1, 0, 0, False),  # v1 with no issues
    (2, 5, 2, False),  # v2 is cleaned
])
def test_r11_uncleaned_data(ver, dups, crits, expected_fired):
    p = _base_profile()
    p["quality_state"]["latest_version_no"] = ver
    p["quality_state"]["duplicate_rows"] = dups
    p["quality_state"]["pending_critical_proposals"] = crits
    res = evaluate_rules(p, goal="qa")
    fired_ids = [r["id"] for r in res["rules_fired"]]
    assert ("R11" in fired_ids) == expected_fired


# ── R12: goal_adjustments & Goal Validation ──────────────────────────────────

def test_r12_goal_adjustments():
    p = _base_profile()

    # qa
    res_qa = evaluate_rules(p, goal="qa")
    assert res_qa["pipeline_spec"]["top_k"] == 5

    # search
    res_search = evaluate_rules(p, goal="search")
    assert res_search["pipeline_spec"]["top_k"] == 10
    assert res_search["pipeline_spec"]["use_rerank"] is False

    # comparison
    res_comp = evaluate_rules(p, goal="comparison")
    assert res_comp["pipeline_spec"]["top_k"] == 8

    # analysis
    res_analysis = evaluate_rules(p, goal="analysis")
    assert res_analysis["pipeline_spec"]["top_k"] == 5
    assert any("Goal is analysis but no structured source" in w for w in res_analysis["warnings"])

    # Invalid goal
    with pytest.raises(ValueError) as exc:
        evaluate_rules(p, goal="summarization")
    assert "Invalid goal 'summarization'" in str(exc.value)


def test_baseline_spec_and_hash():
    base = get_baseline_spec()
    assert base["strategy_default"] == "dense"
    assert base["router_enabled"] is False
    assert base["structured_route_enabled"] is False
    assert base.get("chunk_unit") == "characters"

    h1 = compute_spec_hash(base)
    h2 = compute_spec_hash(base)
    assert h1 == h2
    assert len(h1) == 16


def test_goal_validation_allowed_and_rejected():
    p = _base_profile()
    for valid_goal in ["qa", "search", "comparison", "analysis"]:
        res = evaluate_rules(p, goal=valid_goal)
        assert res["goal"] == valid_goal

    for invalid_goal in ["discovery", "compliance", "cost", "summarization", "other", ""]:
        with pytest.raises(ValueError) as exc:
            evaluate_rules(p, goal=invalid_goal)
        assert f"Invalid goal '{invalid_goal}'" in str(exc.value)


def test_no_unrequested_behavior_keys_in_specs():
    p = _base_profile()
    res = evaluate_rules(p, goal="qa")
    rec_spec = res["pipeline_spec"]
    base_spec = get_baseline_spec()

    forbidden_keys = [
        "freshness_boost_enabled",
        "freshness_boost_weight",
        "embed_model",
        "model_switch",
        "comparison_guidance",
        "evidence_threshold",
    ]

    for key in forbidden_keys:
        assert key not in rec_spec, f"Found unrequested key '{key}' in recommended pipeline_spec"
        assert key not in base_spec, f"Found unrequested key '{key}' in baseline pipeline_spec"

    assert rec_spec.get("chunk_unit") == "characters"
    assert base_spec.get("chunk_unit") == "characters"


