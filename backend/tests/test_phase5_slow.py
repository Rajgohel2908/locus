"""
tests/test_phase5_slow.py — Slow integration test using real models.

Marked slow and skipped by default unless environment variable RUN_SLOW=1 is set.
Runs real SentenceTransformerEmbedder (all-MiniLM-L6-v2) and real CrossEncoderReranker
(ms-marco-MiniLM-L-6-v2) on CPU with FakeLLMClient on the HR knowledge base.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, Source, Document, IndexRun, Chunk
from indexing.embedder import SentenceTransformerEmbedder
from retrieval.rerank import CrossEncoderReranker
from generation.llm import FakeLLMClient
from generation.answer import execute_query


@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("RUN_SLOW"),
    reason="Slow integration test using real embedding and CrossEncoder models; enable with RUN_SLOW=1",
)
def test_real_cross_encoder_and_embedder_hybrid_rerank():
    """
    Integration test running real SentenceTransformer + real CrossEncoder
    on CPU against an in-memory database with actual semantic and reranking inference.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    embedder = SentenceTransformerEmbedder()
    reranker = CrossEncoderReranker()

    src = Source(source_type="file", name="hr_policy.docx")
    db.add(src)
    db.commit()

    run = IndexRun(
        source_id=src.id,
        source_version=1,
        embed_model="sentence-transformers/all-MiniLM-L6-v2",
        embed_dim=384,
        chunk_size=800,
        chunk_overlap=120,
        chunk_count=2,
        status="completed",
    )
    db.add(run)
    db.commit()

    text_leave = "All full-time employees are entitled to 24 annual leave days per calendar year."
    text_unrelated = "The company data center uses 100% renewable wind energy in Iceland."

    embeddings = embedder.embed_documents([text_leave, text_unrelated])

    ch_leave = Chunk(
        index_run_id=run.id,
        source_id=src.id,
        chunk_index=0,
        content=text_leave,
        content_hash="hash_leave_real",
        token_estimate=12,
        embedding=embeddings[0],
        metadata_={"source_name": "hr_policy.docx", "published_at": "2024-06-01T00:00:00", "freshness": "fresh"},
    )
    ch_unrelated = Chunk(
        index_run_id=run.id,
        source_id=src.id,
        chunk_index=1,
        content=text_unrelated,
        content_hash="hash_unrelated_real",
        token_estimate=12,
        embedding=embeddings[1],
        metadata_={"source_name": "hr_policy.docx", "published_at": "2024-06-01T00:00:00", "freshness": "fresh"},
    )
    db.add_all([ch_leave, ch_unrelated])
    db.commit()

    fake_llm = FakeLLMClient(response=f"Full-time employees receive 24 days annual leave [{ch_leave.id}].")

    question = "How many annual leaves are employees entitled to?"
    result = execute_query(
        db=db,
        question=question,
        source_ids=[src.id],
        strategy="hybrid_rerank",
        min_score=0.30,
        min_bm25=0.5,
        min_rerank=0.50,
        embedder=embedder,
        reranker=reranker,
        llm_client=fake_llm,
    )

    assert result["status"] == "answered"
    assert len(result["retrieved"]) > 0
    top_chunk = result["retrieved"][0]
    assert top_chunk["chunk_id"] == ch_leave.id
    # Real cross encoder score on matching question should be very high (> 0.8)
    assert top_chunk["score"] > 0.8
    assert top_chunk["signals"]["rerank_score"] > 0.8
    assert len(result["citations"]) == 1
    assert result["citations"][0]["chunk_id"] == ch_leave.id

    db.close()


@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("RUN_SLOW"),
    reason="Slow integration test using real models; enable with RUN_SLOW=1",
)
def test_warmup_models_loaded_after_startup():
    """
    Assert that when startup runs with WARMUP_MODELS=1, the embedder and cross-encoder
    models are actually initialized in memory, and subsequent inference calls take
    warm latency (< 0.5s) without any model loading overhead.
    """
    import time
    from main import startup
    from indexing.embedder import get_embedder
    from retrieval.rerank import get_reranker

    # Execute server startup sequence which triggers warmup
    startup()

    # Assert models are warm and inference takes < 0.5s
    t0 = time.perf_counter()
    embedder = get_embedder()
    v = embedder.embed_query("warmup check")
    t_embed = time.perf_counter() - t0
    assert len(v) == 384
    assert t_embed < 0.5

    t1 = time.perf_counter()
    reranker = get_reranker()
    res = reranker.rerank("warmup query", [{"chunk_id": 1, "content": "sample content", "score": 0.5}])
    t_rerank = time.perf_counter() - t1
    assert len(res) == 1
    assert t_rerank < 0.5
    assert t_rerank < 0.5
