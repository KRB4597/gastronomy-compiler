"""Export GastronomyIR as Schema.org/Recipe JSON-LD."""

import json
from pathlib import Path

from ..ir.schemas import GastronomyIR


def export_schema_org(ir: GastronomyIR, path: str | Path | None = None) -> str:
    recipe: dict = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": ir.document.title,
        "recipeIngredient": [
            f"{i.quantity or ''} {i.unit or ''} {i.name}".strip()
            for i in ir.ingredients
        ],
        "recipeInstructions": [
            {"@type": "HowToStep", "text": step.instruction}
            for recipe in ir.recipes
            for step in recipe.steps
        ],
        "recipeCuisine": ir.document.cuisine or "Unknown",
        "keywords": ", ".join(ir.aggregate_flavor_vector.dominant_dimensions()),
        "description": (
            ir.harmony_verdict.explanation if ir.harmony_verdict else ""
        ),
    }
    text = json.dumps(recipe, indent=2)
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return text
