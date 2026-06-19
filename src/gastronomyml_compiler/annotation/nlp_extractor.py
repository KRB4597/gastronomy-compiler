"""spaCy-backed text extractor (Tier: nlp).

Drop-in replacement for the rule extractor's *ingredient* detection that fixes
the failure modes the bake-off measures (benchmarks/extractor_eval.py):

  * negation  — "no butter", "without parmesan" no longer extract that
    ingredient (the rule extractor's \\bword\\b regex can't tell);
  * inflection — plurals match via lemma, so "tomatoes"/"eggs"/"mushrooms"
    register tomato/egg/mushroom (the regex misses them).

Everything else (techniques, flavor facts, pairing rules, cuisine/meal/dietary
detection) is inherited unchanged from RuleExtractor — only ingredient
extraction is replaced.

Requires the ``nlp`` extra: ``pip install -e ".[nlp]"`` plus the model,
``python -m spacy download en_core_web_sm``.
"""
from __future__ import annotations

from ..ir.schemas import FlavorVector, FoodGroup, Ingredient
from .rule_extractor import INGREDIENT_LIBRARY, RuleExtractor

# Negation cues, scoped by *how* they attach so we don't negate the wrong noun
# (e.g. "pasta without parmesan" negates parmesan, not pasta):
_NEG_DET = {"no"}                          # determiner: "no garlic"
_NEG_PREP = {"without", "sans", "minus"}   # prep object: "without parmesan"
_NEG_ADV = {"not", "never", "n't"}         # adverbial: windowed before the noun
_MAX_SPAN = 3  # longest multi-word ingredient key (e.g. "pork belly")


class NlpExtractor(RuleExtractor):
    """Rule extractor with spaCy-based, negation-aware ingredient detection."""

    _nlp = None

    @classmethod
    def _load(cls):
        if cls._nlp is None:
            import spacy  # raises ImportError if the extra isn't installed
            cls._nlp = spacy.load("en_core_web_sm")
        return cls._nlp

    @staticmethod
    def _negated(tok) -> bool:
        # direct: "not X", or determiner "no X"
        for c in tok.children:
            if c.dep_ == "neg":
                return True
            if c.lower_ in _NEG_DET and c.dep_ == "det":
                return True
        # object of a negating preposition: "X without <tok>"
        if tok.dep_ == "pobj" and tok.head.lower_ in _NEG_PREP:
            return True
        # negated copula governing an attribute: "is not <tok>"
        if any(c.dep_ == "neg" for c in tok.head.children):
            return True
        # adverbial cue in a tight preceding window: "never with <tok>"
        window = tok.doc[max(0, tok.i - 3):tok.i]
        return any(w.lower_ in _NEG_ADV for w in window)

    def _extract_ingredients(self, text: str, lower: str) -> list[Ingredient]:
        doc = self._load()(lower)
        toks = list(doc)
        n = len(toks)
        found: list[Ingredient] = []
        seen: set[str] = set()

        i = 0
        while i < n:
            matched = False
            for span_len in range(_MAX_SPAN, 0, -1):  # prefer longest match
                if i + span_len > n:
                    continue
                span = toks[i:i + span_len]
                forms = (
                    " ".join(t.lemma_ for t in span),   # lemma → plurals match
                    " ".join(t.lower_ for t in span),   # surface fallback
                )
                key = next((f for f in forms if f in INGREDIENT_LIBRARY), None)
                if key is None:
                    continue
                if key not in seen:
                    seen.add(key)
                    if not any(self._negated(t) for t in span):
                        found.append(self._make_ingredient(key, len(found)))
                i += span_len
                matched = True
                break
            if not matched:
                i += 1

        return found

    @staticmethod
    def _make_ingredient(name: str, index: int) -> Ingredient:
        profile = INGREDIENT_LIBRARY[name]
        flavor_scores = {k: v for k, v in profile.items() if k != "group"}
        return Ingredient(
            id=f"ing_{index}",
            name=name,
            canonical_name=name,
            food_group=profile.get("group", FoodGroup.UNKNOWN),
            flavor_vector=FlavorVector.from_dict(flavor_scores),
        )
