"""End-to-end tests for the spaCy 'nlp' extractor tier.

Skips cleanly if the [nlp] extra (spaCy + en_core_web_sm) isn't installed.
"""
import pytest

from gastronomyml_compiler.pipeline.orchestrator import compile_document
from gastronomyml_compiler.tiers import CompilerTier


def _require_spacy():
    try:
        from gastronomyml_compiler.annotation.nlp_extractor import NlpExtractor
        NlpExtractor._load()
    except Exception:
        pytest.skip("spaCy / en_core_web_sm not installed ([nlp] extra)")


def test_nlp_tier_drops_negated_ingredient():
    _require_spacy()
    ir = compile_document("No butter, just olive oil.", extractor=CompilerTier.NLP)
    names = {i.name for i in ir.ingredients}
    assert "butter" not in names
    assert "olive oil" in names


def test_nlp_tier_handles_plurals():
    _require_spacy()
    ir = compile_document("Roasted tomatoes and mushrooms.", extractor=CompilerTier.NLP)
    names = {i.name for i in ir.ingredients}
    assert {"tomato", "mushroom"} <= names


def test_rule_tier_is_default_and_misses_negation():
    # The default tier stays rule, and documents its negation limitation.
    ir = compile_document("No butter, just olive oil.", extractor=CompilerTier.RULE)
    assert "butter" in {i.name for i in ir.ingredients}
