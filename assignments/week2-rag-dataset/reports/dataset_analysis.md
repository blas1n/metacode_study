# 2주차 RAG 데이터셋 정제 및 분석 결과

대상 프로젝트 `BSVibe/bsvibe-app` 의 실제 코드에서 도출한 RAG seed dataset 입니다.

## 1. 개요

- note 수: **31**, chunk 수: **32** (note 당 평균 1.03, 최대 2)
- verified: 31/31 (100.0%) · 품질 flag 0 · exact-duplicate group 없음 (content_sha256 기준)
- source repo: BSVibe/bsvibe-app

## 2. 정제 처리

redaction (이메일 / API key / 로컬 경로) → 공백·태그 정규화 → `source_type → note_type` 매핑 → provenance (`note_id`, `content_sha256`) 부여 → paragraph 경계 기반 chunk 분할.

## 3. 분포

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

| top-level dir | count |
| --- | --- |
| backend | 22 |
| apps | 5 |
| deploy | 2 |
| README.md | 1 |
| tests | 1 |

## 4. 태그

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

자주 묶이는 페어:

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

## 5. 길이

| target | min | max | mean | median | p90 |
| --- | --- | --- | --- | --- | --- |
| note_content_chars | 247 | 423 | 340.1 | 344 | 404 |
| chunk_chars | 86 | 424 | 329.5 | 334.5 | 395 |

분할 budget 변경 시 chunk 수:

| budget | chunks |
| --- | --- |
| max_chunk_chars=256 | 65 |
| max_chunk_chars=384 | 39 |
| max_chunk_chars=512 | 31 |
| max_chunk_chars=768 | 31 |

## 6. 임베딩 컨텍스트 적합성

대략 1 token ≈ 3.7 chars 가정. `fit` = 가장 긴 chunk 가 truncation 없이 들어가는지.

| embedding_model | context_tokens | approx_max_chunk_tokens | fit |
| --- | --- | --- | --- |
| openai/text-embedding-3-small | 8191 | 114 | fit |
| openai/text-embedding-3-large | 8191 | 114 | fit |
| cohere/embed-multilingual-v3 | 512 | 114 | fit |
| bge-m3 | 8192 | 114 | fit |

## 7. 외부 DB 적재 (pgvector)

- `rag_chunks.jsonl` 한 줄 → `rag_chunks` 한 행 (1:1)
- embedding 대상: `text` · filter 대상: `product`, `source_repo`, `source_path`, `note_type`, `tags`, `verified`
- citation: `source_url`, `source_path`, `note_id`

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


## 8. 소스 코드 링크

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

## 9. 한계

- 코드 분석 기반이라 실제 vault note / frontmatter 샘플은 다음 단계에서 추가 필요
- 실제 서비스 데이터 들어오면 `workspace_id`, `user_id` tenant 필드 필수
- 검색 평가용 golden set (질문 ↔ expected `source_url`) 미보유
