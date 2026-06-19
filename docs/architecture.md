# GastronomyML Compiler Architecture (v0.1.0)

This document describes the runtime architecture of the GastronomyML Compiler as of `main` at v0.1.0. For the ingredient flavor-profile library and extraction tiers see `docs/extraction.md`. For the nine-module FM-DAG see `docs/fm_dag.md`. For the four culinary projections see `docs/projections.md`.

## One-paragraph summary

Text compiles into a typed `FlavorGraph` (the descriptive substrate) with a canonical SHA-256 hash anchored in the audit chain. Four culinary `Projection` analysers read that graph and emit projection-relative harmony verdicts. When projections disagree by normalised polarity, the compiler refuses to aggregate and surfaces all verdicts explicitly via `ir.cross_projection_disagreement`. The nine-module FM-DAG evaluates flavor dimensions in topological dependency order and writes the aggregate `FlavorVector` into the IR. Projections are selected at compile time via the `--projection` flag; any subset of the four is valid.

---

## The two-layer IR

```
              ┌──────────────────────────────────────────────┐
              │              FlavorGraph (DAG)                │
              │                                              │
              │  Nodes: ingredient · technique · dish ·      │
              │         compound · pairing_axis · norm       │
              │                                              │
              │  Edges: contains · transforms · pairs_with · │
              │         contrasts_with · enhances · masks ·  │
              │         cultural_norm · flavor_bridge ·      │
              │         avoids · applies_to                  │
              │                                              │
              │  Canonical SHA-256 → audit.graph_hash        │
              └──────────────────────────────────────────────┘
                                   │
                       (typed graph queries)
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
┌─────────────────┐   ┌──────────────────────┐   ┌──────────────────────────┐
│ FlavorSimilarity│   │ FlavorContrast        │   │ CulturalHarmony          │
│ Projection      │   │ Projection            │   │ Projection               │
│                 │   │                       │   │                          │
│ Pairwise cosine │   │ 6 contrast-pair       │   │ Tradition norm sets:     │
│ similarity on   │   │ GateFinding[]s        │   │ french · japanese ·      │
│ flavor vectors  │   │ + dominance check     │   │ italian · mediterranean  │
│                 │   │                       │   │ indian · chinese         │
│ verdict:        │   │ verdict:              │   │                          │
│  harmonious_by_ │   │  beautifully_balanced │   │ verdict:                 │
│  compound_shar- │   │  well_contrasted      │   │  culturally_coherent     │
│  ing / diverse_ │   │  one_note_dominant    │   │  cross_cultural_harmony  │
│  flavor_profile │   │  flat_profile         │   │  cultural_tension        │
│                 │   │                       │   │                          │
│ polarity:       │   │ polarity:             │   │ polarity:                │
│  harmonious /   │   │  harmonious /         │   │  harmonious /            │
│  neutral        │   │  neutral / discordant │   │  neutral / discordant    │
└─────────────────┘   └──────────────────────┘   └──────────────────────────┘

              ┌──────────────────────────────────────┐
              │         NutritionalBalance            │
              │         Projection                    │
              │                                      │
              │  Food-group coverage findings         │
              │  (protein · vegetable · fat · carb)  │
              │                                      │
              │  verdict:                            │
              │   nutritionally_balanced             │
              │   fat_heavy_no_greens                │
              │   protein_absent · partial_balance   │
              │                                      │
              │  polarity:                           │
              │   harmonious / neutral / discordant  │
              └──────────────────────────────────────┘

                                   │
      ┌────────────────────────────┴────────────────────────────┐
      │  Cross-projection polarity comparison                    │
      │  ─────────────────────────────────────                  │
      │  If {harmonious, discordant} both present in active      │
      │  projections, populate ir.cross_projection_disagreement. │
      │  Compiler refuses to aggregate. Choice deferred to       │
      │  caller; documented as a culinary-framework move.        │
      └──────────────────────────────────────────────────────────┘
```

The substrate is **descriptive**: what ingredients are present, how they are transformed by technique, what pairing relationships hold between them. The projections are **framework-bound**: each emits the kind of analytical object its culinary framework actually produces — cosine-similarity findings for a compound-sharing analysis, gate findings for a cultural-norm analysis, food-group findings for a nutritional analysis. The compiler never silently aggregates across frameworks because framework selection is itself a culinary judgment.

---

## FlavorGraph schema

`src/gastronomyml_compiler/ir/graph/`

```python
class NodeKind(str, Enum):
    INGREDIENT   = "ingredient"
    TECHNIQUE    = "technique"
    DISH         = "dish"
    COMPOUND     = "compound"       # FlavorDB2 PubChem reference
    PAIRING_AXIS = "pairing_axis"
    NORM         = "norm"           # cultural pairing norm

class EdgeKind(str, Enum):
    CONTAINS       = "contains"         # dish → ingredient
    TRANSFORMS     = "transforms"       # technique → ingredient
    PAIRS_WITH     = "pairs_with"       # ingredient ↔ ingredient (positive)
    CONTRASTS_WITH = "contrasts_with"   # ingredient ↔ ingredient (complementary)
    ENHANCES       = "enhances"         # ingredient → ingredient (amplifies)
    MASKS          = "masks"            # ingredient → ingredient (suppresses)
    CULTURAL_NORM  = "cultural_norm"    # norm → ingredient pair
    FLAVOR_BRIDGE  = "flavor_bridge"    # ingredient → compound (shared volatile)
    AVOIDS         = "avoids"           # ingredient → ingredient (incompatible)
    APPLIES_TO     = "applies_to"       # technique → ingredient
```

Node payloads carry the original Pydantic-model contents verbatim. `FlavorNode.flavor_scores` holds the raw float values from the ingredient's `FlavorVector` (one float per dimension in `[-1, 1]`), enabling projection code to query flavor scores without re-traversing the flat IR.

### Canonical hashing

`ir/graph/canonical.py` produces a deterministic JSON encoding (nodes sorted by `id`, edges sorted by `(src, dst, kind)`) and an SHA-256 over it. The same nodes-and-edges content produces the same hash regardless of insertion order. Anchored in `AuditRecord.graph_hash`.

### Graph synthesis (Pass 7.5)

`ir/graph/promote.py` — `graph_from_ir(ir) -> FlavorGraph`. Reads the flat extractor output and synthesises typed nodes and edges:

- Every `Ingredient` becomes an `INGREDIENT` node with a `CONTAINS` edge from the dish root.
- Every `CookingTechnique` becomes a `TECHNIQUE` node with `APPLIES_TO` edges to its target ingredients. The technique's `FlavorTransformation.dimension_deltas` are stored in the edge payload.
- Every `PairingRule` becomes a typed edge (`PAIRS_WITH`, `CONTRASTS_WITH`, `ENHANCES`, `MASKS`, or `AVOIDS`) between the subject and object ingredient nodes.

---

## The nine flavor dimensions

```
k=0  sweet      — sweetness intensity
k=1  salty      — saltiness / mineral
k=2  sour       — acidity / brightness
k=3  bitter     — bitterness / tannins
k=4  umami      — savory depth
k=5  fat        — richness / fat
k=6  heat       — spice / pungency
k=7  aromatic   — volatile aromatic complexity
k=8  texture    — mouthfeel / body
```

The nine dimensions are encoded as `DimensionScore` objects in `[-1, 1]`:

```python
class DimensionScore(BaseModel):
    value:       float   # ∈ [-1, 1], signed
    confidence:  float   # ∈ [0, 1]
    direction:   Literal["dominant", "present", "trace", "absent"]
    explanation: str | None
```

Direction thresholds: `dominant` ≥ 0.65, `present` ≥ 0.35, `trace` ≥ 0.10, `absent` < 0.10.

---

## The 13-pass pipeline

| Pass | Stage | Implementation |
|---|---|---|
| 0 | Ingestion | `ingestion/text_loader.py` — load from file path or inline text; return `(text, sha256)` |
| 1 | Segmentation | `segmentation/segmenter.py` — split on blank lines, assign `SegmentType` heuristically |
| 2–6 | Extraction | `annotation/{mock,rule}_extractor.py` — ingredients, techniques, pairing rules, context, flavor facts |
| 7 | Canonicalization | `canonicalizer/registry.py` — alias resolution (e.g. *parmigiano-reggiano* → *parmesan*) |
| **7.5** | **Graph synthesis** | `ir/graph/promote.py` — promote flat extractor output to `FlavorGraph`, compute `graph_hash` |
| **8** | **FM-DAG** | `fm_dag/dag.py` — run 9 flavor modules in topological order; write aggregate `FlavorVector` |
| 9 | Codegen | IR finalization (no-op pass record; IR is fully assembled) |
| 10 | Projection evaluation | `projections/` — run each selected projection over the IR; write `ir.projections` |
| 11 | Harmony verdict | `pipeline/orchestrator.py:_aggregate_verdict` — aggregate polarity votes; populate `ir.harmony_verdict` |
| 12 | Audit | `audit/hash_chain.py` — finalize `AuditRecord` with pass records, graph hash, active projections |

### Projection selection at compile time

Any subset of the four projections may be selected via the `--projection` flag. The orchestrator validates the list at startup and raises `ValueError` on unknown names:

```bash
# All four (default)
gastronomy-compile compile dish.txt

# Subset
gastronomy-compile compile dish.txt \
    --projection flavor_similarity,cultural_harmony
```

When a projection is not selected it is not run and does not appear in `ir.projections`. The harmony verdict is computed only over the active set.

---

## Projection layer

`src/gastronomyml_compiler/projections/`

Each `BaseProjection` reads the fully-assembled `GastronomyIR` (including `flavor_graph` and `aggregate_flavor_vector`) and returns a `ProjectionResult`:

```python
class ProjectionResult(BaseModel):
    projection_id: str
    verdict:       str
    polarity:      Literal["harmonious", "neutral", "discordant"]
    findings:      list[PairingFinding]
    score:         float   # ∈ [-1, 1]
    explanation:   str | None
```

### The four shipped projections

| Projection | Reads | Emits | Verdict polarities |
|---|---|---|---|
| **`FlavorSimilarityProjection`** | Per-ingredient `FlavorVector`s | Pairwise cosine-similarity `PairingFinding`s | `harmonious` / `neutral` |
| **`FlavorContrastProjection`** | Aggregate `FlavorVector` | 6 contrast-pair findings + dominance findings | `harmonious` / `neutral` / `discordant` |
| **`CulturalHarmonyProjection`** | Ingredient names, `Document.cuisine` | Tradition-norm findings (positive + negative) | `harmonious` / `neutral` / `discordant` |
| **`NutritionalBalanceProjection`** | Ingredient `FoodGroup` labels | Food-group coverage findings | `harmonious` / `neutral` / `discordant` |

See `docs/projections.md` for the full specification of each projection's rules.

### Cross-projection disagreement

`ir.cross_projection_disagreement` is populated iff ≥ 2 active projections emit distinct non-neutral polarities (`harmonious` vs. `discordant`). Comparison is on **polarity**, not on the framework-native verdict string, so vocabulary differences across projections do not register as fake disagreement.

```python
{
  "verdicts":  { projection_id: verdict_str, … },
  "polarities": { projection_id: "harmonious"|"neutral"|"discordant", … },
  "note": "Projections disagree on polarity. The compiler surfaces all verdicts; "
          "choosing is the caller's responsibility."
}
```

The compiler does **not** populate a winner.

---

## FM-DAG (flavor evaluator)

`src/gastronomyml_compiler/fm_dag/`

Nine `FlavorModule` subclasses run in topological dependency order to produce the aggregate `FlavorVector`. See `docs/fm_dag.md` for the full specification.

```
Roots (no upstream deps):
    FatFM        k=5  — fat content from ingredients + fat-augmenting techniques
    UmamiFM      k=4  — umami from ingredients + glutamate/inosinate synergy check

Second tier (read fat or umami outputs):
    SweetFM      k=0  — sweetness; reduced when caramelization is active
    SaltyFM      k=1  — saltiness amplified by umami context
    SourFM       k=2  — acidity; boosted by fermentation
    BitterFM     k=3  — bitterness suppressed by fat context
    HeatFM       k=6  — capsaicin/pungency; tamed by fat context

Third tier (read technique context):
    AromaticFM   k=7  — volatile aromatics; boosted by Maillard/roasting techniques
    TextureFM    k=8  — mouthfeel; boosted by frying, braising, emulsification
```

The key inter-module dependencies:

- **Fat → Bitter**: `BitterFM` applies `× max(0.5, 1.0 − 0.3 × fat_avg)` to suppress perceived bitterness. Fat carries bitter compounds away from taste receptors.
- **Fat → Heat**: `HeatFM` applies `× max(0.6, 1.0 − 0.2 × fat_avg)` to tame capsaicin heat.
- **Umami → Salty**: `SaltyFM` applies `× (1.0 + 0.1 × umami_avg)` to model the efficiency gain that high-glutamate context provides to salt perception.
- **Umami synergy**: `UmamiFM` detects `FlavorFactKind.UMAMI_SYNERGY` in `ir.flavor_facts` (set by the extractor when glutamate-rich and inosinate-rich ingredients co-occur) and applies a 1.4× multiplier to the aggregate umami score.

---

## Audit chain

`AuditRecord` carries:

- `passes` — per-pass `PassRecord` list (pass number, name, status, optional note)
- `extractor_tier` — the tier used (`rule`, `mock`)
- `active_projections` — list of projection IDs that were run
- `graph_hash` — SHA-256 of the canonical `FlavorGraph`
- `input_sha256` — SHA-256 of the raw input text
- `provenance.schema` — `"gastronomyml_ir_v0.1"`
- `provenance.passes_completed` — count of `ok` passes

Identical input + extractor + projection set produces identical `graph_hash`. Two compiles of the same dish yield bit-identical audit records.

---

## GastronomyIR field reference

```
ir.document                       Document metadata (title, cuisine, sha256, …)
ir.ingredients                    list[Ingredient]
ir.techniques                     list[CookingTechnique]
ir.recipes                        list[Recipe]
ir.pairing_rules                  list[PairingRule]
ir.flavor_facts                   list[FlavorFact]
ir.segments                       list[Segment]
ir.flavor_graph                   FlavorGraph — populated Pass 7.5
ir.aggregate_flavor_vector        FlavorVector — populated Pass 8
ir.per_ingredient_vectors         dict[ingredient_id, FlavorVector]
ir.projections                    dict[projection_id, ProjectionResult] — populated Pass 10
ir.cross_projection_disagreement  dict | None — populated Pass 10
ir.harmony_verdict                HarmonyVerdict — populated Pass 11
ir.audit                          AuditRecord — populated Pass 12
ir.schema_version                 "gastronomyml_ir_v0.1"
```

---

## Export formats

| Format | Command | File |
|---|---|---|
| GastronomyIR JSON | `gastronomy-compile compile … --out file.ir.json` | `export/json_export.py` |
| Schema.org/Recipe JSON-LD | `gastronomy-compile export-schema-org file.ir.json` | `export/schema_org.py` |

The Schema.org export serialises the dish title, ingredient list, recipe instructions, cuisine, dominant flavor dimensions (as keywords), and harmony verdict explanation into a `@type: Recipe` JSON-LD object compatible with FoodKG and standard recipe platforms.

---

## What this architecture is not

- **Not framework-neutral.** The substrate's extraction categories (ingredients, techniques, pairing rules, flavor facts) are themselves choices. The FlavorSimilarity projection encodes the Western compound-sharing hypothesis; the CulturalHarmony projection encodes hand-curated tradition norms. Selecting a projection is selecting a culinary framework.
- **Not a culinary authority.** The compiler emits structured findings from N projections and refuses to choose between them when they disagree. That choice belongs to the caller.
- **Not a complete flavor-chemistry analyser.** The rule extractor's flavor profiles are derived from a static library, not from live FlavorDB2 API calls. Volatile compound IDs (`Ingredient.flavor_compounds`) are placeholders pending a PubChem integration pass.
- **Not a replacement for a trained chef.** The harmony verdict and projection findings are structured inputs to human culinary judgment, not substitutes for it.
