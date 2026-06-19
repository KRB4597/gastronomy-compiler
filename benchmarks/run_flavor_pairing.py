"""Test flavor_similarity against the Ahn et al. food-pairing principle.

Ahn et al. (2011) showed that whether two ingredients "go together" relates to
how many flavor compounds they share. This compiler's ``flavor_similarity``
projection estimates pairing affinity from taste-vector cosine similarity — a
*proxy* for shared chemistry, not the chemistry itself. This benchmark asks:
does that proxy actually track real shared-compound counts?

For each ingredient pair it compiles a minimal two-ingredient "dish", reads the
``flavor_similarity`` projection score, and correlates it (Spearman) against the
human/database shared-compound count.

Usage:
    python -m benchmarks.run_flavor_pairing                  # bundled sample
    python -m benchmarks.run_flavor_pairing --data pairs.csv # FlavorDB-derived
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gastronomyml_compiler.pipeline.orchestrator import compile_document

from .datasets import SAMPLE_FLAVOR_PAIRS, load_flavor_pairs
from .metrics import spearman, strength


def _similarity_score(ir) -> float | None:
    pr = ir.projections.get("flavor_similarity")
    return pr.score if pr is not None else None


def run(csv_path: Path, limit: int | None) -> int:
    pairs = load_flavor_pairs(csv_path)
    if limit:
        pairs = pairs[:limit]
    if not pairs:
        print("No pairs found in", csv_path)
        return 1

    shared: list[float] = []
    sim: list[float] = []
    ok, skipped = 0, 0
    rows = []
    for p in pairs:
        text = f"A dish of {p.a} and {p.b}."
        try:
            ir = compile_document(text, projections=["flavor_similarity"])
        except Exception as exc:
            print(f"  ! compile failed for {p.a}+{p.b}: {exc}", file=sys.stderr)
            skipped += 1
            continue
        score = _similarity_score(ir)
        n_ing = len(ir.ingredients)
        if score is None or n_ing < 2:
            # Could not recognise both ingredients → no real similarity to score.
            print(f"  ~ skipped {p.a}+{p.b} (recognised {n_ing} ingredient(s))",
                  file=sys.stderr)
            skipped += 1
            continue
        ok += 1
        shared.append(p.shared_compounds)
        sim.append(score)
        rows.append((p.a, p.b, p.shared_compounds, score))

    print()
    print(f"Scored {ok} pairs ({skipped} skipped) from {csv_path.name}")
    print("=" * 60)
    print(f"{'pair':<28}{'shared':>8}{'similarity':>12}")
    print("-" * 60)
    for a, b, sh, sc in rows:
        print(f"{(a + ' + ' + b):<28}{sh:>8.0f}{sc:>12.3f}")
    print("-" * 60)
    r = spearman(sim, shared) if len(sim) >= 2 else float("nan")
    rtxt = f"{r:+.3f}" if r == r else "n/a"
    print(f"Spearman(similarity, shared_compounds) = {rtxt}  [{strength(r)}]")
    print("=" * 60)
    print("(Positive = the taste-vector proxy tracks real shared chemistry.)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Test flavor_similarity vs shared flavor compounds.")
    p.add_argument("--data", type=Path, default=None,
                   help="CSV: ingredient_a,ingredient_b,shared_compounds. Omit for bundled sample.")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)

    if args.data is None:
        csv_path = SAMPLE_FLAVOR_PAIRS
        print("NOTE: using the bundled SAMPLE pairs (10 rows, illustrative counts).")
        print("      Pass --data <pairs.csv> derived from FlavorDB for real results.")
    else:
        csv_path = args.data
        if not csv_path.exists():
            print(f"Data file not found: {csv_path}", file=sys.stderr)
            return 1

    return run(csv_path, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
