# 2주차 과제: 실제 BSVibe RAG 데이터셋 정제 및 분석

## 제출 내용

실제 BSVibe 코드베이스를 분석해 RAG에 사용할 seed dataset을 만들고, 다음 주차 외부 DB 구축 전에 필요한 정제 자동화와 데이터 분석을 진행했습니다.

- 분석 대상 repo: `BSVibe/bsvibe-app`
- 분석 commit: `a6648ace49fa670136e6f865652990517e9865fa`
- 제출 repo: `blas1n/metacode_study`

이전 예시 데이터는 제거했고, 실제 구현 파일과 테스트에서 확인한 구조만 record로 정리했습니다.

## 폴더 구조

| 경로 | 설명 |
|---|---|
| `data/raw/bsvibe_memory_seed.jsonl` | 실제 BSVibe source 분석 기반 원본 데이터셋 |
| `scripts/clean_dataset.py` | 원본 JSONL 정제 및 RAG chunk 생성 코드 |
| `scripts/analyze_dataset.py` | 정제 데이터 통계 분석 및 Markdown 보고서 생성 코드 |
| `data/processed/clean_notes.jsonl` | 정제된 note 단위 데이터 |
| `data/processed/rag_chunks.jsonl` | 외부 DB/vector DB 적재용 chunk 데이터 |
| `data/processed/cleaning_report.json` | 정제 과정 요약 |
| `reports/analysis_summary.json` | 분석 결과 JSON |
| `reports/dataset_analysis.md` | 제출용 분석 문서 |

## 사용한 실제 소스 코드

| 목적 | Source |
|---|---|
| BSVibe repo 구조와 실행/테스트 기준 | [README.md](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/README.md#L1-L90) |
| workspace별 vault/retriever 구성 | [backend/knowledge/factory.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/factory.py#L1-L160) |
| promoted canonical concept 검색 | [backend/knowledge/retrieval/canon_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/canon_retriever.py#L1-L131) |
| resolved decision 재사용 검색 | [backend/knowledge/retrieval/resolved_decisions_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/resolved_decisions_retriever.py#L1-L239) |
| rejected approach/negative pattern 검색 | [backend/knowledge/retrieval/negative_pattern_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/negative_pattern_retriever.py#L1-L114) |
| 여러 knowledge source 합성 | [backend/knowledge/retrieval/composite_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/composite_retriever.py#L1-L77) |
| runtime retriever 배선과 knowledge-only route | [backend/workflow/application/runtime/agent_runtime.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/agent_runtime.py#L204-L326) |
| settle worker, promotion, embedding hook | [backend/workflow/application/runtime/worker_runtime.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/worker_runtime.py#L168-L200) |
| source ingest compiler | [backend/knowledge/ingest/ingest_compiler/_compiler.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler/_compiler.py#L1-L240) |
| chunk budget and local LLM constraints | [backend/knowledge/ingest/ingest_compiler/_chunking.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler/_chunking.py#L1-L187) |
| semantic note retrieval and pgvector backend | [semantic_note_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/semantic_note_retriever.py#L1-L66), [storage/pg.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/storage/pg.py#L1-L99) |
| PWA knowledge API | [apps/pwa/lib/api/knowledge.ts](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/lib/api/knowledge.ts#L1-L115) |
| PWA knowledge graph UI | [apps/pwa/components/knowledge/KnowledgeGraphView.tsx](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/KnowledgeGraphView.tsx#L1-L150) |
| MCP knowledge tool schemas | [backend/knowledge/mcp/domain_tools.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/mcp/domain_tools.py#L1-L220) |
| decision memory runtime verification | [tests/glue/test_b13_decision_reuse_in_run.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/tests/glue/test_b13_decision_reuse_in_run.py#L1-L311) |

## 실행 방법

프로젝트 루트에서 실행합니다.

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
- `source_repo`, `source_commit`, `source_path`, `source_url`, line range 보존
- `source_id`, `note_id`, `chunk_id` 기반 provenance 유지
- 외부 DB 구축을 위한 metadata filter 분리

## 분석 요약

분석 문서는 [reports/dataset_analysis.md](reports/dataset_analysis.md)에 정리했습니다.

핵심 결론은 다음과 같습니다.

- BSVibe RAG는 단순 문서 QA보다 workspace별 과거 결정, 반복 피드백, canonical concept 재사용이 중요합니다.
- 실제 runtime은 `KnowledgeFactory`와 `CompositeCanonRetriever`를 통해 canonical concept, resolved decision, negative pattern, semantic note search를 합성합니다.
- `SettleWorker`가 workflow activity를 vault note로 흡수하고 promotion/embedding hook을 통해 검색 가능한 지식으로 연결합니다.
- 다음 주차 외부 DB에서는 `text`를 embedding하고, `metadata`의 `source_repo`, `source_commit`, `source_path`, `source_url`, `note_type`, `tags`, `verified`를 filter/citation에 사용해야 합니다.
