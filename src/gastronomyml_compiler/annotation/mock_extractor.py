"""Tier 0 mock extractor — deterministic fixture for testing."""

from __future__ import annotations

from ..ir.schemas import (
    CookingTechnique,
    FlavorTransformation,
    FlavorVector,
    FoodGroup,
    Ingredient,
    TechniqueType,
)
from .base import BaseExtractor, ExtractorResult


class MockExtractor(BaseExtractor):
    def extract(self, text: str) -> ExtractorResult:
        butter = Ingredient(
            id="ing_0",
            name="butter",
            canonical_name="butter",
            food_group=FoodGroup.FAT,
            flavor_vector=FlavorVector.from_dict(
                {"fat": 0.9, "sweet": 0.2, "salty": 0.15, "aromatic": 0.35}
            ),
        )
        lemon = Ingredient(
            id="ing_1",
            name="lemon",
            canonical_name="lemon",
            food_group=FoodGroup.FRUIT,
            flavor_vector=FlavorVector.from_dict(
                {"sour": 0.9, "aromatic": 0.65, "bitter": 0.15}
            ),
        )
        thyme = Ingredient(
            id="ing_2",
            name="thyme",
            canonical_name="thyme",
            food_group=FoodGroup.HERB,
            flavor_vector=FlavorVector.from_dict({"aromatic": 0.8, "bitter": 0.15}),
        )
        tech = CookingTechnique(
            id="tech_0",
            name="sauté",
            technique_type=TechniqueType.SAUTEING,
            applies_to=["ing_0"],
            transformation=FlavorTransformation(
                dimension_deltas={"aromatic": 0.2, "fat": 0.1}
            ),
        )
        return ExtractorResult(
            ingredients=[butter, lemon, thyme],
            techniques=[tech],
            cuisine_hint="french",
            extractor_metadata={"tier": "mock"},
        )
