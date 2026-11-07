"""
backend/evaluation/matching.py — Pure evidence matching functions.

Rules:
- Text-based evidence matching (never chunk IDs) so chunk-size variants are comparable.
- Normalize: lowercase, collapse whitespace, strip punctuation.
- A chunk is relevant to an expected span if at least 80% of the span's tokens occur in the chunk.
- For row evidence (where row_key is present), the row_key value must also appear in the chunk.
- Union coverage: union of top-k chunks covers a span if >= 80% of span tokens appear in the union.
"""

import re
from collections import Counter
from typing import Any, List, Optional, Tuple, Dict


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    if not text:
        return ""
    # Strip punctuation and replace with whitespace
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    # Collapse multiple whitespaces and strip leading/trailing
    return " ".join(cleaned.split())


def tokenize(text: str) -> List[str]:
    """Tokenize normalized text into a list of words."""
    norm = normalize_text(text)
    return norm.split() if norm else []


def chunk_matches_span(
    chunk_text: str,
    span_text: str,
    row_key: Optional[Any] = None,
    threshold: float = 0.80,
) -> Tuple[bool, float]:
    """
    Check if a single chunk is relevant to an expected span.
    Returns (is_relevant: bool, token_overlap_ratio: float).
    """
    span_tokens = tokenize(span_text)
    if not span_tokens:
        return False, 0.0

    chunk_tokens = tokenize(chunk_text)
    if not chunk_tokens:
        return False, 0.0

    span_counts = Counter(span_tokens)
    chunk_counts = Counter(chunk_tokens)

    matched_tokens = sum(
        min(count, chunk_counts[token]) for token, count in span_counts.items()
    )
    overlap = matched_tokens / len(span_tokens)

    # Check row_key if present
    if row_key is not None and str(row_key).strip():
        norm_key = normalize_text(str(row_key))
        norm_chunk = normalize_text(chunk_text)
        if norm_key and norm_key not in norm_chunk:
            return False, overlap

    return overlap >= threshold, overlap


def union_covers_span(
    chunk_texts: List[str],
    span_text: str,
    row_key: Optional[Any] = None,
    threshold: float = 0.80,
) -> Tuple[bool, float]:
    """
    Check if the union of chunks covers an expected span (supporting spans split across chunk boundaries).
    Returns (covers: bool, token_overlap_ratio: float).
    """
    span_tokens = tokenize(span_text)
    if not span_tokens:
        return False, 0.0

    combined_counts: Counter = Counter()
    for c_text in chunk_texts:
        combined_counts.update(tokenize(c_text))

    span_counts = Counter(span_tokens)
    matched_tokens = sum(
        min(count, combined_counts[token]) for token, count in span_counts.items()
    )
    overlap = matched_tokens / len(span_tokens)

    if row_key is not None and str(row_key).strip():
        norm_key = normalize_text(str(row_key))
        key_found = False
        for c_text in chunk_texts:
            if norm_key in normalize_text(c_text):
                key_found = True
                break
        if not key_found:
            return False, overlap

    return overlap >= threshold, overlap


def match_retrieved_chunk(
    chunk_text: str,
    expected_evidence: List[Dict[str, Any]],
    threshold: float = 0.80,
) -> Tuple[bool, List[str]]:
    """
    Evaluate an individual retrieved chunk against an item's expected_evidence list.
    Returns (is_relevant, list_of_matched_spans).
    """
    matched_spans = []
    for ev in expected_evidence:
        span = ev.get("span", "")
        row_key = ev.get("row_key")
        is_rel, _ = chunk_matches_span(chunk_text, span, row_key, threshold=threshold)
        if is_rel:
            matched_spans.append(span)

    return (len(matched_spans) > 0), matched_spans

