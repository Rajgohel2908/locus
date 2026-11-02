"""
retrieval/rerank.py — CrossEncoder reranker and test double for Phase 5 retrieval.

Features:
- Reranker abstract base class.
- CrossEncoderReranker: lazy CPU singleton using sentence_transformers.CrossEncoder.
  Truncates chunk content to ~512 tokens (~2048 chars), evaluates in batches of 16,
  applies sigmoid normalization to map raw logits to 0.0 - 1.0 confidence scores.
- FakeReranker: deterministic test double avoiding model loading.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
import threading
import numpy as np
import logging

import config

logger = logging.getLogger(__name__)


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid function."""
    return np.where(x >= 0, 1.0 / (1.0 + np.exp(-x)), np.exp(x) / (1.0 + np.exp(x)))


class Reranker(ABC):
    """Abstract interface for reranking candidate chunks."""

    @abstractmethod
    def rerank(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank candidates with respect to query.
        Each candidate is annotated with 'rerank_score' and re-ordered.
        """
        pass


class CrossEncoderReranker(Reranker):
    """
    CPU Cross-Encoder reranker using sentence_transformers.
    Lazy loads the configured model on first use.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config.RERANK_MODEL
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import CrossEncoder
                    logger.info(f"Loading CrossEncoder model on CPU: {self.model_name}")
                    self._model = CrossEncoder(self.model_name, device="cpu")
        return self._model

    def rerank(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        model = self._get_model()

        # Build pairs: (query, chunk_content truncated to ~512 tokens / ~2048 chars)
        pairs = []
        for ch in chunks:
            raw_content = ch.get("content", "")
            truncated_content = raw_content[:2048]
            pairs.append((query, truncated_content))

        # Predict in batches of 16
        raw_scores = model.predict(pairs, batch_size=16)

        # Ensure raw_scores is a 1D float numpy array
        scores_arr = np.array(raw_scores, dtype=np.float32)
        if scores_arr.ndim > 1:
            scores_arr = scores_arr.squeeze()
        if scores_arr.ndim == 0:
            scores_arr = np.array([float(scores_arr)])

        # Sigmoid normalize logits to 0.0 - 1.0
        normalized_scores = sigmoid(scores_arr)

        reranked = []
        for idx, ch in enumerate(chunks):
            item = dict(ch)
            item["rerank_score"] = round(float(normalized_scores[idx]), 4)
            reranked.append(item)

        # Sort descending by rerank_score, deterministic tie-breaking by chunk_id ascending
        reranked.sort(key=lambda x: (-x["rerank_score"], x["chunk_id"]))

        for rank, item in enumerate(reranked, start=1):
            item["rank"] = rank

        return reranked


class FakeReranker(Reranker):
    """
    In-memory mock reranker for unit testing without downloading neural weights.
    Supports custom score functions and tracks call count.
    """

    def __init__(self, score_fn: Optional[Callable[[str, Dict[str, Any]], float]] = None):
        self.score_fn = score_fn
        self.call_count = 0
        self.last_query: Optional[str] = None
        self.last_candidate_count: int = 0

    def rerank(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.call_count += 1
        self.last_query = query
        self.last_candidate_count = len(chunks)

        if not chunks:
            return []

        reranked = []
        for idx, ch in enumerate(chunks):
            item = dict(ch)
            if self.score_fn:
                item["rerank_score"] = round(float(self.score_fn(query, item)), 4)
            else:
                # Default mock score: decays based on input index
                base = float(item.get("score") or item.get("rrf_score") or 0.8)
                item["rerank_score"] = round(max(0.01, base - idx * 0.02), 4)
            reranked.append(item)

        reranked.sort(key=lambda x: (-x["rerank_score"], x["chunk_id"]))

        for rank, item in enumerate(reranked, start=1):
            item["rank"] = rank

        return reranked


# Singleton management
_reranker_instance: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Return the global CrossEncoder reranker singleton."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker()
    return _reranker_instance


def set_reranker(reranker: Optional[Reranker]) -> None:
    """Override the global reranker singleton (for tests)."""
    global _reranker_instance
    _reranker_instance = reranker
