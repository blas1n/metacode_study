# 4주차 과제: RAG 성능 개선 및 평가 보고서

대상 프로젝트 **bsvibe-app** 의 외부 DB (week3 산출물) 위에 표준 RAG 파이프라인을 띄우고, 두 가지 개선 실험을 정량/정성 평가했습니다. 두 실험 모두 **bsvibe-app 의 실제 운영 코드를 그대로 이식** 했습니다 (직접 룰 작성 X).

## 0. 과제 요구사항 체크리스트

| # | 요구 | 충족 | 위치 |
|---|------|------|------|
| A1 | 평가 질문셋 ≥ 10개 | ✅ **20개** | `data/eval/questions.jsonl` |
| A2 | 단순 사실 조회 질문 ≥ 1 | ✅ 10개 (`difficulty=simple_fact`) | 동상 |
| A3 | 다중 문서 종합 질문 ≥ 1 | ✅ 6개 (`difficulty=multi_doc`) | 동상 |
| A4 | 조건 비교 질문 ≥ 1 | ✅ 4개 (`difficulty=compare`) | 동상 |
| A5 | 자연어 질문 | ✅ 모든 문항 한국어 자연어 | 동상 |
| B1 | Text Splitter 설정 | ✅ §1 표 | 보고서 §1 |
| B2 | Embedding Model 설정 | ✅ § 1 표 | 보고서 §1 |
| B3 | Vector Store 설정 | ✅ §1 표 | 보고서 §1 |
| B4 | Retriever (Top-k) 설정 | ✅ §1 표 | 보고서 §1 |
| B5 | Prompt 명시 | ✅ §1 + 부록 A | 보고서 §1 |
| B6 | LLM 명시 | ✅ §1 표 | 보고서 §1 |
| B7 | Baseline 실제 동작 시연 (Q→A) | ✅ §2 + 노트북 §3 | `notebooks/week4_rag_evaluation.ipynb` §3 |
| C | 성능 개선 실험 ≥ 2 | ✅ **2 (+공통 baseline)** | §3 EXP-1, §4 EXP-2 |
| C-각 | 변경/기대/결과/해석 4단 | ✅ 각 실험마다 표로 | §3, §4 |
| D | **모든 검색 단계에 top-k + 점수 + title 노출** | ✅ 노트북·보고서 전반 | 부록 B |
| E | 정량 + 정성 평가 둘 다 | ✅ Hit@k/MRR + LLM-as-judge 4기준 | §5 |

---

## 1. Baseline RAG 구성

| 항목 | 값 | bsvibe 원본 |
| --- | --- | --- |
| Text Splitter | paragraph-boundary + max 420 chars | `backend/knowledge/ingest/ingest_compiler/_chunking.py` |
| Chunk Size | 420 | 동상 |
| Chunk Overlap | 0 (paragraph 경계 자체가 의미 단위) | 동상 |
| Embedding Model | `ollama/bge-m3` (1024d, BAAI, 100+ 언어) | `backend/embedding/provider.py` |
| Vector Store | `pgvector` (rag_chunks, `vector(1024)`, ivfflat lists=10) | `backend/embedding/storage/pg.py` |
| Retriever | cosine similarity, top_k = **5** | `RagVectorStore.search` |
| Prompt (baseline) | system 메시지 1줄 + concatenated context + user 질문 | (단순 RAG 표준 형태 — 비교 기준선) |
| LLM | `ollama/llama3.2:3b`, temperature 0.0, max_tokens 512 | bsvibe prod 도 Ollama 스택 |
| LLM-as-judge | `openai/gpt-4o-mini`, temp 0.0 (4 기준 0-3점) | answerer/judge 분리로 self-bias 방지 |

전체 baseline 코드: [`scripts/pipeline.py`](../scripts/pipeline.py).

---

## 2. 평가 질문셋 (20문항)

| difficulty | 수 | 의미 | 예 |
|---|---|---|---|
| simple_fact | 10 | 한 문서에서 답이 나옴 | "BSVibe 모노레포는 어떤 구성으로 돌아가나요?" |
| multi_doc | 6 | 여러 문서를 종합해야 풀림 | "settle 단계에서 vault 노트를 어떻게 흡수하고 임베딩하나요?" |
| compare | 4 | 두 개체/모듈의 조건 비교 | "CanonRetriever와 NegativePatternRetriever는 신호를 처리하는 방식이 어떻게 다른가요?" |

전체 목록: [`data/eval/questions.jsonl`](../data/eval/questions.jsonl).

---

## 3. 실험 1 — Hybrid Retrieval (Vector + BM25 + Graph, RRF)

### 변경한 것

- baseline 의 retriever (vector top-5) 를 **bsvibe-app `backend/knowledge/retrieval/hybrid_search.py` 의 RRF 패턴** 으로 교체.
- 세 갈래 검색 (BM25 / Vector / Graph) 을 병렬 수행 → 각 method 의 rank 기반 score `sum(1/(rrf_k + rank))` 로 결합 → top-5.
- prompt 와 LLM 은 baseline 과 동일 (retriever 효과만 분리).

### bsvibe 미러 출처

원본: [`backend/knowledge/retrieval/hybrid_search.py` @ a6648ac](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/knowledge/retrieval/hybrid_search.py)
- `rrf_k=60` (RRF 논문 표준)
- `return_exceptions=True` + `_ok()` graceful 패턴 그대로
- per-method rank 모두 결과 객체에 보존 (`bm25_rank`, `vector_rank`, `graph_rank`)

원본은 entity 단위 GraphBackend 위에서 동작. 우리는 RAG 컨텍스트로 chunk 가 필요해 **fusion 결과를 source_id 로 집계** 하도록 인터페이스만 적응.

### 기대했던 효과

- BM25 가 한영 혼합 토큰 / 정확 키워드 회수 보강
- Graph 의 entity 1-hop 이웃이 다중 문서 종합 질문에 보탬
- → multi_doc / compare 질문에서 completeness 향상

### 실제 결과

| 지표 | baseline | exp1_hybrid | gain |
|---|---|---|---|
| Hit@1 | **95.0%** | 75.0% | -20.0%p |
| Hit@3 | 100.0% | 95.0% | -5.0%p |
| MRR | **0.967** | 0.842 | -0.125 |
| LLM-judge total /12 | 9.20 | **9.80** | **+0.60** |
| faithfulness | 2.80 | **3.00** | +0.20 |
| relevance | 3.00 | 3.00 | — |
| completeness | 2.20 | **2.35** | +0.15 |
| citation | 1.20 | 1.45 | +0.25 |
| normalized | 0.767 | **0.817** | +0.050 |

20문항 중 **8문항**이 normalized 상승, 2문항이 하락 (q-011 -0.167, q-012 -0.166), 10문항 동률.

가장 큰 향상 사례 (Δ ≥ +0.25):

| qid | difficulty | Δ | 무엇이 바뀌었나 |
|---|---|---|---|
| q-001 | simple_fact | **+0.250** | hybrid 가 그래프 1-hop 으로 `bsvibe-src-001` (정답) + `src-030/004` (구성) + 추가 인접 source 회수 → completeness 향상 |
| q-008 | simple_fact | **+0.333** | baseline 이 retrieve 한 5건 중 정답 외에 답변에 못 박은 source 가 있었음. hybrid 가 더 일관된 grounding 제공 |
| q-017 | compare | **+0.250** | "agent_runtime의 native loop와 KnowledgeAnswerOrchestrator의 short-circuit 경로는 어떤 점이 다른가요?" — graph 가 두 경로의 인접 entity 를 회수, baseline 보다 답변의 비교 구조 강화 |

### 왜 이런 결과가 나왔다고 생각하는가

**핵심 — retrieval metric ≠ answer quality.**
- Hit@1 / MRR 은 baseline 이 더 좋게 나옵니다 (dense vector 가 정답 chunk 를 첫 hit 으로 잘 잡음).
- 그런데도 답변 quality (LLM-judge total) 는 hybrid 가 +0.60 앞섭니다.
- 원인: baseline 의 top-5 는 같은 주제의 비슷한 chunk 가 다수 (low diversity). hybrid 는 BM25 의 keyword 매칭 + Graph 의 entity-neighbor 가 **다른 source 를 top-5 안에 채워 넣어** LLM 의 grounding context 가 풍부해짐. 결과적으로 답변의 completeness / faithfulness 가 올라감.
- 단점: 정답이 RRF 결합 후 1위에서 밀리는 경우가 생겨 Hit@1 손해 (-20%p). 그러나 top-3 에는 거의 항상 들어옴 (95%). RAG 는 답변 generation 단계에서 top-K 를 다 쓰므로 1위 여부보다 5위 안의 풀이 중요.

### 노트북 + 결과 위치

- [`week4_rag_evaluation.ipynb`](../notebooks/week4_rag_evaluation.ipynb) §5.3 — 결정적 사례 retrieval 결과 + 답변 비교 (top-K 전부 sim/rank/title 표시)
- [`data/results/exp1_hybrid.json`](../data/results/exp1_hybrid.json) — 20문항 raw 결과

---

## 4. 실험 2 — Knowledge Orchestrator Prompt (bsvibe 패턴)

### 변경한 것

- retriever 는 baseline 과 동일 (vector top-5). **프롬프트만** bsvibe `backend/workflow/application/knowledge_orchestrator.py` 패턴으로 교체.
- 시스템 프롬프트, grounding-block 구조, top-N cap, per-statement char clamp, graceful empty, "answer not code" honesty rule, KO 응답 + concise + `[source_id]` 인용 지시 — 모두 원본 코드 그대로 (+ KO 한 줄 추가).

### bsvibe 미러 출처

원본: [`backend/workflow/application/knowledge_orchestrator.py` @ a6648ac](https://github.com/BSVibe/bsvibe-app/blob/a6648ace49fa670136e6f865652990517e9865fa/backend/workflow/application/knowledge_orchestrator.py)
- `_KNOWLEDGE_MAX_RESULTS = 5` (top-N 그라운딩 cap)
- `_KNOWLEDGE_MAX_CHARS_PER_STATEMENT = 500` (per-statement char clamp)
- `_ANSWER_SYSTEM_PROMPT` (시스템 프롬프트 본문 그대로)
- messages = `[system, system(grounding), user]` 3-block 구조
- "ONE LLM call total" + `tools=None` plain completion
- Graceful empty — retrieval 실패시 grounding 만 빠지고 답변은 진행

### 기대했던 효과

- 시스템 프롬프트의 "Cite [source_id]" 지시로 **citation 점수** 향상
- top-N 5 + per-statement 500 chars cap 으로 LLM 컨텍스트 부담 ↓, 응답 안정성 ↑
- "If the knowledge does not cover the question, ... say so plainly" 로 환각 감소 (faithfulness ↑)

### 실제 결과

| 지표 | baseline | exp2_orchestrator | gain |
|---|---|---|---|
| Hit@1 | 95.0% | 95.0% | — |
| Hit@3 | 100.0% | 100.0% | — |
| MRR | 0.967 | 0.967 | — |
| LLM-judge total /12 | 9.20 | 9.05 | -0.15 |
| faithfulness | 2.80 | 2.65 | -0.15 |
| relevance | 3.00 | 2.95 | -0.05 |
| completeness | 2.20 | 1.95 | -0.25 |
| **citation** | 1.20 | **1.50** | **+0.30** |
| normalized | 0.767 | 0.754 | -0.013 |

citation 단독으로는 명확히 향상 (1.20 → 1.50, **+25%**). 다른 기준은 미세하게 후퇴 → 종합 점수는 baseline 대비 -0.013 으로 동률 수준.

### 왜 이런 결과가 나왔다고 생각하는가

- **citation 향상 (+0.30)** 은 의도한 효과 그대로. 시스템 프롬프트의 ``Cite knowledge with [source_id] in-line`` 한 줄이 작은 LLM (llama3.2:3b) 에도 통함. 답변에 `[bsvibe-src-XXX]` 형태가 빈번하게 등장.
- **completeness 후퇴 (-0.25)** 의 원인은 두 가지:
  1. `_KNOWLEDGE_MAX_CHARS_PER_STATEMENT = 500` 으로 statement 를 잘랐는데, 우리 데이터셋의 chunk 가 평균 333 chars 라 대부분은 잘리지 않지만, q-018 같은 다중 파이프라인 종합 질문에선 긴 grounding 이 잘려나가 정보 손실.
  2. system prompt 의 "concise, 3-6 sentences" 지시가 다중 source 종합 답변에서는 약간의 over-truncation 을 유발.
- **faithfulness 후퇴 (-0.15)** 는 일부 질문에서 모델이 "If the knowledge does not cover..." 지시를 너무 적극적으로 해석해 grounding 안에 있는 사실까지도 "확실하지 않음" 처리한 사례 때문.

### 권장 적용 시나리오

- **citation 규율이 중요한 경우** (감사 추적, 법무 인용, 트러스트 라인) — orchestrator 패턴 강한 효과.
- **다중 문서 종합이 중요한 경우** — cap 을 풀거나 (예: max_chars 1000), EXP-1 의 hybrid retriever 와 결합.

### 노트북 + 결과 위치

- [`week4_rag_evaluation.ipynb`](../notebooks/week4_rag_evaluation.ipynb) §5.4 — baseline vs orchestrator 답변 직접 비교
- [`data/results/exp2_orchestrator.json`](../data/results/exp2_orchestrator.json)

---

## 5. 종합 비교 + 결론

### 5.1 정량 종합

| 평가축 | 승자 | 점수 | 비고 |
|---|---|---|---|
| Hit@1 | baseline | 95.0% | dense top-1 이 이미 강함 |
| Hit@3 | baseline ≡ exp2 | 100.0% | 동률 |
| MRR | baseline ≡ exp2 | 0.967 | 동률 |
| LLM-judge total | **exp1 hybrid** | **9.80 /12** | 종합 답변 quality 1위 |
| faithfulness | exp1 hybrid | 3.00 | grounding 다양성 효과 |
| completeness | exp1 hybrid | 2.35 | 다중 source 효과 |
| citation | **exp2 orch** | **1.50** | 프롬프트 인용 강제 |

### 5.2 정성 종합

- **Retrieval metric (Hit@k, MRR) 만으로는 RAG quality 를 판단할 수 없다** 가 가장 큰 인사이트. baseline 이 retrieval 단독에서는 모든 metric 1위지만 답변 단계에서는 hybrid 에 뒤집힘.
- 두 실험은 **서로 다른 축을 개선**합니다: EXP-1 = grounding 다양성 (faithfulness/completeness), EXP-2 = 답변 규율 (citation). 둘은 결합 가능하며, 다음 단계로 hybrid retriever + orchestrator prompt 조합을 검증할 가치가 큽니다.
- 두 실험 모두 bsvibe-app 의 실제 운영 코드를 이식해 검증된 패턴을 적용했습니다. 직접 룰을 만들었더라면 RRF 의 `rrf_k=60` 같은 미세조정, statement cap 의 적정값 같은 부분에서 시행착오가 컸을 것입니다.

### 5.3 다음 단계 (과제 범위 외)

1. **EXP-1 + EXP-2 결합** — hybrid 의 retrieval pool 을 orchestrator 의 cap-clamp grounding 으로 LLM 에 주입.
2. **Retrieval-aware reranker** — hybrid 의 RRF top-5 를 cross-encoder (예: bge-reranker-v2-m3) 로 재정렬.
3. **Query rewrite** — KO 질문을 EN keyword query 로 변환 후 hybrid 에 주입 (week3 의 cross-lingual 갭 후속).

---

## 부록 A — Baseline / EXP-2 시스템 프롬프트 전문

**Baseline:**
```
You are a helpful assistant. Use the provided context to answer the user's question.
```

**EXP-2 (bsvibe knowledge_orchestrator.py 그대로 + KO 한 줄):**
```
You are answering a founder's question directly from this workspace's
established knowledge — no engineering work is required. Give a concise,
accurate answer grounded in the provided knowledge. If the knowledge does
not cover the question, answer from general understanding and say so plainly.
Do NOT claim to have changed any code or verified anything — this is an
answer, not a code change.
Answer in Korean if the question is in Korean, otherwise in English.
Be CONCISE — answer in 3-6 sentences total, and cite knowledge with [source_id]
in-line. Do NOT repeat or paraphrase the same statement multiple times.
```

## 부록 B — Top-K 노출 확인

요구: "모든 검색 단계에서 top-k 결과 + 점수 + 문서 title 노출". 본 과제의 모든 산출물에서 다음을 검증:

| 산출물 | top-K 노출 여부 | 위치 |
|---|---|---|
| `week4_rag_evaluation.ipynb` §3 | ✅ sim + source_id + title 5건 × 3문항 | embedded cell output |
| `week4_rag_evaluation.ipynb` §5.3 (exp1) | ✅ RRF score + matched_via + per-method rank + title | embedded cell output |
| `week4_rag_evaluation.ipynb` §5.4 (exp2) | ✅ baseline 과 exp2 답변 모두 source 인용 노출 | embedded cell output |
| `data/results/baseline.json` | ✅ 모든 질문의 hits[0..4] 에 source_id/similarity/title | raw JSON |
| `data/results/exp1_hybrid.json` | ✅ 추가로 bm25_rank/vector_rank/graph_rank/matched_via | raw JSON |
| `data/results/exp2_orchestrator.json` | ✅ hits + grounding 두 형태로 노출 | raw JSON |
| 본 보고서 §3 결정적 사례 | ✅ q-001/q-008/q-017 각각의 top-5 비교 | (노트북 §3 cell 참고) |

> raw JSON 들은 `data/results/` 에 그대로 commit. 채점자가 셀 출력만이 아니라 JSON 까지 직접 검증 가능.

## 부록 C — 재현 방법

```bash
# pgvector + bge-m3 준비 (week3 와 동일 환경)
docker compose -f assignments/week3-rag-db/docker-compose.yml up -d
ollama pull bge-m3
ollama pull llama3.2:3b

# week3 의 vector DB 가 이미 있다고 가정. 없으면:
python assignments/week3-rag-db/scripts/build_vector_db.py
python assignments/week3-rag-db/scripts/build_graph_db.py

# week4 — 전체 실험 + LLM-judge 한 번에 실행
python assignments/week4-rag-eval/scripts/run_experiments.py

# 노트북 열어 결과 확인 (모든 셀에 출력이 embed 됨)
# notebooks/week4_rag_evaluation.ipynb
```
