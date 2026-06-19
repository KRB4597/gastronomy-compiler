"""Ingredient-extraction contenders for the bake-off.

Each contender maps a dish description to the SET of canonical ingredient names
it detects.  They share the same INGREDIENT_LIBRARY so the comparison isolates
the matching strategy:

  * RuleContender      — current extractor: \\bword\\b regex (no negation; misses
                         plurals like "tomatoes").
  * SpacyContender     — the shipped NlpExtractor: lemma matching (plurals) +
                         negation filtering ("no butter" -> no butter).
  * EmbeddingContender — sentence-transformers: maps out-of-vocabulary words to
                         their nearest library ingredient by similarity (catches
                         synonyms like "prawns" -> shrimp).  Optional.

A contender is `available()` only if its dependencies import.
"""
from __future__ import annotations

import re

from gastronomyml_compiler.annotation.rule_extractor import INGREDIENT_LIBRARY, RuleExtractor


class Contender:
    name = "base"

    def available(self) -> bool:
        return True

    def score(self, text: str) -> set[str]:
        raise NotImplementedError


class RuleContender(Contender):
    name = "rule"

    def __init__(self) -> None:
        self._ext = RuleExtractor()

    def score(self, text: str) -> set[str]:
        return {i.name for i in self._ext._extract_ingredients(text, text.lower())}


class SpacyContender(Contender):
    name = "spacy"

    def __init__(self) -> None:
        from gastronomyml_compiler.annotation.nlp_extractor import NlpExtractor
        self._ext = NlpExtractor()

    def available(self) -> bool:
        try:
            self._ext._load()
            return True
        except Exception:
            return False

    def score(self, text: str) -> set[str]:
        return {i.name for i in self._ext._extract_ingredients(text, text.lower())}


class EmbeddingContender(Contender):
    name = "embedding"
    _model = None
    _keys = None
    _key_emb = None

    def available(self) -> bool:
        try:
            import sentence_transformers  # noqa: F401
            self._load()
            return True
        except Exception:
            return False

    @classmethod
    def _load(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
            cls._keys = list(INGREDIENT_LIBRARY)
            cls._key_emb = cls._model.encode(cls._keys, normalize_embeddings=True)
        return cls._model

    def score(self, text: str, threshold: float = 0.62) -> set[str]:
        import numpy as np
        model = self._load()
        words = set(re.findall(r"[a-z]+", text.lower()))
        # 2-grams too, for "olive oil" style keys
        toks = re.findall(r"[a-z]+", text.lower())
        words |= {f"{a} {b}" for a, b in zip(toks, toks[1:])}
        if not words:
            return set()
        cand = list(words)
        emb = np.asarray(model.encode(cand, normalize_embeddings=True))
        sims = emb @ np.asarray(self._key_emb).T  # (n_cand, n_keys)
        out: set[str] = set()
        for row in sims:
            j = int(row.argmax())
            if row[j] >= threshold:
                out.add(self._keys[j])
        return out


def all_contenders() -> list[Contender]:
    return [RuleContender(), SpacyContender(), EmbeddingContender()]
