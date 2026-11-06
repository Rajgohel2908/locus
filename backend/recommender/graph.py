"""
backend/recommender/graph.py — Pipeline graph generation in JSON and Mermaid formats.

Generates deterministic nodes and edges representing the ingestion, chunking,
retrieval, routing, generation, and guardrail lifecycle of a pipeline config.
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
import config
from db import Source, SourceVersion, CleaningProposal


def build_pipeline_graph(
    db: Session,
    pipeline_config_row: Any,
) -> Dict[str, Any]:
    """
    Build JSON structure of the pipeline graph.
    Nodes:
    - data_source (per source: type, version used)
    - parser
    - quality_profiler
    - cleaner (version, approved proposals count)
    - chunker (config)
    - embedder (model, dim)
    - vector_store (pgvector HNSW)
    - router (rules version, enabled)
    - structured_executor (enabled)
    - retriever (strategy default and per-route mapping)
    - reranker (enabled or disabled)
    - llm (provider and model read from config; nothing hardcoded)
    - guardrails (evidence gate thresholds, citation validation, untrusted-chunk boundary)
    - evaluator (status "planned", Phase 7)
    """
    spec = pipeline_config_row.spec or {}
    source_ids = pipeline_config_row.source_ids or []
    sources = db.query(Source).filter(Source.id.in_(source_ids)).all() if source_ids else []

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Data Sources
    source_node_ids = []
    for s in sources:
        latest_ver = (
            db.query(SourceVersion.version_no)
            .filter(SourceVersion.source_id == s.id)
            .order_by(SourceVersion.version_no.desc())
            .first()
        )
        ver_no = latest_ver[0] if latest_ver else 1
        node_id = f"data_source_{s.id}"
        source_node_ids.append(node_id)
        nodes.append({
            "id": node_id,
            "type": "data_source",
            "label": f"Source {s.id}: {s.name} ({s.source_type or 'file'})",
            "config": {
                "source_id": s.id,
                "name": s.name,
                "source_type": s.source_type or "file",
                "version": ver_no,
            },
            "enabled": True,
            "reason": "default",
            "built_in_phase": "Phase 2",
            "status": "built",
        })

    if not source_node_ids:
        # Default placeholder source if no source IDs
        nodes.append({
            "id": "data_source_default",
            "type": "data_source",
            "label": "Data Sources",
            "config": {"source_ids": source_ids},
            "enabled": True,
            "reason": "default",
            "built_in_phase": "Phase 2",
            "status": "built",
        })
        source_node_ids = ["data_source_default"]

    # 2. Parser
    nodes.append({
        "id": "parser",
        "type": "parser",
        "label": "Parser Engine",
        "config": {"supported_formats": ["pdf", "docx", "csv", "image", "html"]},
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 1",
        "status": "built",
    })
    for sid in source_node_ids:
        edges.append({"from": sid, "to": "parser", "label": "raw content"})

    # 3. Quality Profiler
    nodes.append({
        "id": "quality_profiler",
        "type": "quality_profiler",
        "label": "Quality Profiler",
        "config": {
            "heuristics": ["exact_dup", "near_dup", "freshness", "injection", "short_content"],
        },
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 1",
        "status": "built",
    })
    edges.append({"from": "parser", "to": "quality_profiler", "label": "parsed docs/records"})

    # 4. Cleaner
    approved_count = 0
    if source_ids:
        approved_count = (
            db.query(CleaningProposal)
            .filter(
                CleaningProposal.source_id.in_(source_ids),
                CleaningProposal.status.in_(["approved", "applied"]),
            )
            .count()
        )
    nodes.append({
        "id": "cleaner",
        "type": "cleaner",
        "label": f"Cleaning Engine (Approved Proposals: {approved_count})",
        "config": {"approved_proposals_count": approved_count},
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 3",
        "status": "built",
    })
    edges.append({"from": "quality_profiler", "to": "cleaner", "label": "quality reports"})

    # 5. Chunker
    chunk_size = spec.get("chunk_size", 800)
    chunk_overlap = spec.get("chunk_overlap", 120)
    nodes.append({
        "id": "chunker",
        "type": "chunker",
        "label": f"Chunker ({chunk_size}/{chunk_overlap})",
        "config": {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
        "enabled": True,
        "reason": "R6",
        "built_in_phase": "Phase 4",
        "status": "built",
    })
    edges.append({"from": "cleaner", "to": "chunker", "label": "active version content"})

    # 6. Embedder
    embed_model = getattr(config, "EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embed_dim = getattr(config, "EMBED_DIM", 384)
    nodes.append({
        "id": "embedder",
        "type": "embedder",
        "label": f"Embedder ({embed_model})",
        "config": {"model": embed_model, "dimension": embed_dim},
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 4",
        "status": "built",
    })
    edges.append({"from": "chunker", "to": "embedder", "label": "chunks"})

    # 7. Vector Store
    nodes.append({
        "id": "vector_store",
        "type": "vector_store",
        "label": "Vector Store (pgvector HNSW)",
        "config": {"index": "HNSW", "metric": "cosine", "table": "chunks"},
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 4",
        "status": "built",
    })
    edges.append({"from": "embedder", "to": "vector_store", "label": "vectors"})

    # 8. Router
    router_enabled = bool(spec.get("router_enabled", False))
    nodes.append({
        "id": "router",
        "type": "router",
        "label": f"Query Router ({'Enabled' if router_enabled else 'Disabled'})",
        "config": {
            "rules_version": "router-rules-v1",
            "enabled": router_enabled,
        },
        "enabled": router_enabled,
        "reason": "default" if router_enabled else "baseline_mode",
        "built_in_phase": "Phase 6A",
        "status": "built",
    })

    # 9. Structured Executor
    struct_enabled = bool(spec.get("structured_route_enabled", False))
    nodes.append({
        "id": "structured_executor",
        "type": "structured_executor",
        "label": f"Structured Executor ({'Enabled' if struct_enabled else 'Disabled'})",
        "config": {"enabled": struct_enabled},
        "enabled": struct_enabled,
        "reason": "R1" if struct_enabled else "R1_not_fired",
        "built_in_phase": "Phase 6A",
        "status": "built",
    })

    # 10. Retriever
    strategy_default = spec.get("strategy_default", "dense")
    top_k = spec.get("top_k", 5)
    candidates_n = spec.get("candidates_n", 20)
    filters_default = spec.get("filters_default", {})
    nodes.append({
        "id": "retriever",
        "type": "retriever",
        "label": f"Retriever ({strategy_default}, top_k={top_k})",
        "config": {
            "strategy_default": strategy_default,
            "top_k": top_k,
            "candidates_n": candidates_n,
            "filters_default": filters_default,
        },
        "enabled": True,
        "reason": "R3" if strategy_default == "dense" else "R4",
        "built_in_phase": "Phase 5",
        "status": "built",
    })

    # Router edges
    if router_enabled:
        edges.append({"from": "router", "to": "structured_executor", "label": "structured_route"})
        edges.append({"from": "router", "to": "retriever", "label": "rag_route"})
    else:
        edges.append({"from": "router", "to": "structured_executor", "label": "disabled"})
        edges.append({"from": "router", "to": "retriever", "label": "bypassed"})

    edges.append({"from": "vector_store", "to": "retriever", "label": "index lookup"})

    # 11. Reranker
    use_rerank = bool(spec.get("use_rerank", False))
    rerank_model = getattr(config, "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    nodes.append({
        "id": "reranker",
        "type": "reranker",
        "label": f"Cross-Encoder Reranker ({'Enabled' if use_rerank else 'Disabled'})",
        "config": {"model": rerank_model, "enabled": use_rerank},
        "enabled": use_rerank,
        "reason": "R5",
        "built_in_phase": "Phase 5",
        "status": "built",
    })
    edges.append({"from": "retriever", "to": "reranker", "label": "candidates"})

    # 12. Guardrails
    nodes.append({
        "id": "guardrails",
        "type": "guardrails",
        "label": "Evidence Gate & Guardrails",
        "config": {
            "min_score": getattr(config, "MIN_SCORE", 0.5),
            "min_bm25": getattr(config, "MIN_BM25", 0.5),
            "min_rerank": getattr(config, "MIN_RERANK", 0.5),
            "citation_validation": True,
            "untrusted_chunk_boundary": True,
        },
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 5",
        "status": "built",
    })
    if use_rerank:
        edges.append({"from": "reranker", "to": "guardrails", "label": "reranked chunks"})
    else:
        edges.append({"from": "retriever", "to": "guardrails", "label": "retrieved chunks"})

    # 13. LLM Generator
    llm_provider = getattr(config, "LLM_PROVIDER", "gemini")
    llm_model = getattr(config, "LLM_MODEL", "gemini-1.5-flash")
    nodes.append({
        "id": "llm",
        "type": "llm",
        "label": f"LLM Generator ({llm_provider}:{llm_model})",
        "config": {"provider": llm_provider, "model": llm_model},
        "enabled": True,
        "reason": "default",
        "built_in_phase": "Phase 4",
        "status": "built",
    })
    edges.append({"from": "guardrails", "to": "llm", "label": "validated context"})

    # 14. Evaluator (Phase 7 Planned)
    nodes.append({
        "id": "evaluator",
        "type": "evaluator",
        "label": "RAG Evaluator (Phase 7 Planned)",
        "config": {
            "framework": "RAGAS / Ground-Truth",
            "metrics": ["faithfulness", "answer_relevancy"],
        },
        "enabled": False,
        "reason": "planned_for_phase_7",
        "built_in_phase": "Phase 7",
        "status": "planned",
    })
    edges.append({"from": "llm", "to": "evaluator", "label": "answers"})
    edges.append({
        "from": "structured_executor",
        "to": "evaluator",
        "label": "answers" if struct_enabled else "disabled",
    })

    return {
        "pipeline_config_id": pipeline_config_row.id,
        "name": pipeline_config_row.name,
        "kind": pipeline_config_row.kind,
        "nodes": nodes,
        "edges": edges,
    }


def render_mermaid_graph(graph_data: Dict[str, Any]) -> str:
    """
    Render a deterministic Mermaid flowchart TD diagram from graph_data.
    Disabled/planned nodes are visibly styled with dotted stroke and grey fill.
    """
    lines = [
        "flowchart TD",
        "    classDef default fill:#f8f9fa,stroke:#333,stroke-width:1.5px,color:#212529;",
        "    classDef disabled fill:#f1f3f5,stroke:#adb5bd,stroke-width:1.5px,stroke-dasharray: 4 4,color:#868e96;",
        "    classDef planned fill:#fff3bf,stroke:#fab005,stroke-width:1.5px,stroke-dasharray: 4 4,color:#495057;",
    ]

    disabled_nodes = []
    planned_nodes = []

    # Emit node declarations
    for n in graph_data["nodes"]:
        nid = n["id"]
        label = n["label"].replace('"', "'")
        lines.append(f'    {nid}["{label}"]')
        if n["status"] == "planned":
            planned_nodes.append(nid)
        elif not n["enabled"]:
            disabled_nodes.append(nid)

    # Emit edges
    for e in graph_data["edges"]:
        u = e["from"]
        v = e["to"]
        lbl = e.get("label")
        if lbl:
            lbl_clean = lbl.replace('"', "'")
            lines.append(f"    {u} -->|{lbl_clean}| {v}")
        else:
            lines.append(f"    {u} --> {v}")

    # Emit classes
    for d in disabled_nodes:
        lines.append(f"    class {d} disabled;")
    for p in planned_nodes:
        lines.append(f"    class {p} planned;")

    return "\n".join(lines)
