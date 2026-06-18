# Extraction Tiers and Ingredient Library

`src/gastronomyml_compiler/annotation/`

The compiler has three extraction tiers. Passes 2–6 of the 13-pass pipeline are all handled by the active extractor, which is selected via `--extractor` at compile time.

---

## Tier architecture

```python
class CompilerTier(str, Enum):
    STRUCTURED = "structured"   # (future) fully-parsed structured input
    RULE       = "rule"         # production default — rule-based NLP
    LLM        = "llm"          # open-vocabulary LLM extraction (scaffolded)
    MOCK       = "mock"         # deterministic test fixture
```

All extractors implement `BaseExtractor`:

```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> ExtractorResult: ...

@dataclass
class ExtractorResult:
    ingredients:      list[Ingredient]
    techniques:       list[CookingTechnique]
    recipes:          list[Recipe]
    pairing_rules:    list[PairingRule]
    flavor_facts:     list[FlavorFact]
    cuisine_hint:     str | None
    meal_type_hint:   str | None
    dietary_flags:    list[str]
    extractor_metadata: dict
```

---

## Tier 1: MockExtractor

**File**: `annotation/mock_extractor.py`
**Selected by**: `--extractor mock`

Returns a hardcoded `ExtractorResult` with three ingredients (butter, lemon, thyme) and one technique (sauté), cuisine hint `"french"`. Used for testing the pipeline passes and projection logic without depending on text content.

---

## Tier 2: RuleExtractor (production default)

**File**: `annotation/rule_extractor.py`
**Selected by**: `--extractor rule` (default)

A deterministic NLP extractor that matches text against a static ingredient library and technique library using regex and keyword matching. No external dependencies.

### Ingredient library

~80 ingredients with flavor profile dicts and `FoodGroup` labels. Profiles are derived from FlavorDB2 molecular data and the Ahn et al. flavor network. Each entry maps dimension names to float scores in `[0, 1]`:

```python
INGREDIENT_LIBRARY = {
    "butter":    {"fat": 0.9, "sweet": 0.15, "salty": 0.1, "aromatic": 0.2, "group": FoodGroup.FAT},
    "lemon":     {"sour": 0.9, "aromatic": 0.7, "sweet": 0.1, "group": FoodGroup.FRUIT},
    "garlic":    {"aromatic": 0.85, "umami": 0.4, "heat": 0.3, "salty": 0.1, "group": FoodGroup.HERB},
    "thyme":     {"aromatic": 0.75, "bitter": 0.2, "group": FoodGroup.HERB},
    "miso":      {"umami": 0.95, "salty": 0.7, "sweet": 0.2, "aromatic": 0.45, "group": FoodGroup.CONDIMENT},
    "duck":      {"umami": 0.7, "fat": 0.7, "sweet": 0.15, "aromatic": 0.35, "group": FoodGroup.PROTEIN},
    "parmesan":  {"umami": 0.9, "salty": 0.75, "fat": 0.5, "aromatic": 0.4, "group": FoodGroup.DAIRY},
    # ... ~73 more entries
}
```

**Inosinate/glutamate classification** (used by `UmamiFM` for synergy detection):

| Compound class | Ingredients |
|---|---|
| Glutamate-rich | miso, parmesan, tomato, mushroom, soy sauce, fish sauce, marmite, anchovy paste, nutritional yeast |
| Inosinate-rich | duck, chicken, pork, beef, tuna, anchovy, salmon, sardine, shrimp, turkey |

When the extractor finds both classes present, it emits a `FlavorFact` with `fact_kind = FlavorFactKind.UMAMI_SYNERGY`.

### Technique library

25 cooking verbs mapped to `TechniqueType` and `FlavorTransformation.dimension_deltas`:

```python
TECHNIQUE_LIBRARY = {
    "sauté":    {"type": TechniqueType.SAUTEING,       "deltas": {"aromatic": 0.1, "fat": 0.05}},
    "roast":    {"type": TechniqueType.ROASTING,        "deltas": {"aromatic": 0.15, "bitter": 0.05}},
    "grill":    {"type": TechniqueType.GRILLING,        "deltas": {"aromatic": 0.15, "bitter": 0.05}},
    "braise":   {"type": TechniqueType.BRAISING,        "deltas": {"umami": 0.1, "fat": 0.05}},
    "fry":      {"type": TechniqueType.FRYING,          "deltas": {"fat": 0.15, "texture": 0.2}},
    "ferment":  {"type": TechniqueType.FERMENTATION,    "deltas": {"sour": 0.15, "umami": 0.05}},
    "caramelize": {"type": TechniqueType.CARAMELIZATION, "deltas": {"sweet": -0.05, "bitter": 0.05, "aromatic": 0.1}},
    "smoke":    {"type": TechniqueType.SMOKING,         "deltas": {"aromatic": 0.2, "bitter": 0.05}},
    "cure":     {"type": TechniqueType.CURING,          "deltas": {"salty": 0.1, "umami": 0.05}},
    "confit":   {"type": TechniqueType.CONFITING,       "deltas": {"fat": 0.1, "umami": 0.05}},
    # ... 15 more entries
}
```

### Cuisine detection

`CUISINE_KEYWORDS` maps each of the six supported traditions to a set of indicator terms. The extractor votes by counting matches across all terms in the text:

```python
CUISINE_KEYWORDS = {
    "french":         {"confit", "gastrique", "beurre", "roux", "julienne", "mirepoix", "port", "cognac", ...},
    "japanese":       {"dashi", "mirin", "sake", "nori", "miso", "wasabi", "yuzu", "ponzu", ...},
    "mediterranean":  {"olive oil", "capers", "za'atar", "sumac", "preserved lemon", "harissa", ...},
    "indian":         {"garam masala", "ghee", "cardamom", "fenugreek", "paneer", "dal", ...},
    "italian":        {"prosciutto", "parmigiano", "balsamic", "polenta", "risotto", "bruschetta", ...},
    "chinese":        {"five spice", "hoisin", "doubanjiang", "shaoxing", "wok hei", ...},
}
```

The tradition with the highest keyword count is returned as `cuisine_hint`. If two traditions are tied within two matches of each other, both are returned (this is the fusion detection pathway for `CulturalHarmonyProjection`).

### Known pairings

`POSITIVE_PAIRS` and `NEGATIVE_PAIRS` are lists of known-good and known-bad ingredient combinations with explanations and confidence scores. When the extractor finds both members of a pair in the ingredient list, it emits a `PairingRule`:

```python
POSITIVE_PAIRS = [
    {"ids": ["butter", "lemon"], "explanation": "fat rounds and carries citrus volatiles", "confidence": 0.8},
    {"ids": ["miso", "salmon"],  "explanation": "glutamate+inosinate synergy; umami amplification", "confidence": 0.95},
    {"ids": ["duck", "cherry"],  "explanation": "classic French canard aux cerises", "confidence": 0.75},
    # ...
]

NEGATIVE_PAIRS = [
    {"ids": ["fish", "milk"],    "explanation": "protein coagulation; widely perceived as incompatible", "confidence": 0.65},
    {"ids": ["artichoke", "wine"], "explanation": "cynarin makes wine taste sweet and metallic", "confidence": 0.7},
    # ...
]
```

### Pairing rules and flavor facts

In addition to known pairs, the extractor emits `FlavorFact`s for structural observations:

- `ACID_FAT_BALANCE`: when sour and fat dimensions are both `present` or higher, emit a positive balance fact.
- `BITTERNESS_MITIGATION`: when bitter dimension is `present` and fat dimension is `dominant`, emit a mitigation fact.
- `DOMINANCE`: when a single dimension scores `dominant` (≥ 0.65) with no complementary dimension above `present`, emit a dominance fact.

---

## Tier 3: LLM extractor (scaffolded)

**File**: `annotation/llm_extractor.py` (scaffolded)
**Selected by**: `--extractor llm`
**Requires**: `pip install gastronomyml-compiler[llm]` (adds `openai≥1.0`)

The LLM extractor sends the text to an OpenAI-compatible chat endpoint and parses the structured JSON response back into `ExtractorResult`. It is designed for open-vocabulary dish descriptions where the rule extractor's 80-entry library would have low recall.

**Current status**: the extractor class and interface are scaffolded. A caller must supply an OpenAI-compatible endpoint via the `OPENAI_API_KEY` environment variable (and optionally `OPENAI_BASE_URL` for a self-hosted endpoint). The prompt and structured-output schema are implemented; end-to-end integration tests are pending.

---

## Canonicalizer

**File**: `canonicalizer/registry.py`
**Pass**: 7

After extraction, ingredient names are canonicalised against an alias registry:

```python
_ALIASES = {
    "parmigiano-reggiano": "parmesan",
    "parmigiano":          "parmesan",
    "pecorino":            "parmesan",   # approximate — same FoodGroup
    "sea salt":            "salt",
    "kosher salt":         "salt",
    "scallion":            "green onion",
    "spring onion":        "green onion",
    "cilantro":            "coriander",
    "heavy cream":         "cream",
    "double cream":        "cream",
    "crème fraîche":       "sour cream",
    "aubergine":           "eggplant",
    "courgette":           "zucchini",
    "caster sugar":        "sugar",
    # ... ~25 more aliases
}
```

Canonicalization ensures that `POSITIVE_PAIRS`, the FM-DAG ingredient library lookups, and the graph node deduplication all work correctly regardless of recipe-text spelling variation.

---

## Segment types

**File**: `segmentation/segmenter.py`

The segmenter splits text on blank lines and classifies each segment before extraction:

| SegmentType | Detection heuristic |
|---|---|
| `INGREDIENT_LIST` | ≥ 2 quantity patterns (`\d+\s*(g\|oz\|cup\|tbsp\|tsp\|ml\|lb\|kg)`) |
| `INSTRUCTION` | 1 imperative cooking verb |
| `TECHNIQUE` | ≥ 2 cooking technique verbs |
| `GARNISH` | Contains keywords: garnish, serve with, to finish, for serving |
| `CONTEXT` | Contains keywords: cuisine, style, inspired by, traditional, regional |
| `DESCRIPTION` | Fallback for segments that match none of the above |

The segment type is stored in `Segment.segment_type` and included in the IR for downstream inspection. The extractor processes all segments, but weights ingredient extraction more heavily on `INGREDIENT_LIST` segments and technique extraction more heavily on `INSTRUCTION` and `TECHNIQUE` segments.
