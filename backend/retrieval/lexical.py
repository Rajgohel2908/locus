r"""
retrieval/lexical.py — BM25 lexical retriever with lazy per-run caching and pure tokenizer.

Features:
- Pure unit-tested tokenizer preserving identifiers (E1007, E-1007), emails, decimals.
- Strips trailing possessives ('s and typographic ’s) and surrounding punctuation.
- Preserves Devanagari combining marks (no bare \w splitting).
- Small English + Hinglish stopword filtering; drops tokens < 2 characters.
- Query tokens capped at 40.
- Thread-safe LRU cache (capacity 8) for BM25Okapi indices keyed by index_run_id.
- Returns per chunk: bm25 score, rank, matched_terms (up to 5).
- Scores <= 0 are treated as non-matches.
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import List, Dict, Any, Optional, Set, Tuple
import threading
import logging
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from db import Chunk

logger = logging.getLogger(__name__)

# Surrounding punctuation to strip from token boundaries (keeping internal - . _ @ intact)
PUNCT_SURROUNDING = """!"#$%&\'()*+,/:;<=>?[\\]^`{|}~ \t\r\n«»“”‘’—–"""

STOPWORDS = {
    # English common stopwords
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i",
    "if", "in", "into", "is", "isn't", "it", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "should", "shouldn't",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "won't", "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves",
    # Hinglish filler words
    "hai", "hain", "ke", "ki", "ka", "ko", "kya", "kyu", "kyun", "se", "aur", "bhi", "yeh", "woh",
    "ho", "hoga", "tha", "thi", "the", "par", "mein", "kar", "kare", "karna", "nahi", "raha", "rahe", "rahi"
}


def tokenize(text: str, max_tokens: Optional[int] = None) -> List[str]:
    """
    Pure tokenizer function:
    1. Lowercase text.
    2. Split on whitespace.
    3. Strip surrounding punctuation and trailing possessives ('s, ’s).
    4. Keep internal - . _ @ characters intact (e.g. E-1007, user@domain.com, 10.5).
    5. Drop tokens under 2 characters.
    6. Drop English and Hinglish stopwords.
    7. Preserve Devanagari combining characters (does not split on unicode word boundaries).
    8. Cap tokens if max_tokens is specified.
    """
    if not text:
        return []

    raw_tokens = text.lower().split()
    tokens: List[str] = []

    for raw in raw_tokens:
        tok = raw.strip(PUNCT_SURROUNDING)
        if not tok:
            continue

        # Strip trailing possessives ('s and ’s)
        if tok.endswith("'s") or tok.endswith("’s"):
            tok = tok[:-2].strip(PUNCT_SURROUNDING)

        # Strip remaining boundary punctuation
        tok = tok.strip(PUNCT_SURROUNDING)

        # Drop tokens under 2 characters
        if len(tok) < 2:
            continue

        # Drop stopwords
        if tok in STOPWORDS:
            continue

        tokens.append(tok)
        if max_tokens is not None and len(tokens) >= max_tokens:
            break

    return tokens


class LexicalRetriever(ABC):
    """Abstract interface for lexical retrieval."""

    @abstractmethod
    def retrieve(
        self,
        db: Session,
        question: str,
        run_ids: List[int],
        top_k: int = 20,
        allowed_chunk_ids: Optional[Set[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top-k chunks matching question via lexical search."""
        pass


class BM25Retriever(LexicalRetriever):
    """
    BM25Okapi lexical retriever with an in-memory thread-safe LRU cache of indices.
    Cache capacity: 8 runs. Index runs are immutable so invalidation is not required.
    """

    def __init__(self, cache_capacity: int = 8):
        self._capacity = cache_capacity
        self._cache: OrderedDict[int, Tuple[BM25Okapi, List[Dict[str, Any]], List[List[str]]]] = OrderedDict()
        self._lock = threading.Lock()

    def _get_or_build_index(
        self,
        db: Session,
        run_id: int,
    ) -> Tuple[BM25Okapi, List[Dict[str, Any]], List[List[str]]]:
        """Fetch or lazily build the BM25 index for a single index run."""
        with self._lock:
            if run_id in self._cache:
                self._cache.move_to_end(run_id)
                return self._cache[run_id]

        # Build index outside the lock to avoid blocking readers of other runs
        chunks = (
            db.query(Chunk)
            .filter(Chunk.index_run_id == run_id)
            .order_by(Chunk.id.asc())
            .all()
        )

        chunk_data = []
        tokenized_corpus = []

        for ch in chunks:
            toks = tokenize(ch.content)
            tokenized_corpus.append(toks)
            chunk_data.append({
                "chunk_id": ch.id,
                "content": ch.content,
                "metadata": ch.metadata_ if isinstance(ch.metadata_, dict) else {},
                "source_id": ch.source_id,
                "document_id": ch.document_id,
                "record_id": ch.record_id,
                "index_run_id": ch.index_run_id,
            })

        # When corpus is empty or tokens empty, BM25Okapi handles it if corpus has at least 1 doc
        # If corpus is completely empty, initialize with dummy doc
        bm25 = BM25Okapi(tokenized_corpus if tokenized_corpus else [["__empty__"]])

        with self._lock:
            if run_id in self._cache:
                self._cache.move_to_end(run_id)
                return self._cache[run_id]

            if len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)

            result = (bm25, chunk_data, tokenized_corpus)
            self._cache[run_id] = result
            return result

    def retrieve(
        self,
        db: Session,
        question: str,
        run_ids: List[int],
        top_k: int = 20,
        allowed_chunk_ids: Optional[Set[int]] = None,
    ) -> List[Dict[str, Any]]:
        query_tokens = tokenize(question, max_tokens=40)
        if not query_tokens or not run_ids:
            return []

        scored_candidates: List[Dict[str, Any]] = []

        for run_id in run_ids:
            bm25, chunk_items, tokenized_corpus = self._get_or_build_index(db, run_id)
            if not chunk_items:
                continue

            scores = bm25.get_scores(query_tokens)

            for idx, ch in enumerate(chunk_items):
                score = float(scores[idx])
                # Treat score <= 0 as no match (tiny corpora give zero or negative BM25 scores)
                if score <= 0.0:
                    continue

                cid = ch["chunk_id"]
                if allowed_chunk_ids is not None and cid not in allowed_chunk_ids:
                    continue

                # Find up to 5 matched query terms present in this chunk
                chunk_tokens_set = set(tokenized_corpus[idx])
                matched = []
                for q_tok in query_tokens:
                    if q_tok in chunk_tokens_set and q_tok not in matched:
                        matched.append(q_tok)
                        if len(matched) == 5:
                            break

                candidate = dict(ch)
                candidate["score"] = round(score, 4)
                candidate["matched_terms"] = matched
                scored_candidates.append(candidate)

        # Sort descending by bm25 score, deterministic tie-breaking by chunk_id ascending
        scored_candidates.sort(key=lambda x: (-x["score"], x["chunk_id"]))

        top_candidates = scored_candidates[:top_k]
        for rank, c in enumerate(top_candidates, start=1):
            c["rank"] = rank

        return top_candidates


# Singleton instance
_lexical_retriever_instance: Optional[LexicalRetriever] = None


def get_lexical_retriever() -> LexicalRetriever:
    """Return the global BM25 lexical retriever singleton."""
    global _lexical_retriever_instance
    if _lexical_retriever_instance is None:
        _lexical_retriever_instance = BM25Retriever(cache_capacity=8)
    return _lexical_retriever_instance


def set_lexical_retriever(retriever: LexicalRetriever) -> None:
    """Override the global lexical retriever (for testing)."""
    global _lexical_retriever_instance
    _lexical_retriever_instance = retriever
