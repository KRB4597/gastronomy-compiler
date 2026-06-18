# Culinary Projections

`src/gastronomyml_compiler/projections/`

A projection is a culinary framework analyser. It reads the fully-assembled `GastronomyIR` and emits a `ProjectionResult` expressing what that specific framework says about the dish's harmony. The compiler ships four projections. Any subset may be selected at compile time via the `--projection` flag.

---

## Architecture

```python
class BaseProjection(ABC):
    projection_id: str

    @abstractmethod
    def run(self, ir: GastronomyIR) -> ProjectionResult: ...

class ProjectionResult(BaseModel):
    projection_id: str
    verdict:       str
    polarity:      Literal["harmonious", "neutral", "discordant"]
    findings:      list[PairingFinding]
    score:         float   # ∈ [-1, 1]
    explanation:   str | None
```

`PairingFinding` records a single detected relationship (positive or negative) between one or more ingredients:

```python
class PairingFinding(BaseModel):
    ingredient_ids: list[str]
    finding_type:   str
    score:          float   # ∈ [-1, 1]
    explanation:    str
```

---

## Selecting projections at compile time

```bash
# All four (default)
gastronomy-compile compile recipe.txt

# Two projections
gastronomy-compile compile recipe.txt \
    --projection flavor_similarity,cultural_harmony

# One projection
gastronomy-compile compile recipe.txt \
    --projection nutritional_balance
```

The orchestrator validates the requested names against `ALL_PROJECTIONS` and raises `ValueError` on unrecognised IDs.

---

## `FlavorSimilarityProjection`

**ID**: `flavor_similarity`
**File**: `projections/flavor_similarity.py`

**Theoretical basis**: Ahn et al. (2011) compound-sharing hypothesis. Ingredients that share a high proportion of flavor-active volatile compounds tend to be perceived as harmonious in Western culinary contexts. The compiler approximates compound-sharing distance via cosine similarity over the nine-dimensional `FlavorVector`, where each dimension is a proxy for a class of flavor-active compounds.

**Algorithm**:

For each pair of ingredient nodes in the `FlavorGraph`:

1. Retrieve the ingredient's `FlavorVector` from `ir.per_ingredient_vectors`.
2. Extract the 9-element float array via `flavor_vector.to_array()`.
3. Compute pairwise cosine similarity: `sim = dot(a, b) / (||a|| × ||b||)`.
4. Emit a `PairingFinding` for every pair with `score = sim`.

**Aggregate score**: mean of all pairwise cosine similarities.

**Verdict mapping**:

| Mean similarity | Verdict | Polarity |
|---|---|---|
| ≥ 0.60 | `harmonious_by_compound_sharing` | `harmonious` |
| ≥ 0.35 | `moderate_compound_affinity` | `harmonious` |
| ≥ 0.15 | `diverse_flavor_profile` | `neutral` |
| < 0.15 | `low_compound_overlap` | `neutral` |

**Note on polarity**: this projection never emits `discordant`. Under the compound-sharing hypothesis, low cosine similarity is not a *bad* pairing — it simply reflects a composed dish where the chef intentionally combined contrasting flavor families. Discordance is evaluated by `FlavorContrastProjection` instead.

---

## `FlavorContrastProjection`

**ID**: `flavor_contrast`
**File**: `projections/flavor_contrast.py`

**Theoretical basis**: Classical Western complementarity theory. Certain flavor dimension pairs are considered complementary: sweet/sour creates brightness and depth, bitter/fat creates richness, acid/richness (sour/fat) creates palatability, and so on. A dish that exhibits these complementary dimensions is considered to have contrast balance. A dish that is completely dominated by a single unmitigated dimension is considered unbalanced.

**Contrast pairs and weights**:

| Pair | Weight |
|---|---|
| sweet / sour | 0.80 |
| bitter / fat | 0.85 |
| umami / sour | 0.75 |
| heat / fat | 0.80 |
| salty / sweet | 0.70 |
| bitter / sweet | 0.65 |

**Algorithm**:

For each contrast pair `(A, B)` with weight `w`:

1. Retrieve `a = ir.aggregate_flavor_vector.{A}.value` and `b = ir.aggregate_flavor_vector.{B}.value`.
2. Minimum contrast score: `contrast = min(a, b)`.
3. Emit a `PairingFinding` with `score = contrast × w`.

Dominance check: if any single dimension has `value > 0.75` with no corresponding partner scoring `> 0.35`, emit a negative `PairingFinding` (`finding_type = "unmitigated_dominance"`, `score = −0.3`).

**Aggregate score**: weighted average of contrast findings, clipped to `[−1, 1]`.

**Verdict mapping**:

| Score | Verdict | Polarity |
|---|---|---|
| > 0.65 | `beautifully_balanced` | `harmonious` |
| > 0.40 | `well_contrasted` | `harmonious` |
| > 0.15 | `partial_contrast` | `neutral` |
| > −0.15 | `one_note_dominant` | `discordant` |
| ≤ −0.15 | `flat_profile` | `discordant` |

---

## `CulturalHarmonyProjection`

**ID**: `cultural_harmony`
**File**: `projections/cultural_harmony.py`

**Theoretical basis**: Culinary tradition encodes pairing norms that evolved over centuries within a culture's specific ingredient pantry, climate, and social context. A dish that respects its tradition's positive norms will be perceived as coherent within that tradition. A dish that violates its tradition's negative norms will produce cultural dissonance. When a dish's ingredients span multiple traditions simultaneously, it may be evaluated as fusion — an explicit culinary choice rather than an error.

**Tradition norm sets** (`_NORMS`):

| Tradition | Positive norm examples | Negative norm examples |
|---|---|---|
| `french` | butter+wine, cream+mushroom, duck+cherry | |
| `japanese` | miso+dashi, sake+ginger, sesame+mirin, seafood+nori | |
| `mediterranean` | tomato+olive+basil, lemon+herb, garlic+fish | |
| `indian` | cumin+coriander, turmeric+ginger+garlic, yogurt+spice | |
| `italian` | tomato+basil+garlic, parmesan+truffle, seafood+lemon | |
| `chinese` | soy+ginger+garlic, five spice+pork, rice wine+sesame | |

**Algorithm**:

1. Detect cuisine: check `ir.document.cuisine` first; if absent, match ingredient names against `CUISINE_KEYWORDS` dict in the rule extractor.
2. For each matched tradition, score positive norms present in the dish as `PairingFinding`s with positive scores.
3. If negative norm ingredients co-occur, emit negative `PairingFinding`s.
4. Fusion detection: if two or more distinct traditions are matched, mark the result as fusion.

**Aggregate score**: `(positive_matches − negative_matches) / max(1, total_possible_norms)`.

**Verdict mapping**:

| Condition | Verdict | Polarity |
|---|---|---|
| Score > 0.70, single tradition | `culturally_coherent` | `harmonious` |
| Score > 0.50, single tradition | `tradition_aligned` | `harmonious` |
| Fusion detected, score > 0.40 | `cross_cultural_harmony` | `harmonious` |
| Fusion detected, score ≤ 0.40 | `fusion_blend` | `neutral` |
| No tradition matched | `tradition_undetermined` | `neutral` |
| Score 0.20–0.50, single tradition | `partial_tradition_match` | `neutral` |
| Score < 0.20, negative norms present | `cultural_tension` | `discordant` |

---

## `NutritionalBalanceProjection`

**ID**: `nutritional_balance`
**File**: `projections/nutritional_balance.py`

**Theoretical basis**: USDA FoodData Central food-group classification. A nutritionally complete meal covers the major macro-nutrient groups (protein, vegetables, fat/oil, carbohydrate). The projection does not model micronutrients, caloric density, or specific dietary requirements — it applies a coarse food-group coverage heuristic suitable for a first-pass structural analysis.

**Food group checks**:

| Check | Ingredient FoodGroup values | Flag |
|---|---|---|
| `has_protein` | `PROTEIN`, `SEAFOOD`, `DAIRY`, `FUNGUS` | absence → negative finding |
| `has_veg` | `VEGETABLE`, `HERB`, `FRUIT` | absence → negative finding |
| `has_fat` | `FAT`, `DAIRY` | absence → neutral (fat is not required) |
| `has_carb` | `CARBOHYDRATE`, `SWEETENER` | absence → neutral |
| `fat_count` | count of `FAT`, `DAIRY` ingredients | `fat_count ≥ 3` → warning |
| `carb_count` | count of `CARBOHYDRATE`, `SWEETENER` ingredients | `carb_count ≥ 3` → warning |
| high fat + high carb | `fat_count ≥ 2` and `carb_count ≥ 2` | → negative finding |

**Aggregate score**: `(checks_passed − checks_failed × 0.5) / total_checks_run`, clipped to `[−1, 1]`.

**Verdict mapping**:

| Condition | Verdict | Polarity |
|---|---|---|
| All major groups covered, no flags | `nutritionally_balanced` | `harmonious` |
| All major groups covered, minor flags only | `reasonable_balance` | `harmonious` |
| Fat ≥ 3, no vegetables | `fat_heavy_no_greens` | `discordant` |
| No protein source detected | `protein_absent` | `discordant` |
| Some groups present, some absent | `partial_balance` | `neutral` |

---

## Cross-projection disagreement

When two or more active projections emit distinct non-neutral polarities, `ir.cross_projection_disagreement` is populated. The comparison is on **polarity** (`harmonious` vs. `discordant`), not on the framework-native verdict string:

```python
{
  "verdicts": {
    "flavor_similarity": "diverse_flavor_profile",
    "cultural_harmony":  "culturally_coherent"
  },
  "polarities": {
    "flavor_similarity": "neutral",
    "cultural_harmony":  "harmonious"
  },
  "note": "Projections disagree on polarity. ..."
}
```

A `neutral` polarity is not a party to disagreement — only `harmonious` vs. `discordant` constitutes a true conflict. This means a dish can have one framework call it harmonious and another call it neutral without triggering disagreement. Only when one framework calls it harmonious and another calls it discordant does the compiler refuse to aggregate.

---

## Adding a new projection

1. Create `projections/my_projection.py` with a class that inherits from `BaseProjection` and implements `run(ir) -> ProjectionResult`.
2. Set `projection_id` to a snake_case string.
3. Add the ID to `ALL_PROJECTIONS` in `tiers.py`.
4. Register the projection instance in the orchestrator's `_PROJECTION_REGISTRY` dict in `pipeline/orchestrator.py`.
5. Add a test in `tests/test_projections.py`.

The CLI's `--projection` flag will accept the new ID automatically once it is in `ALL_PROJECTIONS`.
