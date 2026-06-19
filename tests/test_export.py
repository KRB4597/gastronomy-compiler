"""Tests for the JSON and Schema.org/Recipe exporters (were 0% covered)."""
import json

from gastronomyml_compiler.export import export_json, export_schema_org
from gastronomyml_compiler.ir.schemas import GastronomyIR
from gastronomyml_compiler.pipeline.orchestrator import compile_document
from gastronomyml_compiler.tiers import CompilerTier


def _ir():
    return compile_document(
        "Miso pork ramen with mushroom, nori, scallion and soy sauce.",
        extractor=CompilerTier.RULE,
    )


def test_export_json_roundtrips_into_model():
    ir = _ir()
    data = json.loads(export_json(ir))
    assert data["document"]["title"]
    # The exported JSON must validate back into the model unchanged in shape.
    ir2 = GastronomyIR.model_validate(data)
    assert len(ir2.ingredients) == len(ir.ingredients)
    assert ir2.schema_version == ir.schema_version


def test_export_json_excludes_none():
    # exporter uses exclude_none=True — no null values should appear.
    text = export_json(_ir())
    assert ": null" not in text


def test_export_json_writes_file(tmp_path):
    p = tmp_path / "dish.json"
    s = export_json(_ir(), p)
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8")) == json.loads(s)


def test_schema_org_recipe_structure():
    ir = _ir()
    o = json.loads(export_schema_org(ir))
    assert o["@context"] == "https://schema.org"
    assert o["@type"] == "Recipe"
    assert len(o["recipeIngredient"]) == len(ir.ingredients)
    assert o["recipeCuisine"]  # ramen => japanese detected


def test_schema_org_writes_file(tmp_path):
    p = tmp_path / "recipe.jsonld"
    s = export_schema_org(_ir(), p)
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8")) == json.loads(s)
