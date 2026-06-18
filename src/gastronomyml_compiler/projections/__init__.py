from .flavor_similarity import FlavorSimilarityProjection
from .flavor_contrast import FlavorContrastProjection
from .cultural_harmony import CulturalHarmonyProjection
from .nutritional_balance import NutritionalBalanceProjection
from .base import BaseProjection

PROJECTION_REGISTRY: dict[str, type] = {
    "flavor_similarity": FlavorSimilarityProjection,
    "flavor_contrast": FlavorContrastProjection,
    "cultural_harmony": CulturalHarmonyProjection,
    "nutritional_balance": NutritionalBalanceProjection,
}

__all__ = [
    "FlavorSimilarityProjection",
    "FlavorContrastProjection",
    "CulturalHarmonyProjection",
    "NutritionalBalanceProjection",
    "BaseProjection",
    "PROJECTION_REGISTRY",
]
