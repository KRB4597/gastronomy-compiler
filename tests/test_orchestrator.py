"""Tests for the 13-pass pipeline orchestrator."""

import pytest
from gastronomyml_compiler.pipeline.orchestrator import compile_document
from gastronomyml_compiler.tiers import CompilerTier, ALL_PROJECTIONS


DUCK_TEXT = """
Duck confit with cherry gastrique.

Duck legs are cured in salt and thyme, then slow-cooked in rendered duck fat.
Cherry gastrique: caramelized sugar deglazed with red wine vinegar and cherries.
Served with wilted spinach sautéed in butter.
"""


def test_compile_default_projections():
    ir = compile_document(DUCK_TEXT, extractor=CompilerTier.MOCK)
    assert ir.schema_version == "gastronomyml_ir_v0.1"
    assert ir.harmony_verdict is not None
    assert ir.audit is not None


def test_compile_single_projection():
    ir = compile_document(
        DUCK_TEXT, extractor=CompilerTier.MOCK, projections=["flavor_similarity"]
    )
    assert "flavor_similarity" in ir.projections
    assert "flavor_contrast" not in ir.projections


def test_compile_subset_projections():
    ir = compile_document(
        DUCK_TEXT,
        extractor=CompilerTier.MOCK,
        projections=["flavor_similarity", "nutritional_balance"],
    )
    assert set(ir.projections.keys()) == {"flavor_similarity", "nutritional_balance"}


def test_compile_all_projections():
    ir = compile_document(DUCK_TEXT, extractor=CompilerTier.MOCK)
    assert set(ir.projections.keys()) == set(ALL_PROJECTIONS)


def test_invalid_projection_raises():
    with pytest.raises(ValueError, match="Unknown projection"):
        compile_document(DUCK_TEXT, projections=["not_a_real_projection"])


def test_graph_hash_present():
    ir = compile_document(DUCK_TEXT, extractor=CompilerTier.MOCK)
    assert ir.flavor_graph is not None
    assert ir.flavor_graph.graph_hash is not None


def test_rule_extractor_on_duck():
    ir = compile_document(DUCK_TEXT, extractor=CompilerTier.RULE)
    assert len(ir.ingredients) >= 3
    assert ir.document.cuisine in ("french", None)


def test_rule_extractor_on_ramen():
    ramen = (
        "Tonkotsu miso ramen with chashu pork, soft-boiled egg marinated in soy sauce "
        "and mirin. Broth simmered with ginger, garlic, and scallion. "
        "Garnished with nori, sesame seeds, and chili oil."
    )
    ir = compile_document(ramen, extractor=CompilerTier.RULE)
    assert len(ir.ingredients) >= 4
    ing_names = {i.name for i in ir.ingredients}
    assert "miso" in ing_names or "soy sauce" in ing_names


def test_audit_records_all_passes():
    ir = compile_document(DUCK_TEXT, extractor=CompilerTier.MOCK)
    assert ir.audit is not None
    statuses = {p.status for p in ir.audit.passes}
    assert "failed" not in statuses


def test_cross_projection_disagreement_type():
    ir = compile_document(DUCK_TEXT, extractor=CompilerTier.MOCK)
    # May or may not be set; just check type
    assert ir.cross_projection_disagreement is None or isinstance(
        ir.cross_projection_disagreement, dict
    )
