"""Tests for the extractor bake-off instrument.

Lock in the findings that motivate the spaCy 'nlp' tier: the rule extractor
mishandles negation and plurals; the spaCy contender fixes both.
(spaCy-dependent assertions skip cleanly if spaCy is absent.)
"""
import pytest

from benchmarks.contenders import RuleContender, SpacyContender


def test_rule_extracts_negated_ingredient_documented():
    # Documents the bug: \bword\b regex can't tell "no butter" from "butter".
    assert "butter" in RuleContender().score("No butter, just olive oil.")


def test_rule_misses_plurals_documented():
    # \btomato\b does not match "tomatoes".
    assert "tomato" not in RuleContender().score("Roasted tomatoes.")


def _spacy():
    c = SpacyContender()
    if not c.available():
        pytest.skip("spaCy / en_core_web_sm not installed")
    return c


def test_spacy_handles_negation():
    s = _spacy().score("No butter, just olive oil.")
    assert "butter" not in s
    assert "olive oil" in s


def test_spacy_scopes_without_preposition():
    # "pasta without parmesan" negates parmesan, not pasta.
    s = _spacy().score("Pasta without parmesan.")
    assert "pasta" in s
    assert "parmesan" not in s


def test_spacy_handles_plurals():
    s = _spacy().score("Roasted tomatoes with mushrooms.")
    assert {"tomato", "mushroom"} <= s


def test_spacy_beats_rule_overall():
    from benchmarks.extractor_eval import GOLD, _judge
    rule, spacy = RuleContender(), _spacy()
    r_ok = r_tot = s_ok = s_tot = 0
    for text, _cat, present, absent in GOLD:
        c, t = _judge(rule.score(text), present, absent)
        r_ok += c; r_tot += t
        c, t = _judge(spacy.score(text), present, absent)
        s_ok += c; s_tot += t
    assert (s_ok / s_tot) > (r_ok / r_tot)
