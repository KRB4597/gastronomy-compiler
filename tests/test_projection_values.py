"""Value-pinned projection tests.

test_projections.py only checks results are in range; these pin the actual
numbers and assert the intended direction of each projection.  Combine:
* ordering/direction — robust, encodes intent;
* approximate value  — characterization, catches silent drift (update the
  pinned number deliberately if you change a formula).
"""
import pytest

from gastronomyml_compiler.ir.graph.promote import graph_from_ir
from gastronomyml_compiler.ir.schemas import (
    Document, FlavorVector, FoodGroup, GastronomyIR, Ingredient,
)
from gastronomyml_compiler.pipeline.orchestrator import compile_document
from gastronomyml_compiler.projections import (
    FlavorContrastProjection, FlavorSimilarityProjection, NutritionalBalanceProjection,
)
from gastronomyml_compiler.tiers import CompilerTier

TOL = 0.03


def _ir(ingredients) -> GastronomyIR:
    ir = GastronomyIR(document=Document(title="t", sha256="x"), ingredients=ingredients)
    ir.flavor_graph = graph_from_ir(ir)
    return ir


def _ing(name, scores, group=FoodGroup.UNKNOWN):
    return Ingredient(id=name, name=name, food_group=group,
                      flavor_vector=FlavorVector.from_dict(scores))


# ------------------------------------------------------- flavor_similarity (cosine)
def test_flavor_similarity_high_for_aligned_profiles():
    ir = _ir([_ing("miso", {"umami": 0.9, "salty": 0.5}),
              _ing("parmesan", {"umami": 0.9, "salty": 0.6})])
    r = FlavorSimilarityProjection().project(ir)
    assert r.score == pytest.approx(0.997, abs=TOL)


def test_flavor_similarity_zero_for_orthogonal_profiles():
    ir = _ir([_ing("sugar", {"sweet": 0.9}), _ing("lemon", {"sour": 0.9})])
    r = FlavorSimilarityProjection().project(ir)
    assert r.score == pytest.approx(0.0, abs=TOL)


def test_flavor_similarity_aligned_beats_orthogonal():
    aligned = FlavorSimilarityProjection().project(
        _ir([_ing("miso", {"umami": 0.9}), _ing("parmesan", {"umami": 0.9})])).score
    orthog = FlavorSimilarityProjection().project(
        _ir([_ing("sugar", {"sweet": 0.9}), _ing("lemon", {"sour": 0.9})])).score
    assert aligned > orthog


# ------------------------------------------------------------ nutritional_balance
def test_nutritional_balance_protein_and_veg():
    ir = _ir([_ing("chicken", {"umami": 0.5}, FoodGroup.PROTEIN),
              _ing("spinach", {"bitter": 0.3}, FoodGroup.VEGETABLE)])
    r = NutritionalBalanceProjection().project(ir)
    assert r.score == pytest.approx(0.75, abs=TOL)
    assert r.verdict == "nutritionally_balanced"


def test_nutritional_balance_empty_dish_characterized():
    # Documents a known quirk: an empty dish currently scores 0.3 / reasonable.
    # If this is ever "fixed" to a neutral/penalised verdict, update this test.
    r = NutritionalBalanceProjection().project(_ir([]))
    assert r.score == pytest.approx(0.3, abs=TOL)


# ---------------------------------------------------- range invariants (all four)
def test_all_projection_scores_within_range():
    ir = _ir([_ing("butter", {"fat": 0.9}), _ing("lemon", {"sour": 0.8})])
    for proj in (FlavorSimilarityProjection(), FlavorContrastProjection(),
                 NutritionalBalanceProjection()):
        assert -1.0 <= proj.project(ir).score <= 1.0


# --------------------------------------------------- full-pipeline characterization
def test_pipeline_salmon_dish_pinned():
    ir = compile_document("Garlic butter salmon with lemon.", extractor=CompilerTier.RULE)
    scores = {k: v.score for k, v in ir.projections.items()}
    assert scores["flavor_similarity"] == pytest.approx(0.393, abs=0.05)
    assert scores["cultural_harmony"] == pytest.approx(0.9, abs=0.05)
    assert scores["nutritional_balance"] == pytest.approx(0.85, abs=0.05)
    assert ir.harmony_verdict.verdict.value == "harmonious"
