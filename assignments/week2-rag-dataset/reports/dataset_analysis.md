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

pinned commit 기준 폴더 단위 링크입니다. 파일별 line range 는 raw/processed JSONL 의 `source_url` 에 보존되어 있습니다.

| count | folder |
| --- | --- |
| 5 | [`backend/knowledge/retrieval`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval) |
| 4 | [`apps/pwa/components/knowledge`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/components/knowledge) |
| 4 | [`backend/workflow/application/runtime`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/runtime) |
| 3 | [`backend/knowledge/canonicalization`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/canonicalization) |
| 2 | [`backend/knowledge/application`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/application) |
| 2 | [`backend/knowledge/graph`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/graph) |
| 2 | [`backend/knowledge/ingest/ingest_compiler`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/ingest/ingest_compiler) |
| 2 | [`deploy`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/deploy) |
| 1 | [`README.md`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/README.md) |
| 1 | [`apps/pwa/lib/api`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/apps/pwa/lib/api) |
| 1 | [`backend/knowledge`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge) |
| 1 | [`backend/knowledge/_internal`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/_internal) |
| 1 | [`backend/knowledge/domain`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/domain) |
| 1 | [`backend/knowledge/mcp`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/mcp) |
| 1 | [`tests/glue`](https://github.com/BSVibe/bsvibe-app/tree/a6648ace49fa670136e6f865652990517e9865fa/tests/glue) |

## 9. 한계

- 코드 분석 기반이라 실제 vault note / frontmatter 샘플은 다음 단계에서 추가 필요
- 실제 서비스 데이터 들어오면 `workspace_id`, `user_id` tenant 필드 필수
- 검색 평가용 golden set (질문 ↔ expected `source_url`) 미보유
