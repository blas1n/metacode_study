"""Week3 VectorRAG 빌드 CLI — rag_chunks.jsonl → litellm 임베딩 → pgvector 적재.

bsvibe-app 의 임베딩 파이프라인(load → embed → upsert)을 스터디용 단일 진입점으로
엮습니다. 실제 OpenAI 임베딩 호출 + 실제 pgvector 컨테이너에 적재합니다.

실행::

    docker compose -f assignments/week3-rag-db/docker-compose.yml up -d
    python assignments/week3-rag-db/scripts/build_vector_db.py

검증(루브릭)::

    - 차원: 적재 후 모든 행 dimension == 1536 == vector(1536)
    - count: SELECT count(*) == 입력 chunk 수
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import structlog
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from vector_store import (
    EMBED_DIM,
    EMBED_MODEL,
    RagVectorStore,
    VectorEntry,
    embed_texts,
    load_chunks,
)

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = (
    REPO_ROOT
    / "assignments"
    / "week2-rag-dataset"
    / "data"
    / "processed"
    / "rag_chunks.jsonl"
)
DEFAULT_DSN = "postgresql+asyncpg://rag:rag@localhost:5433/rag_week3"


async def build(dsn: str, chunks_path: Path) -> dict:
    """전체 파이프라인 실행 후 검증 지표 dict 반환."""
    chunks = load_chunks(chunks_path)
    logger.info("chunks_loaded", count=len(chunks), path=str(chunks_path))

    embeddings = await embed_texts([c.text for c in chunks], model=EMBED_MODEL)
    dims = {len(e) for e in embeddings}
    logger.info("embedded", model=EMBED_MODEL, dims=sorted(dims))

    entries = [
        VectorEntry(chunk=c, embedding=emb, embedding_model=EMBED_MODEL)
        for c, emb in zip(chunks, embeddings, strict=True)
    ]

    engine = create_async_engine(dsn)
    try:
        async with AsyncSession(engine) as session:
            store = RagVectorStore(session)
            # 모델/차원 변경 시 안전하게 새로 빌드. 운영 환경이면 false 로.
            await store.create_schema(drop_existing=True)
            await store.upsert(entries)
            await session.commit()
            db_count = await store.count()
    finally:
        await engine.dispose()

    return {
        "embedding_model": EMBED_MODEL,
        "expected_dim": EMBED_DIM,
        "observed_dims": sorted(dims),
        "chunk_count": len(chunks),
        "db_count": db_count,
        "dim_match": dims == {EMBED_DIM},
        "count_match": db_count == len(chunks),
    }


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY 가 .env 에 없습니다.")
    dsn = os.getenv("RAG_DB_DSN", DEFAULT_DSN)

    report = asyncio.run(build(dsn, CHUNKS_PATH))

    print("\n=== VectorRAG 적재 검증 ===")
    print(f"임베딩 모델      : {report['embedding_model']}")
    print(f"기대 차원        : {report['expected_dim']}")
    print(
        f"실측 차원        : {report['observed_dims']}  -> 일치: {report['dim_match']}"
    )
    print(f"입력 chunk 수    : {report['chunk_count']}")
    print(f"DB 적재 count    : {report['db_count']}  -> 일치: {report['count_match']}")
    if not (report["dim_match"] and report["count_match"]):
        raise SystemExit("검증 실패: 차원 또는 count 불일치")
    print("검증 통과 ✅")


if __name__ == "__main__":
    main()
