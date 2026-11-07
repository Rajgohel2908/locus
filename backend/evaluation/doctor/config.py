"""
backend/evaluation/doctor/config.py — Configuration and prior thresholds for RAG Doctor v1.

All thresholds are explicit, documented priors.
"""

from typing import Dict, Any


class DoctorConfig:
    # D1 Slice Weakness
    SLICE_GAP_THRESHOLD: float = 0.15  # slice recall@5 below run recall@5 by >= 0.15

    # D2 Depth Gap
    DEPTH_GAP_THRESHOLD: float = 0.15  # recall@20 - recall@5 >= 0.15

    # D3 Broad Chunks
    BROAD_CHUNK_MIN_HIT: float = 0.50                      # hit@5 >= 0.50 (healthy)
    BROAD_CHUNK_MAX_CONTEXT_PRECISION_TOKENS: float = 0.35 # context_precision_tokens@5 <= 0.35
    PROPOSED_CHUNK_SIZE: int = 400                         # proposed smaller chunk size
    PROPOSED_CHUNK_OVERLAP: int = 60                       # proposed smaller chunk overlap

    # D4 False Refusals (Evidence Gate too high)
    FALSE_REFUSAL_MAX_RATE: float = 0.05   # false_refusal rate > 0.05

    # D5 Unsafe Answers (Evidence Gate too low on unanswerables)
    UNSAFE_ANSWER_MAX_RATE: float = 0.05    # unsafe_answer rate > 0.05

    # D6 Citation Problems
    INVALID_CITATION_MAX_RATE: float = 0.10 # invalid_citation_rate > 0.10

    # D9 Rerank No Gain
    RERANK_MIN_LATENCY_SAVING_MS: float = 15.0  # reranker adds >= 15 ms

