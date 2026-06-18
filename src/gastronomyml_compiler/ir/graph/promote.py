"""Promote flat IR entities into the FlavorGraph DAG (Pass 7.5)."""

from __future__ import annotations

from ..schemas import GastronomyIR
from .canonical import canonical_hash
from .container import FlavorGraph
from .schema import EdgeKind, FlavorEdge, FlavorNode, NodeKind


def graph_from_ir(ir: GastronomyIR) -> FlavorGraph:
    graph = FlavorGraph()

    # Dish root node
    dish_id = "dish:root"
    graph.add_node(FlavorNode(id=dish_id, kind=NodeKind.DISH, label=ir.document.title))

    # Ingredient nodes
    for ing in ir.ingredients:
        node_id = f"ingredient:{ing.id}"
        from ...ir.schemas import FLAVOR_DIMENSIONS
        scores = {
            d: getattr(ing.flavor_vector, d).value
            for d in FLAVOR_DIMENSIONS
        } if ing.flavor_vector else {}
        graph.add_node(FlavorNode(
            id=node_id,
            kind=NodeKind.INGREDIENT,
            label=ing.canonical_name or ing.name,
            flavor_scores=scores,
            metadata={"food_group": ing.food_group, "preparation": ing.preparation},
        ))
        graph.add_edge(FlavorEdge(src=dish_id, dst=node_id, kind=EdgeKind.CONTAINS))

    # Technique nodes
    for tech in ir.techniques:
        node_id = f"technique:{tech.id}"
        graph.add_node(FlavorNode(
            id=node_id,
            kind=NodeKind.TECHNIQUE,
            label=tech.name,
            metadata={"technique_type": tech.technique_type},
        ))
        for target_id in tech.applies_to:
            graph.add_edge(FlavorEdge(
                src=node_id,
                dst=f"ingredient:{target_id}",
                kind=EdgeKind.APPLIES_TO,
                payload={"transformation": tech.transformation.model_dump()},
            ))

    # Pairing rule edges
    for rule in ir.pairing_rules:
        edge_kind = _rule_modality_to_edge(rule.modality)
        graph.add_edge(FlavorEdge(
            src=f"ingredient:{rule.subject_id}",
            dst=f"ingredient:{rule.object_id}",
            kind=edge_kind,
            payload={"confidence": rule.confidence, "source": rule.source},
        ))

    graph.graph_hash = canonical_hash(graph)
    return graph


def _rule_modality_to_edge(modality: str) -> EdgeKind:
    return {
        "pairs_with": EdgeKind.PAIRS_WITH,
        "contrasts_with": EdgeKind.CONTRASTS_WITH,
        "enhances": EdgeKind.ENHANCES,
        "masks": EdgeKind.MASKS,
        "avoids": EdgeKind.AVOIDS,
    }.get(modality, EdgeKind.PAIRS_WITH)
