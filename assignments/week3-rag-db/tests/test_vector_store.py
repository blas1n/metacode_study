"""VectorRAG store 유닛 테스트 — litellm / DB 전부 mock."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from conftest import make_litellm_response

import vector_store
from vector_store import (
    EMBED_DIM,
    EMBED_MODEL,
    Chunk,
    RagVectorStore,
    SearchHit,
    embed_texts,
    load_chunks,
    to_pgvector_literal,
)

# 2주차 산출물 (in-repo, 결정론적)
REAL_CHUNKS = (
    Path(__file__).resolve().parents[2]
    / "week2-rag-dataset"
    / "data"
    / "processed"
    / "rag_chunks.jsonl"
)


# --- load_chunks -----------------------------------------------------------


def test_load_chunks_reads_all_37_from_real_dataset():
    chunks = load_chunks(REAL_CHUNKS)
    assert len(chunks) == 37


def test_load_chunks_parses_core_fields():
    chunks = load_chunks(REAL_CHUNKS)
    c = chunks[0]
    assert isinstance(c, Chunk)
    assert c.chunk_id and c.note_id and c.source_id
    assert c.text
    assert "note_type" in c.metadata
    assert "source_url" in c.metadata


# --- to_pgvector_literal ---------------------------------------------------


def test_to_pgvector_literal_format():
    assert to_pgvector_literal([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"


def test_to_pgvector_literal_no_spaces():
    # asyncpg + pgvector 텍스트 캐스팅은 공백 없는 형태가 안전
    out = to_pgvector_literal([1.0, 2.0])
    assert " " not in out
    assert out.startswith("[") and out.endswith("]")


# --- embed_texts (litellm mocked) ------------------------------------------


async def test_embed_texts_calls_litellm_with_model():
    fake = make_litellm_response([[0.1] * EMBED_DIM, [0.2] * EMBED_DIM])
    with patch.object(vector_store, "litellm") as m:
        m.aembedding = AsyncMock(return_value=fake)
        out = await embed_texts(["a", "b"], model=EMBED_MODEL)
    assert m.aembedding.await_count == 1
    assert m.aembedding.await_args.kwargs["model"] == EMBED_MODEL
    assert len(out) == 2
    assert len(out[0]) == EMBED_DIM


async def test_embed_texts_empty_returns_empty():
    with patch.object(vector_store, "litellm") as m:
        out = await embed_texts([])
    assert out == []
    m.aembedding.assert_not_called()


async def test_embed_texts_truncates_long_input():
    long_text = "x" * 100_000
    fake = make_litellm_response([[0.0] * EMBED_DIM])
    with patch.object(vector_store, "litellm") as m:
        m.aembedding = AsyncMock(return_value=fake)
        await embed_texts([long_text])
    sent = m.aembedding.await_args.kwargs["input"][0]
    assert len(sent) <= vector_store.MAX_INPUT_LENGTH


# --- RagVectorStore.upsert -------------------------------------------------


async def test_upsert_stamps_model_and_dimension(mock_session, sample_entry):
    store = RagVectorStore(mock_session)
    await store.upsert([sample_entry])
    assert mock_session.execute.await_count == 1
    params = mock_session.execute.await_args.args[1]
    # dimension 은 임베딩 길이로 stamp
    assert params["dimension"] == len(sample_entry.embedding)
    assert params["embedding_model"] == "text-embedding-3-small"
    # 임베딩은 pgvector 리터럴 문자열로 bind
    assert params["embedding"] == to_pgvector_literal(sample_entry.embedding)


async def test_upsert_sql_uses_on_conflict(mock_session, sample_entry):
    store = RagVectorStore(mock_session)
    await store.upsert([sample_entry])
    sql = str(mock_session.execute.await_args.args[0])
    assert "ON CONFLICT" in sql.upper()
    assert "RAG_CHUNKS" in sql.upper()


async def test_upsert_binds_created_at_as_datetime(mock_session, sample_entry):
    # asyncpg 는 timestamptz 에 ISO 문자열 bind 를 거부(CAST 로도 안 풀림) → datetime 으로.
    from datetime import datetime

    store = RagVectorStore(mock_session)
    await store.upsert([sample_entry])
    params = mock_session.execute.await_args.args[1]
    assert isinstance(params["created_at"], datetime)


# --- RagVectorStore.count --------------------------------------------------


async def test_count_returns_scalar(mock_session):
    mock_session.execute.return_value.scalar.return_value = 37
    store = RagVectorStore(mock_session)
    assert await store.count() == 37


# --- RagVectorStore.search -------------------------------------------------


async def test_search_similarity_is_one_minus_distance(mock_session):
    rows = [
        {
            "chunk_id": "c1",
            "note_id": "n1",
            "source_id": "s1",
            "text": "t1",
            "source_url": "u1",
            "note_type": "project_overview",
            "distance": 0.1,
        },
        {
            "chunk_id": "c2",
            "note_id": "n2",
            "source_id": "s2",
            "text": "t2",
            "source_url": "u2",
            "note_type": "implementation_evidence",
            "distance": 0.25,
        },
    ]
    mock_session.execute.return_value.mappings.return_value = rows
    store = RagVectorStore(mock_session)
    hits = await store.search(query=[0.1, 0.2, 0.3], limit=2)
    assert all(isinstance(h, SearchHit) for h in hits)
    assert hits[0].similarity == pytest.approx(0.9)
    assert hits[1].similarity == pytest.approx(0.75)


async def test_search_binds_query_as_pgvector_literal(mock_session):
    mock_session.execute.return_value.mappings.return_value = []
    store = RagVectorStore(mock_session)
    await store.search(query=[0.1, 0.2], limit=3)
    params = mock_session.execute.await_args.args[1]
    assert params["qv"] == to_pgvector_literal([0.1, 0.2])
    assert params["lim"] == 3


async def test_search_applies_filters(mock_session):
    mock_session.execute.return_value.mappings.return_value = []
    store = RagVectorStore(mock_session)
    await store.search(
        query=[0.1],
        limit=5,
        note_types=["project_overview"],
        product="BSVibe",
        verified_only=True,
    )
    sql = " ".join(str(mock_session.execute.await_args.args[0]).upper().split())
    params = mock_session.execute.await_args.args[1]
    assert "NOTE_TYPE = ANY(:NOTE_TYPES)" in sql
    assert "PRODUCT = :PRODUCT" in sql
    assert "VERIFIED = TRUE" in sql
    assert params["note_types"] == ["project_overview"]
    assert params["product"] == "BSVibe"
