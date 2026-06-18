import hashlib
import json

from .container import FlavorGraph


def canonical_hash(graph: FlavorGraph) -> str:
    """Deterministic SHA-256 of the graph — identical graphs produce identical hashes."""
    nodes_data = sorted(
        [{"id": n.id, "kind": n.kind, "label": n.label} for n in graph.nodes],
        key=lambda x: x["id"],
    )
    edges_data = sorted(
        [{"src": e.src, "dst": e.dst, "kind": e.kind} for e in graph.edges],
        key=lambda x: (x["src"], x["dst"], x["kind"]),
    )
    payload = json.dumps({"nodes": nodes_data, "edges": edges_data}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
