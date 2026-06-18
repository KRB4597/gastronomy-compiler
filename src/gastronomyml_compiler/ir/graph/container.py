from __future__ import annotations

from pydantic import BaseModel, Field

from .schema import EdgeKind, FlavorEdge, FlavorNode, NodeKind


class FlavorGraph(BaseModel):
    nodes: list[FlavorNode] = Field(default_factory=list)
    edges: list[FlavorEdge] = Field(default_factory=list)
    graph_hash: str | None = None

    # ------------------------------------------------------------------ #
    # Mutation helpers
    # ------------------------------------------------------------------ #

    def add_node(self, node: FlavorNode) -> None:
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: FlavorEdge) -> None:
        self.edges.append(edge)

    # ------------------------------------------------------------------ #
    # Query helpers
    # ------------------------------------------------------------------ #

    def node(self, node_id: str) -> FlavorNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def neighbors(self, node_id: str, kind: EdgeKind | None = None) -> list[str]:
        result = []
        for e in self.edges:
            if e.src == node_id and (kind is None or e.kind == kind):
                result.append(e.dst)
        return result

    def edges_between(self, src: str, dst: str) -> list[FlavorEdge]:
        return [e for e in self.edges if e.src == src and e.dst == dst]

    def nodes_of_kind(self, kind: NodeKind) -> list[FlavorNode]:
        return [n for n in self.nodes if n.kind == kind]

    def ingredient_nodes(self) -> list[FlavorNode]:
        return self.nodes_of_kind(NodeKind.INGREDIENT)

    def ingredient_pairs(self) -> list[tuple[FlavorNode, FlavorNode]]:
        ing = self.ingredient_nodes()
        return [(ing[i], ing[j]) for i in range(len(ing)) for j in range(i + 1, len(ing))]
