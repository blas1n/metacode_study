# 2주차 RAG 데이터셋 정제 및 분석 결과

## 1. 데이터셋 개요

실제 `BSVibe/bsvibe-app` 코드베이스를 분석해, 개인화 작업 메모리 RAG에 사용할 source-derived seed dataset 을 구성했습니다. 사용자 데이터가 아니라 구현 파일, 런타임 배선, 프론트 surface, 운영 문서, 검증 테스트에서 확인한 구조적 사실을 record 로 만들었습니다.

- 정제된 note 수: **31**
- RAG chunk 수: **32** (note 당 평균 1.03 chunk, 최대 2)
- 검증 완료 note 비율: 31/31 (100.0%)
- 품질 flag 수: 0 · exact-duplicate group 없음 (content_sha256 기준)
- source repo: BSVibe/bsvibe-app

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

| source_type | count |
| --- | --- |
| backend_code | 18 |
| frontend_code | 5 |
| runtime_code | 4 |
| readme | 1 |
| test_code | 1 |
| ops_yaml | 1 |
| ops_doc | 1 |

| note_type | count |
| --- | --- |
| implementation_evidence | 18 |
| surface_evidence | 5 |
| runtime_evidence | 4 |
| operational_evidence | 2 |
| project_overview | 1 |
| verification_evidence | 1 |

## 4. Source 디렉토리 coverage

어느 영역을 얼마나 다뤘는지 한눈에 보기 위한 디렉토리 단위 집계입니다.

| top-level directory | count |
| --- | --- |
| backend | 22 |
| apps | 5 |
| deploy | 2 |
| README.md | 1 |
| tests | 1 |

## 5. Source path 분포

| source_path | count |
| --- | --- |
| README.md | 1 |
| backend/knowledge/factory.py | 1 |
| backend/knowledge/retrieval/canon_retriever.py | 1 |
| backend/knowledge/retrieval/resolved_decisions_retriever.py | 1 |
| backend/knowledge/retrieval/negative_pattern_retriever.py | 1 |
| backend/knowledge/retrieval/composite_retriever.py | 1 |
| backend/workflow/application/runtime/agent_runtime.py | 1 |
| backend/workflow/application/runtime/worker_runtime.py | 1 |
| backend/knowledge/ingest/ingest_compiler/_compiler.py | 1 |
| backend/knowledge/ingest/ingest_compiler/_chunking.py | 1 |
| backend/knowledge/retrieval/semantic_note_retriever.py | 1 |
| apps/pwa/lib/api/knowledge.ts | 1 |
| apps/pwa/components/knowledge/KnowledgeGraphView.tsx | 1 |
| backend/knowledge/mcp/domain_tools.py | 1 |
| tests/glue/test_b13_decision_reuse_in_run.py | 1 |
| backend/knowledge/application/retraction_service.py | 1 |
| backend/knowledge/canonicalization/promotion.py | 1 |
| backend/knowledge/canonicalization/lint.py | 1 |
| backend/knowledge/canonicalization/watcher.py | 1 |
| backend/knowledge/graph/analytics.py | 1 |
| backend/knowledge/graph/graph_extractor.py | 1 |
| backend/knowledge/domain/retraction.py | 1 |
| backend/knowledge/_internal/events.py | 1 |
| backend/knowledge/application/audit_events.py | 1 |
| backend/workflow/application/runtime/settle_runtime.py | 1 |
| backend/workflow/application/runtime/dispatcher.py | 1 |
| apps/pwa/components/knowledge/RetractModal.tsx | 1 |
| apps/pwa/components/knowledge/InspectorActions.tsx | 1 |
| apps/pwa/components/knowledge/UndoToast.tsx | 1 |
| deploy/compose.prod.yaml | 1 |
| deploy/README.md | 1 |

## 6. 상위 태그 / 태그 공출현

가장 자주 묶이는 태그 페어는 RAG 검색 facet 후보입니다.

| tag | count |
| --- | --- |
| workspace-scoping | 4 |
| verification | 3 |
| garden-notes | 3 |
| pgvector | 3 |
| correct | 3 |
| retract | 3 |
| ontology-correction | 3 |
| docker-compose | 2 |
| garden-writer | 2 |
| vault | 2 |
| canonicalization | 2 |
| signal-filtering | 2 |
| tombstone | 2 |
| embedding-hook | 2 |
| promotion | 2 |

| tag_left | tag_right | co_occurrence |
| --- | --- | --- |
| correct | retract | 3 |
| garden-notes | signal-filtering | 2 |
| garden-notes | verification | 2 |
| signal-filtering | verification | 2 |
| embedding-hook | pgvector | 2 |
| idempotency | undo-window | 2 |
| bsvibe-app | docker-compose | 1 |
| bsvibe-app | fastapi | 1 |
| bsvibe-app | monorepo | 1 |
| bsvibe-app | nextjs | 1 |

## 7. 길이 분석 (note vs chunk)

| target | min | max | mean | median | p90 |
| --- | --- | --- | --- | --- | --- |
| note_content_chars | 247 | 423 | 340.1 | 344 | 404 |
| chunk_chars | 86 | 424 | 329.5 | 334.5 | 395 |

분할 budget 을 바꿀 때 chunk 수가 어떻게 변하는지 (chunking sensitivity):

| budget | chunks |
| --- | --- |
| max_chunk_chars=256 | 65 |
| max_chunk_chars=384 | 39 |
| max_chunk_chars=512 | 31 |
| max_chunk_chars=768 | 31 |

## 8. 임베딩 컨텍스트 적합성

각 임베딩 모델 컨텍스트 안에 chunk 최대 길이가 들어가는지 추정합니다 (대략 1 token ≈ 3.7 chars 기준).

| embedding_model | context_tokens | approx_max_chunk_tokens | fit |
| --- | --- | --- | --- |
| openai/text-embedding-3-small | 8191 | 114 | fit |
| openai/text-embedding-3-large | 8191 | 114 | fit |
| cohere/embed-multilingual-v3 | 512 | 114 | fit |
| bge-m3 | 8192 | 114 | fit |

> `fit` 은 _가장 긴 chunk_ 가 truncation 없이 들어가는지 여부입니다. 모든 모델에서 fit 이면 chunk 추가 분할은 불필요합니다.

## 9. RAG 적재 관점 분석

다음 주차 외부 DB 구축에서 바로 쓸 수 있도록 `clean_notes.jsonl` 과 `rag_chunks.jsonl` 을 분리해뒀습니다.

- `clean_notes.jsonl`: note 단위 정제 결과. `source_id`, `title`, `content`, `tags`, `verified`, `quality_flags`, `content_sha256` 를 포함.
- `rag_chunks.jsonl`: vector DB / pgvector 에 그대로 넣는 chunk. `text` 는 embedding 대상, `metadata` 는 filter 및 citation 대상.
- 권장 metadata filter: `product`, `source_repo`, `source_commit`, `source_path`, `source_type`, `note_type`, `tags`, `verified`, `created_at`
- 권장 provenance field: `chunk_id`, `note_id`, `source_id`, `metadata.title`, `metadata.source_url`, `metadata.source_path`

### pgvector 스키마 제안

```sql
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

| record | source_path | link |
| --- | --- | --- |
| BSVibe monorepo layout and local stack | README.md | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/README.md#L1-L90) |
| KnowledgeFactory binds knowledge to workspace and region | backend/knowledge/factory.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/factory.py#L1-L160) |
| Canonical concept retrieval uses promoted active concepts only | backend/knowledge/retrieval/canon_retriever.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/canon_retriever.py#L1-L131) |
| Resolved decisions are retrieved from settled garden notes | backend/knowledge/retrieval/resolved_decisions_retriever.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/resolved_decisions_retriever.py#L1-L239) |
| Negative patterns preserve founder rejection feedback | backend/knowledge/retrieval/negative_pattern_retriever.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/negative_pattern_retriever.py#L1-L114) |
| Composite retriever merges multiple knowledge sources behind one protocol | backend/knowledge/retrieval/composite_retriever.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/composite_retriever.py#L1-L77) |
| Agent runtime wires workspace retriever into execution and knowledge-only route | backend/workflow/application/runtime/agent_runtime.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/agent_runtime.py#L204-L326) |
| Settle worker writes vault notes, promotes concepts, and embeds notes | backend/workflow/application/runtime/worker_runtime.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/worker_runtime.py#L168-L200) |
| IngestCompiler compiles imported seed content per chunk | backend/knowledge/ingest/ingest_compiler/_compiler.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler/_compiler.py#L1-L240) |
| Chunking budget protects local LLM ingestion | backend/knowledge/ingest/ingest_compiler/_chunking.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler/_chunking.py#L1-L187) |
| Semantic note retrieval searches pgvector note embeddings | backend/knowledge/retrieval/semantic_note_retriever.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/semantic_note_retriever.py#L1-L66) |
| PWA Knowledge API exposes concepts, observations, graph, retract, and correct | apps/pwa/lib/api/knowledge.ts | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/lib/api/knowledge.ts#L1-L115) |
| Knowledge graph view presents ontology nodes and inspector actions | apps/pwa/components/knowledge/KnowledgeGraphView.tsx | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/KnowledgeGraphView.tsx#L1-L150) |
| MCP domain tools define search, graph, tag, and create-note surfaces | backend/knowledge/mcp/domain_tools.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/mcp/domain_tools.py#L1-L220) |
| Cross-run decision reuse is tested through seed and verification fold | tests/glue/test_b13_decision_reuse_in_run.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/tests/glue/test_b13_decision_reuse_in_run.py#L1-L311) |
| RetractionService orchestrates ontology corrections with a 30s undo window | backend/knowledge/application/retraction_service.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/application/retraction_service.py#L1-L366) |
| GardenObservationPromoter turns recurring garden tags into canonical anchors | backend/knowledge/canonicalization/promotion.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization/promotion.py#L1-L304) |
| canon-lint surfaces orphan tags, alias collisions, and redirect anomalies | backend/knowledge/canonicalization/lint.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization/lint.py#L1-L210) |
| CanonWatcher bridges external vault edits into the canonicalization index | backend/knowledge/canonicalization/watcher.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization/watcher.py#L1-L173) |
| Graph analytics expose centrality, components, and knowledge gaps | backend/knowledge/graph/analytics.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/graph/analytics.py#L1-L216) |
| GraphExtractor pulls entities and relations from vault frontmatter and wikilinks | backend/knowledge/graph/graph_extractor.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/graph/graph_extractor.py#L1-L367) |
| RetractionSignal locks the wire shape of every founder-issued correction | backend/knowledge/domain/retraction.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/domain/retraction.py#L1-L108) |
| EventBus enumerates lifecycle, vault, and ingest events for streaming | backend/knowledge/_internal/events.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/_internal/events.py#L1-L185) |
| Audit events trace the ontology correction lifecycle through the outbox | backend/knowledge/application/audit_events.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/application/audit_events.py#L1-L53) |
| Settle runtime factories build per-settlement extractor and embedding hook | backend/workflow/application/runtime/settle_runtime.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/settle_runtime.py#L1-L165) |
| Runtime dispatcher binds gateway plus cheap-LLM seams to the same per-session pattern | backend/workflow/application/runtime/dispatcher.py | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime/dispatcher.py#L1-L174) |
| RetractModal renders the pre-flight confirmation for an ontology retract | apps/pwa/components/knowledge/RetractModal.tsx | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/RetractModal.tsx#L1-L157) |
| InspectorActions runs the idle to modal to toast state machine for retract and correct | apps/pwa/components/knowledge/InspectorActions.tsx | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/InspectorActions.tsx#L1-L203) |
| UndoToast derives the 30s countdown from server wall-clock apply_at | apps/pwa/components/knowledge/UndoToast.tsx | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge/UndoToast.tsx#L1-L140) |
| compose.prod.yaml overrides dev defaults for prod env-driven startup | deploy/compose.prod.yaml | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/deploy/compose.prod.yaml#L1-L115) |
| Deploy README documents the migrate-on-boot and single-migrator contract | deploy/README.md | [source](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/deploy/README.md#L1-L164) |

## 12. 보완 필요 사항

- 실제 서비스 데이터가 들어오면 `workspace_id`, `user_id` 같은 tenant 분리 필드가 필수입니다. 현재는 product 단일 값만 보존.
- 현재 record 는 코드 분석 기반 요약이라, 다음 단계에서 실제 vault note / frontmatter 샘플을 별도 source 로 추가해야 합니다.
- 의미가 같은 태그를 안정적으로 합치기 위한 synonym dictionary 가 필요합니다 (예: `undo-window` / `undo-toast` / `apply-at`).
- 검색 평가를 위해 질문과 expected `source_url` 을 묶은 retrieval fixture (golden set) 가 필요합니다.
- 개인화 메모리 특성상 redaction rule 을 이메일/API key/로컬 경로 외에도 전화번호, URL token, 고객명까지 확장해야 합니다.
- 한국어 문서 ingestion 까지 확장되면 `paragraph_split` 정규식과 token 환산 비율 (현재 영문 가정 0.27) 을 ko/en 분기로 두는 것이 안전합니다.
