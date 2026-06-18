"""Pass 12 — build audit record with pass provenance.

Analogous to ErisML audit/hash_chain.py.
"""

from __future__ import annotations

from ..ir.schemas import AuditRecord, PassRecord


def build_audit(
    pass_records: list[PassRecord],
    extractor_tier: str,
    active_projections: list[str],
    graph_hash: str | None,
    input_sha256: str | None,
) -> AuditRecord:
    return AuditRecord(
        passes=pass_records,
        extractor_tier=extractor_tier,
        active_projections=active_projections,
        graph_hash=graph_hash,
        input_sha256=input_sha256,
        provenance={
            "schema": "gastronomyml_ir_v0.1",
            "passes_completed": len([p for p in pass_records if p.status == "ok"]),
        },
    )
