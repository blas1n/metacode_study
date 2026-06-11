"""Week3 GraphRAG 빌드 CLI — rag_chunks → litellm triplet 추출 → NetworkX 그래프.

bsvibe-app 의 GraphExtractor/LLMExtractor + vault_backend dedup 파이프라인을
스터디용 단일 진입점으로 엮습니다. 실제 OpenAI 호출로 triplet 을 뽑고,
개체명을 정제(normalize_name + alias)한 뒤 NetworkX MultiDiGraph 로 적재합니다.

산출물:
    - data/knowledge_graph.json   : node_link_data (재현용)
    - reports/knowledge_graph.png : NetworkX 시각화 (루브릭 ③ 스크린샷)

실행::

    python assignments/week3-rag-db/scripts/build_graph_db.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import litellm
import matplotlib
import structlog
from dotenv import load_dotenv

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from graph_store import (  # noqa: E402
    GRAPH_LLM_MODEL,
    ExtractionResult,
    KnowledgeGraph,
    extract_triplets,
)
from vector_store import load_chunks  # noqa: E402

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = (
    REPO_ROOT
    / "assignments"
    / "week2-rag-dataset"
    / "data"
    / "processed"
    / "rag_chunks.jsonl"
)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

# 개체명 정제 — 동일 개체의 표기 흔들림을 canonical 로 통합 (충무공/이순신 의 BSVibe 판).
ALIASES: dict[str, list[str]] = {
    "BSVibe": ["bsvibe-app", "bsvibe app", "the bsvibe app", "bsvibe monorepo"],
    "KnowledgeFactory": ["knowledge factory", "knowledge-factory"],
    "Vault": ["the vault", "vaults"],
    "PWA": ["next.js pwa", "nextjs pwa"],
    "SettleWorker": ["settle worker"],
}


async def llm_complete(system: str, user: str, *, model: str = GRAPH_LLM_MODEL) -> str:
    """litellm.acompletion JSON 모드 (LLMExtractor 의 llm_fn 시그니처)."""
    resp = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


async def build() -> tuple[KnowledgeGraph, dict]:
    chunks = load_chunks(CHUNKS_PATH)
    logger.info("chunks_loaded", count=len(chunks))

    sem = asyncio.Semaphore(6)

    async def _one(text: str) -> ExtractionResult:
        async with sem:
            return await extract_triplets(text, llm_complete)

    results = await asyncio.gather(*[_one(c.text) for c in chunks])

    kg = KnowledgeGraph()
    for canonical, aliases in ALIASES.items():
        kg.register_aliases(canonical, aliases)

    rejected_entities = 0
    rejected_relationships = 0
    parse_failures = 0

    # 개체명 정제 퍼널 (루브릭 ②): mention → 표기 → normalize → alias 환원
    raw_surface: set[str] = set()
    after_normalize: set[str] = set()
    after_alias: set[str] = set()
    raw_entity_mentions = 0

    for res in results:
        if not res.parse_ok:
            parse_failures += 1
        rejected_entities += res.rejected_entities
        rejected_relationships += res.rejected_relationships
        for e in res.entities:
            raw_entity_mentions += 1
            raw_surface.add(e.name)
            after_normalize.add(e.name.strip().lower())
            after_alias.add(kg._resolve(e.name).strip().lower())
            kg.upsert_entity(e)
        for r in res.relationships:
            kg.upsert_relationship(r)

    # 관계에만 등장해 자동 생성된 노드 = 전체 노드 - entity 로 등록된(정제 후) 노드
    autocreated = kg.num_nodes() - len(after_alias)
    comp_sizes = sorted(
        (len(c) for c in nx.weakly_connected_components(kg.graph)), reverse=True
    )
    report = {
        "chunks": len(chunks),
        "raw_entity_mentions": raw_entity_mentions,
        "distinct_raw_surfaces": len(raw_surface),
        "after_normalize": len(after_normalize),
        "after_alias": len(after_alias),
        "autocreated_from_relationships": autocreated,
        "nodes": kg.num_nodes(),
        "edges": kg.num_edges(),
        "components": len(comp_sizes),
        "largest_component": comp_sizes[0] if comp_sizes else 0,
        "largest_component_pct": round(100 * comp_sizes[0] / kg.num_nodes(), 1)
        if kg.num_nodes()
        else 0.0,
        "rejected_entities": rejected_entities,
        "rejected_relationships": rejected_relationships,
        "parse_failures": parse_failures,
    }
    return kg, report


def _draw(graph: nx.MultiDiGraph, path: Path, *, title: str, font_size: int) -> None:
    plt.figure(figsize=(20, 16))
    pos = nx.spring_layout(graph, k=0.6, seed=42)
    nx.draw_networkx_nodes(graph, pos, node_size=450, node_color="#4C8BF5", alpha=0.85)
    nx.draw_networkx_edges(graph, pos, alpha=0.25, arrows=True, arrowsize=8)
    labels = {n: d.get("name", n) for n, d in graph.nodes(data=True)}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=font_size)
    plt.title(title, fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=130, bbox_inches="tight")
    plt.close()


def save_artifacts(kg: KnowledgeGraph) -> tuple[Path, Path, Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = DATA_DIR / "knowledge_graph.json"
    json_path.write_text(
        json.dumps(
            nx.node_link_data(kg.graph, edges="links"), ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    # 전체 그래프 — 연결 코어 + 주변 파편을 있는 그대로 (정직한 토폴로지)
    full_png = REPORTS_DIR / "knowledge_graph.png"
    _draw(
        kg.graph,
        full_png,
        title=f"Full graph ({kg.num_nodes()} nodes, {kg.num_edges()} edges)",
        font_size=6,
    )

    # 최대 연결 컴포넌트 — 라벨이 읽히는 코어 (연결성 직관 검증용)
    core_png = REPORTS_DIR / "knowledge_graph_core.png"
    largest = max(nx.weakly_connected_components(kg.graph), key=len)
    sub = kg.graph.subgraph(largest)
    _draw(
        sub,
        core_png,
        title=f"Largest connected component ({len(largest)} nodes)",
        font_size=9,
    )

    return json_path, full_png, core_png


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    kg, report = asyncio.run(build())
    json_path, full_png, core_png = save_artifacts(kg)
    (DATA_DIR / "graph_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== 개체명 정제 퍼널 (루브릭 ②) ===")
    print(f"entity mention 총합      : {report['raw_entity_mentions']}")
    print(f"distinct 표기(raw)       : {report['distinct_raw_surfaces']}")
    print(f"  → normalize_name 후    : {report['after_normalize']}")
    print(f"  → alias 환원 후         : {report['after_alias']}  (= entity 노드 수)")
    print("\n=== 그래프 토폴로지 (루브릭 ③) ===")
    print(f"총 노드 수              : {report['nodes']}")
    print(f"  - 관계서 자동생성(unknown): {report['autocreated_from_relationships']}")
    print(f"총 엣지 수              : {report['edges']}")
    print(
        f"weakly connected comp  : {report['components']}"
        f"  (최대 {report['largest_component']} 노드 = {report['largest_component_pct']}%)"
    )
    print("\n=== triplet 무결성 (루브릭 ①) ===")
    print(f"거부된 entity          : {report['rejected_entities']} (None/빈값 방어)")
    print(
        f"거부된 relationship    : {report['rejected_relationships']} (None/빈값 방어)"
    )
    print(f"JSON 파싱 실패 chunk    : {report['parse_failures']}")
    print(f"\n그래프 저장   : {json_path}")
    print(f"시각화(전체)  : {full_png}")
    print(f"시각화(코어)  : {core_png}")


if __name__ == "__main__":
    main()
