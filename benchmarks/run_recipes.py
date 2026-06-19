"""Evaluate the harmony verdict against human recipe ratings.

For each graded recipe it:
  1. compiles the dish description  (``compile_document(text)``),
  2. reads the compiler's harmony signal, and
  3. checks — across the whole set — whether higher compiler harmony goes with
     higher human ratings, via Spearman rank correlation.

Two compiler signals are reported:
  * mean projection score  — average of the four projection scores (-1..1)
  * verdict confidence     — the harmony_verdict.confidence (0..1)

Usage:
    python -m benchmarks.run_recipes                    # bundled sample
    python -m benchmarks.run_recipes --data graded.csv  # your data
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gastronomyml_compiler.pipeline.orchestrator import compile_document

from .datasets import SAMPLE_RECIPES, load_recipes
from .metrics import spearman, strength


def _mean_projection_score(ir) -> float:
    scores = [pr.score for pr in ir.projections.values()]
    return sum(scores) / len(scores) if scores else 0.0


def run(csv_path: Path, limit: int | None) -> int:
    recipes = load_recipes(csv_path)
    if limit:
        recipes = recipes[:limit]
    if not recipes:
        print("No recipes found in", csv_path)
        return 1

    ratings: list[float] = []
    mean_scores: list[float] = []
    confidences: list[float] = []

    ok, failed = 0, 0
    for r in recipes:
        try:
            ir = compile_document(r.text)
        except Exception as exc:
            print(f"  ! compile failed: {exc}", file=sys.stderr)
            failed += 1
            continue
        ok += 1
        ratings.append(r.rating)
        mean_scores.append(_mean_projection_score(ir))
        confidences.append(ir.harmony_verdict.confidence if ir.harmony_verdict else 0.0)

    print()
    print(f"Compiled {ok} recipes ({failed} failed) from {csv_path.name}")
    print("=" * 60)
    print(f"{'compiler signal':<26}{'n':>4}  {'Spearman':>9}  strength")
    print("-" * 60)
    for label, series in (("mean projection score", mean_scores),
                          ("verdict confidence", confidences)):
        r = spearman(series, ratings) if len(series) >= 2 else float("nan")
        rtxt = f"{r:+.3f}" if r == r else "   n/a"
        print(f"{label:<26}{len(series):>4}  {rtxt:>9}  {strength(r)}")
    print("=" * 60)
    print("(Positive = compiler harmony agrees with human ratings.)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate harmony verdict vs human recipe ratings.")
    p.add_argument("--data", type=Path, default=None,
                   help="CSV with columns text,rating. Omit to use the bundled sample.")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args(argv)

    if args.data is None:
        csv_path = SAMPLE_RECIPES
        print("NOTE: using the bundled SAMPLE recipes (10 rows).")
        print("      Numbers are a smoke test - pass --data <graded.csv> for real results.")
    else:
        csv_path = args.data
        if not csv_path.exists():
            print(f"Data file not found: {csv_path}", file=sys.stderr)
            return 1

    return run(csv_path, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
