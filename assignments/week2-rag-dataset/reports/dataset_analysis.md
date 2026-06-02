# 2주차 RAG 데이터셋 정제 및 분석 결과

## 데이터셋 개요

이번 과제에서는 실제 BSVibe 코드베이스(`BSVibe/bsvibe-app`)를 분석해 개인화 작업 메모리 RAG에 사용할 source-derived seed dataset을 구성했습니다. 실제 사용자 데이터가 아니라 구현 파일, 런타임 배선, 프론트 API, 테스트 코드에서 확인한 구조적 사실을 record로 만들었습니다.

- 원본 record 수: 15
- RAG chunk 수: 15
- 검증 완료 note 비율: 15/15 (100.0%)
- 품질 flag 수: 0
- source repo: BSVibe/bsvibe-app

## 정제 자동화 결과

정제 코드는 다음 처리를 자동화합니다.

- JSONL 원본 record validation
- 이메일, API key, 로컬 경로 redaction
- 공백 정규화
- 태그 소문자 및 hyphen 형태 정규화
- source_type 기반 note_type 매핑
- GitHub source URL, source path, commit, line range 보존
- 외부 DB 적재를 위한 provenance field 생성
- embedding 대상 text chunk 생성

## Source Type 분포

| source_type | count |
| --- | --- |
| backend_code | 9 |
| runtime_code | 2 |
| frontend_code | 2 |
| readme | 1 |
| test_code | 1 |

## Note Type 분포

| note_type | count |
| --- | --- |
| implementation_evidence | 9 |
| runtime_evidence | 2 |
| surface_evidence | 2 |
| project_overview | 1 |
| verification_evidence | 1 |

## Source Path 분포

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

## 상위 태그

| tag | count |
| --- | --- |
| workspace-scoping | 3 |
| verification | 3 |
| vault | 2 |
| garden-notes | 2 |
| signal-filtering | 2 |
| pgvector | 2 |
| settle-worker | 2 |
| chunking | 2 |
| correct | 2 |
| retract | 2 |
| bsvibe-app | 1 |
| docker-compose | 1 |

## 길이 분석

| target | min | max | mean | median |
| --- | --- | --- | --- | --- |
| note_content_chars | 247 | 333 | 294.3 | 292 |
| chunk_chars | 247 | 333 | 294.3 | 292 |

## RAG 적재 관점 분석

이 데이터셋은 다음 주차 외부 DB 구축에서 바로 사용할 수 있도록 `clean_notes.jsonl`과 `rag_chunks.jsonl`로 분리했습니다.

- `clean_notes.jsonl`: 원본 note 단위의 정제 결과입니다. source_id, title, content, tags, verified, quality_flags를 보존합니다.
- `rag_chunks.jsonl`: vector DB 또는 pgvector에 넣기 좋은 chunk 단위 데이터입니다. `text`는 embedding 대상이고 `metadata`는 filter 및 citation 대상입니다.
- 추천 metadata filter: `product`, `source_repo`, `source_commit`, `source_path`, `source_type`, `note_type`, `tags`, `verified`, `created_at`
- 추천 provenance field: `chunk_id`, `note_id`, `source_id`, `metadata.title`, `metadata.source_url`, `metadata.source_path`

## 데이터 특성

현재 seed dataset은 실제 BSVibe 구현에서 RAG 관련성이 높은 파일을 선별한 작은 데이터셋입니다. 핵심 source는 `backend/knowledge`, `backend/workflow/application/runtime`, `apps/pwa/lib/api/knowledge.ts`, `apps/pwa/components/knowledge`, 그리고 decision reuse 검증 테스트입니다.

분석 결과 BSVibe RAG 데이터는 단순 문서 QA용 문서 묶음이 아니라, workspace-scoped vault, canonical concept, resolved decision, negative pattern, semantic note, frontend inspection/correction surface를 구분해야 합니다. 따라서 외부 DB에는 `note_type`과 `source_path`를 보존하고, 답변에는 `source_url`을 citation으로 노출하는 것이 적절합니다.

## 소스 코드 링크

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

## 보완 필요 사항

- 실제 서비스 데이터가 들어오면 workspace_id, user_id 같은 tenant 분리 field가 반드시 필요합니다.
- 현재 record는 코드 분석 기반 요약이므로, 다음 단계에서는 실제 vault note/frontmatter 샘플도 별도 source로 추가해야 합니다.
- 같은 의미의 태그를 더 안정적으로 합치기 위한 synonym dictionary가 필요합니다.
- 검색 평가를 위해 질문과 expected source_url을 묶은 retrieval fixture가 필요합니다.
- 개인화 메모리 특성상 redaction rule을 이메일/API key/로컬 경로 외에도 전화번호, URL token, 고객명까지 확장해야 합니다.
