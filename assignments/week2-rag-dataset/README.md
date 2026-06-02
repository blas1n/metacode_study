# 2주차 과제: 실제 BSVibe RAG 데이터셋 정제 및 분석

실제 `BSVibe/bsvibe-app` 코드베이스를 분석해, RAG 에 사용할 source-derived seed dataset 을 만들고, 다음 주차 외부 DB 구축에 필요한 정제 자동화와 데이터 분석을 진행했어요. 합성 예시 데이터는 모두 제거했고, 구현 파일·런타임 배선·프론트 컴포넌트·운영 문서·검증 테스트에서 확인한 사실만 record 로 정리했습니다.

- 분석 대상 repo: `BSVibe/bsvibe-app`
- 분석 commit: `a6648ace49fa670136e6f865652990517e9865fa` (pinned)
- 제출 repo: `blas1n/metacode_study`
- record 수: 31 (cleaning 후), chunk 수: 33

## 폴더 구조

| 경로 | 설명 |
| --- | --- |
| `data/raw/bsvibe_memory_seed.jsonl` | 실제 BSVibe source 분석 기반 원본 데이터셋 (수기 작성) |
| `scripts/clean_dataset.py` | 원본 JSONL 정제 + RAG chunk 생성 |
| `scripts/analyze_dataset.py` | 정제 데이터 통계 분석 + Markdown 보고서 생성 |
| `data/processed/clean_notes.jsonl` | 정제된 note 단위 데이터 (provenance 포함) |
| `data/processed/rag_chunks.jsonl` | 외부 DB / vector DB 적재용 chunk 데이터 |
| `data/processed/cleaning_report.json` | 정제 과정 요약 (입력 수, redaction 카운트, 품질 flag) |
| `reports/analysis_summary.json` | 분석 결과 raw JSON |
| `reports/dataset_analysis.md` | 제출용 분석 문서 |

## 실행 방법

`metacode_study` 루트에서 실행해요.

```bash
source .venv/bin/activate
python assignments/week2-rag-dataset/scripts/clean_dataset.py
python assignments/week2-rag-dataset/scripts/analyze_dataset.py
```

스크립트는 모두 `argparse` 기본값으로 동작하고, 별도 옵션 없이도 raw → processed → reports 흐름이 끝까지 돌아갑니다.

## 정제 자동화 기준

1. JSONL record 필수 필드 검증 (`id`, `created_at`, `source_type`, `product`, `title`, `content`, `tags`)
2. `created_at` 의 ISO-8601 파싱 검증
3. 이메일 / API key (`sk-…`, `pk-…`, `ghp-…`, `github_pat-…`, `demo-secret-token-…`) / 로컬 경로 (`/Users/…`) redaction
4. 공백 정규화, 태그 소문자·하이픈 형태 정규화
5. `source_type` → `note_type` 자동 매핑 (`readme`/`backend_code`/`runtime_code`/`frontend_code`/`test_code`/`ops_doc`/`ops_yaml`)
6. GitHub `source_url`, `source_path`, `source_commit`, `source_line_start`/`source_line_end` 보존
7. `note_id` (해시 기반), `source_id`, `content_sha256` 로 provenance 유지
8. 외부 DB 적재용 metadata filter 분리 + embedding 대상 text 를 paragraph 경계에서 chunk 로 분할 (작은 trailing fragment 는 이전 chunk 에 흡수)

## 분석 요약

분석 문서: [reports/dataset_analysis.md](reports/dataset_analysis.md)

핵심 결론을 한 단락으로 요약하면:

- BSVibe RAG 는 단순 문서 QA 가 아니라 workspace 별 과거 결정·반복 피드백·canonical concept·negative pattern·ontology correction surface·운영 런북을 모두 다뤄야 해요.
- 실제 runtime 은 `KnowledgeFactory` + `CompositeCanonRetriever` 가 canonical concept, resolved decision, negative pattern, semantic note 를 합성해서 사용하고, `SettleWorker` 가 workflow activity 를 vault note 로 흡수하면서 promotion / embedding hook 으로 검색 가능 상태까지 연결합니다.
- M3a 의 retraction service / undo toast / inspector actions 까지 dataset 에 포함했기 때문에, RAG 응답에 사용된 node 가 사후에 retract 되었는지를 citation 단계에서 검증할 수 있어요.
- 다음 주차 외부 DB 에서는 `text` 를 embedding 하고, `metadata` 의 `source_repo` / `source_commit` / `source_path` / `source_url` / `note_type` / `tags` / `verified` 를 filter 와 citation 에 함께 사용하면 됩니다. pgvector DDL 과 검색 쿼리 sketch 는 분석 문서 §9 에 정리했습니다.

## 사용한 실제 소스 코드 (pinned commit 기준)

| 영역 | Source |
| --- | --- |
| repo 구조 / 실행·테스트 가이드 | [README.md](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/README.md#L1-L90) |
| workspace 별 vault / retriever 구성 | [backend/knowledge/factory.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/factory.py#L1-L160) |
| canonical concept 검색 | [canon_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/canon_retriever.py#L1-L131) |
| resolved decision 검색 | [resolved_decisions_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/resolved_decisions_retriever.py#L1-L239) |
| rejected approach / negative pattern | [negative_pattern_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/negative_pattern_retriever.py#L1-L114) |
| 여러 knowledge source 합성 | [composite_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/composite_retriever.py#L1-L77) |
| agent runtime + knowledge-only route | [agent_runtime.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/agent_runtime.py#L204-L326) |
| settle worker / promotion / embedding | [worker_runtime.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/worker_runtime.py#L168-L200), [settle_runtime.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/settle_runtime.py#L1-L165), [dispatcher.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/dispatcher.py#L1-L174) |
| ingest compiler / chunking budget | [_compiler.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler/_compiler.py#L1-L240), [_chunking.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler/_chunking.py#L1-L187) |
| semantic note retrieval + pgvector backend | [semantic_note_retriever.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/semantic_note_retriever.py#L1-L66), [storage/pg.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/storage/pg.py#L1-L99) |
| canonicalization (promotion / lint / watcher) | [promotion.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization/promotion.py#L1-L304), [lint.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization/lint.py#L1-L210), [watcher.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization/watcher.py#L1-L173) |
| graph analytics + extractor | [graph/analytics.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/graph/analytics.py#L1-L216), [graph/graph_extractor.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/graph/graph_extractor.py#L1-L367) |
| ontology correction (M3a backend) | [retraction_service.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/application/retraction_service.py#L1-L366), [domain/retraction.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/domain/retraction.py#L1-L108), [application/audit_events.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/application/audit_events.py#L1-L53) |
| event bus | [_internal/events.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/_internal/events.py#L1-L185) |
| PWA knowledge API + 그래프 UI | [knowledge.ts](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/lib/api/knowledge.ts#L1-L115), [KnowledgeGraphView.tsx](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/KnowledgeGraphView.tsx#L1-L150) |
| ontology correction (M3b PWA) | [RetractModal.tsx](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/RetractModal.tsx#L1-L157), [InspectorActions.tsx](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/InspectorActions.tsx#L1-L203), [UndoToast.tsx](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/UndoToast.tsx#L1-L140) |
| MCP knowledge tool schemas | [domain_tools.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/mcp/domain_tools.py#L1-L220) |
| decision memory runtime 검증 | [test_b13_decision_reuse_in_run.py](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/tests/glue/test_b13_decision_reuse_in_run.py#L1-L311) |
| 운영 (deploy) | [deploy/README.md](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/deploy/README.md#L1-L164), [deploy/compose.prod.yaml](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/deploy/compose.prod.yaml#L1-L115) |

## 다음 단계 (3주차 외부 DB 구축 준비)

분석 문서 §9 의 pgvector DDL 을 그대로 가져가면 돼요. 핵심만 다시 정리하면:

1. `rag_chunks.jsonl` 의 한 줄 = `rag_chunks` 테이블의 한 행으로 1:1 매핑.
2. embedding 차원은 선택한 모델에 맞춰 `vector(N)` 조정 (bge-m3 → 1024, OpenAI 3-small → 1536).
3. 검색은 `embedding <=> $1` (코사인 거리) + metadata filter (`product`, `note_type`, `verified`) 조합.
4. 응답에는 항상 `source_url` + `source_path` 를 citation 으로 같이 반환.
