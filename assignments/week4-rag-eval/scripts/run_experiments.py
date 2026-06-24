"""Week4 — 모든 실험을 한 번에 돌려 결과 JSON 으로 저장.

산출:
    data/results/baseline.json
    data/results/exp1_hybrid.json
    data/results/exp2_orchestrator.json
    data/results/judged.json   (각 실험의 LLM-judge 점수 + 종합 비교)

각 답변마다 다음을 stamp:
    qid / question / difficulty / expected_source_ids
    setup (어느 retriever + 어느 prompt)
    hits (top-K, source_id, score/sim, title)
    grounding (LLM 에 들어간 cap-clamp 후 statement)
    answer (LLM 출력)
    retrieval_metrics (hit@1, hit@3, rank)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "data" / "results"
QUESTIONS_PATH = ROOT / "data" / "eval" / "questions.jsonl"
DEFAULT_DSN = "postgresql+asyncpg://rag:rag@localhost:5433/rag_week3"

sys.path.insert(0, str(HERE))
from pipeline import BaselineRagPipeline, load_questions, retrieve_topk, format_baseline_context  # type: ignore  # noqa: E402
from hybrid_search import hybrid_search, load_knowledge_graph, _load_chunk_lookup  # type: ignore  # noqa: E402
from knowledge_orchestrator import KnowledgeAnswerOrchestrator  # type: ignore  # noqa: E402
from judge import judge_batch  # type: ignore  # noqa: E402


# ─── 공통 유틸 ────────────────────────────────────────────────────────────────

def _hits_to_records(hits: list[Any]) -> list[dict[str, Any]]:
    """SearchHit / HybridHit 둘 다 수용 — 디버깅용 dict 직렬화."""
    out: list[dict[str, Any]] = []
    for i, h in enumerate(hits, start=1):
        rec: dict[str, Any] = {
            "rank": i,
            "source_id": h.source_id,
            "similarity": round(float(getattr(h, "similarity", 0.0)), 4),
            "title": getattr(h, "title", ""),
        }
        # HybridHit 만 가진 per-method rank
        for k in ("bm25_rank", "vector_rank", "graph_rank", "score"):
            if hasattr(h, k):
                v = getattr(h, k)
                if v is not None:
                    rec[k] = round(v, 4) if isinstance(v, float) else v
        if hasattr(h, "matched_via"):
            rec["matched_via"] = list(h.matched_via)
        out.append(rec)
    return out


def _retrieval_metrics(hits: list[Any], expected: list[str]) -> dict[str, Any]:
    expected_set = set(expected)
    ranked = [h.source_id for h in hits]
    hit1 = bool(ranked[:1] and ranked[0] in expected_set)
    hit3 = any(sid in expected_set for sid in ranked[:3])
    hit5 = any(sid in expected_set for sid in ranked[:5])
    rank = next((i + 1 for i, sid in enumerate(ranked) if sid in expected_set), None)
    recall_at_k = len([sid for sid in ranked[: len(expected_set) + 2] if sid in expected_set]) / len(expected_set) if expected_set else 0.0
    return {
        "hit@1": hit1,
        "hit@3": hit3,
        "hit@5": hit5,
        "first_match_rank": rank,
        "recall_loose": round(recall_at_k, 3),
    }


# ─── Setup 1: baseline ────────────────────────────────────────────────────────

async def run_baseline(engine, questions: list[dict[str, Any]]) -> dict[str, Any]:
    """vector top-5 + baseline prompt."""
    pipe = BaselineRagPipeline(engine=engine, top_k=5)
    results = []
    t0 = time.time()
    for q in questions:
        ans = await pipe.answer(q["question"])
        results.append(
            {
                "qid": q["qid"],
                "question": q["question"],
                "difficulty": q["difficulty"],
                "expected_source_ids": q["expected_source_ids"],
                "hits": _hits_to_records(ans.hits),
                "grounding": [f"[{h.source_id}] {h.text}" for h in ans.hits],
                "answer": ans.answer,
                "retrieval_metrics": _retrieval_metrics(ans.hits, q["expected_source_ids"]),
            }
        )
    elapsed = time.time() - t0
    return {
        "name": "baseline",
        "label": "vector top-5 + baseline prompt",
        "settings": pipe.settings,
        "elapsed_s": round(elapsed, 1),
        "n": len(results),
        "results": results,
    }


# ─── Setup 2: EXP-1 hybrid retriever + baseline prompt ────────────────────────

async def run_exp1(engine, questions: list[dict[str, Any]]) -> dict[str, Any]:
    graph = load_knowledge_graph()
    lookup = _load_chunk_lookup()
    pipe = BaselineRagPipeline(engine=engine, top_k=5)  # 동일 prompt — retriever 만 교체

    results = []
    t0 = time.time()
    for q in questions:
        hits = await hybrid_search(
            q["question"], engine=engine, graph=graph, chunk_lookup=lookup, limit=5
        )
        # baseline pipeline 의 prompt 그대로 사용 — 단, retrieve 결과만 hybrid 로 대체
        context = format_baseline_context(hits)
        import litellm
        messages = [
            {"role": "system", "content": pipe._system},
            {"role": "system", "content": f"Context:\n{context}"},
            {"role": "user", "content": q["question"]},
        ]
        resp = await litellm.acompletion(
            model=pipe._model, messages=messages, temperature=pipe._temp, max_tokens=512
        )
        ans_text = resp.choices[0].message.content or ""
        results.append(
            {
                "qid": q["qid"],
                "question": q["question"],
                "difficulty": q["difficulty"],
                "expected_source_ids": q["expected_source_ids"],
                "hits": _hits_to_records(hits),
                "grounding": [f"[{h.source_id}] {h.text}" for h in hits],
                "answer": ans_text,
                "retrieval_metrics": _retrieval_metrics(hits, q["expected_source_ids"]),
            }
        )
    elapsed = time.time() - t0
    settings = dict(pipe.settings)
    settings["retriever"] = "hybrid: BM25 + Vector(bge-m3) + Graph(NetworkX), RRF k=60, top_k=5"
    settings["mirrors_retriever"] = "bsvibe-app backend/knowledge/retrieval/hybrid_search.py @ a6648ac"
    return {
        "name": "exp1_hybrid",
        "label": "hybrid retriever (Vector+BM25+Graph, RRF) + baseline prompt",
        "settings": settings,
        "elapsed_s": round(elapsed, 1),
        "n": len(results),
        "results": results,
    }


# ─── Setup 3: EXP-2 baseline retriever + orchestrator prompt ──────────────────

async def run_exp2(engine, questions: list[dict[str, Any]]) -> dict[str, Any]:
    async def vec_retrieve(q: str):
        return await retrieve_topk(q, engine=engine, k=5)

    orch = KnowledgeAnswerOrchestrator(
        retrieve_fn=vec_retrieve,
        retriever_label="vector(top-5)",
    )
    results = []
    t0 = time.time()
    for q in questions:
        r = await orch.answer(q["question"])
        hits = r.raw_hits
        results.append(
            {
                "qid": q["qid"],
                "question": q["question"],
                "difficulty": q["difficulty"],
                "expected_source_ids": q["expected_source_ids"],
                "hits": _hits_to_records(hits),
                "grounding": r.grounding,
                "answer": r.answer,
                "retrieval_metrics": _retrieval_metrics(hits, q["expected_source_ids"]),
            }
        )
    elapsed = time.time() - t0
    return {
        "name": "exp2_orchestrator",
        "label": "vector top-5 + KnowledgeAnswerOrchestrator prompt (bsvibe-mirror)",
        "settings": orch.settings,
        "elapsed_s": round(elapsed, 1),
        "n": len(results),
        "results": results,
    }


# ─── Judge: 세 setup 모두 LLM-judge 평가 ──────────────────────────────────────

async def run_judge(questions: list[dict[str, Any]], setups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    judged: dict[str, Any] = {}
    for setup_name, setup in setups.items():
        ans_map: dict[str, dict[str, Any]] = {
            r["qid"]: {"grounding": r["grounding"], "answer": r["answer"]}
            for r in setup["results"]
        }
        summary = await judge_batch(questions=questions, answers=ans_map)
        judged[setup_name] = {
            "overall": summary.overall(),
            "per_question": summary.rows,
        }
    return judged


# ─── 메인 ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    load_dotenv()
    os.environ.setdefault("OPENAI_API_KEY", "sk-noop")
    if "openai" in os.environ.get("OPENAI_API_KEY", ""):
        pass  # OK
    RESULTS.mkdir(parents=True, exist_ok=True)

    questions = load_questions(QUESTIONS_PATH)
    print(f"질문 {len(questions)}개 로드")

    engine = create_async_engine(DEFAULT_DSN)
    try:
        print("\n[baseline] vector top-5 + baseline prompt")
        baseline = await run_baseline(engine, questions)
        (RESULTS / "baseline.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  완료 ({baseline['elapsed_s']}s)")

        print("\n[exp1] hybrid retriever + baseline prompt")
        exp1 = await run_exp1(engine, questions)
        (RESULTS / "exp1_hybrid.json").write_text(json.dumps(exp1, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  완료 ({exp1['elapsed_s']}s)")

        print("\n[exp2] vector top-5 + orchestrator prompt")
        exp2 = await run_exp2(engine, questions)
        (RESULTS / "exp2_orchestrator.json").write_text(json.dumps(exp2, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  완료 ({exp2['elapsed_s']}s)")

        if os.getenv("OPENAI_API_KEY", "").startswith("sk-") and not os.getenv("OPENAI_API_KEY", "").startswith("sk-noop"):
            print("\n[judge] LLM-as-judge (gpt-4o-mini) for all setups")
            judged = await run_judge(questions, {"baseline": baseline, "exp1_hybrid": exp1, "exp2_orchestrator": exp2})
            (RESULTS / "judged.json").write_text(json.dumps(judged, ensure_ascii=False, indent=2), encoding="utf-8")
            print("  완료 — overall scores:")
            for name, j in judged.items():
                print(f"    {name}: {j['overall']}")
        else:
            print("\n[judge] SKIPPED — OPENAI_API_KEY 가 없거나 noop 입니다.")
    finally:
        await engine.dispose()

    print(f"\n결과 폴더: {RESULTS}")


if __name__ == "__main__":
    asyncio.run(main())
