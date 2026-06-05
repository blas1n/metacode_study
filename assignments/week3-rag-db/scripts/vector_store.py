"""Week3 VectorRAG store — bsvibe-app `backend/embedding` 패턴 이식.

bsvibe-app 의 실제 임베딩 스택을 스터디용으로 옮긴 모듈입니다.

- 임베딩: ``litellm.aembedding`` (provider.py 의 ``LiteLLMEmbeddingProvider``)
- 저장/검색: SQLAlchemy async + asyncpg + pgvector raw ``text()`` SQL (storage/pg.py)
- 모델·차원 stamp: 모든 행에 ``embedding_model`` + ``dimension`` 기록 → 모델 교체 시
  stale 임베딩 감지 (provider.py docstring)
- 코사인 검색: ``embedding <=> CAST(:qv AS vector)``, similarity = ``1 - distance``

차이점 한 가지: bsvibe 는 임베딩 list 를 bind 파라미터로 직접 넘기지만, asyncpg 는
raw ``text()`` SQL 에서 Python list 를 거부합니다("expected str, got list"). 그래서
pgvector 텍스트 리터럴 ``"[v1,v2,...]"`` 로 직렬화한 뒤 ``CAST(:p AS vector)`` 로 넘깁니다.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import litellm
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# 과제에서 검증할 임베딩 모델·차원 (루브릭: 모델·차원 일치 검증)
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

# bsvibe EmbeddingSettings.max_input_length 와 같은 역할 — 과도하게 긴 입력 절단
MAX_INPUT_LENGTH = 8192


@dataclass(slots=True)
class Chunk:
    """rag_chunks.jsonl 한 줄 = 적재 단위."""

    chunk_id: str
    note_id: str
    source_id: str
    chunk_index: int
    text: str
    char_count: int
    metadata: dict


@dataclass(slots=True)
class VectorEntry:
    """임베딩까지 끝난 적재 엔트리 (모델 stamp 포함)."""

    chunk: Chunk
    embedding: list[float]
    embedding_model: str


@dataclass(slots=True)
class SearchHit:
    """코사인 검색 결과 한 건. similarity = 1 - cosine_distance."""

    chunk_id: str
    note_id: str
    source_id: str
    text: str
    source_url: str
    note_type: str
    similarity: float


def load_chunks(path: str | Path) -> list[Chunk]:
    """rag_chunks.jsonl 을 읽어 :class:`Chunk` 리스트로."""
    chunks: list[Chunk] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        chunks.append(
            Chunk(
                chunk_id=d["chunk_id"],
                note_id=d["note_id"],
                source_id=d["source_id"],
                chunk_index=d["chunk_index"],
                text=d["text"],
                char_count=d["char_count"],
                metadata=d["metadata"],
            )
        )
    return chunks


def to_pgvector_literal(embedding: Sequence[float]) -> str:
    """임베딩 벡터를 pgvector 텍스트 리터럴 ``"[v1,v2,...]"`` 로 직렬화.

    asyncpg 는 raw ``text()`` SQL 에서 Python list bind 를 거부하므로
    (``expected str, got list``) 공백 없는 문자열 리터럴로 만들어 ``CAST(:p AS vector)``.
    """
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


async def embed_texts(
    texts: list[str], *, model: str = EMBED_MODEL
) -> list[list[float]]:
    """``litellm.aembedding`` 으로 텍스트 배치를 임베딩 (provider.py 미러).

    bsvibe ``LiteLLMEmbeddingProvider.embed`` 처럼 빈 입력은 즉시 ``[]``,
    과도하게 긴 입력은 ``MAX_INPUT_LENGTH`` 로 절단한 뒤 호출합니다.
    """
    if not texts:
        return []
    truncated = [t[:MAX_INPUT_LENGTH] for t in texts]
    response = await litellm.aembedding(model=model, input=truncated)
    return [item["embedding"] for item in response.data]


class RagVectorStore:
    """pgvector 백엔드 — storage/pg.py 의 ``PgVectorBackend`` 이식."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_schema(self) -> None:
        """vector 확장 + rag_chunks 테이블 + 인덱스 생성 (idempotent).

        스키마는 2주차 보고서 §7 을 그대로 옮기되 차원만 ``vector(1536)`` 으로
        고정 — text-embedding-3-small 의 차원과 일치(루브릭 ①).
        """
        statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            f"""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id        text PRIMARY KEY,
                note_id         text NOT NULL,
                source_id       text NOT NULL,
                chunk_index     int  NOT NULL,
                text            text NOT NULL,
                char_count      int  NOT NULL,
                embedding       vector({EMBED_DIM}),
                embedding_model text NOT NULL,
                dimension       int  NOT NULL,
                product         text NOT NULL,
                source_type     text NOT NULL,
                note_type       text NOT NULL,
                source_repo     text NOT NULL,
                source_commit   text NOT NULL,
                source_path     text NOT NULL,
                source_url      text NOT NULL,
                tags            text[] NOT NULL DEFAULT '{{}}',
                verified        boolean NOT NULL DEFAULT false,
                created_at      timestamptz NOT NULL DEFAULT now()
            )
            """,
            "CREATE INDEX IF NOT EXISTS rag_chunks_note_type_idx ON rag_chunks (note_type)",
            "CREATE INDEX IF NOT EXISTS rag_chunks_tags_gin ON rag_chunks USING GIN (tags)",
            "CREATE INDEX IF NOT EXISTS rag_chunks_embedding_ivfflat "
            "ON rag_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)",
        ]
        for stmt in statements:
            await self._session.execute(text(stmt))
        await self._session.flush()

    async def upsert(self, entries: Iterable[VectorEntry]) -> None:
        """INSERT ... ON CONFLICT (chunk_id) DO UPDATE. dimension = len(embedding) stamp.

        bsvibe ``PgVectorBackend.upsert`` 와 동일 wire-shape. 임베딩은 pgvector
        리터럴 + ``CAST(:embedding AS vector)``, 모델·차원을 행에 stamp.
        """
        sql = text(
            """
            INSERT INTO rag_chunks
                (chunk_id, note_id, source_id, chunk_index, text, char_count,
                 embedding, embedding_model, dimension,
                 product, source_type, note_type, source_repo, source_commit,
                 source_path, source_url, tags, verified, created_at)
            VALUES
                (:chunk_id, :note_id, :source_id, :chunk_index, :text, :char_count,
                 CAST(:embedding AS vector), :embedding_model, :dimension,
                 :product, :source_type, :note_type, :source_repo, :source_commit,
                 :source_path, :source_url, :tags, :verified, :created_at)
            ON CONFLICT (chunk_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                dimension = EXCLUDED.dimension,
                text = EXCLUDED.text
            """
        )
        for e in entries:
            md = e.chunk.metadata
            await self._session.execute(
                sql,
                {
                    "chunk_id": e.chunk.chunk_id,
                    "note_id": e.chunk.note_id,
                    "source_id": e.chunk.source_id,
                    "chunk_index": e.chunk.chunk_index,
                    "text": e.chunk.text,
                    "char_count": e.chunk.char_count,
                    "embedding": to_pgvector_literal(e.embedding),
                    "embedding_model": e.embedding_model,
                    "dimension": len(e.embedding),
                    "product": md["product"],
                    "source_type": md["source_type"],
                    "note_type": md["note_type"],
                    "source_repo": md["source_repo"],
                    "source_commit": md["source_commit"],
                    "source_path": md["source_path"],
                    "source_url": md["source_url"],
                    "tags": list(md.get("tags", [])),
                    "verified": bool(md.get("verified", False)),
                    "created_at": datetime.fromisoformat(md["created_at"]),
                },
            )
        await self._session.flush()

    async def count(self) -> int:
        """적재된 행 수 (루브릭: chunk 수 == DB count 검증)."""
        result = await self._session.execute(text("SELECT count(*) FROM rag_chunks"))
        return int(result.scalar() or 0)

    async def search(
        self,
        *,
        query: list[float],
        limit: int = 5,
        note_types: list[str] | None = None,
        product: str | None = None,
        verified_only: bool = False,
    ) -> list[SearchHit]:
        """코사인 검색. ``embedding <=> CAST(:qv AS vector)``, similarity = 1 - distance.

        bsvibe ``PgVectorBackend.search`` 미러: cosine_distance = 1 - cosine_similarity
        이므로 similarity = ``1 - distance``.
        """
        conditions = ["embedding IS NOT NULL"]
        params: dict = {"qv": to_pgvector_literal(query), "lim": limit}
        if note_types:
            conditions.append("note_type = ANY(:note_types)")
            params["note_types"] = note_types
        if product:
            conditions.append("product = :product")
            params["product"] = product
        if verified_only:
            conditions.append("verified = true")
        where = " AND ".join(conditions)
        sql = text(
            f"""
            SELECT chunk_id, note_id, source_id, text, source_url, note_type,
                   embedding <=> CAST(:qv AS vector) AS distance
            FROM rag_chunks
            WHERE {where}
            ORDER BY embedding <=> CAST(:qv AS vector)
            LIMIT :lim
            """
        )
        result = await self._session.execute(sql, params)
        return [
            SearchHit(
                chunk_id=r["chunk_id"],
                note_id=r["note_id"],
                source_id=r["source_id"],
                text=r["text"],
                source_url=r["source_url"],
                note_type=r["note_type"],
                similarity=1.0 - float(r["distance"]),
            )
            for r in result.mappings()
        ]
