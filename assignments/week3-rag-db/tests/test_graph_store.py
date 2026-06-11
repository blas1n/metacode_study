"""GraphRAG store 유닛 테스트 — LLM 은 mock (실제 호출 금지)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from graph_store import (
    Entity,
    KnowledgeGraph,
    Relationship,
    build_messages,
    extract_triplets,
    normalize_name,
    parse_triplets,
)

# --- normalize_name --------------------------------------------------------


def test_normalize_name_lowercases_and_strips():
    assert normalize_name("  BSVibe  ") == "bsvibe"
    assert normalize_name("KnowledgeFactory") == "knowledgefactory"


# --- parse_triplets: 무결성 방어 (루브릭 ①) -------------------------------


def test_parse_valid_triplets():
    raw = json.dumps(
        {
            "entities": [
                {"name": "KnowledgeFactory", "entity_type": "component"},
                {"name": "Vault", "entity_type": "component"},
            ],
            "relationships": [
                {"source": "KnowledgeFactory", "target": "Vault", "rel_type": "constructs"}
            ],
        }
    )
    res = parse_triplets(raw)
    assert res.parse_ok is True
    assert len(res.entities) == 2
    assert len(res.relationships) == 1
    assert res.relationships[0].rel_type == "constructs"


def test_parse_drops_empty_and_none_entities():
    raw = json.dumps(
        {
            "entities": [
                {"name": "Vault", "entity_type": "component"},
                {"name": "", "entity_type": "component"},  # 빈 이름
                {"name": None, "entity_type": "component"},  # None
                {"name": "X", "entity_type": ""},  # 빈 타입
            ],
            "relationships": [],
        }
    )
    res = parse_triplets(raw)
    assert len(res.entities) == 1
    assert res.entities[0].name == "Vault"
    assert res.rejected_entities == 3


def test_parse_drops_incomplete_relationships():
    raw = json.dumps(
        {
            "entities": [],
            "relationships": [
                {"source": "A", "target": "B", "rel_type": "uses"},
                {"source": "A", "target": "", "rel_type": "uses"},  # 빈 target
                {"source": None, "target": "B", "rel_type": "uses"},  # None source
                {"source": "A", "target": "B", "rel_type": ""},  # 빈 rel_type
            ],
        }
    )
    res = parse_triplets(raw)
    assert len(res.relationships) == 1
    assert res.rejected_relationships == 3


def test_parse_malformed_json_returns_empty_not_crash():
    res = parse_triplets("이건 JSON 이 아닙니다 {")
    assert res.parse_ok is False
    assert res.entities == []
    assert res.relationships == []


def test_parse_strips_whitespace_in_names():
    raw = json.dumps(
        {"entities": [{"name": "  Vault  ", "entity_type": " component "}], "relationships": []}
    )
    res = parse_triplets(raw)
    assert res.entities[0].name == "Vault"
    assert res.entities[0].entity_type == "component"


# --- build_messages --------------------------------------------------------


def test_build_messages_includes_relation_types_and_text():
    system, user = build_messages("KnowledgeFactory constructs Vault.")
    assert "related_to" in system
    assert "constructs" in system
    assert "KnowledgeFactory constructs Vault." in user


# --- extract_triplets (llm mocked) -----------------------------------------


async def test_extract_triplets_calls_llm_and_parses():
    payload = json.dumps(
        {"entities": [{"name": "Vault", "entity_type": "component"}], "relationships": []}
    )
    llm_fn = AsyncMock(return_value=payload)
    res = await extract_triplets("some text", llm_fn)
    assert llm_fn.await_count == 1
    assert len(res.entities) == 1


# --- KnowledgeGraph: dedup (루브릭 ②) -------------------------------------


def test_upsert_entity_dedupes_by_normalized_name():
    g = KnowledgeGraph()
    g.upsert_entity(Entity(name="BSVibe", entity_type="product"))
    g.upsert_entity(Entity(name="bsvibe", entity_type="product"))  # 대소문자만 다름
    g.upsert_entity(Entity(name="  BSVibe  ", entity_type="product"))  # 공백
    assert g.num_nodes() == 1


def test_upsert_entity_same_name_merges_types_into_one_node():
    # LLM 이 같은 개체에 다른 free-form 타입을 줘도 이름으로 한 노드. 타입은 누적.
    g = KnowledgeGraph()
    nid = g.upsert_entity(Entity(name="vault", entity_type="component"))
    g.upsert_entity(Entity(name="vault", entity_type="concept"))
    assert g.num_nodes() == 1
    assert set(g.graph.nodes[nid]["entity_types"]) == {"component", "concept"}


def test_register_aliases_merges_into_one_node():
    # 이순신/충무공 의 BSVibe 판: 동일 개체 다른 표기 통합
    g = KnowledgeGraph()
    g.register_aliases("KnowledgeFactory", ["knowledge factory", "knowledge-factory"])
    g.upsert_entity(Entity(name="KnowledgeFactory", entity_type="component"))
    g.upsert_entity(Entity(name="knowledge factory", entity_type="component"))
    g.upsert_entity(Entity(name="knowledge-factory", entity_type="component"))
    assert g.num_nodes() == 1


def test_upsert_relationship_links_existing_nodes():
    g = KnowledgeGraph()
    g.upsert_entity(Entity(name="KnowledgeFactory", entity_type="component"))
    g.upsert_entity(Entity(name="Vault", entity_type="component"))
    edge_id = g.upsert_relationship(
        Relationship(source="KnowledgeFactory", target="Vault", rel_type="constructs")
    )
    assert edge_id is not None
    assert g.num_edges() == 1


def test_upsert_relationship_autocreates_missing_nodes():
    # 관계만 등장한 개체도 노드로 — 끊긴 컴포넌트 방지 (루브릭 ③ 연결성)
    g = KnowledgeGraph()
    g.upsert_relationship(Relationship(source="A", target="B", rel_type="uses"))
    assert g.num_nodes() == 2
    assert g.num_edges() == 1


def test_upsert_relationship_respects_aliases():
    g = KnowledgeGraph()
    g.register_aliases("Vault", ["the vault"])
    g.upsert_entity(Entity(name="Vault", entity_type="component"))
    g.upsert_entity(Entity(name="KnowledgeFactory", entity_type="component"))
    g.upsert_relationship(
        Relationship(source="KnowledgeFactory", target="the vault", rel_type="constructs")
    )
    # alias 가 canonical Vault 로 환원되므로 새 노드가 생기지 않음
    assert g.num_nodes() == 2
    assert g.num_edges() == 1
