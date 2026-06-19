"""Rule-extractor recall tests.

These iterate the actual ingredient/technique libraries, so they are
self-maintaining: add a library entry the matcher can't detect from a plain
sentence and the test fails — flagging vocabulary that won't actually work.
"""
from gastronomyml_compiler.annotation.rule_extractor import (
    INGREDIENT_LIBRARY,
    RuleExtractor,
    TECHNIQUE_LIBRARY,
)


def test_ingredient_recall_is_complete():
    ext = RuleExtractor()
    missed = [
        name for name in INGREDIENT_LIBRARY
        if name not in {i.name for i in ext.extract(f"A dish with {name} and salt.").ingredients}
    ]
    assert not missed, f"unrecognised ingredients: {missed}"


def test_technique_recall_is_complete():
    ext = RuleExtractor()
    missed = [
        t for t in TECHNIQUE_LIBRARY
        if not any(t in tech.name for tech in ext.extract(f"The ingredients are {t}.").techniques)
    ]
    assert not missed, f"unrecognised techniques: {missed}"


def test_multi_ingredient_dish_extracted_together():
    r = RuleExtractor().extract(
        "Tomato basil parmesan pasta with garlic, olive oil, mushroom, and butter."
    )
    names = {i.name for i in r.ingredients}
    expected = {"tomato", "basil", "parmesan", "pasta",
                "garlic", "olive oil", "mushroom", "butter"}
    assert expected <= names, f"missing: {expected - names}"


def test_canonicalization_maps_aliases():
    # parmigiano should canonicalise toward parmesan (alias registry).
    from gastronomyml_compiler.canonicalizer.registry import IngredientRegistry
    reg = IngredientRegistry()
    assert reg.canonicalize("parmigiano") in ("parmesan", "parmigiano")
