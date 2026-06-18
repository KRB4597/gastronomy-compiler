"""Tests for GastronomyIR schemas."""

import pytest
from gastronomyml_compiler.ir.schemas import (
    FLAVOR_DIMENSIONS,
    DimensionScore,
    FlavorVector,
    GastronomyIR,
    Document,
    Ingredient,
    FoodGroup,
)


def test_flavor_dimensions_count():
    assert len(FLAVOR_DIMENSIONS) == 9


def test_flavor_vector_to_array():
    fv = FlavorVector.from_dict({"sweet": 0.5, "umami": 0.8})
    arr = fv.to_array()
    assert len(arr) == 9
    assert arr[0] == pytest.approx(0.5)   # sweet
    assert arr[4] == pytest.approx(0.8)   # umami


def test_flavor_vector_dominant():
    fv = FlavorVector.from_dict({"fat": 0.9, "umami": 0.7, "sweet": 0.1})
    doms = fv.dominant_dimensions(threshold=0.5)
    assert "fat" in doms
    assert "umami" in doms
    assert "sweet" not in doms


def test_dimension_score_clamp():
    with pytest.raises(Exception):
        DimensionScore(value=2.0)  # out of range


def test_gastronomyir_schema_version():
    doc = Document(title="Test", sha256="abc")
    ir = GastronomyIR(document=doc)
    assert ir.schema_version == "gastronomyml_ir_v0.1"


def test_ingredient_defaults():
    ing = Ingredient(id="i0", name="butter")
    assert ing.food_group == FoodGroup.UNKNOWN
    assert ing.flavor_vector is not None
