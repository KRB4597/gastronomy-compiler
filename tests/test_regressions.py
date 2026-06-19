"""Regression tests for bugs that previously shipped green.

Each corresponds to a real defect the original suite did not catch; written to
FAIL on the old (buggy) code and PASS on the fix.
"""
import subprocess
import sys

import pytest

from gastronomyml_compiler.ir.schemas import Document, GastronomyIR, Ingredient
from gastronomyml_compiler.pipeline.orchestrator import compile_document
from gastronomyml_compiler.projections import CulturalHarmonyProjection
from gastronomyml_compiler.tiers import CompilerTier


def _ir(names, cuisine=None):
    return GastronomyIR(
        document=Document(title="t", sha256="x", cuisine=cuisine),
        ingredients=[Ingredient(id=f"i{k}", name=n) for k, n in enumerate(names)],
    )


def test_single_cuisine_dish_is_not_labeled_fusion():
    """A pure Italian dish must NOT be tagged cross-cultural/fusion.

    Bug: any shared pair (e.g. tomato+basil, in both Italian and Mediterranean
    norm sets) flipped is_fusion on, mislabeling single-cuisine dishes.
    """
    r = CulturalHarmonyProjection().project(
        _ir(["tomato", "basil", "parmesan", "pasta", "garlic", "olive oil"], cuisine="italian")
    )
    assert r.verdict != "cross_cultural_harmony"
    assert "fusion" not in (r.explanation or "").lower()


def test_genuine_fusion_still_detected():
    """A real cross-tradition dish should still be flagged as fusion."""
    r = CulturalHarmonyProjection().project(
        _ir(["miso", "pork", "parmesan", "basil", "tomato"])
    )
    assert r.verdict == "cross_cultural_harmony"


def test_empty_dish_cultural_harmony_does_not_crash():
    r = CulturalHarmonyProjection().project(_ir([]))
    assert -1.0 <= r.score <= 1.0


def test_cli_runs_as_module():
    """`python -m gastronomyml_compiler.cli` must actually run.

    Bug: missing `if __name__ == '__main__': app()` guard.
    """
    out = subprocess.run(
        [sys.executable, "-m", "gastronomyml_compiler.cli", "version"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert "gastronomyml" in out.stdout.lower()


def test_no_llm_tier_advertised():
    """The unimplemented LLM tier was removed from CompilerTier."""
    assert "llm" not in {t.value for t in CompilerTier}


def test_degenerate_input_does_not_crash():
    ir = compile_document("xyzzy nothing here", extractor=CompilerTier.RULE)
    assert ir.harmony_verdict is not None
    assert ir.audit.graph_hash
    for pr in ir.projections.values():
        assert -1.0 <= pr.score <= 1.0
