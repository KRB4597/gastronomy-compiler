# GastronomyML Compiler

A natural-language culinary modeling language and compiler, analogous in structure to [ErisML Compiler](https://github.com/ahb-sjsu/erisml-compiler).

GastronomyML accepts plain-English dish descriptions and compiles them into a typed, hashable **FlavorGraph IR** — a canonical intermediate representation of ingredients, cooking techniques, pairing rules, and flavor assessments grounded in published flavor science (Ahn et al. 2011, FlavorDB2, geometric-gastronomy).

---

## Architecture

The compiler runs a **13-pass pipeline** mirroring ErisML:

| Pass | Stage | Description |
|------|-------|-------------|
| 0 | Ingestion | Load text or file |
| 1 | Segmentation | Split into typed segments (ingredient_list, technique, context…) |
| 2–6 | Extraction | Ingredients, techniques, pairings, context, flavor facts |
| 7 | Canonicalization | Normalize ingredient names to canonical forms |
| 7.5 | Graph synthesis | Build FlavorGraph DAG |
| 8 | FM-DAG | 9 Flavor Modules compute aggregate FlavorVector |
| 9 | Codegen | IR finalization |
| 10 | Projections | Run selected culinary projections |
| 11 | Harmony verdict | Aggregate verdict across projections |
| 12 | Audit | Hash chain + provenance |

### ErisML → GastronomyML analogs

| ErisML | GastronomyML |
|--------|-------------|
| Stakeholders | Ingredients |
| Events | Cooking Techniques |
| Commitments | Recipes |
| Norms | Pairing Rules |
| EthicalFacts (9-dim) | FlavorFacts (9-dim) |
| MoralGraph (DAG) | FlavorGraph (DAG) |
| 4 Framework Projections | 4 Culinary Projections |
| DEME verdict | Harmony Verdict |

### The 9 Flavor Dimensions

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

### The 4 Culinary Projections (compile-time selectable)

| Projection | Grounding | Assesses |
|---|---|---|
| `flavor_similarity` | Ahn et al. 2011, FlavorGraph | Shared volatile compound affinity (cosine similarity) |
| `flavor_contrast` | Classical culinary theory | Complementary pairs: sweet/sour, bitter/fat, acid/richness |
| `cultural_harmony` | Cuisine tradition norms | French, Japanese, Italian, Mediterranean, Indian, Chinese rule sets |
| `nutritional_balance` | USDA FoodData Central | Protein/fat/carb/vegetable coverage |

---

## Installation

```bash
pip install -e ".[dev]"
```

**Python 3.10+, Pydantic v2 required.**

---

## Usage

### Compile a dish description

```bash
# Run all 4 projections (default)
gastronomy-compile compile examples/duck_confit.txt --out duck_confit.ir.json

# Select projections at compile time
gastronomy-compile compile examples/miso_ramen.txt \
    --projection flavor_similarity,cultural_harmony \
    --extractor rule \
    --out ramen.ir.json

# Inline text
gastronomy-compile compile "Seared salmon with lemon butter and capers." \
    --projection flavor_contrast,nutritional_balance
```

### Validate an IR file

```bash
gastronomy-compile validate duck_confit.ir.json
```

### Print a human-readable report

```bash
gastronomy-compile report duck_confit.ir.json
```

### Export as Schema.org/Recipe JSON-LD

```bash
gastronomy-compile export-schema-org duck_confit.ir.json --out duck_confit.jsonld
```

---

## Extractor tiers

| Flag | Tier | Description |
|------|------|-------------|
| `--extractor rule` | Tier 2 | Deterministic pattern library (default) |
| `--extractor mock` | Tier 0 | Deterministic fixture for testing |
| `--extractor llm` | Tier 3 | OpenAI-compatible model (requires `[llm]` extra) |

---

## GastronomyIR structure

```json
{
  "document": { "title": "...", "cuisine": "french", "sha256": "..." },
  "ingredients": [...],
  "techniques": [...],
  "pairing_rules": [...],
  "flavor_facts": [...],
  "flavor_graph": { "nodes": [...], "edges": [...], "graph_hash": "..." },
  "aggregate_flavor_vector": {
    "sweet": { "value": 0.18, "direction": "trace" },
    "umami": { "value": 0.72, "direction": "dominant" },
    ...
  },
  "projections": {
    "flavor_similarity": { "verdict": "moderate_compound_affinity", "score": 0.42, ... },
    "flavor_contrast":   { "verdict": "beautifully_balanced", "score": 0.61, ... },
    "cultural_harmony":  { "verdict": "culturally_coherent", "score": 0.87, ... },
    "nutritional_balance": { "verdict": "nutritionally_balanced", "score": 0.65, ... }
  },
  "harmony_verdict": {
    "verdict": "harmonious",
    "confidence": 0.82,
    "explanation": "..."
  },
  "audit": { "passes": [...], "graph_hash": "...", "active_projections": [...] },
  "schema_version": "gastronomyml_ir_v0.1"
}
```

---

## Scientific grounding

- **FlavorDB2** — 25,595 flavor molecules with PubChem IDs and receptor associations
- **Ahn et al. 2011** — "Flavor network and the principles of food pairing" (Sci. Reports)
- **FlavorGraph 2021** — Heterogeneous food-chemical graph with learned embeddings
- **FoodOn** — OWL-based food ontology for ingredient canonicalization
- **geometric-gastronomy** — Mathematical structure of flavor space (Bond, SJSU)

---

## Tests

```bash
pytest tests/ -v
```

---

## Related

- [ahb-sjsu/erisml-compiler](https://github.com/ahb-sjsu/erisml-compiler)
- [ahb-sjsu/erisml-lib](https://github.com/ahb-sjsu/erisml-lib)
- [ahb-sjsu/geometric-gastronomy](https://github.com/ahb-sjsu/geometric-gastronomy)

---

MIT License — Andrew H. Bond
