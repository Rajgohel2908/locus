"""
backend/tests/test_phase6b_graph.py — Pipeline graph and config comparison tests.

Tests:
- Every edge references existing nodes.
- No orphan nodes.
- Disabled nodes carry a reason.
- Mermaid graph is valid, deterministic, and contains every node id.
- GET /pipeline-configs/compare returns field-by-field diff with rule causes.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from db import PipelineConfig
from recommender.rules import get_baseline_spec, compute_spec_hash
from recommender.graph import build_pipeline_graph, render_mermaid_graph


@pytest.fixture
def mock_configs(db: Session):
    b_spec = get_baseline_spec()
    b_cfg = PipelineConfig(
        name="Phase 4 Baseline",
        kind="baseline",
        source_ids=[101],
        spec=b_spec,
        spec_hash=compute_spec_hash(b_spec),
        index_runs={"101": 501},
    )

    r_spec = {
        "chunk_size": 500,
        "chunk_overlap": 75,
        "strategy_default": "hybrid",
        "use_rerank": True,
        "top_k": 8,
        "candidates_n": 20,
        "filters_default": {"min_extraction_confidence": 60},
        "structured_route_enabled": True,
        "router_enabled": True,
        "suggested_filters": {"freshness": ["fresh", "aging", "unknown"]},
        "notes": [],
        "basis": "rule-based priors, not validated; compare with evaluation in Phase 7",
    }
    r_cfg = PipelineConfig(
        name="Recommended (comparison)",
        kind="recommended",
        source_ids=[101],
        spec=r_spec,
        spec_hash=compute_spec_hash(r_spec),
        index_runs={"101": 502},
    )

    db.add(b_cfg)
    db.add(r_cfg)
    db.commit()
    db.refresh(b_cfg)
    db.refresh(r_cfg)
    return {"baseline": b_cfg, "recommended": r_cfg}


def test_pipeline_graph_json_structure(db: Session, mock_configs):
    for cfg in (mock_configs["baseline"], mock_configs["recommended"]):
        graph = build_pipeline_graph(db, cfg)
        node_ids = {n["id"] for n in graph["nodes"]}
        edge_nodes = set()

        # 1. Every edge references existing nodes
        for e in graph["edges"]:
            assert e["from"] in node_ids, f"Edge source {e['from']} not in nodes"
            assert e["to"] in node_ids, f"Edge target {e['to']} not in nodes"
            edge_nodes.add(e["from"])
            edge_nodes.add(e["to"])

        # 2. No orphan nodes (every node appears in at least one edge)
        for n in graph["nodes"]:
            assert n["id"] in edge_nodes, f"Orphan node found: {n['id']}"

            # 3. Disabled nodes carry a reason
            if not n["enabled"]:
                assert n.get("reason"), f"Disabled node {n['id']} has no reason"

            # 4. Built-in phase and status
            assert n.get("built_in_phase"), f"Node {n['id']} missing built_in_phase"
            assert n.get("status") in ("built", "planned"), f"Node {n['id']} invalid status"


def test_pipeline_graph_mermaid_rendering(db: Session, mock_configs):
    for cfg in (mock_configs["baseline"], mock_configs["recommended"]):
        graph = build_pipeline_graph(db, cfg)
        m1 = render_mermaid_graph(graph)
        m2 = render_mermaid_graph(graph)

        # Deterministic
        assert m1 == m2
        assert m1.startswith("flowchart TD")

        # Contains every node id
        for n in graph["nodes"]:
            assert n["id"] in m1, f"Mermaid output missing node id: {n['id']}"

        # Disabled styling applied
        assert "classDef disabled" in m1


def test_pipeline_config_compare_endpoint(db: Session, mock_configs):
    client = TestClient(app)
    b_id = mock_configs["baseline"].id
    r_id = mock_configs["recommended"].id

    resp = client.get(f"/pipeline-configs/compare?a={b_id}&b={r_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["config_a"]["id"] == b_id
    assert data["config_b"]["id"] == r_id

    diff_map = {d["field"]: d for d in data["differences"]}
    assert "chunk_size" in diff_map
    assert diff_map["chunk_size"]["a"] == 800
    assert diff_map["chunk_size"]["b"] == 500
    assert "R6" in diff_map["chunk_size"]["rules"]

    assert "strategy_default" in diff_map
    assert diff_map["strategy_default"]["a"] == "dense"
    assert diff_map["strategy_default"]["b"] == "hybrid"

    assert "use_rerank" in diff_map
    assert diff_map["use_rerank"]["a"] is False
    assert diff_map["use_rerank"]["b"] is True

    assert "top_k" in diff_map
    assert diff_map["top_k"]["a"] == 5
    assert diff_map["top_k"]["b"] == 8
    assert "R12" in diff_map["top_k"]["rules"]

