"""Pass 7 — canonicalize ingredient names.

Lightweight Jaccard-based registry analogous to ErisML canonicalizer/registry.py.
Maps surface forms to canonical names (e.g. 'parmigiano-reggiano' → 'parmesan').
"""

from __future__ import annotations

_ALIASES: dict[str, str] = {
    "parmigiano-reggiano": "parmesan",
    "parmigiano reggiano": "parmesan",
    "ev olive oil": "olive oil",
    "extra-virgin olive oil": "olive oil",
    "extra virgin olive oil": "olive oil",
    "evoo": "olive oil",
    "heavy cream": "cream",
    "double cream": "cream",
    "fresh cream": "cream",
    "soy": "soy sauce",
    "shoyu": "soy sauce",
    "noodles": "noodle",
    "ramen noodles": "ramen",
    "bing cherry": "cherry",
    "dried cherry": "cherry",
    "chilli": "chili",
    "chile": "chili",
    "scallions": "scallion",
    "spring onion": "scallion",
    "green onion": "scallion",
    "black pepper": "black pepper",
    "freshly ground pepper": "black pepper",
    "chashu pork": "chashu",
    "pork belly": "pork belly",
}


class IngredientRegistry:
    def canonicalize(self, name: str) -> str:
        lower = name.lower().strip()
        if lower in _ALIASES:
            return _ALIASES[lower]
        # Try substring match
        for alias, canonical in _ALIASES.items():
            if alias in lower:
                return canonical
        return lower
