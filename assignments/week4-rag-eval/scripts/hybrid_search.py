"""Week4 EXP-1 — Hybrid retrieval: Vector + BM25 + Graph fused via RRF.

bsvibe-app `backend/knowledge/retrieval/hybrid_search.py` 의 RRF (Reciprocal
Rank Fusion) 패턴을 그대로 이식. 차이점은 인터페이스 단위:

- **원본 (bsvibe)**: entity 단위 GraphBackend 위에서 fusion → ``SearchResult``
  (GraphEntity + per-method rank).
- **이식 (week4)**: chunk 단위 RAG 컨텍스트가 필요하므로 fusion 결과를
  ``source_id`` 로 집계 → ``HybridHit`` (SearchHit + per-method rank).

세 갈래 검색 모두 ``limit*2`` 까지 가져온 뒤 RRF 점수
``sum(1 / (rrf_k + rank))`` 로 결합. ``rrf_k=60`` 은 원본 RRF 논문 표준값.

실패한 검색 한 갈래는 빈 리스트로 graceful degrade — bsvibe ``hybrid_search``
의 ``return_exceptions=True`` + ``_ok()`` 패턴 그대로.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import networkx as nx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# week3 자산 재사용 — bm25 baseline + pgvector store + 그래프 JSON
WEEK3_SCRIPTS = Path(__file__).resolve().parents[2] / "week3-rag-db" / "scripts"
WEEK3_DATA = Path(__file__).resolve().parents[2] / "week3-rag-db" / "data"
sys.path.insert(0, str(WEEK3_SCRIPTS))

from bm25_baseline import (  # type: ignore  # noqa: E402
    CHUNKS_PATH,
    bm25_ranked_source_ids,
    load_chunks_as_docs,
    tokenize as bm25_tokenize,
)
from graph_store import normalize_name  # type: ignore  # noqa: E402
from vector_store import RagVectorStore, SearchHit, embed_texts  # type: ignore  # noqa: E402

DEFAULT_RRF_K = 60

# ─── Chunk 메타 룩업 (source_id → 본문/제목) ──────────────────────────────────

def _load_chunk_lookup() -> dict[str, dict[str, Any]]:
    """source_id → 첫 chunk 의 (text, title, source_url, note_type) 매핑.

    Hybrid 결과를 SearchHit 호환 객체로 만들어 baseline pipeline 이 그대로
    받게 하기 위함.
    """
    lookup: dict[str, dict[str, Any]] = {}
    for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        sid = d["source_id"]
        if sid not in lookup:
            md = d["metadata"]
            lookup[sid] = {
                "chunk_id": d["chunk_id"],
                "note_id": d["note_id"],
                "text": d["text"],
                "title": md.get("title", ""),
                "source_url": md.get("source_url", ""),
                "note_type": md.get("note_type", ""),
            }
    return lookup


# ─── 그래프 로드 (week3 knowledge_graph.json) ─────────────────────────────────

def load_knowledge_graph(path: Path | None = None) -> nx.MultiDiGraph:
    p = path or WEEK3_DATA / "knowledge_graph.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    g: nx.MultiDiGraph = nx.node_link_graph(data, edges="links", multigraph=True, directed=True)
    return g


# ─── 결과 컨테이너 ────────────────────────────────────────────────────────────

@dataclass(slots=True)
class HybridHit:
    """RRF 결합 결과 한 건. SearchHit 호환 + per-method rank.

    ``matched_via`` 는 어떤 method 가 이 결과를 기여했는지 정렬 리스트.
    """

    source_id: str
    chunk_id: str
    note_id: str
    text: str
    title: str
    source_url: str
    note_type: str
    score: float
    bm25_rank: int | None = None
    vector_rank: int | None = None
    graph_rank: int | None = None
    matched_via: list[str] = field(default_factory=list)
    # SearchHit 호환을 위해 (질문생성 pipeline 에서 .similarity 를 기대) — RRF 점수.
    similarity: float = 0.0


# ─── 개별 retriever (각각 source_id 리스트를 rank 순서로 반환) ────────────────

async def bm25_search(question: str, *, limit: int) -> list[str]:
    """BM25 검색. week3 bm25_baseline.bm25_ranked_source_ids 그대로."""
    docs = load_chunks_as_docs(CHUNKS_PATH)
    tokens = bm25_tokenize(question)
    return [sid for sid, _ in bm25_ranked_source_ids(docs, tokens)[:limit]]


async def vector_search(question: str, *, engine, limit: int) -> list[str]:
    """pgvector 검색. week3 RagVectorStore 그대로."""
    emb = (await embed_texts([question]))[0]
    async with AsyncSession(engine) as s:
        store = RagVectorStore(s)
        hits = await store.search(query=emb, limit=limit)
    return [h.source_id for h in hits]


async def graph_search(
    question: str,
    *,
    graph: nx.MultiDiGraph,
    chunk_lookup: dict[str, dict[str, Any]],
    limit: int,
) -> list[str]:
    """그래프 검색 — bsvibe ``_graph_search`` 의 substring + 1-hop 이웃 패턴.

    1. 질문 토큰에서 graph 노드 이름과 substring 매칭되는 seed entity 찾기
       (bsvibe ``backend.search_entities`` 와 동일 의미).
    2. 각 seed 의 1-hop 이웃까지 확장 (bsvibe ``multi_hop_query(max_hops=1)``).
    3. 모은 entity 이름들로 chunk text 를 다시 substring 매칭해서 source_id 회수.

    Step 3 는 우리 그래프가 chunk provenance 를 stamping 하지 않아서 추가된
    역매핑. bsvibe 는 노드 자체가 source_path 를 들고 있으므로 불필요.
    """
    q_lower = question.casefold()
    q_tokens = [t for t in bm25_tokenize(question) if len(t) >= 3]
    if not q_tokens:
        return []

    # 1. seed entity — node name 토큰 중 질문 토큰과 겹치거나 질문 본문에 포함된 것
    seed_ids: list[str] = []
    for node_id, attrs in graph.nodes(data=True):
        name = (attrs.get("name") or "").casefold()
        if not name:
            continue
        if name in q_lower or any(tok in name or name in tok for tok in q_tokens):
            seed_ids.append(node_id)
        if len(seed_ids) >= 5:
            break

    if not seed_ids:
        return []

    # 2. 1-hop 이웃 확장 (방향 무관)
    related_names: list[str] = []
    seen_nodes: set[str] = set()
    for seed in seed_ids:
        if seed not in seen_nodes:
            seen_nodes.add(seed)
            related_names.append(graph.nodes[seed].get("name", ""))
        # 1-hop 이웃
        for nbr in list(graph.successors(seed)) + list(graph.predecessors(seed)):
            if nbr in seen_nodes:
                continue
            seen_nodes.add(nbr)
            related_names.append(graph.nodes[nbr].get("name", ""))

    related_names = [n for n in related_names if n]
    if not related_names:
        return []

    # 3. entity 이름 → chunk text substring 매칭 → source_id (등장 횟수로 ranking)
    scores: dict[str, int] = {}
    for sid, meta in chunk_lookup.items():
        body = (meta["title"] + " " + meta["text"]).casefold()
        hits = 0
        for name in related_names:
            n = name.casefold()
            if n and n in body:
                hits += 1
        if hits:
            scores[sid] = hits

    ordered = sorted(scores.items(), key=lambda x: -x[1])
    return [sid for sid, _ in ordered[:limit]]


# ─── RRF fusion (bsvibe hybrid_search.hybrid_search 의 RRF 블록 그대로) ──────

def reciprocal_rank_fusion(
    ranked_lists: dict[str, list[str]],
    *,
    rrf_k: int = DEFAULT_RRF_K,
) -> tuple[list[tuple[str, float]], dict[str, dict[str, int]]]:
    """method 이름 → ranked source_id 리스트. (sorted_sid_score, per-method rank)."""
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    for method, ids in ranked_lists.items():
        for rank, sid in enumerate(ids, start=1):
            scores[sid] = scores.get(sid, 0.0) + 1.0 / (rrf_k + rank)
            ranks.setdefault(sid, {})[method] = rank
    ordered = sorted(scores.items(), key=lambda x: -x[1])
    return ordered, ranks


# ─── 메인 entry point ─────────────────────────────────────────────────────────

async def hybrid_search(
    question: str,
    *,
    engine,
    graph: nx.MultiDiGraph | None = None,
    chunk_lookup: dict[str, dict[str, Any]] | None = None,
    limit: int = 5,
    rrf_k: int = DEFAULT_RRF_K,
    enabled_methods: Iterable[str] = ("bm25", "vector", "graph"),
) -> list[HybridHit]:
    """bsvibe 패턴: 세 갈래 검색 병렬 실행 → 빈 결과는 graceful 무시 → RRF."""
    if graph is None:
        graph = load_knowledge_graph()
    if chunk_lookup is None:
        chunk_lookup = _load_chunk_lookup()

    methods = set(enabled_methods)
    tasks = []
    task_names = []
    if "bm25" in methods:
        tasks.append(bm25_search(question, limit=limit * 2))
        task_names.append("bm25")
    if "vector" in methods:
        tasks.append(vector_search(question, engine=engine, limit=limit * 2))
        task_names.append("vector")
    if "graph" in methods:
        tasks.append(graph_search(question, graph=graph, chunk_lookup=chunk_lookup, limit=limit * 2))
        task_names.append("graph")

    raw = await asyncio.gather(*tasks, return_exceptions=True)
    ranked: dict[str, list[str]] = {}
    for name, value in zip(task_names, raw, strict=True):
        if isinstance(value, BaseException):
            logger.warning("hybrid_search_method_failed", method=name, error=str(value))
            ranked[name] = []
        else:
            ranked[name] = value

    ordered, ranks = reciprocal_rank_fusion(ranked, rrf_k=rrf_k)
    results: list[HybridHit] = []
    for sid, score in ordered[:limit]:
        meta = chunk_lookup.get(sid)
        if not meta:
            continue
        per = ranks.get(sid, {})
        results.append(
            HybridHit(
                source_id=sid,
                chunk_id=meta["chunk_id"],
                note_id=meta["note_id"],
                text=meta["text"],
                title=meta["title"],
                source_url=meta["source_url"],
                note_type=meta["note_type"],
                score=score,
                bm25_rank=per.get("bm25"),
                vector_rank=per.get("vector"),
                graph_rank=per.get("graph"),
                matched_via=sorted(per.keys()),
                similarity=score,  # SearchHit 호환 — pipeline 이 .similarity 사용
            )
        )

    logger.info(
        "hybrid_search",
        question=question[:60],
        bm25=len(ranked.get("bm25", [])),
        vector=len(ranked.get("vector", [])),
        graph=len(ranked.get("graph", [])),
        fused=len(results),
    )
    return results


# ─── 직접 실행 시 스모크 ──────────────────────────────────────────────────────

async def _smoke() -> None:
    import os
    from dotenv import load_dotenv
    from sqlalchemy.ext.asyncio import create_async_engine

    load_dotenv()
    os.environ.setdefault("OPENAI_API_KEY", "sk-noop")

    engine = create_async_engine("postgresql+asyncpg://rag:rag@localhost:5433/rag_week3")
    try:
        graph = load_knowledge_graph()
        lookup = _load_chunk_lookup()
        for q in [
            "BSVibe 모노레포는 어떤 구성으로 돌아가나요?",
            "파운더가 잘못된 노드를 retract하면 어떤 흐름으로 처리되나요?",
        ]:
            print(f"Q: {q}")
            hits = await hybrid_search(q, engine=engine, graph=graph, chunk_lookup=lookup, limit=5)
            for i, h in enumerate(hits, 1):
                via = "+".join(h.matched_via)
                print(
                    f"  {i}. score={h.score:.4f}  via={via:<14}  {h.source_id:18}  "
                    f"bm25={h.bm25_rank} vec={h.vector_rank} graph={h.graph_rank}  {h.title[:42]}"
                )
            print()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_smoke())
