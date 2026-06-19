"""Dataset loading for the gastronomy benchmarks.

Two loaders, two ground-truth sources:

1. ``load_recipes(csv_path)`` — graded recipes.  Columns:

       text,rating

   ``text`` is a natural-language dish description (the same thing you'd pass to
   ``gastronomy-compile compile``).  ``rating`` is a human score on any scale
   (e.g. 1-5 stars).  Public sources: the Epicurious and food.com recipe
   datasets on Kaggle, or Recipe1M+ joined with a ratings table.

2. ``load_flavor_pairs(csv_path)`` — ingredient pairs with a shared-compound
   count.  Columns:

       ingredient_a,ingredient_b,shared_compounds

   ``shared_compounds`` is the number of flavor molecules the two ingredients
   have in common (the quantity behind Ahn et al. 2011's flavor network).
   Source: FlavorDB / FlavorGraph ingredient–compound tables.

Both ship with a small bundled sample CSV (plain text, committed to the repo)
so the harness runs immediately.  The samples are illustrative; swap in real
data for meaningful numbers.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

_SAMPLE_DIR = Path(__file__).parent / "sample_data"
SAMPLE_RECIPES = _SAMPLE_DIR / "recipes_sample.csv"
SAMPLE_FLAVOR_PAIRS = _SAMPLE_DIR / "flavor_pairs_sample.csv"


@dataclass
class Recipe:
    text: str
    rating: float


@dataclass
class FlavorPair:
    a: str
    b: str
    shared_compounds: float


def load_recipes(csv_path: str | Path) -> list[Recipe]:
    out: list[Recipe] = []
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rating = _to_float(row.get("rating"))
            text = (row.get("text") or "").strip()
            if text and rating is not None:
                out.append(Recipe(text=text, rating=rating))
    return out


def load_flavor_pairs(csv_path: str | Path) -> list[FlavorPair]:
    out: list[FlavorPair] = []
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            shared = _to_float(row.get("shared_compounds"))
            a = (row.get("ingredient_a") or "").strip()
            b = (row.get("ingredient_b") or "").strip()
            if a and b and shared is not None:
                out.append(FlavorPair(a=a, b=b, shared_compounds=shared))
    return out


def _to_float(v) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None
