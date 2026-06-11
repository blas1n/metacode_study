"""Shared fixtures — litellm 과 DB 세션은 전부 mock (실제 API/DB 호출 금지)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from vector_store import Chunk, VectorEntry


@pytest.fixture
def sample_chunk() -> Chunk:
    return Chunk(
        chunk_id="note-abc-chunk-01",
        note_id="note-abc",
        source_id="bsvibe-src-001",
        chunk_index=1,
        text="BSVibe is a unified monorepo with FastAPI backend and Next.js PWA.",
        char_count=65,
        metadata={
            "product": "BSVibe",
            "source_type": "readme",
            "note_type": "project_overview",
            "source_repo": "BSVibe/bsvibe-app",
            "source_commit": "a6648ac",
            "source_path": "README.md",
            "source_url": "https://github.com/BSVibe/bsvibe-app/blob/a6648ac/README.md#L1-L90",
            "tags": ["bsvibe", "monorepo"],
            "verified": True,
            "created_at": "2026-06-02T22:55:00+09:00",
        },
    )


@pytest.fixture
def sample_entry(sample_chunk: Chunk) -> VectorEntry:
    return VectorEntry(
        chunk=sample_chunk,
        embedding=[0.1, 0.2, 0.3],
        embedding_model="ollama/bge-m3",
    )


@pytest.fixture
def mock_session() -> MagicMock:
    """AsyncSession mock — execute 는 AsyncMock 이되, await 결과는 *동기* MagicMock
    result 로 고정합니다. (AsyncMock 기본 return_value 는 또 AsyncMock 이라
    ``result.scalar()`` / ``result.mappings()`` 가 코루틴을 돌려주는 함정 회피.)"""
    session = MagicMock()
    result = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    return session


def make_litellm_response(embeddings: list[list[float]]) -> MagicMock:
    """litellm.aembedding 응답 형태 모사: response.data[i]['embedding']."""
    resp = MagicMock()
    resp.data = [{"embedding": e} for e in embeddings]
    return resp
