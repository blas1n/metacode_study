#!/usr/bin/env python3
"""Analyze the cleaned BSVibe RAG dataset and write a Markdown report."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


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
        return {"min": 0, "max": 0, "mean": 0, "median": 0}
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 1),
        "median": round(statistics.median(values), 1),
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        output.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(output)


def analyze(notes: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(str(note["source_type"]) for note in notes)
    note_type_counts = Counter(str(note["note_type"]) for note in notes)
    tag_counts = Counter(tag for note in notes for tag in note["tags"])
    verified_count = sum(1 for note in notes if note["verified"])
    quality_flag_count = sum(len(note["quality_flags"]) for note in notes)
    chunk_lengths = [int(chunk["char_count"]) for chunk in chunks]
    note_lengths = [len(str(note["content"])) for note in notes]

    return {
        "total_notes": len(notes),
        "total_chunks": len(chunks),
        "verified_notes": verified_count,
        "verified_ratio": pct(verified_count, len(notes)),
        "quality_flag_count": quality_flag_count,
        "source_counts": dict(source_counts.most_common()),
        "note_type_counts": dict(note_type_counts.most_common()),
        "top_tags": dict(tag_counts.most_common(12)),
        "note_length_stats": length_stats(note_lengths),
        "chunk_length_stats": length_stats(chunk_lengths),
        "db_readiness": {
            "metadata_filters": ["product", "source_type", "note_type", "tags", "verified", "created_at"],
            "embedding_text_field": "text",
            "provenance_fields": ["chunk_id", "note_id", "source_id", "metadata.title"],
        },
    }


def build_report(summary: dict[str, Any]) -> str:
    source_rows = [[key, value] for key, value in summary["source_counts"].items()]
    note_type_rows = [[key, value] for key, value in summary["note_type_counts"].items()]
    tag_rows = [[key, value] for key, value in summary["top_tags"].items()]

    note_stats = summary["note_length_stats"]
    chunk_stats = summary["chunk_length_stats"]

    return f"""# 2주차 RAG 데이터셋 정제 및 분석 결과

## 데이터셋 개요

이번 과제에서는 BSVibe의 개인화 작업 메모리 RAG를 위한 synthetic seed dataset을 구성했습니다. 실제 사용자 데이터, 개인 이메일, API key, 로컬 경로는 사용하지 않고 공개 제출 가능한 예시 데이터만 넣었습니다.

- 원본 record 수: {summary["total_notes"]}
- RAG chunk 수: {summary["total_chunks"]}
- 검증 완료 note 비율: {summary["verified_notes"]}/{summary["total_notes"]} ({summary["verified_ratio"]}%)
- 품질 flag 수: {summary["quality_flag_count"]}

## 정제 자동화 결과

정제 코드는 다음 처리를 자동화합니다.

- JSONL 원본 record validation
- 이메일, API key, 로컬 경로 redaction
- 공백 정규화
- 태그 소문자 및 hyphen 형태 정규화
- source_type 기반 note_type 매핑
- 외부 DB 적재를 위한 provenance field 생성
- embedding 대상 text chunk 생성

## Source Type 분포

{markdown_table(["source_type", "count"], source_rows)}

## Note Type 분포

{markdown_table(["note_type", "count"], note_type_rows)}

## 상위 태그

{markdown_table(["tag", "count"], tag_rows)}

## 길이 분석

{markdown_table(["target", "min", "max", "mean", "median"], [
    ["note_content_chars", note_stats["min"], note_stats["max"], note_stats["mean"], note_stats["median"]],
    ["chunk_chars", chunk_stats["min"], chunk_stats["max"], chunk_stats["mean"], chunk_stats["median"]],
])}

## RAG 적재 관점 분석

이 데이터셋은 다음 주차 외부 DB 구축에서 바로 사용할 수 있도록 `clean_notes.jsonl`과 `rag_chunks.jsonl`로 분리했습니다.

- `clean_notes.jsonl`: 원본 note 단위의 정제 결과입니다. source_id, title, content, tags, verified, quality_flags를 보존합니다.
- `rag_chunks.jsonl`: vector DB 또는 pgvector에 넣기 좋은 chunk 단위 데이터입니다. `text`는 embedding 대상이고 `metadata`는 filter 대상입니다.
- 추천 metadata filter: `product`, `source_type`, `note_type`, `tags`, `verified`, `created_at`
- 추천 provenance field: `chunk_id`, `note_id`, `source_id`, `metadata.title`

## 데이터 특성

현재 seed dataset은 사용자 요청, 결정 기록, 피드백, Delivery Report, GitHub issue, 프로젝트 문서가 섞인 작은 데이터셋입니다. BSVibe RAG의 목적이 단순 문서 QA보다 과거 결정과 반복 피드백 재사용에 있으므로, `decision_memory`와 `repeated_pattern_candidate`를 별도 note_type으로 분리했습니다.

검증 완료 note 비율이 높아 검색 결과를 작업 기준으로 쓰기 좋지만, GitHub issue처럼 아직 검증되지 않은 외부 입력도 포함되어 있습니다. 따라서 검색 단계에서는 `verified=true`를 강한 기준으로 우선 검색하고, `verified=false`는 참고 컨텍스트로만 쓰는 것이 적절합니다.

## 보완 필요 사항

- 실제 서비스 데이터가 들어오면 workspace_id, user_id 같은 tenant 분리 field가 필요합니다.
- 같은 의미의 태그를 더 안정적으로 합치기 위한 synonym dictionary가 필요합니다.
- chunk 수가 적은 seed dataset이므로 다음 단계에서는 평가 질문과 expected source를 함께 만들어 retrieval 품질을 측정해야 합니다.
- 개인화 메모리 특성상 redaction rule을 이메일/API key/로컬 경로 외에도 전화번호, URL token, 고객명까지 확장해야 합니다.
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
