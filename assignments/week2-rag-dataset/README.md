# 2주차 과제: RAG 데이터셋 정제 및 분석

## 제출 내용

BSVibe 개인화 작업 메모리 RAG에 사용할 seed dataset을 구성하고, 다음 주차 외부 DB 구축 전에 필요한 정제 자동화와 데이터 분석을 진행했습니다.

## 폴더 구조

| 경로 | 설명 |
|---|---|
| `data/raw/bsvibe_memory_seed.jsonl` | 공개 제출 가능한 synthetic 원본 데이터셋 |
| `scripts/clean_dataset.py` | 원본 JSONL 정제 및 RAG chunk 생성 코드 |
| `scripts/analyze_dataset.py` | 정제 데이터 통계 분석 및 Markdown 보고서 생성 코드 |
| `data/processed/clean_notes.jsonl` | 정제된 note 단위 데이터 |
| `data/processed/rag_chunks.jsonl` | 외부 DB/vector DB 적재용 chunk 데이터 |
| `data/processed/cleaning_report.json` | 정제 과정 요약 |
| `reports/analysis_summary.json` | 분석 결과 JSON |
| `reports/dataset_analysis.md` | 제출용 분석 문서 |

## 실행 방법

프로젝트 루트에서 실행합니다.

```bash
python assignments/week2-rag-dataset/scripts/clean_dataset.py
python assignments/week2-rag-dataset/scripts/analyze_dataset.py
```

가상환경을 사용하는 경우:

```bash
source .venv/bin/activate
python assignments/week2-rag-dataset/scripts/clean_dataset.py
python assignments/week2-rag-dataset/scripts/analyze_dataset.py
```

## 정제 기준

- JSONL record 필수 필드 검증
- 이메일, API key, 로컬 경로 redaction
- 공백 정규화
- 태그 정규화
- `source_type` 기반 `note_type` 분류
- `source_id`, `note_id`, `chunk_id` 기반 provenance 유지
- 외부 DB 구축을 위한 metadata filter 분리

## 분석 요약

분석 문서는 [reports/dataset_analysis.md](reports/dataset_analysis.md)에 정리했습니다.

핵심 결론은 다음과 같습니다.

- BSVibe RAG는 단순 문서 QA보다 과거 결정과 반복 피드백 재사용이 중요합니다.
- `decision_memory`, `repeated_pattern_candidate`, `delivery_evidence`를 분리하면 검색 시 사용 목적에 맞게 필터링할 수 있습니다.
- 다음 주차 외부 DB에서는 `text`를 embedding하고, `metadata`의 `product`, `source_type`, `note_type`, `tags`, `verified`, `created_at`을 filter로 사용하는 구조가 적절합니다.
