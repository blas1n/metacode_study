#!/usr/bin/env python3
"""Analyze the cleaned BSVibe RAG dataset and write a Markdown report."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any


# Reference budgets for popular embedding stacks (tokens, approximated as chars * 0.27
# for English-heavy text). We only report whether the dataset fits — no truncation here.
EMBEDDING_BUDGETS = {
    "openai/text-embedding-3-small": 8191,
    "openai/text-embedding-3-large": 8191,
    "cohere/embed-multilingual-v3": 512,
    "bge-m3": 8192,
}

# Chunk-size sensitivity sweep: simulate how the same content splits at different budgets.
CHUNK_BUDGET_SWEEP = (256, 384, 512, 768)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def pct(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(part / total * 100, 1)


def length_stats(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0, "max": 0, "mean": 0, "median": 0, "p90": 0}
    sorted_values = sorted(values)
    p90_idx = max(0, int(round(0.9 * (len(sorted_values) - 1))))
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 1),
        "median": round(statistics.median(values), 1),
        "p90": sorted_values[p90_idx],
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(output)


def tag_cooccurrence(notes: list[dict[str, Any]], top_n: int = 10) -> list[tuple[str, str, int]]:
    """Top tag pairs by co-occurrence count — signals which retrieval facets cluster."""
    pair_counts: Counter[tuple[str, str]] = Counter()
    for note in notes:
        tags = sorted(set(note.get("tags") or []))
        for left, right in combinations(tags, 2):
            pair_counts[(left, right)] += 1
    return [(left, right, count) for (left, right), count in pair_counts.most_common(top_n)]


def duplicate_groups(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group notes by content_sha256 — flags exact duplicates the dedupe pass missed."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        digest = note.get("content_sha256", "")
        if digest:
            by_hash[digest].append(str(note.get("source_id", note.get("note_id", ""))))
    return [
        {"content_sha256": digest, "source_ids": ids}
        for digest, ids in by_hash.items()
        if len(ids) > 1
    ]


def source_directory_coverage(notes: list[dict[str, Any]]) -> dict[str, int]:
    """How many notes per top-level directory of the source repo — coverage breadth."""
    counts: Counter[str] = Counter()
    for note in notes:
        path = str(note.get("source_path") or "")
        if not path:
            counts["(unknown)"] += 1
            continue
        head = path.split("/", 1)[0] if "/" in path else path
        counts[head] += 1
    return dict(counts.most_common())


def chunk_budget_sweep(notes: list[dict[str, Any]], budgets: tuple[int, ...]) -> dict[int, int]:
    """For each budget, count how many chunks the dataset would produce — chunking sensitivity."""
    paragraph_split = re.compile(r"\n+|(?<=[.!?。])\s+")
    result: dict[int, int] = {}
    for budget in budgets:
        total = 0
        for note in notes:
            text = str(note.get("content") or "")
            paragraphs = [p.strip() for p in paragraph_split.split(text) if p.strip()]
            current = ""
            count = 0
            for paragraph in paragraphs:
                candidate = f"{current} {paragraph}".strip()
                if len(candidate) <= budget:
                    current = candidate
                    continue
                if current:
                    count += 1
                if len(paragraph) <= budget:
                    current = paragraph
                else:
                    count += -(-len(paragraph) // budget)
                    current = ""
            if current:
                count += 1
            total += max(count, 1)
        result[budget] = total
    return result


def embedding_budget_fit(chunk_lengths: list[int]) -> dict[str, dict[str, Any]]:
    """For each reference embedding model, report whether chunks fit (approx tokens)."""
    if not chunk_lengths:
        return {}
    max_chars = max(chunk_lengths)
    approx_max_tokens = max(1, int(round(max_chars * 0.27)))
    fits: dict[str, dict[str, Any]] = {}
    for model, ctx_tokens in EMBEDDING_BUDGETS.items():
        fits[model] = {
            "context_tokens": ctx_tokens,
            "approx_max_chunk_tokens": approx_max_tokens,
            "fits_without_truncation": approx_max_tokens <= ctx_tokens,
        }
    return fits


def analyze(notes: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(str(note["source_type"]) for note in notes)
    note_type_counts = Counter(str(note["note_type"]) for note in notes)
    source_path_counts = Counter(str(note.get("source_path", "unknown")) for note in notes)
    source_repo_counts = Counter(str(note.get("source_repo", "unknown")) for note in notes)
    tag_counts = Counter(tag for note in notes for tag in note["tags"])
    verified_count = sum(1 for note in notes if note["verified"])
    quality_flag_count = sum(len(note["quality_flags"]) for note in notes)
    chunk_lengths = [int(chunk["char_count"]) for chunk in chunks]
    note_lengths = [len(str(note["content"])) for note in notes]
    chunks_per_note = Counter(chunk["note_id"] for chunk in chunks)
    multi_chunk_notes = sum(1 for c in chunks_per_note.values() if c > 1)
    source_links = [
        {
            "title": note["title"],
            "source_path": note.get("source_path", ""),
            "source_url": note.get("source_url", ""),
        }
        for note in notes
        if note.get("source_url")
    ]

    return {
        "total_notes": len(notes),
        "total_chunks": len(chunks),
        "verified_notes": verified_count,
        "verified_ratio": pct(verified_count, len(notes)),
        "quality_flag_count": quality_flag_count,
        "duplicate_groups": duplicate_groups(notes),
        "source_counts": dict(source_counts.most_common()),
        "note_type_counts": dict(note_type_counts.most_common()),
        "source_directory_coverage": source_directory_coverage(notes),
        "source_path_counts": dict(source_path_counts.most_common()),
        "source_repo_counts": dict(source_repo_counts.most_common()),
        "top_tags": dict(tag_counts.most_common(15)),
        "top_tag_pairs": [
            {"left": left, "right": right, "count": count}
            for left, right, count in tag_cooccurrence(notes, top_n=10)
        ],
        "note_length_stats": length_stats(note_lengths),
        "chunk_length_stats": length_stats(chunk_lengths),
        "chunks_per_note": {
            "mean": round(statistics.mean(chunks_per_note.values()), 2) if chunks_per_note else 0,
            "max": max(chunks_per_note.values()) if chunks_per_note else 0,
            "multi_chunk_notes": multi_chunk_notes,
        },
        "chunk_budget_sweep": chunk_budget_sweep(notes, CHUNK_BUDGET_SWEEP),
        "embedding_budget_fit": embedding_budget_fit(chunk_lengths),
        "source_links": source_links,
        "db_readiness": {
            "metadata_filters": [
                "product",
                "source_repo",
                "source_commit",
                "source_path",
                "source_type",
                "note_type",
                "tags",
                "verified",
                "created_at",
            ],
            "embedding_text_field": "text",
            "provenance_fields": [
                "chunk_id",
                "note_id",
                "source_id",
                "metadata.title",
                "metadata.source_url",
                "metadata.source_path",
            ],
        },
    }


def _pgvector_schema_block() -> str:
    return """```sql
-- pgvector 적재용 최소 스키마 (다음 주차에 그대로 옮길 수 있도록 한 곳에 정리)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_chunks (
    chunk_id        text PRIMARY KEY,
    note_id         text NOT NULL,
    source_id       text NOT NULL,
    chunk_index     int  NOT NULL,
    text            text NOT NULL,
    char_count      int  NOT NULL,
    embedding       vector(1024),                 -- bge-m3 / 임베딩 모델에 맞춰 차원 조정
    product         text NOT NULL,
    source_type     text NOT NULL,
    note_type       text NOT NULL,
    source_repo     text NOT NULL,
    source_commit   text NOT NULL,
    source_path     text NOT NULL,
    source_url      text NOT NULL,
    tags            text[] NOT NULL DEFAULT '{}',
    verified        boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL
);

-- citation/필터링 자주 쓰는 컬럼에 단일 인덱스
CREATE INDEX rag_chunks_source_path_idx ON rag_chunks (source_path);
CREATE INDEX rag_chunks_note_type_idx   ON rag_chunks (note_type);
CREATE INDEX rag_chunks_tags_gin        ON rag_chunks USING GIN (tags);

-- 검색용 ANN 인덱스 (코사인). lists 는 데이터 규모에 따라 조정.
CREATE INDEX rag_chunks_embedding_ivfflat
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

검색 쿼리는 보통 다음 패턴입니다.

```sql
-- workspace/product/note_type 로 필터링한 뒤 코사인 거리 정렬 + citation 동시 반환
SELECT chunk_id, note_id, text, source_url, source_path, note_type,
       embedding <=> $1 AS distance
FROM rag_chunks
WHERE product = $2
  AND note_type = ANY($3)
  AND verified = true
ORDER BY embedding <=> $1
LIMIT $4;
```
"""


def build_report(summary: dict[str, Any]) -> str:
    source_rows = [[key, value] for key, value in summary["source_counts"].items()]
    note_type_rows = [[key, value] for key, value in summary["note_type_counts"].items()]
    source_path_rows = [[key, value] for key, value in summary["source_path_counts"].items()]
    tag_rows = [[key, value] for key, value in summary["top_tags"].items()]
    tag_pair_rows = [
        [pair["left"], pair["right"], pair["count"]] for pair in summary["top_tag_pairs"]
    ]
    directory_rows = [[key, value] for key, value in summary["source_directory_coverage"].items()]
    chunk_sweep_rows = [
        [f"max_chunk_chars={budget}", count]
        for budget, count in summary["chunk_budget_sweep"].items()
    ]
    embedding_rows = [
        [
            model,
            info["context_tokens"],
            info["approx_max_chunk_tokens"],
            "fit" if info["fits_without_truncation"] else "truncate",
        ]
        for model, info in summary["embedding_budget_fit"].items()
    ]
    source_link_rows = [
        [item["title"], item["source_path"], f"[source]({item['source_url']})"]
        for item in summary["source_links"]
    ]

    duplicates = summary["duplicate_groups"]
    duplicate_line = (
        "exact-duplicate group 없음 (content_sha256 기준)"
        if not duplicates
        else f"⚠️ {len(duplicates)}개 exact-duplicate group 발견 — `analysis_summary.json` 의 `duplicate_groups` 참고"
    )

    chunks_per_note = summary["chunks_per_note"]
    note_stats = summary["note_length_stats"]
    chunk_stats = summary["chunk_length_stats"]

    return f"""# 2주차 RAG 데이터셋 정제 및 분석 결과

## 1. 데이터셋 개요

실제 `BSVibe/bsvibe-app` 코드베이스를 분석해, 개인화 작업 메모리 RAG에 사용할 source-derived seed dataset 을 구성했습니다. 사용자 데이터가 아니라 구현 파일, 런타임 배선, 프론트 surface, 운영 문서, 검증 테스트에서 확인한 구조적 사실을 record 로 만들었습니다.

- 정제된 note 수: **{summary["total_notes"]}**
- RAG chunk 수: **{summary["total_chunks"]}** (note 당 평균 {chunks_per_note["mean"]} chunk, 최대 {chunks_per_note["max"]})
- 검증 완료 note 비율: {summary["verified_notes"]}/{summary["total_notes"]} ({summary["verified_ratio"]}%)
- 품질 flag 수: {summary["quality_flag_count"]} · {duplicate_line}
- source repo: {", ".join(summary["source_repo_counts"].keys())}

## 2. 정제 자동화 결과

정제 스크립트는 다음을 자동화합니다.

- JSONL record 필수 필드 검증과 ISO-8601 created_at 파싱
- 이메일, API key (`sk-/pk-/ghp-/github_pat-…`), 로컬 경로 redaction
- 공백 정규화, 태그 소문자/하이픈 형태 정규화
- `source_type` 기반 `note_type` 자동 매핑 (operational 포함)
- GitHub `source_url`, `source_path`, `source_commit`, line range 보존
- 외부 DB 적재용 provenance field (`note_id`, `source_id`, `content_sha256`) 생성
- embedding 대상 text 를 paragraph 경계에서 chunk 로 분할

## 3. Source / Note Type 분포

{markdown_table(["source_type", "count"], source_rows)}

{markdown_table(["note_type", "count"], note_type_rows)}

## 4. Source 디렉토리 coverage

어느 영역을 얼마나 다뤘는지 한눈에 보기 위한 디렉토리 단위 집계입니다.

{markdown_table(["top-level directory", "count"], directory_rows)}

## 5. Source path 분포

{markdown_table(["source_path", "count"], source_path_rows)}

## 6. 상위 태그 / 태그 공출현

가장 자주 묶이는 태그 페어는 RAG 검색 facet 후보입니다.

{markdown_table(["tag", "count"], tag_rows)}

{markdown_table(["tag_left", "tag_right", "co_occurrence"], tag_pair_rows) if tag_pair_rows else "_공출현 페어 없음._"}

## 7. 길이 분석 (note vs chunk)

{markdown_table(["target", "min", "max", "mean", "median", "p90"], [
    [
        "note_content_chars",
        note_stats["min"],
        note_stats["max"],
        note_stats["mean"],
        note_stats["median"],
        note_stats["p90"],
    ],
    [
        "chunk_chars",
        chunk_stats["min"],
        chunk_stats["max"],
        chunk_stats["mean"],
        chunk_stats["median"],
        chunk_stats["p90"],
    ],
])}

분할 budget 을 바꿀 때 chunk 수가 어떻게 변하는지 (chunking sensitivity):

{markdown_table(["budget", "chunks"], chunk_sweep_rows)}

## 8. 임베딩 컨텍스트 적합성

각 임베딩 모델 컨텍스트 안에 chunk 최대 길이가 들어가는지 추정합니다 (대략 1 token ≈ 3.7 chars 기준).

{markdown_table(["embedding_model", "context_tokens", "approx_max_chunk_tokens", "fit"], embedding_rows)}

> `fit` 은 _가장 긴 chunk_ 가 truncation 없이 들어가는지 여부입니다. 모든 모델에서 fit 이면 chunk 추가 분할은 불필요합니다.

## 9. RAG 적재 관점 분석

다음 주차 외부 DB 구축에서 바로 쓸 수 있도록 `clean_notes.jsonl` 과 `rag_chunks.jsonl` 을 분리해뒀습니다.

- `clean_notes.jsonl`: note 단위 정제 결과. `source_id`, `title`, `content`, `tags`, `verified`, `quality_flags`, `content_sha256` 를 포함.
- `rag_chunks.jsonl`: vector DB / pgvector 에 그대로 넣는 chunk. `text` 는 embedding 대상, `metadata` 는 filter 및 citation 대상.
- 권장 metadata filter: `product`, `source_repo`, `source_commit`, `source_path`, `source_type`, `note_type`, `tags`, `verified`, `created_at`
- 권장 provenance field: `chunk_id`, `note_id`, `source_id`, `metadata.title`, `metadata.source_url`, `metadata.source_path`

### pgvector 스키마 제안

{_pgvector_schema_block()}

## 10. 데이터 특성 정리

seed dataset 은 BSVibe 구현 중 RAG 관련성이 높은 파일을 선별한 작은 데이터셋입니다. 핵심 영역은 다음과 같습니다.

- `backend/knowledge` — vault, canonicalization, retrieval, lint, watcher, graph 분석
- `backend/workflow/application/runtime` — agent runtime, settle/dispatcher 배선
- `apps/pwa/components/knowledge` — graph view, retract/correct/undo UI
- `apps/pwa/lib/api/knowledge.ts` — knowledge API 클라이언트
- `tests/glue` — runtime decision reuse 검증
- `deploy/` — 운영 런북과 prod compose

분석 결과, BSVibe RAG 데이터는 단순 문서 QA 묶음이 아닙니다. workspace-scoped vault, canonical concept, resolved decision, negative pattern, semantic note, ontology correction surface, operational runbook 을 모두 구분해야 하므로, 외부 DB 에는 `note_type` 과 `source_path` 를 반드시 보존하고 답변에는 `source_url` 을 citation 으로 노출하는 것이 적절합니다.

## 11. 소스 코드 링크

{markdown_table(["record", "source_path", "link"], source_link_rows)}

## 12. 보완 필요 사항

- 실제 서비스 데이터가 들어오면 `workspace_id`, `user_id` 같은 tenant 분리 필드가 필수입니다. 현재는 product 단일 값만 보존.
- 현재 record 는 코드 분석 기반 요약이라, 다음 단계에서 실제 vault note / frontmatter 샘플을 별도 source 로 추가해야 합니다.
- 의미가 같은 태그를 안정적으로 합치기 위한 synonym dictionary 가 필요합니다 (예: `undo-window` / `undo-toast` / `apply-at`).
- 검색 평가를 위해 질문과 expected `source_url` 을 묶은 retrieval fixture (golden set) 가 필요합니다.
- 개인화 메모리 특성상 redaction rule 을 이메일/API key/로컬 경로 외에도 전화번호, URL token, 고객명까지 확장해야 합니다.
- 한국어 문서 ingestion 까지 확장되면 `paragraph_split` 정규식과 token 환산 비율 (현재 영문 가정 0.27) 을 ko/en 분기로 두는 것이 안전합니다.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes", type=Path, default=Path("assignments/week2-rag-dataset/data/processed/clean_notes.jsonl"))
    parser.add_argument("--chunks", type=Path, default=Path("assignments/week2-rag-dataset/data/processed/rag_chunks.jsonl"))
    parser.add_argument("--summary-out", type=Path, default=Path("assignments/week2-rag-dataset/reports/analysis_summary.json"))
    parser.add_argument("--markdown-out", type=Path, default=Path("assignments/week2-rag-dataset/reports/dataset_analysis.md"))
    args = parser.parse_args()

    notes = load_jsonl(args.notes)
    chunks = load_jsonl(args.chunks)
    summary = analyze(notes, chunks)

    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_out.write_text(build_report(summary), encoding="utf-8")

    print(f"notes={summary['total_notes']} chunks={summary['total_chunks']} report={args.markdown_out}")


if __name__ == "__main__":
    main()
