# 2주차 과제: BSVibe RAG 데이터셋 정제 및 분석

`bsvibe-app` 코드베이스에서 도출한 RAG seed dataset 을 정제

- record 35 / chunk 37 (코드 31 + vault frontmatter fixture 4)
- 검색 평가용 golden set 15 문항

## 폴더 구조

| 경로 | 설명 |
| --- | --- |
| `data/raw/bsvibe_memory_seed.jsonl` | 원본 seed (소스 분석 기반) |
| `scripts/clean_dataset.py` | 정제 + chunk 생성 |
| `scripts/analyze_dataset.py` | 분석 + 보고서 생성 |
| `data/processed/clean_notes.jsonl` | 정제된 note |
| `data/processed/rag_chunks.jsonl` | pgvector 적재용 chunk |
| `data/processed/cleaning_report.json` | 정제 요약 |
| `data/eval/retrieval_golden.jsonl` | 검색 평가용 golden set (질문 ↔ expected source) |
| `reports/dataset_analysis.md` | 분석 보고서 |
| `reports/analysis_summary.json` | 분석 raw JSON |

## 실행

```bash
source .venv/bin/activate
python assignments/week2-rag-dataset/scripts/clean_dataset.py
python assignments/week2-rag-dataset/scripts/analyze_dataset.py
```

## 분석 결과

자세한 내용은 [reports/dataset_analysis.md](reports/dataset_analysis.md) 참고. 핵심만 요약하면:

- 정제는 redaction (이메일/API key/로컬 경로), 태그·공백 정규화, `source_type → note_type` 매핑, 자동 태깅, chunk 분할까지 자동화
- 자동 태깅은 bsvibe-app `settle_worker.derive_content_tags` 규칙을 그대로 이식 (수기 215 + 자동 280 → 머지 467)
- 외부 DB (pgvector) 적재용 스키마와 검색 쿼리 sketch 는 분석 보고서 7. 외부 DB 적재 섹션에 포함
- BM25 sparse baseline 측정: Recall@1=53%, Recall@5=90%, Recall@10=90% (다음 주차 dense embedding 이 넘어야 할 floor)
- 검증 100%, 중복 0, 품질 flag 0
