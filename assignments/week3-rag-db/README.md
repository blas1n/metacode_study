# 3주차 과제: RAG 외부 DB 구축 (VectorRAG + GraphRAG)

2주차 정제 데이터셋(37 chunk)을 외부 DB 2종으로 적재하고 정량·정성 검증합니다.
기술 스택은 우리 제품 **bsvibe-app** 의 실제 구현을 그대로 이식했습니다.

- **VectorRAG** = pgvector — `litellm` 임베딩 + SQLAlchemy/asyncpg raw SQL (bsvibe `backend/embedding`)
- **GraphRAG** = NetworkX 지식 그래프 + LLM triplet 추출 (bsvibe `backend/knowledge/graph`)

## 폴더 구조

| 경로 | 설명 |
| --- | --- |
| `docker-compose.yml` | 전용 pgvector/pgvector:pg16 (포트 5433, 격리) |
| `requirements.txt` | bsvibe 스택 정렬 추가 의존성 |
| `scripts/vector_store.py` | pgvector 적재/검색 (bsvibe `storage/pg.py` 이식) |
| `scripts/build_vector_db.py` | VectorRAG 빌드 + 차원/count 검증 CLI |
| `scripts/graph_store.py` | triplet 추출 + NetworkX 그래프 (bsvibe `graph` 이식) |
| `scripts/build_graph_db.py` | GraphRAG 빌드 + 토폴로지/시각화 CLI |
| `scripts/bm25_baseline.py` | sparse BM25 baseline (dense 와 동일 metric 으로 비교) |
| `notebooks/01_vector_rag.ipynb` | VectorRAG 검증 (차원·count·유사도) |
| `notebooks/02_graph_rag.ipynb` | GraphRAG 검증 (무결성·dedup·토폴로지) |
| `reports/week3_db_report.md` | 검증 보고서 |
| `reports/knowledge_graph*.png` | NetworkX 시각화 (전체 / 코어) |
| `data/knowledge_graph.json` | 그래프 node_link_data (재현용) |
| `tests/` | 유닛 테스트 (28개, litellm·DB mock) |

## 실행

```bash
source .venv/bin/activate
pip install -r assignments/week3-rag-db/requirements.txt

# pgvector 컨테이너
docker compose -f assignments/week3-rag-db/docker-compose.yml up -d

# 빌드
python assignments/week3-rag-db/scripts/build_vector_db.py
python assignments/week3-rag-db/scripts/build_graph_db.py

# sparse baseline (dense 와 비교)
python assignments/week3-rag-db/scripts/bm25_baseline.py

# 테스트
cd assignments/week3-rag-db && python -m pytest tests/ -q
```

## 검증 결과 요약

**VectorRAG** — ① `vector(1536)` == 모델 차원 == 행 stamp dimension == 쿼리 임베딩 길이 ✅
② 37 chunk == 37 rows ✅ ③ golden 15문항 Hit@1 80% / Hit@3 100% / MRR 0.878.
한국어 질의↔영어 문서 cross-lingual 갭(KO 0.456 vs EN 0.716)을 정량 확인.
④ sparse BM25 baseline 비교: Hit@1 60%→80%(+20%p), Hit@3 73.3%→100%(+26.7%p),
MRR 0.692→0.878(+0.186) — dense 도입 정량 정당화.

**GraphRAG** — ① triplet None/빈값 방어(거부 카운트) + 깨진 JSON 안전 처리, 실빌드 거부 0 ·
빈 노드 0 ✅ ② 5종 표기 → 1 노드 통합(`normalize_name` + alias) ✅ ③ 272 노드 / 226 엣지 /
49 컴포넌트(최대 24.3%) + NetworkX 시각화 ✅

자세한 내용은 [reports/week3_db_report.md](reports/week3_db_report.md) 참고.

## 비고

- bsvibe-app 은 prod 에서 임베딩 모델로 `ollama/nomic-embed-text` 를 쓰지만, 과제는 루브릭 예시인
  `text-embedding-3-small`(1536d)로 구축했습니다.
- `litellm`+`openai 2.x` 도입으로 코스 `langchain-openai` 를 0.3.35 로 상향(openai 2.x 공존,
  langchain 0.3 라인 유지). 자세한 핀은 `requirements.txt`.
- 그래프 수치는 LLM 추출 비결정성으로 실행마다 ±소폭 변동. 보고서는 커밋된 산출물 기준.
