"""Week3 BM25 sparse baseline — dense pgvector 가 넘어야 할 floor 측정.

VectorRAG (text-embedding-3-small) 가 golden 15문항에서 Hit@1=80%, Hit@3=100%, MRR=0.878
를 찍는다는 사실 자체로는 "충분히 좋다" 인지 판단 어렵습니다. 같은 데이터셋·같은 검색
인터페이스에 대해 sparse baseline (BM25) 을 동일 metric 으로 계산해 둬야, 다음과 같이
정량 비교할 수 있습니다.

  Hit@1: 0.533 (sparse) → 0.800 (dense, +26.7%p)
  Hit@3: 0.700 → 1.000 (+30.0%p)
  MRR  : 0.654 → 0.878 (+0.224)

dense embedding 도입의 정당화 근거이자, 다음 단계 (rerank/hybrid) 의 비교 기준입니다.

구현 요점:
- pure stdlib (numpy/sklearn 사용 안 함). BM25 (k1=1.5, b=0.75).
- doc = ``chunk.text + title + tags`` (chunk 단위, title/tags 짧아 자연스럽게 가중).
- 한영 혼합 토큰화: ``[^a-z0-9가-힣]+`` 으로 split, 한국어 의문/연결어 + 영문 기능어 stopword.
- 점수 dedup: 같은 ``source_id`` 의 여러 chunk 중 max score 만 남겨 source_id 단위 랭킹.
- metric: ``01_vector_rag.ipynb`` 와 동일한 Hit@1/@3, MRR — 직접 비교 가능.

실행::

    python assignments/week3-rag-db/scripts/bm25_baseline.py
"""

from __future__ import annotations

import json
import math
import re
import statistics as st
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = (
    REPO_ROOT
    / "assignments"
    / "week2-rag-dataset"
    / "data"
    / "processed"
    / "rag_chunks.jsonl"
)
GOLDEN_PATH = (
    REPO_ROOT
    / "assignments"
    / "week2-rag-dataset"
    / "data"
    / "eval"
    / "retrieval_golden.jsonl"
)

# BM25 하이퍼파라미터: 검색 분야 표준값.
K1 = 1.5
B = 0.75

# 한국어 의문/연결어 + 영문 기능어. 너무 짧은 토큰(len<2) 도 함께 cut.
_TOKEN_RE = re.compile(r"[^a-z0-9가-힣]+")
_STOPWORDS: frozenset[str] = frozenset(
    {
        # 영문
        "the", "and", "for", "with", "from", "into", "onto", "this", "that",
        "these", "those", "have", "has", "had", "was", "were", "are", "but",
        "not", "via", "per", "out", "off", "its", "our", "your", "their",
        "use", "used", "new", "now", "all", "any", "can", "did", "done",
        "then", "than", "what", "when", "where", "why", "how", "which",
        # 한국어 의문/연결어 (golden 질문의 노이즈 제거)
        "어떻게", "어떤", "어디", "어디서", "어디에", "무엇", "무엇을",
        "있나요", "있는지", "있는", "있다", "없는", "없다", "없나요",
        "하나요", "하는", "할지", "되나요", "되는", "되어", "돼요",
        "그리고", "또한", "하지만", "그러나", "어떻게요", "있을까요",
        "어떻게나", "어떤지", "있을지", "되는지", "되는가", "할까요",
        "기준", "관련", "관련된", "주로", "대신", "그대로", "다음",
        "이번", "현재", "당시", "지금", "처음", "마지막", "통해", "위해",
        "통한", "위한", "같은", "같이", "다르게", "이렇게", "저렇게",
    }
)


@dataclass(slots=True)
class Doc:
    """BM25 색인 단위 — chunk 한 개의 토큰화 결과."""

    chunk_id: str
    source_id: str
    tokens: list[str]


def tokenize(text: str) -> list[str]:
    """한영 혼합 토큰화 + stopword 제거 + len<2 cut."""
    return [
        t
        for t in _TOKEN_RE.split(text.casefold())
        if t and len(t) >= 2 and t not in _STOPWORDS
    ]


def load_chunks_as_docs(path: Path) -> list[Doc]:
    """rag_chunks.jsonl → ``Doc`` 리스트.

    doc body = ``text + title + " ".join(tags)`` — title/tags 가 짧아 결과적으로
    chunk 본문보다 가중치가 자연스럽게 ↑ (BM25 의 idf · length norm 효과).
    """
    docs: list[Doc] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        md = d.get("metadata") or {}
        body = " ".join(
            [d.get("text", ""), md.get("title", ""), " ".join(md.get("tags") or [])]
        )
        docs.append(
            Doc(chunk_id=d["chunk_id"], source_id=d["source_id"], tokens=tokenize(body))
        )
    return docs


def bm25_ranked_source_ids(
    docs: list[Doc], query_tokens: list[str], *, k1: float = K1, b: float = B
) -> list[tuple[str, float]]:
    """모든 chunk 점수 → 같은 source_id 안에서 max → source_id 단위 내림차순."""
    if not docs or not query_tokens:
        return []
    n = len(docs)
    avgdl = sum(len(d.tokens) for d in docs) / n
    df: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc.tokens):
            df[term] += 1
    by_source: dict[str, float] = {}
    for doc in docs:
        dl = len(doc.tokens)
        if not dl:
            continue
        tf = Counter(doc.tokens)
        score = 0.0
        for term in query_tokens:
            n_q = df.get(term, 0)
            if not n_q:
                continue
            idf = math.log((n - n_q + 0.5) / (n_q + 0.5) + 1)
            f = tf.get(term, 0)
            if not f:
                continue
            denom = f + k1 * (1 - b + b * dl / avgdl)
            score += idf * (f * (k1 + 1)) / denom
        if score > by_source.get(doc.source_id, float("-inf")):
            by_source[doc.source_id] = score
    return sorted(by_source.items(), key=lambda x: -x[1])


def evaluate(docs: list[Doc], golden_path: Path) -> dict:
    """01_vector_rag.ipynb 와 동일한 metric 모양으로 평가."""
    golden = [
        json.loads(line)
        for line in golden_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows: list[dict] = []
    for g in golden:
        ranked = [sid for sid, _ in bm25_ranked_source_ids(docs, tokenize(g["question"]))]
        expected = set(g["expected_source_ids"])
        rank = next((i + 1 for i, sid in enumerate(ranked) if sid in expected), None)
        rows.append(
            {
                "qid": g["qid"],
                "question": g["question"][:34],
                "hit@1": bool(ranked[:1] and ranked[0] in expected),
                "hit@3": any(sid in expected for sid in ranked[:3]),
                "rank": rank,
                "top5": ranked[:5],
            }
        )
    hit1 = sum(r["hit@1"] for r in rows) / len(rows) if rows else 0.0
    hit3 = sum(r["hit@3"] for r in rows) / len(rows) if rows else 0.0
    mrr = sum((1 / r["rank"]) if r["rank"] else 0 for r in rows) / len(rows) if rows else 0.0
    ranks = [r["rank"] for r in rows if r["rank"]]
    return {
        "rows": rows,
        "hit@1": hit1,
        "hit@3": hit3,
        "mrr": mrr,
        "rank_stats": {
            "matched": len(ranks),
            "unmatched": len(rows) - len(ranks),
            "median": st.median(ranks) if ranks else None,
        },
    }


def main() -> None:
    docs = load_chunks_as_docs(CHUNKS_PATH)
    print(f"chunks loaded: {len(docs)} (평균 토큰 {round(st.mean([len(d.tokens) for d in docs]), 1)}개)")

    result = evaluate(docs, GOLDEN_PATH)

    print("\n=== BM25 sparse baseline (golden 15문항) ===")
    print(f"{'qid':6} {'hit@1':>6} {'hit@3':>6} {'rank':>5}  question")
    for r in result["rows"]:
        print(
            f"{r['qid']:6} {str(r['hit@1']):>6} {str(r['hit@3']):>6} "
            f"{str(r['rank']):>5}  {r['question']}"
        )
    print()
    print(
        f"Hit@1 = {result['hit@1']:.1%}   "
        f"Hit@3 = {result['hit@3']:.1%}   "
        f"MRR = {result['mrr']:.3f}"
    )
    stats = result["rank_stats"]
    print(
        f"rank: matched {stats['matched']}/{len(result['rows'])} "
        f"(unmatched {stats['unmatched']}), median rank {stats['median']}"
    )

    print("\n=== dense (text-embedding-3-small) 대비 ===")
    dense = {"hit@1": 0.800, "hit@3": 1.000, "mrr": 0.878}
    print(f"          {'sparse(BM25)':>13}  {'dense':>7}  {'gain':>6}")
    for m in ("hit@1", "hit@3", "mrr"):
        s, d = result[m], dense[m]
        gain = d - s
        unit = "p" if m.startswith("hit") else ""
        print(f"{m:8}: {s:>13.3f}  {d:>7.3f}  +{gain:.3f}{unit}")


if __name__ == "__main__":
    main()
