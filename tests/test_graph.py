"""Tests for FlavorGraph DAG substrate."""

from gastronomyml_compiler.ir.graph import (
    FlavorGraph,
    FlavorNode,
    FlavorEdge,
    NodeKind,
    EdgeKind,
    canonical_hash,
)


def _make_simple_graph() -> FlavorGraph:
    g = FlavorGraph()
    g.add_node(FlavorNode(id="dish:root", kind=NodeKind.DISH, label="Test Dish"))
    g.add_node(FlavorNode(id="ingredient:butter", kind=NodeKind.INGREDIENT, label="butter"))
    g.add_node(FlavorNode(id="ingredient:lemon", kind=NodeKind.INGREDIENT, label="lemon"))
    g.add_edge(FlavorEdge(src="dish:root", dst="ingredient:butter", kind=EdgeKind.CONTAINS))
    g.add_edge(FlavorEdge(src="dish:root", dst="ingredient:lemon", kind=EdgeKind.CONTAINS))
    g.add_edge(FlavorEdge(src="ingredient:lemon", dst="ingredient:butter", kind=EdgeKind.CONTRASTS_WITH))
    return g


def test_graph_construction():
    g = _make_simple_graph()
    assert len(g.nodes) == 3
    assert len(g.edges) == 3


def test_graph_node_lookup():
    g = _make_simple_graph()
    node = g.node("ingredient:butter")
    assert node is not None
    assert node.label == "butter"


def test_graph_neighbors():
    g = _make_simple_graph()
    neighbors = g.neighbors("dish:root", kind=EdgeKind.CONTAINS)
    assert "ingredient:butter" in neighbors
    assert "ingredient:lemon" in neighbors


def test_canonical_hash_deterministic():
    g = _make_simple_graph()
    h1 = canonical_hash(g)
    h2 = canonical_hash(g)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_canonical_hash_changes_on_mutation():
    g = _make_simple_graph()
    h1 = canonical_hash(g)
    g.add_node(FlavorNode(id="ingredient:thyme", kind=NodeKind.INGREDIENT, label="thyme"))
    h2 = canonical_hash(g)
    assert h1 != h2


def test_ingredient_pairs():
    g = _make_simple_graph()
    pairs = g.ingredient_pairs()
    assert len(pairs) == 1
    names = {pairs[0][0].label, pairs[0][1].label}
    assert names == {"butter", "lemon"}
