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

대상 프로젝트 `BSVibe/bsvibe-app` 의 실제 코드에서 도출한 RAG seed dataset 입니다.

## 1. 개요

- note 수: **{summary["total_notes"]}**, chunk 수: **{summary["total_chunks"]}** (note 당 평균 {chunks_per_note["mean"]}, 최대 {chunks_per_note["max"]})
- verified: {summary["verified_notes"]}/{summary["total_notes"]} ({summary["verified_ratio"]}%) · 품질 flag {summary["quality_flag_count"]} · {duplicate_line}
- source repo: {", ".join(summary["source_repo_counts"].keys())}

## 2. 정제 처리

redaction (이메일 / API key / 로컬 경로) → 공백·태그 정규화 → `source_type → note_type` 매핑 → provenance (`note_id`, `content_sha256`) 부여 → paragraph 경계 기반 chunk 분할.

## 3. 분포

{markdown_table(["source_type", "count"], source_rows)}

{markdown_table(["note_type", "count"], note_type_rows)}

{markdown_table(["top-level dir", "count"], directory_rows)}

## 4. 태그

{markdown_table(["tag", "count"], tag_rows)}

자주 묶이는 페어:

{markdown_table(["tag_left", "tag_right", "co_occurrence"], tag_pair_rows) if tag_pair_rows else "_공출현 페어 없음._"}

## 5. 길이

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

분할 budget 변경 시 chunk 수:

{markdown_table(["budget", "chunks"], chunk_sweep_rows)}

## 6. 임베딩 컨텍스트 적합성

대략 1 token ≈ 3.7 chars 가정. `fit` = 가장 긴 chunk 가 truncation 없이 들어가는지.

{markdown_table(["embedding_model", "context_tokens", "approx_max_chunk_tokens", "fit"], embedding_rows)}

## 7. 외부 DB 적재 (pgvector)

- `rag_chunks.jsonl` 한 줄 → `rag_chunks` 한 행 (1:1)
- embedding 대상: `text` · filter 대상: `product`, `source_repo`, `source_path`, `note_type`, `tags`, `verified`
- citation: `source_url`, `source_path`, `note_id`

{_pgvector_schema_block()}

## 8. 소스 코드 링크

{markdown_table(["record", "source_path", "link"], source_link_rows)}

## 9. 한계

- 코드 분석 기반이라 실제 vault note / frontmatter 샘플은 다음 단계에서 추가 필요
- 실제 서비스 데이터 들어오면 `workspace_id`, `user_id` tenant 필드 필수
- 검색 평가용 golden set (질문 ↔ expected `source_url`) 미보유
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
