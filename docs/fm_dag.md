# FM-DAG: Nine-Module Flavor Evaluator

`src/gastronomyml_compiler/fm_dag/`

The FM-DAG (Flavor Module directed acyclic graph) evaluates the nine canonical flavor dimensions in topological dependency order and writes the aggregate `FlavorVector` into `ir.aggregate_flavor_vector` during Pass 8 of the 13-pass pipeline. Each module is a `FlavorModule` subclass in `fm_dag/modules/`.

---

## Why a topological order?

Flavor perception is not independent across dimensions. Fat suppresses bitterness because lipids bind bitter-tasting polyphenols and reduce their availability at taste receptors. Umami amplifies saltiness because glutamate lowers the detection threshold for sodium chloride. Heat from capsaicin is subjectively tamed by fat. These are documented physiological interactions, not heuristics invented for this compiler.

A flat average of ingredient scores, applied without order, cannot model these interactions: it would compute fat and bitterness simultaneously and have nowhere to put the suppression relationship. A topological module graph executes `FatFM` before `BitterFM`, writes the fat context into a shared state dict, and lets `BitterFM` read from it. The interaction is modelled at the right place in the computation graph.

---

## Execution order

```
┌──────────┐   ┌──────────┐
│  FatFM   │   │ UmamiFM  │   (roots — no upstream dependencies)
└────┬─────┘   └────┬─────┘
     │              │
     ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ BitterFM │   │ SaltyFM  │   │ SourFM   │   │ SweetFM  │   │  HeatFM  │
│ (fat dep)│   │(umami dep│   │          │   │          │   │ (fat dep)│
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
                                   │
                    ───────────────┴───────────────
                    │                             │
                    ▼                             ▼
              ┌──────────┐                 ┌──────────┐
              │AromaticFM│                 │TextureFM │
              │(technique│                 │(technique│
              │  context)│                 │  context)│
              └──────────┘                 └──────────┘
```

`_MODULE_ORDER` in `fm_dag/dag.py`:

```python
_MODULE_ORDER = [FatFM, UmamiFM, SweetFM, SaltyFM, SourFM, BitterFM, HeatFM, AromaticFM, TextureFM]
```

`FMDAG.evaluate(ir)` runs each module in sequence. Each module receives the `GastronomyIR` and a mutable `context: dict[str, float]` that accumulates intermediate dimension scores for downstream modules to read.

---

## Module specifications

### FatFM (k=5)

**Dimension**: fat (richness, lubricity, lipid content)

**Logic**:
1. Collect per-ingredient fat scores.
2. Technique adjustment: `FRYING`, `CONFITING`, and `EMULSIFICATION` each add 0.1 to the aggregate, capped at 1.0.
3. Write `context["fat"]` for downstream modules.

**Writes to context**: `fat`

**Why first**: fat is a perceptual modifier for bitterness and heat. `BitterFM` and `HeatFM` both read from `context["fat"]`.

---

### UmamiFM (k=4)

**Dimension**: umami (savory depth, glutamate content)

**Logic**:
1. Collect per-ingredient umami scores.
2. Synergy detection: if `ir.flavor_facts` contains a `FlavorFactKind.UMAMI_SYNERGY` entry, apply a 1.4× multiplier to the aggregate umami score. The extractor sets this fact when a glutamate-rich ingredient (miso, parmesan, tomato, mushroom, soy sauce, fish sauce, marmite) co-occurs with an inosinate-rich ingredient (duck, chicken, pork, beef, tuna, anchovy, salmon, sardine, shrimp).
3. Write `context["umami"]` for `SaltyFM`.

**Synergy motivation**: the inosinate-glutamate combination is among the most-studied interactions in flavor chemistry. Ninomiya (2002) documents up to 8× perceptual amplification of umami intensity when both nucleotides are co-presented. The 1.4× multiplier used here is conservative relative to that upper bound; it models the typical in-dish effect rather than an isolated receptor experiment.

**Writes to context**: `umami`

---

### SweetFM (k=0)

**Dimension**: sweet (sucrose equivalents, reducing sugars)

**Logic**:
1. Collect per-ingredient sweet scores.
2. Caramelization reduction: for each ingredient that has a `CARAMELIZATION` technique applied to it, reduce the sweet contribution of that ingredient by 15%, modelling the conversion of sucrose into more complex, slightly bitter caramel compounds.

**Reads from context**: none (second tier but no fat/umami dependency)

---

### SaltyFM (k=1)

**Dimension**: salty (NaCl equivalents, mineral)

**Logic**:
1. Collect per-ingredient salty scores.
2. Umami amplification: `adjusted = base × (1.0 + 0.1 × context["umami"])`. High-umami context lowers the effective threshold for saltiness perception.

**Reads from context**: `umami`

---

### SourFM (k=2)

**Dimension**: sour (acidity, titratable acid)

**Logic**:
1. Collect per-ingredient sour scores.
2. Fermentation bonus: for each `FERMENTATION` technique present, add 0.15 to the aggregate, capped at 1.0. Fermentation produces lactic acid, acetic acid, and other organic acids.

**Reads from context**: none

---

### BitterFM (k=3)

**Dimension**: bitter (polyphenols, alkaloids, tannins)

**Logic**:
1. Collect per-ingredient bitter scores.
2. Fat suppression: `adjusted = base × max(0.5, 1.0 − 0.3 × context["fat"])`. Fat suppresses perceived bitterness by binding bitter compounds. The `max(0.5, ...)` floor prevents fat from completely eliminating bitterness in a high-fat dish.

**Reads from context**: `fat`

---

### HeatFM (k=6)

**Dimension**: heat (capsaicin / pungency units, allicin)

**Logic**:
1. Collect per-ingredient heat scores.
2. Fat modulation: `adjusted = base × max(0.6, 1.0 − 0.2 × context["fat"])`. Fat dissolves capsaicin (a lipophilic molecule), reducing its effective concentration at mucous membranes. The `max(0.6, ...)` floor ensures that a very high-fat dish retains most of its perceived heat, since the dish's vehicle is itself present in the mouth.

**Reads from context**: `fat`

---

### AromaticFM (k=7)

**Dimension**: aromatic (volatile compound complexity)

**Logic**:
1. Collect per-ingredient aromatic scores.
2. Maillard/roasting bonus: for each technique of type `MAILLARD`, `ROASTING`, `GRILLING`, or `SMOKING`, add 0.1, capped at total bonus of 0.3. These reactions generate hundreds of new volatile aromatic compounds not present in the raw ingredients.

**Reads from context**: technique types (read directly from `ir.techniques`, not from the context dict)

---

### TextureFM (k=8)

**Dimension**: texture (mouthfeel, body, viscosity)

**Logic**:
1. Collect per-ingredient texture scores.
2. Technique bonuses:
   - `FRYING` or `GRILLING` (crisp-developing techniques): +0.2
   - `BRAISING`, `POACHING`, or `STEAMING` (soft-developing techniques): +0.15
   - `EMULSIFICATION`: +0.2 (creates stable fat-water dispersions with distinct mouthfeel)
   - All bonuses are capped together at +0.3 total.

**Reads from context**: technique types (read directly from `ir.techniques`)

---

## FlavorVector output format

Each module writes one `DimensionScore` into the aggregate `FlavorVector`:

```python
class DimensionScore(BaseModel):
    value:       float   # ∈ [-1, 1], final adjusted score
    confidence:  float   # ∈ [0, 1], mean of per-ingredient confidences
    direction:   Literal["dominant", "present", "trace", "absent"]
    explanation: str | None  # summary of key interactions applied
```

Direction thresholds applied by `_direction(v: float)`:

| Threshold | Label |
|---|---|
| `v ≥ 0.65` | `dominant` |
| `v ≥ 0.35` | `present` |
| `v ≥ 0.10` | `trace` |
| `v < 0.10` | `absent` |

The nine `DimensionScore` objects are assembled into a `FlavorVector` (fields: `sweet`, `salty`, `sour`, `bitter`, `umami`, `fat`, `heat`, `aromatic`, `texture`) and written to `ir.aggregate_flavor_vector`.

---

## Context dict contract

| Key | Written by | Read by |
|---|---|---|
| `"fat"` | `FatFM` | `BitterFM`, `HeatFM` |
| `"umami"` | `UmamiFM` | `SaltyFM` |

No other keys are used. Modules that don't need context ignore the dict. Adding a new interaction (e.g. acidity → aromatics) requires only: (a) the upstream module writes a new key, (b) the downstream module reads it, (c) the execution order is adjusted if needed.

---

## Adding a new flavor module

1. Create `fm_dag/modules/my_module.py` with a class that inherits from `FlavorModule` and implements `evaluate(ir, context) -> DimensionScore`.
2. Add the class to `_MODULE_ORDER` in `fm_dag/dag.py` at the correct topological position.
3. If the module reads a context key that doesn't exist yet, add that key to the contract table above and ensure the writer runs first.
4. Add a test in `tests/test_fm_dag.py`.

The module doesn't need to register itself — `FMDAG.evaluate` iterates `_MODULE_ORDER` directly.
