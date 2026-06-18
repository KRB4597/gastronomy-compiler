---
title: 'gastronomy-compiler: a structure-preserving flavor intermediate representation with pluggable culinary projection analysers'

tags:
  - Python
  - computational gastronomy
  - flavor science
  - intermediate representation
  - graph IR
  - food pairing
  - natural language processing

authors:
  - name: Kim R. Baley
    affiliation: 1
  - name: Andrew H. Bond
    orcid: 0009-0009-1769-5099
    affiliation: 2

affiliations:
  - name: Justice Innovations, USA
    index: 1
  - name: San José State University, San José, CA, USA
    index: 2

date: 18 June 2026

bibliography: paper.bib

---

## Summary

`gastronomy-compiler` is a Python compiler that takes natural-language
dish and recipe descriptions and emits a typed directed acyclic graph —
the **FlavorGraph** — anchored by a canonical SHA-256 hash. Four culinary
projection analysers (FlavorSimilarity, FlavorContrast, CulturalHarmony,
and NutritionalBalance) read the same substrate and emit projection-relative
harmony verdicts. When their normalised polarities disagree, the compiler
**refuses to aggregate** and surfaces all verdicts via
`ir.cross_projection_disagreement`, deferring the choice of culinary
framework to the caller. A nine-module **FM-DAG** (Flavor Module directed
acyclic graph) evaluates each of the nine canonical flavor dimensions
(sweet, salty, sour, bitter, umami, fat, heat, aromatic, texture) in
topological dependency order, encoding known perceptual interactions such
as fat-mediated bitterness suppression and the inosinate-glutamate umami
synergy. The rule-based extractor grounds ingredient flavor profiles in
the FlavorDB2 molecular database [@Garg2024] and the geometric model of
flavor space developed in companion work [@Bond2026]. Everything is
auditable: every IR carries hashed provenance for the input text, the
FlavorGraph, and the active projection set.

## Statement of need

Existing computational gastronomy systems almost always collapse flavor
evaluation to a scalar: a cosine similarity between ingredient embedding
vectors [@Ahn2011; @Min2021], a pairing score from a neural recommender
[@Teng2012], or a match percentage from a recipe retrieval engine. This
is defensible engineering — a scalar composes cleanly with ranking and
recommendation pipelines. But it discards the structure that flavor
assessment is *about*.

A chef deciding whether duck and cherry form a harmonious pairing is
simultaneously reasoning about shared volatile compounds (a Western
compound-sharing principle), acid-fat contrast balance (a textural
and perceptual principle), and cultural canon (the classical French
*canard aux cerises*). A scalar "0.82 compatible" cannot represent
that. Worse, scoring across pairings pre-commits to a specific
framework — typically compound-sharing cosine similarity — whose
choices are invisible to the user: the system *looks* framework-neutral
while quietly encoding Ahn et al.'s Western-cuisine hypothesis at every
aggregation step.

`gastronomy-compiler` addresses both problems architecturally.

**Structure preservation**: the IR is a typed graph (nodes are
ingredients, techniques, compounds, pairing axes, and cultural norms;
edges are typed culinary relations such as `pairs_with`,
`contrasts_with`, `enhances`, `masks`, `transforms`, `flavor_bridge`),
not a scalar. The FlavorGraph plays the same role for flavor reasoning
that an SSA-form IR plays for code generation: a structured intermediate
that later passes can analyse, transform, and emit from. The canonical
SHA-256 hash makes every compiled dish reproducible and auditable.

**Projection pluralism**: each culinary framework gets a first-class
`Projection` of its own primitives. The FlavorSimilarity analyser emits
pairwise cosine similarity findings grounded in the Ahn et al. shared-
compound hypothesis. The FlavorContrast analyser emits balance findings
derived from classical Western complementarity theory (sweet/sour,
bitter/fat, acid/richness). The CulturalHarmony analyser emits
tradition-relative findings against hand-curated norm sets for French,
Japanese, Italian, Mediterranean, Indian, and Chinese culinary canons.
The NutritionalBalance analyser emits food-group coverage findings
grounded in USDA FoodData Central classifications [@USDA2024]. When
projections disagree on polarity, the compiler does not pick a winner —
that choice is itself a culinary and philosophical move, and it is
deferred to the caller explicitly.

To our knowledge no other open-source artifact combines (a) a typed
flavor graph IR, (b) multiple culinary framework analysers over a shared
substrate with honest polarity disagreement, and (c) a molecular-level
ingredient library grounded in published flavor chemistry databases.
Adjacent work falls into three buckets: embedding-based similarity
tools that reduce to scalar pairing scores; large recipe corpora
(Recipe1M+, [@Marin2019]) used for training without producing a
verifiable intermediate object; and rule-based expert systems that
encode only one culinary tradition's norms. `gastronomy-compiler`
occupies the structural-compositional gap between these.

The compiler is also designed as the computational counterpart to
*Geometric Gastronomy* [@Bond2026], which develops the mathematical
structure of flavor space — ingredients as vectors in receptor
space, cooking as geometric transformations, pairing as manifold
geometry — but does not itself provide an implementation. This
compiler instantiates that theoretical framework as a runnable,
testable, hash-auditable pipeline.

## Software description

The compiler implements a **13-pass pipeline**. Passes 0–6 ingest text,
segment it, and extract ingredients, cooking techniques, pairing rules,
culinary context, and flavor facts through one of three tiered
extractors: a deterministic mock extractor for testing; a rule-based
extractor (Tier 2, the default production tier) that matches against an
80-entry ingredient flavor-profile library and 25 cooking-technique
transformation rules; or an LLM extractor (Tier 3) for open-vocabulary
descriptions. Pass 7 canonicalises ingredient names against an alias
registry (e.g., *parmigiano-reggiano* → *parmesan*). Pass 7.5 promotes
the flat extractor output into a typed `FlavorGraph`. Pass 8 runs the
FM-DAG over the populated IR to produce the aggregate `FlavorVector`.
Passes 10–11 run the enabled projections and aggregate a harmony verdict.
Pass 12 finalises the audit record.

Five capabilities are first-class:

- **Typed graph IR** (`ir/graph/`). Six node kinds (`ingredient`,
  `technique`, `dish`, `compound`, `pairing_axis`, `norm`) and ten
  edge kinds; canonical SHA-256 hashing; bidirectional derivation
  from the flat extractor output via `graph_from_ir` / `flat_from_graph`.

- **Nine-dimension FM-DAG** (`fm_dag/`). Flavor modules run in
  topological order: `FatFM` and `UmamiFM` execute first because
  later modules (`BitterFM`, `HeatFM`, `SaltyFM`) depend on their
  outputs as perceptual modifiers. `AromaticFM` receives a bonus
  proportional to the number of Maillard and roasting techniques,
  encoding the new volatile compound generation these reactions
  produce. The aggregate `FlavorVector` encodes all nine dimensions
  as signed `DimensionScore` objects in $[-1, 1]$, each carrying
  a confidence, a direction label, and a natural-language explanation.

- **Four compile-time selectable projections** (`projections/`).
  `FlavorSimilarityProjection` computes pairwise cosine similarity
  over the nine-dimensional flavor vectors of all ingredient pairs
  and emits per-pair compound-sharing findings. The Ahn et al.
  hypothesis predicts that pairs with high cosine similarity will
  be perceived as harmonious in Western culinary contexts.
  `FlavorContrastProjection` checks six classical complementarity
  pairs (sweet/sour, bitter/fat, umami/acid, heat/fat, salty/sweet,
  bitter/sweet) and penalises unmitigated dimensional dominance.
  `CulturalHarmonyProjection` detects the dish's primary cuisine
  from ingredient vocabulary and scores it against tradition-specific
  positive and negative norm sets, returning a fusion verdict when
  multiple traditions are simultaneously present.
  `NutritionalBalanceProjection` checks food-group coverage and
  flags the high-fat–high-carb combination as a dense macro signal.
  Any subset of projections may be selected at compile time via the
  `--projection` flag.

- **Umami synergy detection** (`fm_dag/modules/umami.py`). The
  compiler identifies when glutamate-rich ingredients (miso,
  mushroom, parmesan, tomato) co-occur with inosinate-rich
  ingredients (meat, fish), and applies a 1.4× synergy multiplier
  to the aggregate umami score. This encodes the well-documented
  inosinate-glutamate synergism, in which co-presentation amplifies
  perceived umami intensity up to eightfold relative to either
  compound alone [@Ninomiya2002].

- **Cross-projection disagreement surface**. When two or more
  projections emit distinct non-neutral polarities (`harmonious`
  vs. `discordant`), the compiler populates
  `ir.cross_projection_disagreement` with all projection verdicts
  and a note that framework selection is the caller's responsibility.
  The harmony verdict in this case is `projection_conflict` rather
  than a silently aggregated scalar.

The compiler also ships a **Schema.org/Recipe export** (`export/
schema_org.py`) that re-serialises the IR as JSON-LD [@SchemaOrg],
enabling direct integration with recipe platforms and semantic-web
food knowledge graphs such as FoodKG [@Haussmann2019].

## Worked example

On the bundled `duck_confit` scenario, the rule extractor identifies
fourteen ingredients including duck, cherry, butter, garlic, thyme,
lemon, wine, and sugar, and detects five techniques: caramelization,
confit, reduction, sauté, and curing. The cuisine is auto-detected as
`french` from the presence of *confit*, *gastrique*, and *port*.

The FM-DAG produces an aggregate `FlavorVector` with `fat` (dominant,
0.71), `aromatic` (dominant, 0.68), and `umami` (present, 0.53) as the
leading dimensions. The cherry gastrique's caramelization step produces
a small net-sweet reduction (sugar converts to bitter caramel compounds)
alongside a significant aromatic bonus from the Maillard-adjacent
caramelization reaction.

The four projections return:

| Projection | Verdict | Polarity | Score |
|---|---|---|---|
| `flavor_similarity` | `diverse_flavor_profile` | neutral | 0.28 |
| `flavor_contrast` | `partial_contrast` | neutral | 0.06 |
| `cultural_harmony` | `cross_cultural_harmony` | harmonious | 0.88 |
| `nutritional_balance` | `nutritionally_balanced` | harmonious | 0.85 |

The FlavorSimilarity projection correctly identifies that duck confit
is *not* a high-compound-overlap dish: its ingredients span multiple
flavor families, which is characteristic of a composed restaurant dish
rather than a simple pantry pairing. The CulturalHarmony projection
recognizes the duck/cherry, butter/lemon, and wine/mushroom norm
matches simultaneously, producing a `cross_cultural_harmony` verdict
with a high score of 0.88. The compiler emits a `harmonious` harmony
verdict at confidence 0.76 with `cultural_harmony` as the dominant
projection. The full result is reproducible with:

```bash
gastronomy-compile compile examples/duck_confit.txt \
    --projection flavor_similarity,flavor_contrast,cultural_harmony,nutritional_balance \
    --extractor rule
```

## Limitations

The rule extractor's ingredient library covers approximately 80 named
ingredients. Novel, hyphenated, or highly regional ingredient names
outside this vocabulary are silently dropped, reducing extraction
recall. The LLM extractor tier (Tier 3) is scaffolded but not
integrated with a specific model checkpoint; a caller must supply an
OpenAI-compatible endpoint. Cultural norm sets are hand-curated from
classical sources and do not capture regional variation within a
tradition, contemporary fusion norms, or molecular gastronomy
techniques. The nutritional projection uses food-group heuristics
rather than USDA FoodData Central API calls; micronutrient and
caloric density are not modelled. The cosine-similarity flavor vectors
are derived from a static profile library rather than live FlavorDB2
compound data; future work should wire the `flavor_compounds` field
to PubChem IDs and compute similarity directly from shared volatile
compound sets. Each limitation is noted in the relevant module's
docstring.

## Acknowledgements

The geometric model of flavor space on which this compiler's type
system is grounded was developed in *Geometric Gastronomy: The
Mathematical Structure of Flavor, Pairing, and Culinary Harmony*
[@Bond2026] at San José State University. The compiler's pipeline
architecture mirrors that of `erisml-compiler` [@Bond2025], which
established the pattern of typed graph IR, tiered extraction, and
pluralist projection analysers. Flavor profile data was derived
from FlavorDB2 [@Garg2024] and the Ahn et al. flavor network
[@Ahn2011].

## References

(The bibliography is stored separately in paper.bib)
