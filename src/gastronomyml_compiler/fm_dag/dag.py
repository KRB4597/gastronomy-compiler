"""FM-DAG orchestrator — runs all 9 flavor modules in dependency order.

Analogous to ErisML EMDAG.  Produces the aggregate FlavorVector for the dish.
"""

from __future__ import annotations

from ..ir.schemas import FLAVOR_DIMENSIONS, FlavorVector, GastronomyIR
from .modules import (
    AromaticFM,
    BitterFM,
    FatFM,
    HeatFM,
    SaltyFM,
    SourFM,
    SweetFM,
    TextureFM,
    UmamiFM,
)

# Topological order: fat/umami must run before bitter/heat (they modulate each other)
_MODULE_ORDER = [
    FatFM,      # k=5 — runs first; fat modulates bitter + heat
    UmamiFM,    # k=4 — depends on flavor_facts (synergy)
    SweetFM,    # k=0
    SaltyFM,    # k=1 — uses umami context
    SourFM,     # k=2
    BitterFM,   # k=3 — uses fat context
    HeatFM,     # k=6 — uses fat context
    AromaticFM, # k=7 — uses technique context
    TextureFM,  # k=8 — uses technique context
]


class FMDAG:
    """Run all flavor modules and aggregate into a FlavorVector."""

    def __init__(self) -> None:
        self._modules = [cls() for cls in _MODULE_ORDER]

    def evaluate(self, ir: GastronomyIR) -> FlavorVector:
        scores = {}
        for module in self._modules:
            scores[module.dimension] = module.score(ir)

        return FlavorVector(
            sweet=scores["sweet"],
            salty=scores["salty"],
            sour=scores["sour"],
            bitter=scores["bitter"],
            umami=scores["umami"],
            fat=scores["fat"],
            heat=scores["heat"],
            aromatic=scores["aromatic"],
            texture=scores["texture"],
        )
