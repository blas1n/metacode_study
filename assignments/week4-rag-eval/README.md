# 4주차 과제: RAG 성능 개선 및 평가

지난 주 (week3) 의 외부 DB 위에 표준 RAG 파이프라인을 띄우고, 두 가지 개선 실험을 정량/정성 평가했습니다. 두 실험 모두 우리 제품 **bsvibe-app** 의 실제 운영 코드를 그대로 이식.

- 평가 질문: **20문항** (simple_fact 10 / multi_doc 6 / compare 4)
- Baseline: vector top-5 + 평범한 RAG 프롬프트
- **EXP-1**: Hybrid retriever — Vector + BM25 + Graph 의 RRF 결합 (`bsvibe hybrid_search.py` 이식)
- **EXP-2**: Knowledge Orchestrator prompt — top-N cap + per-statement clamp + 인용 강제 (`bsvibe knowledge_orchestrator.py` 이식)
- 평가: 검색 metric (Hit@1/3/5, MRR) + 답변 metric (LLM-as-judge, gpt-4o-mini, 4기준 0-3점)

## 결과 요약

| 평가축 | baseline | exp1_hybrid | exp2_orchestrator |
|---|---|---|---|
| Hit@1 | **95.0%** | 75.0% | 95.0% |
| Hit@3 | 100% | 95.0% | 100% |
| MRR | **0.967** | 0.842 | 0.967 |
| LLM-judge total /12 | 9.20 | **9.80** | 9.05 |
| faithfulness | 2.80 | **3.00** | 2.65 |
| completeness | 2.20 | **2.35** | 1.95 |
| citation | 1.20 | 1.45 | **1.50** |

핵심 인사이트 — **retrieval metric ≠ answer quality**. Hit@1/MRR 은 baseline 이 더 좋지만 답변 품질은 hybrid 가 +0.6/12. 자세한 분석은 [`reports/week4_report.md`](reports/week4_report.md).

## 폴더 구조

| 경로 | 설명 |
| --- | --- |
| `data/eval/questions.jsonl` | 평가 질문 20개 (난이도 마킹) |
| `data/results/` | 세 setup 의 raw 결과 JSON + LLM-judge 결과 |
| `scripts/pipeline.py` | Baseline RAG (retrieve + generate) |
| `scripts/hybrid_search.py` | EXP-1 — bsvibe `hybrid_search.py` 이식 (RRF) |
| `scripts/knowledge_orchestrator.py` | EXP-2 — bsvibe `knowledge_orchestrator.py` 이식 |
| `scripts/judge.py` | LLM-as-judge (gpt-4o-mini, 4기준) |
| `scripts/run_experiments.py` | 전체 파이프라인 실행 → JSON 산출 |
| `notebooks/01_baseline_and_questions.ipynb` | Baseline + 질문셋 시연 (top-K 출력 embed) |
| `notebooks/02_experiments_comparison.ipynb` | 세 setup 비교 (정량 + 결정적 사례) |
| `reports/week4_report.md` | 메인 보고서 (체크리스트·실험·분석) |
| `tests/test_hybrid_search.py` | RRF 로직 단위 테스트 |

## 실행

```bash
source .venv/bin/activate
# 의존: week3 의 docker compose + ollama 모델 + .env (OPENAI_API_KEY)
docker compose -f assignments/week3-rag-db/docker-compose.yml up -d
ollama pull bge-m3 && ollama pull llama3.2:3b

# week3 vector/graph DB 가 이미 있다고 가정 (없으면 week3 build 스크립트 먼저)

# 전체 실험 + LLM-judge 일괄 실행 (~3분)
python assignments/week4-rag-eval/scripts/run_experiments.py

# 단위 테스트
cd assignments/week4-rag-eval && python -m pytest tests/ -q
```

## 비고

- LLM (answerer) 은 `ollama/llama3.2:3b` — 작고 빠른 로컬 (3B). 응답 일관성 위해 `max_tokens=512` 와 "concise 3-6 sentences" 시스템 프롬프트.
- LLM-judge 는 `openai/gpt-4o-mini` — answerer/judge 분리해서 self-grading bias 차단.
- bsvibe 미러는 모듈 docstring 에 출처 commit 까지 명시 (`@ a6648ac`).
