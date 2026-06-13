"""Week4 — LLM-as-judge (4 criteria) for answer quality.

판단자(judge) 와 답변자(answerer) 는 분리 — 같은 모델이면 self-grading bias.

- answerer: ``ollama/llama3.2:3b`` (작고 빠른 로컬, 답변 생성용)
- judge: ``openai/gpt-4o-mini`` (강하고 객관적, 채점용)

평가 기준 4종:
1. **faithfulness** — 답변이 grounding 안의 내용으로 뒷받침되는가 (환각 없음)
2. **relevance** — 질문에 직접 답하는가
3. **completeness** — expected source 의 핵심 사실을 모두 다루는가 (다중 문서 종합 평가)
4. **citation** — `[source_id]` 인용이 사용됐고 grounding 의 source 와 일치하는가

각 기준 0~3 정수 점수. JSON schema 강제.

bsvibe-app 미러 포인트: ``backend/workflow/application/verification`` 의 LLM-judge
의 "structured JSON verdict + per-criterion score" 패턴과 유사한 모양으로 결과 구조화.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

import litellm

JUDGE_MODEL = "openai/gpt-4o-mini"
JUDGE_TEMPERATURE = 0.0

CRITERIA = ("faithfulness", "relevance", "completeness", "citation")
SCORE_MIN = 0
SCORE_MAX = 3

_JUDGE_SYSTEM = (
    "You are a strict but fair evaluator for a RAG question-answering system. "
    "Score the answer on four criteria (each integer 0-3). Be terse — return "
    "JSON only, no prose."
)

_RUBRIC = (
    "Criteria (each 0=fail, 1=poor, 2=acceptable, 3=excellent):\n"
    "- faithfulness: answer is supported by the GROUNDING snippets (no hallucination "
    "  beyond what the snippets or general well-known facts allow)\n"
    "- relevance: answer directly addresses the QUESTION\n"
    "- completeness: answer covers the key facts from ALL the EXPECTED source_ids\n"
    "- citation: answer cites [source_id] inline AND the cited ids appear in GROUNDING\n"
)

_JUDGE_INSTRUCTION = (
    "Output STRICT JSON of the form:\n"
    '{"faithfulness": int, "relevance": int, "completeness": int, "citation": int, '
    '"comment": "<1-2 sentence terse rationale>"}\n'
    "Nothing else. No markdown fence."
)


@dataclass(slots=True)
class JudgeVerdict:
    faithfulness: int
    relevance: int
    completeness: int
    citation: int
    comment: str = ""
    raw: str = ""

    @property
    def total(self) -> int:
        return self.faithfulness + self.relevance + self.completeness + self.citation

    @property
    def normalized(self) -> float:
        """0~1 정규화 — 각 기준 0~3 * 4기준 = 0~12."""
        return self.total / (SCORE_MAX * len(CRITERIA))

    def as_dict(self) -> dict[str, Any]:
        return {
            "faithfulness": self.faithfulness,
            "relevance": self.relevance,
            "completeness": self.completeness,
            "citation": self.citation,
            "total": self.total,
            "normalized": round(self.normalized, 3),
            "comment": self.comment,
        }


def _clip(x: Any) -> int:
    try:
        n = int(x)
    except (TypeError, ValueError):
        return 0
    return max(SCORE_MIN, min(SCORE_MAX, n))


def _parse_verdict(raw: str) -> JudgeVerdict:
    """JSON 추출 — ```json ... ``` 펜스가 섞여 와도 안전하게."""
    text = raw.strip()
    # remove fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 마지막 { ... } block 만 추출 시도
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
    return JudgeVerdict(
        faithfulness=_clip(data.get("faithfulness", 0)),
        relevance=_clip(data.get("relevance", 0)),
        completeness=_clip(data.get("completeness", 0)),
        citation=_clip(data.get("citation", 0)),
        comment=str(data.get("comment", "")).strip()[:240],
        raw=raw,
    )


async def judge_answer(
    *,
    question: str,
    expected_source_ids: list[str],
    grounding: list[str],
    answer: str,
    model: str = JUDGE_MODEL,
    temperature: float = JUDGE_TEMPERATURE,
) -> JudgeVerdict:
    """단일 답변 채점. grounding 은 LLM 에 실제 넘어간 cap-clamp 된 문장 목록."""
    user = (
        f"QUESTION:\n{question}\n\n"
        f"EXPECTED source_ids: {expected_source_ids}\n\n"
        f"GROUNDING ({len(grounding)} statements):\n"
        + ("\n".join(f"- {s}" for s in grounding) if grounding else "(none)")
        + f"\n\nANSWER:\n{answer}"
    )
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM + "\n\n" + _RUBRIC + "\n" + _JUDGE_INSTRUCTION},
        {"role": "user", "content": user},
    ]
    resp = await litellm.acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=300,
    )
    raw = resp.choices[0].message.content or "{}"
    return _parse_verdict(raw)


@dataclass(slots=True)
class JudgeSummary:
    """여러 답변의 평균 점수 + per-question breakdown."""

    rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.rows)

    def mean(self, key: str) -> float:
        if not self.rows:
            return 0.0
        return sum(r[key] for r in self.rows) / len(self.rows)

    def overall(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "mean_faithfulness": round(self.mean("faithfulness"), 2),
            "mean_relevance": round(self.mean("relevance"), 2),
            "mean_completeness": round(self.mean("completeness"), 2),
            "mean_citation": round(self.mean("citation"), 2),
            "mean_total": round(self.mean("total"), 2),
            "mean_normalized": round(self.mean("normalized"), 3),
        }


async def judge_batch(
    *,
    questions: list[dict[str, Any]],
    answers: dict[str, dict[str, Any]],
    model: str = JUDGE_MODEL,
) -> JudgeSummary:
    """questions 의 qid 별로 answers[qid] = {grounding, answer} 매핑.

    answers[qid] 가 없으면 그 질문은 건너뜀 (빠진 케이스 가시화는 caller 책임).
    """
    summary = JudgeSummary()
    sem = asyncio.Semaphore(4)

    async def one(q: dict[str, Any]) -> dict[str, Any] | None:
        qid = q["qid"]
        if qid not in answers:
            return None
        async with sem:
            verdict = await judge_answer(
                question=q["question"],
                expected_source_ids=q["expected_source_ids"],
                grounding=answers[qid]["grounding"],
                answer=answers[qid]["answer"],
                model=model,
            )
        row = {
            "qid": qid,
            "difficulty": q.get("difficulty", ""),
            **verdict.as_dict(),
        }
        return row

    rows = await asyncio.gather(*[one(q) for q in questions])
    summary.rows = [r for r in rows if r]
    return summary


async def _smoke() -> None:
    import os
    from dotenv import load_dotenv

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY 가 .env 에 없습니다.")

    v = await judge_answer(
        question="BSVibe 모노레포는 어떤 구성으로 돌아가나요?",
        expected_source_ids=["bsvibe-src-001"],
        grounding=[
            "[bsvibe-src-001] BSVibe is a unified monorepo with FastAPI backend and Next.js PWA, with Docker Compose for local stack and pgvector / Redis as data stores.",
        ],
        answer="BSVibe 모노레포는 FastAPI 백엔드와 Next.js PWA 로 구성되며, 로컬은 Docker Compose 로 띄워요 [bsvibe-src-001].",
    )
    print(json.dumps(v.as_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_smoke())
