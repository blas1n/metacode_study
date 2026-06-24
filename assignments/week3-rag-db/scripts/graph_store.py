"""Week3 GraphRAG store — bsvibe-app `backend/knowledge/graph` 패턴 이식.

- triplet 추출: ``litellm`` JSON 계약 (llm_extractor.py 의 system prompt + 스키마)
- 무결성 방어: ``parse_triplets`` 가 None/빈 문자열 entity·relationship 을 버리고
  거부 카운트를 남김 (루브릭 ① triplet 무결성 + 방어 코드)
- 개체명 중복 제거: ``normalize_name`` 키로 노드 병합 + alias 정제
  (graph_models.normalize_name + vault_backend.upsert_entity 미러, 루브릭 ②)
- 토폴로지: NetworkX ``MultiDiGraph`` — node/edge count + 시각화 (루브릭 ③)
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from string import Template

import networkx as nx
import structlog

logger = structlog.get_logger(__name__)

# 그래프 추출용 LLM (litellm 라우팅). gpt-4o-mini = 저렴 + JSON 추출 안정적.
GRAPH_LLM_MODEL = "gpt-4o-mini"

# 큐레이션된 관계 타입 — llm_extractor.py 의 ontology relation 화이트리스트 역할.
# 없으면 "related_to" 로 폴백 (프롬프트가 강제).
RELATION_TYPES = [
    "uses",
    "binds",
    "constructs",
    "exposes",
    "scopes",
    "verifies",
    "delivers",
    "persists",
    "depends_on",
    "produces",
    "part_of",
    "routes_to",
    "related_to",
]

# llm_extractor._SYSTEM_PROMPT_TEMPLATE 이식
SYSTEM_PROMPT = Template("""\
You are a knowledge graph extraction assistant.
Extract entities and relationships from the given text.

GUIDELINES:
- Entity types are FREE-FORM lowercase strings describing what the entity
  IS (e.g. "component", "tool", "concept", "product").
- Relationship types should come from this list when one fits:
  $relationship_types. If none fits, use "related_to".
- Only extract clearly stated facts, not speculation.

Respond with ONLY valid JSON in this format:
{
  "entities": [
    {"name": "entity name", "entity_type": "type"}
  ],
  "relationships": [
    {"source": "entity name", "target": "entity name", "rel_type": "type"}
  ]
}

If nothing can be extracted, respond with: {"entities": [], "relationships": []}""")

LlmFn = Callable[[str, str], Awaitable[str]]


def normalize_name(name: str) -> str:
    """graph_models.normalize_name 이식 — 노드 중복 제거용 정규형."""
    return name.strip().lower()


@dataclass(slots=True)
class Entity:
    name: str
    entity_type: str


@dataclass(slots=True)
class Relationship:
    source: str
    target: str
    rel_type: str


@dataclass(slots=True)
class ExtractionResult:
    """파싱 결과 + 무결성 거부 통계 (검증 로그용)."""

    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    rejected_entities: int = 0
    rejected_relationships: int = 0
    parse_ok: bool = True


def _clean(value: object) -> str:
    """문자열이면 strip, 아니면(None/숫자 등) 빈 문자열."""
    return value.strip() if isinstance(value, str) else ""


def parse_triplets(raw: str) -> ExtractionResult:
    """LLM 응답 JSON 을 방어적으로 파싱. None/빈 문자열은 버리고 카운트.

    llm_extractor.py 의 ``except (json.JSONDecodeError, ValueError)`` 방어를 이식 +
    entity name/type, relationship source/target/rel_type 가 비면 DB 에 넣지 않습니다.
    """
    res = ExtractionResult()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        res.parse_ok = False
        logger.warning("triplet_parse_failed", raw_preview=raw[:80])
        return res

    for e in data.get("entities", []) or []:
        name = _clean(e.get("name")) if isinstance(e, dict) else ""
        etype = _clean(e.get("entity_type")) if isinstance(e, dict) else ""
        if name and etype:
            res.entities.append(Entity(name=name, entity_type=etype))
        else:
            res.rejected_entities += 1

    for r in data.get("relationships", []) or []:
        src = _clean(r.get("source")) if isinstance(r, dict) else ""
        tgt = _clean(r.get("target")) if isinstance(r, dict) else ""
        rtype = _clean(r.get("rel_type")) if isinstance(r, dict) else ""
        if src and tgt and rtype:
            res.relationships.append(Relationship(source=src, target=tgt, rel_type=rtype))
        else:
            res.rejected_relationships += 1

    return res


def build_messages(text: str) -> tuple[str, str]:
    """(system, user) 프롬프트 쌍 생성."""
    system = SYSTEM_PROMPT.substitute(relationship_types=", ".join(RELATION_TYPES))
    user = f"Text:\n{text}"
    return system, user


async def extract_triplets(text: str, llm_fn: LlmFn) -> ExtractionResult:
    """``llm_fn(system, user)`` 호출 → :func:`parse_triplets`."""
    system, user = build_messages(text)
    raw = await llm_fn(system, user)
    return parse_triplets(raw)


class KnowledgeGraph:
    """NetworkX MultiDiGraph 백엔드 — vault_backend.py 의 dedup 의미 이식."""

    def __init__(self) -> None:
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()
        # normalize_name(canonical) -> node_id
        # bsvibe vault_backend 는 (name, entity_type) 로 키잉하지만, 그건 ontology 가
        # 타입을 제약하기 때문입니다. 여기서는 LLM 이 같은 개체에 chunk 마다 다른
        # free-form entity_type 을 붙여 노드가 파편화되므로 *이름* 을 개체 정체성으로
        # 삼고, 관측된 타입들은 노드 속성(entity_types)에 누적 보존합니다.
        self._name_index: dict[str, str] = {}
        # normalize_name(alias) -> canonical name  (개체명 정제)
        self._alias_map: dict[str, str] = {}

    def register_aliases(self, canonical: str, aliases: list[str]) -> None:
        """동일 개체를 가리키는 alias 들을 canonical 이름으로 매핑 (개체명 정제)."""
        for alias in aliases:
            self._alias_map[normalize_name(alias)] = canonical

    def _resolve(self, name: str) -> str:
        """alias 를 canonical 이름으로 환원."""
        return self._alias_map.get(normalize_name(name), name)

    def upsert_entity(self, entity: Entity) -> str:
        """normalize_name 으로 dedup. 기존 노드 있으면 관측 타입만 누적 병합."""
        canonical = self._resolve(entity.name)
        nn = normalize_name(canonical)
        existing = self._name_index.get(nn)
        if existing is not None:
            types = self._g.nodes[existing].setdefault("entity_types", [])
            if entity.entity_type and entity.entity_type not in types:
                types.append(entity.entity_type)
            return existing

        node_id = nn
        self._g.add_node(
            node_id,
            name=canonical,
            entity_type=entity.entity_type,
            entity_types=[entity.entity_type] if entity.entity_type else [],
        )
        self._name_index[nn] = node_id
        return node_id

    def _resolve_node(self, name: str) -> str | None:
        canonical = self._resolve(name)
        return self._name_index.get(normalize_name(canonical))

    def upsert_relationship(self, rel: Relationship) -> str | None:
        """source/target 이름을 노드로 해석 후 엣지 추가.

        관계에만 등장한 개체는 ``entity_type="unknown"`` 노드로 자동 생성해
        컴포넌트가 끊기지 않게 합니다 (루브릭 ③ 연결성).
        """
        src = self._resolve_node(rel.source)
        if src is None:
            src = self.upsert_entity(Entity(name=self._resolve(rel.source), entity_type="unknown"))
        tgt = self._resolve_node(rel.target)
        if tgt is None:
            tgt = self.upsert_entity(Entity(name=self._resolve(rel.target), entity_type="unknown"))

        self._g.add_edge(src, tgt, key=rel.rel_type, rel_type=rel.rel_type)
        return f"{src}->{tgt}:{rel.rel_type}"

    def num_nodes(self) -> int:
        return self._g.number_of_nodes()

    def num_edges(self) -> int:
        return self._g.number_of_edges()

    @property
    def graph(self) -> nx.MultiDiGraph:
        return self._g
