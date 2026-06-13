"""Week4 EXP-2 — bsvibe ``KnowledgeAnswerOrchestrator`` 패턴 이식.

원본: ``backend/workflow/application/knowledge_orchestrator.py``

이식한 핵심:
1. ``_ANSWER_SYSTEM_PROMPT`` — 그대로. "answer not code", "if not covered say so".
2. ``_KNOWLEDGE_MAX_RESULTS = 5`` — top-N 그라운딩 cap (로컬 LLM 컨텍스트 예산).
3. ``_KNOWLEDGE_MAX_CHARS_PER_STATEMENT = 500`` — 한 statement 당 char clamp.
4. messages 구조 — ``[system, system(grounding), user]``. 두 번째 system block
   에 "Relevant established knowledge for this workspace (ground your answer
   in this)" 헤더 + bullet list.
5. Graceful empty — retrieval 실패시 ``[]`` 로 답변 그라운딩만 빠짐, never raises.
6. "ONE LLM call total" — tools=None plain completion.

차이점:
- 원본은 ``LoopLlm.complete(messages, tools=None)`` seam 호출. 우리는
  ``litellm.acompletion`` 으로 같은 single-call 의미를 유지.
- 원본은 retrieval seam (CanonRetriever.retrieve_for_signals) 을 받음. 우리는
  baseline retriever (Vector top-K) 또는 EXP-1 hybrid retriever 를 주입.
- 원본은 KO 답변 요구가 없음. 한국어 사용자 환경이라 system prompt 끝에
  "Answer in Korean unless the question is in English." 한 줄 추가.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

import litellm

# bsvibe knowledge_orchestrator.py 의 상수 이식 ─────────────────────────────────

_KNOWLEDGE_MAX_RESULTS = 5
_KNOWLEDGE_MAX_CHARS_PER_STATEMENT = 500
_INTENT_MAX_CHARS = 4_000

# 원본 시스템 프롬프트. KO 응답 + 반복 금지(작은 로컬 LLM 안정화용) 두 줄 추가.
_ANSWER_SYSTEM_PROMPT = (
    "You are answering a founder's question directly from this workspace's "
    "established knowledge — no engineering work is required. Give a concise, "
    "accurate answer grounded in the provided knowledge. If the knowledge does "
    "not cover the question, answer from general understanding and say so plainly. "
    "Do NOT claim to have changed any code or verified anything — this is an "
    "answer, not a code change. "
    "Answer in Korean if the question is in Korean, otherwise in English. "
    "Be CONCISE — answer in 3-6 sentences total, and cite knowledge with [source_id] "
    "in-line. Do NOT repeat or paraphrase the same statement multiple times."
)

# 작은 로컬 LLM (llama3.2:3b) 의 폭주를 막는 출력 cap.
_GENERATION_MAX_TOKENS = 512

# ─── 결과 컨테이너 ────────────────────────────────────────────────────────────

@dataclass(slots=True)
class OrchestratedAnswer:
    """orchestrator 호출 1회 결과."""

    question: str
    answer: str
    grounding: list[str]       # 실제 LLM 에 넘긴 cap 적용 후 statement 목록
    raw_hits: Any              # 원래 회수된 retriever 결과 (디버깅용)
    messages: list[dict[str, Any]]
    settings: dict[str, Any]


# ─── 핵심 — bsvibe orchestrator 의 _retrieve_knowledge + _compose_answer ────

def _to_statement(hit: Any) -> str:
    """retriever hit 한 건을 grounding statement 한 줄로 정규화.

    - SearchHit / HybridHit 둘 다 ``.text`` 와 ``.source_id`` 보유 가정.
    - 답변에서 인용 가능하도록 ``[source_id] text`` 형태로 emit.
    """
    sid = getattr(hit, "source_id", "?")
    text = getattr(hit, "text", "") or ""
    return f"[{sid}] {text}"


def _cap_statements(statements: Sequence[str]) -> list[str]:
    """bsvibe ``_retrieve_knowledge`` 의 cap 로직 그대로:
    statement strip + char clamp + top-N."""
    cleaned: list[str] = []
    for s in statements:
        if not s:
            continue
        c = s.strip()[:_KNOWLEDGE_MAX_CHARS_PER_STATEMENT]
        if c:
            cleaned.append(c)
        if len(cleaned) >= _KNOWLEDGE_MAX_RESULTS:
            break
    return cleaned


# ─── Orchestrator 클래스 (bsvibe 동명 클래스의 단순화 이식) ──────────────────

RetrieveFn = Callable[[str], Awaitable[list[Any]]]


class KnowledgeAnswerOrchestrator:
    """ONE LLM call 로 답변 생성. ``retrieve_fn`` 으로 retriever 만 갈아끼움."""

    def __init__(
        self,
        *,
        retrieve_fn: RetrieveFn,
        llm_model: str = "ollama/llama3.2:3b",
        temperature: float = 0.0,
        system_prompt: str = _ANSWER_SYSTEM_PROMPT,
        max_results: int = _KNOWLEDGE_MAX_RESULTS,
        max_chars_per_statement: int = _KNOWLEDGE_MAX_CHARS_PER_STATEMENT,
        retriever_label: str = "baseline-vector-topK",
    ) -> None:
        self._retrieve = retrieve_fn
        self._model = llm_model
        self._temp = temperature
        self._system = system_prompt
        self._max_results = max_results
        self._max_chars = max_chars_per_statement
        self._retriever_label = retriever_label

    @property
    def settings(self) -> dict[str, Any]:
        return {
            "prompt": "bsvibe KnowledgeAnswerOrchestrator (system + grounding-block + user)",
            "grounding_max_results": self._max_results,
            "grounding_max_chars_per_statement": self._max_chars,
            "llm_model": self._model,
            "llm_temperature": self._temp,
            "retriever": self._retriever_label,
            "graceful_empty": True,
            "mirrors": "backend/workflow/application/knowledge_orchestrator.py @ a6648ac",
        }

    async def _retrieve_grounding(self, question: str) -> tuple[list[str], list[Any]]:
        """bsvibe ``_retrieve_knowledge`` — 실패는 그대로 [] 로 (never raise).

        반환: (cap 적용된 statement 목록, raw hit 목록 — 디버깅용).
        """
        try:
            hits = await self._retrieve(question)
        except Exception:  # noqa: BLE001 — 그라운딩 실패가 답변을 깨면 안 됨
            return [], []
        cleaned = _cap_statements([_to_statement(h) for h in hits])
        return cleaned, list(hits)

    async def answer(self, question: str) -> OrchestratedAnswer:
        """bsvibe ``_compose_answer`` 의 messages 구조 이식 + single complete()."""
        question = question.strip()[:_INTENT_MAX_CHARS]
        grounding, raw_hits = await self._retrieve_grounding(question)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system},
        ]
        if grounding:
            body = "\n".join(f"- {s}" for s in grounding)
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Relevant established knowledge for this workspace "
                        "(ground your answer in this — cite by [source_id] when used):\n"
                        + body
                    ),
                }
            )
        messages.append({"role": "user", "content": question})

        resp = await litellm.acompletion(
            model=self._model,
            messages=messages,
            temperature=self._temp,
            max_tokens=_GENERATION_MAX_TOKENS,
        )
        answer_text = resp.choices[0].message.content or ""
        return OrchestratedAnswer(
            question=question,
            answer=answer_text,
            grounding=grounding,
            raw_hits=raw_hits,
            messages=messages,
            settings=self.settings,
        )


# ─── 직접 실행 시 스모크 ──────────────────────────────────────────────────────

async def _smoke() -> None:
    import os
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    from sqlalchemy.ext.asyncio import create_async_engine

    load_dotenv()
    os.environ.setdefault("OPENAI_API_KEY", "sk-noop")

    HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(HERE))
    from pipeline import retrieve_topk  # type: ignore

    engine = create_async_engine("postgresql+asyncpg://rag:rag@localhost:5433/rag_week3")
    try:
        async def vec_retrieve(q: str):
            return await retrieve_topk(q, engine=engine, k=5)

        orch = KnowledgeAnswerOrchestrator(
            retrieve_fn=vec_retrieve,
            retriever_label="vector(top-5)",
        )
        result = await orch.answer(
            "파운더가 잘못된 노드를 retract하면 어떤 흐름으로 처리되나요?"
        )
        print("Q:", result.question)
        print(f"\nGrounding ({len(result.grounding)} statements, cap={_KNOWLEDGE_MAX_RESULTS}):")
        for s in result.grounding:
            print(f"  - {s[:120]}...")
        print(f"\nA: {result.answer}\n")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_smoke())
