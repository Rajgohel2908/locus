"""
tests/test_citation_regression.py — Synthetic regression test for citation validation consistency.

Asserts that if any cited chunk ID was not present in the prompt (e.g. filtered below threshold),
it is flagged in invalid_citations and the query status is strictly 'unverified'.
"""

import pytest
from generation.answer import parse_and_validate_citations, build_rag_prompt


def test_citation_validation_regression():
    """
    Synthetic regression test:
    When retrieved chunks below threshold are excluded from prompt context (used_in_prompt=False),
    and an LLM response cites both an included chunk and an excluded chunk,
    verify that the excluded chunk is marked invalid and query status is 'unverified'.
    """
    retrieved_chunks = [
        {
            "chunk_id": 1876,
            "score": 0.72,
            "source_id": 10,
            "content": "All regular full-time employees are entitled to 24 annual leave days.",
            "metadata": {"source_name": "leave_policy_2024.docx", "published_at": "2024-06-01"},
            "signals": {"dense_score": 0.72, "lexical_score": 0.65},
            "used_in_prompt": True,
        },
        {
            "chunk_id": 1877,
            "score": 0.22,  # Below threshold 0.30
            "source_id": 9,
            "content": "Historical 2019 archived policy stated 20 annual leave days.",
            "metadata": {"source_name": "leave_policy_2019_archived.pdf", "published_at": "2019-03-01"},
            "signals": {"dense_score": 0.22, "lexical_score": 0.15},
            "used_in_prompt": False,
        },
    ]

    prompt_chunks = [c for c in retrieved_chunks if c["used_in_prompt"]]
    prompt_chunk_ids = [c["chunk_id"] for c in prompt_chunks]

    build_rag_prompt("How many annual leaves are employees entitled to?", prompt_chunks)

    raw_answer = (
        "Conflict detected between sources: historical policy granted 20 days [1877], "
        "but current policy grants 24 days [1876]."
    )

    citation_info = parse_and_validate_citations(raw_answer, prompt_chunks)
    valid_citations = citation_info["valid_citations"]
    valid_ids = list(citation_info["valid_ids"])
    invalid_ids = citation_info["invalid_citations"]

    if (not valid_citations) or (len(invalid_ids) > 0):
        status = "unverified"
    else:
        status = "answered"

    assert prompt_chunk_ids == [1876], "Only chunk 1876 should be in prompt"
    assert valid_ids == [1876], "Only 1876 is valid"
    assert invalid_ids == [1877], "1877 must be marked invalid"
    assert status == "unverified", "Status must be 'unverified' when any citation is invalid"

