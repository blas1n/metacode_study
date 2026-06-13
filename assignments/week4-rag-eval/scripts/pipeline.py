"""Week4 baseline RAG pipeline — retrieve + generate.

End-to-end 단일 LLM call 로 답변하는 baseline. 이 스크립트는 다음 둘만 정의합니다.

1. ``retrieve_topk(question, k)``: week3 의 pgvector 스토어(bge-m3)에서 top-K 청크
   회수. 같은 코드 경로를 baseline / EXP-1 (hybrid) 둘 다 가져다 씁니다.
2. ``BaselineRagPipeline``: retrieve 결과를 baseline prompt 로 LLM 에 넘겨 답변
   생성. EXP-2 (knowledge-orchestrator 패턴) 와 직접 비교 가능한 단순 형태.

bsvibe-app 미러: ``backend/workflow/application/knowledge_orchestrator.py`` 의
LoopLlm seam 구조를 그대로 따랐습니다 (single complete() 호출 + messages 리스트).
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import litellm
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# week3 의 vector_store 를 그대로 재사용
WEEK3_SCRIPTS = Path(__file__).resolve().parents[2] / "week3-rag-db" / "scripts"
sys.path.insert(0, str(WEEK3_SCRIPTS))

from vector_store import RagVectorStore, SearchHit, embed_texts  # type: ignore  # noqa: E402

# ─── Baseline 설정 (보고서/노트북에서 그대로 표시) ───────────────────────────

DEFAULT_DSN = "postgresql+asyncpg://rag:rag@localhost:5433/rag_week3"
DEFAULT_TOP_K = 5

# baseline prompt — 가능한 짧고 평범한 RAG 프롬프트. EXP-2 와 대비.
BASELINE_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the provided context to answer the user's "
    "question."
)
BASELINE_LLM_MODEL = "ollama/llama3.2:3b"  # bsvibe prod 의 ollama 스택과 컨벤션 일치, 빠른 응답
BASELINE_LLM_TEMPERATURE = 0.0
BASELINE_MAX_TOKENS = 512  # 작은 로컬 LLM 의 반복 출력 방지


@dataclass(slots=True)
class RagAnswer:
    """단일 RAG 호출 결과 — 답변 텍스트 + 회수된 hits + 사용된 prompt."""

    question: str
    answer: str
    hits: list[SearchHit]
    messages: list[dict[str, Any]]
    settings: dict[str, Any]


def load_questions(path: Path | None = None) -> list[dict[str, Any]]:
    """questions.jsonl 한 줄 = 평가용 질문 하나."""
    p = path or Path(__file__).resolve().parent.parent / "data" / "eval" / "questions.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


async def retrieve_topk(
    question: str,
    *,
    engine,
    k: int = DEFAULT_TOP_K,
) -> list[SearchHit]:
    """질문을 bge-m3 로 임베딩 → pgvector 코사인 검색 → top-K hit 반환.

    week3 와 동일 경로 (week3-rag-db/scripts/vector_store.py).
    """
    emb = (await embed_texts([question]))[0]
    async with AsyncSession(engine) as s:
        store = RagVectorStore(s)
        return await store.search(query=emb, limit=k)


def format_baseline_context(hits: list[SearchHit]) -> str:
    """Baseline 의 context block — hit 별로 출처와 본문을 단순히 나열."""
    parts: list[str] = []
    for idx, h in enumerate(hits, start=1):
        parts.append(f"[{idx}] ({h.source_id}) {h.text}")
    return "\n".join(parts)


class BaselineRagPipeline:
    """Baseline RAG: retrieve → format context → LLM 한 번 호출.

    ``litellm.acompletion`` 으로 ollama / openai 둘 다 같은 인터페이스에서 동작.
    """

    def __init__(
        self,
        *,
        engine,
        top_k: int = DEFAULT_TOP_K,
        llm_model: str = BASELINE_LLM_MODEL,
        temperature: float = BASELINE_LLM_TEMPERATURE,
        system_prompt: str = BASELINE_SYSTEM_PROMPT,
    ) -> None:
        self._engine = engine
        self._k = top_k
        self._model = llm_model
        self._temp = temperature
        self._system = system_prompt

    @property
    def settings(self) -> dict[str, Any]:
        """과제 B 항목 (Baseline 구성 명시) 를 그대로 노출."""
        return {
            "text_splitter": "paragraph-boundary + max 420 chars (week2 chunking)",
            "chunk_size": 420,
            "chunk_overlap": 0,
            "embedding_model": "ollama/bge-m3",
            "embedding_dim": 1024,
            "vector_store": "pgvector (rag_chunks, vector(1024), ivfflat lists=10)",
            "retriever": f"cosine similarity, top_k={self._k}",
            "llm_model": self._model,
            "llm_temperature": self._temp,
            "prompt": "baseline (system + concatenated context + question)",
        }

    async def answer(self, question: str) -> RagAnswer:
        hits = await retrieve_topk(question, engine=self._engine, k=self._k)
        context = format_baseline_context(hits)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system},
            {"role": "system", "content": f"Context:\n{context}"},
            {"role": "user", "content": question},
        ]
        resp = await litellm.acompletion(
            model=self._model,
            messages=messages,
            temperature=self._temp,
            max_tokens=BASELINE_MAX_TOKENS,
        )
        answer_text = resp.choices[0].message.content or ""
        return RagAnswer(
            question=question,
            answer=answer_text,
            hits=hits,
            messages=messages,
            settings=self.settings,
        )


async def _smoke() -> None:
    """import 시 동작 확인 용 — `python pipeline.py` 직접 실행 시 1문항 시연."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        os.environ.setdefault("OPENAI_API_KEY", "sk-noop-for-ollama")

    engine = create_async_engine(DEFAULT_DSN)
    try:
        pipeline = BaselineRagPipeline(engine=engine)
        questions = load_questions()
        ans = await pipeline.answer(questions[0]["question"])
        print(f"Q: {ans.question}")
        print(f"\nTop-{len(ans.hits)} hits:")
        for i, h in enumerate(ans.hits, 1):
            print(f"  {i}. sim={h.similarity:.3f}  {h.source_id}  {h.text[:60]}...")
        print(f"\nA: {ans.answer}\n")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_smoke())
