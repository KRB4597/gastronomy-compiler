"""Tests for the four culinary projections."""

import pytest
from gastronomyml_compiler.annotation.mock_extractor import MockExtractor
from gastronomyml_compiler.fm_dag.dag import FMDAG
from gastronomyml_compiler.ir.graph.promote import graph_from_ir
from gastronomyml_compiler.ir.schemas import Document, GastronomyIR
from gastronomyml_compiler.projections import (
    FlavorSimilarityProjection,
    FlavorContrastProjection,
    CulturalHarmonyProjection,
    NutritionalBalanceProjection,
)


def _make_ir(text: str = "") -> GastronomyIR:
    result = MockExtractor().extract(text or "butter lemon thyme sauté french")
    doc = Document(title="Test", sha256="000", cuisine="french")
    ir = GastronomyIR(
        document=doc,
        ingredients=result.ingredients,
        techniques=result.techniques,
        flavor_facts=result.flavor_facts,
    )
    ir.flavor_graph = graph_from_ir(ir)
    ir.aggregate_flavor_vector = FMDAG().evaluate(ir)
    return ir


def test_flavor_similarity_returns_result():
    ir = _make_ir()
    result = FlavorSimilarityProjection().project(ir)
    assert result.projection_id == "flavor_similarity"
    assert result.polarity in ("harmonious", "neutral", "discordant")
    assert -1.0 <= result.score <= 1.0


def test_flavor_contrast_returns_result():
    ir = _make_ir()
    result = FlavorContrastProjection().project(ir)
    assert result.projection_id == "flavor_contrast"
    assert -1.0 <= result.score <= 1.0


def test_cultural_harmony_french():
    ir = _make_ir()
    result = CulturalHarmonyProjection().project(ir)
    assert result.projection_id == "cultural_harmony"


def test_nutritional_balance_returns_result():
    ir = _make_ir()
    result = NutritionalBalanceProjection().project(ir)
    assert result.projection_id == "nutritional_balance"
    assert result.verdict is not None


def test_all_projections_have_findings():
    ir = _make_ir()
    for cls in [FlavorSimilarityProjection, FlavorContrastProjection,
                CulturalHarmonyProjection, NutritionalBalanceProjection]:
        result = cls().project(ir)
        assert isinstance(result.findings, list)
