"""Lightweight correlation statistics — pure Python, no third-party deps.

Why pure Python?  So the benchmark harness adds *zero* new dependencies to the
project.  These three functions are all the eval layer needs.

The key metric is **Spearman rank correlation** (`spearman`): it measures
whether two quantities move together in the same *order*, ignoring their
absolute scales.  That is exactly what we want when comparing a compiler score
(say, 0..1) against a human rating (say, 1..5) — we don't care that the scales
differ, only whether pictures the compiler calls "more balanced" are also the
ones humans called "more balanced".

Interpreting a Spearman value `r`:
    r ≈  1.0   perfect agreement in ranking
    r ≈  0.0   no relationship
    r ≈ -1.0   perfectly reversed (a red flag — likely an inverted sign)
A rough field convention: |r| < 0.1 negligible, 0.1–0.3 weak, 0.3–0.5 moderate,
> 0.5 strong.
"""
from __future__ import annotations

import math
from typing import Sequence


def _ranks(xs: Sequence[float]) -> list[float]:
    """Return 1-based ranks of ``xs``, averaging ranks within tie groups."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # +1 → 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson linear correlation coefficient.  NaN if undefined."""
    n = len(x)
    if n < 2 or n != len(y):
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0.0 or dy == 0.0:
        return float("nan")
    return num / (dx * dy)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman rank correlation = Pearson correlation of the ranks."""
    if len(x) < 2 or len(x) != len(y):
        return float("nan")
    return pearson(_ranks(x), _ranks(y))


def mae(x: Sequence[float], y: Sequence[float]) -> float:
    """Mean absolute error between two equally-scaled series."""
    if not x or len(x) != len(y):
        return float("nan")
    return sum(abs(a - b) for a, b in zip(x, y)) / len(x)


def strength(r: float) -> str:
    """Human-readable label for a correlation magnitude."""
    if r != r:  # NaN
        return "n/a"
    a = abs(r)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "weak"
    if a < 0.5:
        return "moderate"
    return "strong"
