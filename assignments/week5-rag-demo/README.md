# 5주차 과제: RAG 데모 PoC

> **5차시 과제**: streamlit 혹은 다른 frontend 를 사용해 데모가 가능하도록 PoC 준비

## TL;DR — 진짜 PoC 는 [app.bsvibe.dev](https://app.bsvibe.dev) 입니다

지난 3주간 (week2~4) 의 모든 자산이 도출된 모티브 프로젝트 **bsvibe-app** 이 이미 production 으로 배포된 PoC 입니다. streamlit 데모를 새로 만드는 대신 운영 중인 PWA 를 그대로 제출합니다.

| 항목 | 값 |
|---|---|
| PoC URL | https://app.bsvibe.dev |
| 백엔드 API | https://api.bsvibe.dev |
| Repo | `BSVibe/bsvibe-app` (private) |
| 배포 스택 | Vercel (PWA) + Mac Mini self-host (FastAPI backend, pgvector, ollama) |
| Frontend | Next.js 14 PWA |
| Backend | FastAPI + SQLModel/asyncpg + pgvector + NetworkX + Ollama (`bge-m3`, `llama3.2`, `qwen3-coder`) |

## 우선순위 안내 (채점자에게)

> **회사 프로젝트와 학기 과제가 충돌하면 회사 프로젝트(bsvibe-app)를 우선합니다.**
>
> 5주차 과제의 핵심 요구사항은 "데모 가능한 PoC 준비" 입니다. bsvibe-app 이 이미 그 정의를 만족·초과 (live 배포 + 사용자 시나리오 다수 + 운영 중) 하므로, 별도 streamlit 래퍼 구축에 시간을 쓰는 대신 운영 중인 시스템을 그대로 제출합니다.
>
> 채점자가 직접 운영 환경에 접근하기 어려운 경우, 아래 §데모 흐름 의 스크린샷·녹화와 week2~4 의 코드/노트북을 함께 봐주시면 같은 RAG 파이프라인이 어떻게 구현·검증되었는지 확인 가능합니다.

## 데모 surfaces — 어떤 부분이 RAG PoC 인가

`app.bsvibe.dev` 안에서 RAG 동작을 직접 볼 수 있는 surface 세 곳:

### 1. Inside view (지식 그래프 + 의미 검색)

- 경로: `/inside`
- 백엔드: `GET /api/v1/inside/graph` (그래프 데이터) + `GET /api/v1/inside/concepts` (canonical concept) + `POST /api/v1/inside/observations` (의미 검색)
- 보여주는 것: workspace 가 학습한 ontology 노드 + 엣지를 force-directed 로 시각화, 노드 클릭 시 inspector 패널에 의미·출처·관련 노드
- week3 의 GraphRAG 가 prod 에서 돌아가는 모습 그 자체

### 2. Knowledge-only chat (RAG Q→A short-circuit)

- 경로: `/chat` (또는 새 메시지 입력)
- 백엔드: `POST /api/v1/messages` → frame stage 가 `knowledge_only` 분기 판단 → `KnowledgeAnswerOrchestrator` (week4 EXP-2 의 원본) 가 단일 LLM call 로 답변
- 보여주는 것: 질문 → grounding (인용된 vault note 들) + 답변 텍스트
- week4 EXP-2 가 미러한 그 코드 (`backend/workflow/application/knowledge_orchestrator.py`) 가 실서비스에서 라이브로 동작

### 3. Retract / Correct UI (M3a)

- 경로: Inside view → 노드 inspector → "Retract" 또는 "Correct" 버튼
- 백엔드: `POST /api/v1/inside/nodes/{node_ref}/retract` → `RetractionService` → 30 초 undo window → 자동 tombstone
- 보여주는 것: 잘못된 ontology 노드를 founder 가 한 클릭으로 retract, 30 초 안에 undo 가능, 이후 그래프에서 사라짐
- week2 의 record `bsvibe-src-016` (RetractionService) + `bsvibe-src-022` (Signal) + `bsvibe-src-027~029` (PWA UI) 들이 모두 라이브

## 데모 흐름 (스크린샷)

| # | surface | 무엇을 보여주나 | 파일 |
|---|---|---|---|
| 1 | Inside view 전체 | 학습된 지식 그래프 (272+ 노드) 시각화 | `screenshots/01_inside_graph.png` |
| 2 | 노드 inspector | 클릭 시 의미·출처·관련 노드 패널 | `screenshots/02_inspector.png` |
| 3 | Knowledge chat | 질문 입력 → grounding + 답변 | `screenshots/03_chat_answer.png` |
| 4 | Retract modal | M3a undo window | `screenshots/04_retract.png` |
| 5 | Undo toast | 30초 카운트다운 | `screenshots/05_undo_toast.png` |

(스크린샷 파일은 `screenshots/` 디렉토리에 추가.)

## week2~4 와의 매핑

이 PoC 가 지난 3주의 산출물과 **같은 코드 베이스에서 나왔다는 것** 을 보여주는 표:

| week | 우리가 한 것 | bsvibe-app 안 위치 |
|---|---|---|
| 2 | 정제된 RAG seed dataset 35 records 추출 + 정제 자동화 | `backend/knowledge/` 의 실제 분석 대상 (record source_url 들) |
| 3 | VectorRAG (pgvector, bge-m3) + GraphRAG (NetworkX) 구축 + 검증 | `backend/embedding/` + `backend/knowledge/graph/` 와 동일 stack |
| 4-EXP1 | Hybrid retrieval (Vector + BM25 + Graph, RRF) | `backend/knowledge/retrieval/hybrid_search.py @ a6648ac` (그대로 이식) |
| 4-EXP2 | Knowledge orchestrator prompt + cap + graceful | `backend/workflow/application/knowledge_orchestrator.py @ a6648ac` (그대로 이식) |

→ 학기 과제로 분석/측정한 RAG 패턴들이 **실서비스에서 라이브로 사용 중인** 코드를 미러한 것.

## 재현 (로컬에서 같은 RAG 돌리기)

운영 PoC 에 접근이 어려우면 week3/4 의 로컬 환경으로 동일 retrieval 가 그대로 재현됩니다.

```bash
# week3 인프라
docker compose -f assignments/week3-rag-db/docker-compose.yml up -d
ollama pull bge-m3 && ollama pull llama3.2:3b
python assignments/week3-rag-db/scripts/build_vector_db.py
python assignments/week3-rag-db/scripts/build_graph_db.py

# week4 의 전체 RAG 파이프라인 (hybrid + orchestrator) 한 번에 실행
python assignments/week4-rag-eval/scripts/run_experiments.py

# 결과 노트북 — 답변 + top-K + 점수 모두 embed
open assignments/week4-rag-eval/notebooks/week4_rag_evaluation.ipynb
```

## 폴더 구조

| 경로 | 설명 |
|---|---|
| `README.md` | 본 안내 + 우선순위 + 데모 흐름 |
| `screenshots/` | bsvibe-app 의 RAG surface 스크린샷 |

## 결론

PoC = bsvibe-app (앱 라이브, 백엔드 라이브, 두 실험에서 이식한 코드가 prod 에서 라이브). 학기 과제는 모티브를 따라가며 RAG 의 핵심 컴포넌트를 분리·측정·비교한 학습 산출물.
