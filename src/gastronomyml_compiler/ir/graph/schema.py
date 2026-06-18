from enum import Enum
from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    INGREDIENT = "ingredient"
    TECHNIQUE = "technique"
    DISH = "dish"
    COMPOUND = "compound"       # flavor compound (FlavorDB2 PubChem ref)
    PAIRING_AXIS = "pairing_axis"
    NORM = "norm"               # cultural pairing norm


class EdgeKind(str, Enum):
    CONTAINS = "contains"               # dish → ingredient
    TRANSFORMS = "transforms"           # technique → ingredient
    PAIRS_WITH = "pairs_with"           # ingredient ↔ ingredient (positive)
    CONTRASTS_WITH = "contrasts_with"   # ingredient ↔ ingredient (complementary)
    ENHANCES = "enhances"               # ingredient → ingredient (amplifies)
    MASKS = "masks"                     # ingredient → ingredient (suppresses)
    CULTURAL_NORM = "cultural_norm"     # norm → ingredient pair
    FLAVOR_BRIDGE = "flavor_bridge"     # ingredient → compound (shared compound)
    AVOIDS = "avoids"                   # ingredient → ingredient (incompatible)
    APPLIES_TO = "applies_to"           # technique → ingredient


class FlavorNode(BaseModel):
    id: str
    kind: NodeKind
    label: str
    flavor_scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class FlavorEdge(BaseModel):
    src: str
    dst: str
    kind: EdgeKind
    payload: dict = Field(default_factory=dict)
