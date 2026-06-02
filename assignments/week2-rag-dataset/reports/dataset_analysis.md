# 2주차 RAG 데이터셋 정제 및 분석 결과

## 데이터셋 개요

이번 과제에서는 BSVibe의 개인화 작업 메모리 RAG를 위한 synthetic seed dataset을 구성했습니다. 실제 사용자 데이터, 개인 이메일, API key, 로컬 경로는 사용하지 않고 공개 제출 가능한 예시 데이터만 넣었습니다.

- 원본 record 수: 16
- RAG chunk 수: 16
- 검증 완료 note 비율: 14/16 (87.5%)
- 품질 flag 수: 0

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

| source_type | count |
| --- | --- |
| feedback | 5 |
| decision | 3 |
| user_request | 2 |
| delivery_report | 2 |
| github_issue | 2 |
| project_doc | 2 |

## Note Type 분포

| note_type | count |
| --- | --- |
| repeated_pattern_candidate | 5 |
| decision_memory | 3 |
| raw_request | 2 |
| delivery_evidence | 2 |
| external_context | 2 |
| project_knowledge | 2 |

## 상위 태그

| tag | count |
| --- | --- |
| verification | 5 |
| decision | 4 |
| security | 3 |
| proposal-first | 2 |
| delivery-report | 2 |
| no-fake-done | 2 |
| approval-queue | 2 |
| github | 2 |
| rag | 2 |
| metadata | 2 |
| dashboard | 2 |
| mobile-ux | 1 |

## 길이 분석

| target | min | max | mean | median |
| --- | --- | --- | --- | --- |
| note_content_chars | 74 | 148 | 95.9 | 91.0 |
| chunk_chars | 74 | 148 | 95.9 | 91.0 |

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
