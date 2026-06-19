# Benchmarks — is the compiler actually right about food?

A standalone evaluation layer. It does **not** change the compiler; it measures
it against two kinds of real-world ground truth. Both run out-of-the-box on
bundled sample data (plain-text CSVs in `sample_data/`), and both accept your
own data via `--data`.

The shared metric is **Spearman rank correlation** (see `metrics.py`):
+1 = perfect agreement in ranking, 0 = no relationship, −1 = backwards.

## 1. Harmony verdict vs human ratings — `run_recipes`

> Do dishes the compiler calls "harmonious" match dishes people actually rated
> highly?

```bash
python -m benchmarks.run_recipes                     # bundled sample
python -m benchmarks.run_recipes --data graded.csv   # your data
```

Your CSV needs two columns:

```csv
text,rating
"Miso-braised pork belly ramen with mushroom and nori.",4.7
"Plain boiled lettuce, unseasoned.",1.6
```

`text` is the dish description (exactly what you'd pass to `gastronomy-compile
compile`). `rating` is a human score on any scale. Public sources: the
**Epicurious** and **food.com** recipe datasets (Kaggle) ship recipe text +
user star ratings; **Recipe1M+** can be joined with a ratings table.

It reports two compiler signals correlated against the ratings: the mean
projection score and the harmony-verdict confidence.

## 2. flavor_similarity vs shared compounds — `run_flavor_pairing`

> Ahn et al. (2011): ingredients pair well in proportion to the flavor
> compounds they share. The compiler estimates pairing from taste-vector cosine
> similarity — a *proxy* for that chemistry. Does the proxy hold up?

```bash
python -m benchmarks.run_flavor_pairing                  # bundled sample
python -m benchmarks.run_flavor_pairing --data pairs.csv # FlavorDB-derived
```

Your CSV needs three columns:

```csv
ingredient_a,ingredient_b,shared_compounds
butter,cheese,29
soy sauce,ginger,4
```

`shared_compounds` is the number of flavor molecules the two ingredients have
in common — derivable from **FlavorDB** / **FlavorGraph** ingredient–compound
tables. Only pairs whose *both* ingredients are in the compiler's ingredient
library are scored (others are reported as skipped).

> Heads-up: on the tiny bundled sample this correlation comes out near zero —
> and that is itself informative. Cosine similarity of taste vectors is not the
> same thing as shared volatile chemistry (e.g. `nori`+`mushroom` share few
> compounds but both read as strongly umami, so the proxy rates them similar).
> Run it on real FlavorDB-derived data to see how large the gap actually is.

## Files

| file                    | purpose                                              |
|-------------------------|------------------------------------------------------|
| `metrics.py`            | Spearman / Pearson / MAE in pure Python (no deps).   |
| `datasets.py`           | CSV loaders for both benchmarks.                     |
| `run_recipes.py`        | Harmony verdict vs human ratings.                   |
| `run_flavor_pairing.py` | flavor_similarity vs shared compounds.              |
| `sample_data/`          | Small bundled CSVs so everything runs immediately.   |
