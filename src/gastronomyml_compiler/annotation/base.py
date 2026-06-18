from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..ir.schemas import (
    CookingTechnique,
    FlavorFact,
    Ingredient,
    PairingRule,
    Recipe,
)


@dataclass
class ExtractorResult:
    """Structured output of Passes 2–6."""

    ingredients: list[Ingredient] = field(default_factory=list)
    techniques: list[CookingTechnique] = field(default_factory=list)
    recipes: list[Recipe] = field(default_factory=list)
    pairing_rules: list[PairingRule] = field(default_factory=list)
    flavor_facts: list[FlavorFact] = field(default_factory=list)
    cuisine_hint: str | None = None
    meal_type_hint: str | None = None
    dietary_flags: list[str] = field(default_factory=list)
    extractor_metadata: dict = field(default_factory=dict)


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> ExtractorResult:
        ...
