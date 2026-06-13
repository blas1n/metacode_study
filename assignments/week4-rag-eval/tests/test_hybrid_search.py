"""RRF fusion + 토큰화 단위 테스트 — week4 EXP-1."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(HERE))

from hybrid_search import (  # type: ignore
    DEFAULT_RRF_K,
    reciprocal_rank_fusion,
)


def test_rrf_single_source_ranks_in_order():
    """한 method 만 결과를 내면 그 method 의 순위가 그대로 유지."""
    ranked = {"vector": ["a", "b", "c"]}
    ordered, ranks = reciprocal_rank_fusion(ranked)
    assert [sid for sid, _ in ordered] == ["a", "b", "c"]
    # 1위가 가장 큰 score
    assert ordered[0][1] > ordered[1][1] > ordered[2][1]
    assert ranks["a"]["vector"] == 1


def test_rrf_combines_two_methods_addition():
    """두 method 가 같은 source 를 다른 rank 로 회수하면 점수가 합산 → 다른 source 보다 상위."""
    ranked = {
        "vector": ["a", "b", "c"],
        "bm25": ["b", "a", "d"],
    }
    ordered, ranks = reciprocal_rank_fusion(ranked, rrf_k=DEFAULT_RRF_K)
    score = dict(ordered)
    # a 와 b 는 두 method 모두 회수 → c, d 보다 위
    assert score["a"] > score["c"]
    assert score["b"] > score["d"]
    # b 가 1+2 위, a 가 2+1 위 — 합산이 같음
    assert abs(score["a"] - score["b"]) < 1e-9


def test_rrf_empty_method_graceful():
    """한 method 가 빈 결과여도 다른 method 결과는 그대로 반영."""
    ordered, _ = reciprocal_rank_fusion({"vector": ["x"], "bm25": [], "graph": []})
    assert ordered == [("x", 1 / (DEFAULT_RRF_K + 1))]


def test_rrf_ranks_recorded_per_method():
    """결과 객체에 method 별 rank 가 모두 기록 (디버깅용)."""
    _, ranks = reciprocal_rank_fusion(
        {"vector": ["x", "y"], "graph": ["y", "z"]}
    )
    assert ranks["x"]["vector"] == 1
    assert ranks["y"]["vector"] == 2
    assert ranks["y"]["graph"] == 1
    assert ranks["z"]["graph"] == 2
    # x 는 graph 에 없음 → graph rank 없음
    assert "graph" not in ranks["x"]


def test_rrf_k_changes_score_scale():
    """rrf_k 크기에 따라 절대 score 변화 (큰 k → 작은 score)."""
    a_small, _ = reciprocal_rank_fusion({"v": ["a"]}, rrf_k=10)
    a_large, _ = reciprocal_rank_fusion({"v": ["a"]}, rrf_k=100)
    assert a_small[0][1] > a_large[0][1]
