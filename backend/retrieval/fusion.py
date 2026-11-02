"""
retrieval/fusion.py — Pure reciprocal rank fusion (RRF) with deterministic tie-breaking.
"""

from typing import List, Dict, Any


def reciprocal_rank_fusion(
    rank_lists: List[List[Dict[str, Any]]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    """
    Pure Reciprocal Rank Fusion across multiple candidate ranked lists.

    Score formula:
        RRF_score(d) = sum_{l in rank_lists} 1.0 / (k + rank_l(d))
    where rank_l(d) is the 1-based rank of document d in list l.

    Deterministic tie-breaking:
        Primary: rrf_score DESC
        Secondary: chunk_id ASC
    """
    if not rank_lists:
        return []

    # Map chunk_id -> aggregate info
    chunk_map: Dict[int, Dict[str, Any]] = {}
    score_map: Dict[int, float] = {}

    for r_list in rank_lists:
        for idx, item in enumerate(r_list, start=1):
            cid = item["chunk_id"]
            # Rank can be explicit rank or 1-based index in the list
            r = item.get("rank", idx)
            score_contribution = 1.0 / (k + r)

            score_map[cid] = score_map.get(cid, 0.0) + score_contribution
            if cid not in chunk_map:
                # Retain item fields (content, metadata, etc.)
                chunk_map[cid] = dict(item)

    fused_items: List[Dict[str, Any]] = []
    for cid, total_score in score_map.items():
        entry = dict(chunk_map[cid])
        entry["rrf_score"] = round(total_score, 6)
        fused_items.append(entry)

    # Sort descending by rrf_score, tie-breaking by chunk_id ascending
    fused_items.sort(key=lambda x: (-x["rrf_score"], x["chunk_id"]))

    for rank, item in enumerate(fused_items, start=1):
        item["rank"] = rank

    return fused_items
