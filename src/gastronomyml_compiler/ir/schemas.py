"""Core GastronomyML intermediate representation (IR) schemas.

Analogous to erisml-compiler ir/schemas.py.  The 9 flavor dimensions mirror
the 9 moral dimensions in ErisML; each culinary projection (FlavorSimilarity,
FlavorContrast, CulturalHarmony, NutritionalBalance) mirrors an ethical
framework projection.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Flavor dimensions
# ---------------------------------------------------------------------------

FLAVOR_DIMENSIONS: tuple[str, ...] = (
    "sweet",     # k=0  sweetness intensity
    "salty",     # k=1  saltiness / mineral
    "sour",      # k=2  acidity / brightness
    "bitter",    # k=3  bitterness / tannins
    "umami",     # k=4  savory depth
    "fat",       # k=5  richness / fat
    "heat",      # k=6  spice / pungency
    "aromatic",  # k=7  volatile aromatic complexity
    "texture",   # k=8  mouthfeel / body
)

DIMENSION_INDEX: dict[str, int] = {d: i for i, d in enumerate(FLAVOR_DIMENSIONS)}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FoodGroup(str, Enum):
    PROTEIN = "protein"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    FAT = "fat"
    CARBOHYDRATE = "carbohydrate"
    DAIRY = "dairy"
    SPICE = "spice"
    HERB = "herb"
    CONDIMENT = "condiment"
    LIQUID = "liquid"
    SWEETENER = "sweetener"
    FUNGUS = "fungus"
    SEAFOOD = "seafood"
    UNKNOWN = "unknown"


class TechniqueType(str, Enum):
    MAILLARD = "maillard"               # high heat + protein → browning + aromatics
    CARAMELIZATION = "caramelization"   # sugar + heat → amber sweetness
    FERMENTATION = "fermentation"       # time + microbes → umami / sour
    EMULSIFICATION = "emulsification"   # fat + liquid → stable suspension
    REDUCTION = "reduction"             # heat + liquid → concentrated flavor
    ROASTING = "roasting"               # dry high heat
    GRILLING = "grilling"               # direct high heat
    SAUTEING = "sauteing"               # medium-high heat, fat
    BRAISING = "braising"               # slow moist heat
    POACHING = "poaching"               # gentle moist heat
    STEAMING = "steaming"               # moist heat, no browning
    FRYING = "frying"                   # oil immersion, high heat
    BLANCHING = "blanching"             # brief boiling + shock
    MARINATING = "marinating"           # soaking in acid / flavor
    CURING = "curing"                   # salt / sugar preservation
    SMOKING = "smoking"                 # smoke aromatic infusion
    CONFITING = "confiting"             # slow cook submerged in fat
    RAW = "raw"
    UNKNOWN = "unknown"


class FlavorFactKind(str, Enum):
    HARMONY = "harmony"
    CLASH = "clash"
    BALANCE = "balance"
    IMBALANCE = "imbalance"
    COMPOUND_BRIDGE = "compound_bridge"
    CONTRAST = "contrast"
    DOMINANCE = "dominance"
    UMAMI_SYNERGY = "umami_synergy"     # glutamate + inosinate synergy
    ACID_FAT_BALANCE = "acid_fat_balance"
    BITTERNESS_MITIGATION = "bitterness_mitigation"


class PairingRuleType(str, Enum):
    PERMISSION = "permission"
    RECOMMENDATION = "recommendation"
    PROHIBITION = "prohibition"
    CULTURAL_NORM = "cultural_norm"


class SegmentType(str, Enum):
    INGREDIENT_LIST = "ingredient_list"
    TECHNIQUE = "technique"
    CONTEXT = "context"
    DESCRIPTION = "description"
    INSTRUCTION = "instruction"
    GARNISH = "garnish"
    NOTE = "note"


class HarmonyVerdictLabel(str, Enum):
    HARMONIOUS = "harmonious"
    COMPLEMENTARY = "complementary"
    NEUTRAL = "neutral"
    DISCORDANT = "discordant"
    CLASHING = "clashing"
    PROJECTION_CONFLICT = "projection_conflict"  # projections disagree on polarity


# ---------------------------------------------------------------------------
# Dimension score
# ---------------------------------------------------------------------------

class DimensionScore(BaseModel):
    """Score on a single flavor dimension; analogous to ErisML DimensionScore."""

    value: float = Field(ge=-1.0, le=1.0, default=0.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    direction: Literal["dominant", "present", "trace", "absent"] = "absent"
    explanation: str | None = None


class FlavorVector(BaseModel):
    """9-dimensional flavor state — aggregate dish or per-ingredient."""

    sweet: DimensionScore = Field(default_factory=DimensionScore)
    salty: DimensionScore = Field(default_factory=DimensionScore)
    sour: DimensionScore = Field(default_factory=DimensionScore)
    bitter: DimensionScore = Field(default_factory=DimensionScore)
    umami: DimensionScore = Field(default_factory=DimensionScore)
    fat: DimensionScore = Field(default_factory=DimensionScore)
    heat: DimensionScore = Field(default_factory=DimensionScore)
    aromatic: DimensionScore = Field(default_factory=DimensionScore)
    texture: DimensionScore = Field(default_factory=DimensionScore)

    def to_array(self) -> list[float]:
        return [getattr(self, dim).value for dim in FLAVOR_DIMENSIONS]

    def dominant_dimensions(self, threshold: float = 0.5) -> list[str]:
        return [d for d in FLAVOR_DIMENSIONS if abs(getattr(self, d).value) >= threshold]

    @classmethod
    def from_dict(cls, scores: dict[str, float]) -> "FlavorVector":
        kwargs: dict[str, DimensionScore] = {}
        for dim in FLAVOR_DIMENSIONS:
            v = scores.get(dim, 0.0)
            kwargs[dim] = DimensionScore(
                value=max(-1.0, min(1.0, v)),
                direction=_direction(v),
            )
        return cls(**kwargs)


def _direction(v: float) -> Literal["dominant", "present", "trace", "absent"]:
    a = abs(v)
    if a >= 0.65:
        return "dominant"
    if a >= 0.35:
        return "present"
    if a >= 0.1:
        return "trace"
    return "absent"


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class Document(BaseModel):
    title: str
    source: str | None = None
    sha256: str
    cuisine: str | None = None
    meal_type: str | None = None
    dietary_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Extracted entities
# ---------------------------------------------------------------------------

class Ingredient(BaseModel):
    """Culinary ingredient — analogous to ErisML Stakeholder."""

    id: str
    name: str
    canonical_name: str | None = None
    quantity: str | None = None
    unit: str | None = None
    preparation: list[str] = Field(default_factory=list)
    food_group: FoodGroup = FoodGroup.UNKNOWN
    flavor_vector: FlavorVector = Field(default_factory=FlavorVector)
    flavor_compounds: list[str] = Field(default_factory=list)
    is_primary: bool = True


class FlavorTransformation(BaseModel):
    """Flavor-vector delta produced by a cooking technique."""

    dimension_deltas: dict[str, float] = Field(default_factory=dict)
    new_compounds: list[str] = Field(default_factory=list)
    description: str | None = None


class CookingTechnique(BaseModel):
    """Cooking operation — analogous to ErisML Event."""

    id: str
    name: str
    technique_type: TechniqueType = TechniqueType.UNKNOWN
    applies_to: list[str] = Field(default_factory=list)
    transformation: FlavorTransformation = Field(default_factory=FlavorTransformation)
    duration: str | None = None
    temperature: str | None = None


class RecipeStep(BaseModel):
    order: int
    instruction: str
    technique_id: str | None = None
    ingredient_ids: list[str] = Field(default_factory=list)


class Recipe(BaseModel):
    """Ordered sequence of steps — analogous to ErisML Commitment."""

    id: str
    name: str
    steps: list[RecipeStep] = Field(default_factory=list)
    status: Literal["complete", "partial", "sketch"] = "sketch"


class PairingRule(BaseModel):
    """Declared or inferred pairing rule — analogous to ErisML Norm."""

    id: str
    rule_type: PairingRuleType = PairingRuleType.RECOMMENDATION
    modality: Literal["pairs_with", "contrasts_with", "enhances", "masks", "avoids"]
    subject_id: str
    object_id: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source: str | None = None
    explanation: str | None = None


class FlavorFact(BaseModel):
    """Flavor-relevant observation — analogous to ErisML EthicalFact."""

    id: str
    fact_kind: FlavorFactKind
    subject_ids: list[str]
    dimension: str | None = None
    severity: Literal["trace", "minor", "moderate", "significant", "dominant"] = "minor"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    explanation: str | None = None


class Segment(BaseModel):
    id: str
    text: str
    segment_type: SegmentType
    start_char: int
    end_char: int


# ---------------------------------------------------------------------------
# Projection results
# ---------------------------------------------------------------------------

class PairingFinding(BaseModel):
    ingredient_ids: list[str]
    finding_type: str
    score: float = Field(ge=-1.0, le=1.0, default=0.0)
    explanation: str | None = None


class ProjectionResult(BaseModel):
    """Output of one culinary projection — analogous to ErisML ProjectionResult."""

    projection_id: str
    verdict: str
    polarity: Literal["harmonious", "neutral", "discordant"]
    findings: list[PairingFinding] = Field(default_factory=list)
    score: float = Field(ge=-1.0, le=1.0, default=0.0)
    explanation: str | None = None


# ---------------------------------------------------------------------------
# Harmony verdict
# ---------------------------------------------------------------------------

class HarmonyVerdict(BaseModel):
    verdict: HarmonyVerdictLabel
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    explanation: str
    dominant_projection: str | None = None


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class PassRecord(BaseModel):
    pass_number: int
    pass_name: str
    status: Literal["ok", "skipped", "failed", "warned"] = "ok"
    note: str | None = None


class AuditRecord(BaseModel):
    passes: list[PassRecord] = Field(default_factory=list)
    extractor_tier: str = "rule"
    active_projections: list[str] = Field(default_factory=list)
    graph_hash: str | None = None
    input_sha256: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level IR
# ---------------------------------------------------------------------------

class GastronomyIR(BaseModel):
    """Root IR object emitted by the compiler pipeline.

    Analogous to ErisML CompilerIR.  Carries all extracted entities, the
    FlavorGraph substrate, per-projection results, and the aggregate harmony
    verdict.
    """

    document: Document
    ingredients: list[Ingredient] = Field(default_factory=list)
    techniques: list[CookingTechnique] = Field(default_factory=list)
    recipes: list[Recipe] = Field(default_factory=list)
    pairing_rules: list[PairingRule] = Field(default_factory=list)
    flavor_facts: list[FlavorFact] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)

    # Populated in Pass 7.5
    flavor_graph: Any | None = None

    # Populated in Pass 8
    aggregate_flavor_vector: FlavorVector = Field(default_factory=FlavorVector)
    per_ingredient_vectors: dict[str, FlavorVector] = Field(default_factory=dict)

    # Populated in Pass 10
    projections: dict[str, ProjectionResult] = Field(default_factory=dict)
    cross_projection_disagreement: dict[str, Any] | None = None

    # Populated in Pass 11
    harmony_verdict: HarmonyVerdict | None = None

    audit: AuditRecord | None = None
    schema_version: str = "gastronomyml_ir_v0.1"
