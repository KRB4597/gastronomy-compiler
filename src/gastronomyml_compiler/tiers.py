from enum import Enum


class CompilerTier(str, Enum):
    STRUCTURED = "structured"   # Tier 1 — pre-parsed JSON input
    RULE = "rule"               # Tier 2 — deterministic pattern library (default)
    MOCK = "mock"               # Deterministic test fixture


ALL_PROJECTIONS = [
    "flavor_similarity",
    "flavor_contrast",
    "cultural_harmony",
    "nutritional_balance",
]
