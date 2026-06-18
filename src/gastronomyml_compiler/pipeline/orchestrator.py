"""13-pass GastronomyML compiler pipeline.

Analogous to ErisML pipeline/orchestrator.py.  Each pass is numbered to match
the ErisML spec structure for easy cross-reference.

Pass  0 — Ingestion
Pass  1 — Segmentation
Pass  2 — Ingredient extraction
Pass  3 — Technique extraction
Pass  4 — Pairing extraction
Pass  5 — Context / dietary extraction
Pass  6 — Flavor fact extraction
Pass  7 — Canonicalization
Pass  7.5 — FlavorGraph synthesis
Pass  8 — FlavorVector construction (FM-DAG)
Pass  9 — GastronomyML codegen (IR finalisation)
Pass 10 — Projection evaluation
Pass 11 — Harmony verdict
Pass 12 — Audit & artifact
"""

from __future__ import annotations

from pathlib import Path

from ..annotation.base import ExtractorResult
from ..annotation.mock_extractor import MockExtractor
from ..annotation.rule_extractor import RuleExtractor
from ..audit.hash_chain import build_audit
from ..canonicalizer.registry import IngredientRegistry
from ..fm_dag.dag import FMDAG
from ..ingestion.text_loader import load_text
from ..ir.graph.promote import graph_from_ir
from ..ir.schemas import (
    AuditRecord,
    Document,
    GastronomyIR,
    HarmonyVerdict,
    HarmonyVerdictLabel,
    PassRecord,
    ProjectionResult,
)
from ..projections import PROJECTION_REGISTRY
from ..segmentation.segmenter import segment_text
from ..tiers import ALL_PROJECTIONS, CompilerTier


def compile_document(
    source: str | Path,
    *,
    extractor: CompilerTier = CompilerTier.RULE,
    projections: list[str] | None = None,
    title: str | None = None,
) -> GastronomyIR:
    """Compile a natural-language culinary description into a GastronomyIR.

    Parameters
    ----------
    source:
        File path or raw text of the dish description.
    extractor:
        Extraction tier — ``rule`` (default), ``mock``, or ``llm``.
    projections:
        List of projection IDs to run at compile time.  Pass ``None`` to run
        all four.  Available: ``flavor_similarity``, ``flavor_contrast``,
        ``cultural_harmony``, ``nutritional_balance``.
    title:
        Optional document title override.
    """
    if projections is None:
        projections = ALL_PROJECTIONS
    else:
        unknown = set(projections) - set(ALL_PROJECTIONS)
        if unknown:
            raise ValueError(f"Unknown projection(s): {unknown}. Available: {ALL_PROJECTIONS}")

    passes: list[PassRecord] = []

    def _pass(n: str, fn, *args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            passes.append(PassRecord(pass_number=len(passes), pass_name=n, status="ok"))
            return result
        except Exception as exc:
            passes.append(PassRecord(pass_number=len(passes), pass_name=n, status="failed", note=str(exc)))
            raise

    # ── Pass 0: Ingestion ────────────────────────────────────────────────
    text, sha256 = _pass("ingestion", load_text, source)

    # ── Pass 1: Segmentation ─────────────────────────────────────────────
    segments = _pass("segmentation", segment_text, text)

    # ── Passes 2–6: Extraction ───────────────────────────────────────────
    _extractor = {
        CompilerTier.RULE: RuleExtractor,
        CompilerTier.MOCK: MockExtractor,
    }.get(extractor, RuleExtractor)()

    result: ExtractorResult = _pass("extraction", _extractor.extract, text)

    # ── Pass 7: Canonicalization ──────────────────────────────────────────
    registry = IngredientRegistry()

    def _canonicalize(res: ExtractorResult) -> ExtractorResult:
        for ing in res.ingredients:
            ing.canonical_name = registry.canonicalize(ing.name)
        return res

    result = _pass("canonicalization", _canonicalize, result)

    # ── Build document ────────────────────────────────────────────────────
    doc_title = title or _infer_title(text)
    doc = Document(
        title=doc_title,
        sha256=sha256,
        cuisine=result.cuisine_hint,
        meal_type=result.meal_type_hint,
        dietary_flags=result.dietary_flags,
    )

    # Assemble partial IR (needed for Pass 7.5 and FM-DAG)
    ir = GastronomyIR(
        document=doc,
        ingredients=result.ingredients,
        techniques=result.techniques,
        recipes=result.recipes,
        pairing_rules=result.pairing_rules,
        flavor_facts=result.flavor_facts,
        segments=segments,
    )

    # ── Pass 7.5: FlavorGraph synthesis ──────────────────────────────────
    graph = _pass("graph_synthesis", graph_from_ir, ir)
    ir.flavor_graph = graph

    # ── Pass 8: FlavorVector construction (FM-DAG) ───────────────────────
    fmdag = FMDAG()
    agg_vector = _pass("fm_dag", fmdag.evaluate, ir)
    ir.aggregate_flavor_vector = agg_vector

    # Per-ingredient vectors already set during extraction; finalise here
    ir.per_ingredient_vectors = {
        ing.id: ing.flavor_vector for ing in ir.ingredients
    }
    passes.append(PassRecord(pass_number=len(passes), pass_name="per_ingredient_vectors", status="ok"))

    # ── Pass 9: Codegen (IR finalisation) ────────────────────────────────
    # Nothing additional needed — IR is fully assembled; pass recorded.
    passes.append(PassRecord(pass_number=len(passes), pass_name="codegen", status="ok"))

    # ── Pass 10: Projection evaluation ───────────────────────────────────
    projection_results: dict[str, ProjectionResult] = {}
    for proj_id in projections:
        proj_cls = PROJECTION_REGISTRY.get(proj_id)
        if proj_cls is None:
            continue
        proj_result = _pass(f"projection:{proj_id}", proj_cls().project, ir)
        projection_results[proj_id] = proj_result

    ir.projections = projection_results

    # Cross-projection disagreement check
    polarities = {pid: r.polarity for pid, r in projection_results.items()}
    distinct = set(polarities.values()) - {"neutral"}
    if len(distinct) > 1:
        ir.cross_projection_disagreement = {
            "verdicts": {pid: r.verdict for pid, r in projection_results.items()},
            "polarities": polarities,
            "note": (
                "Projections disagree on polarity. "
                "The compiler surfaces all verdicts; choosing is the caller's responsibility."
            ),
        }

    # ── Pass 11: Harmony verdict ──────────────────────────────────────────
    verdict = _pass("harmony_verdict", _aggregate_verdict, projection_results)
    ir.harmony_verdict = verdict

    # ── Pass 12: Audit ────────────────────────────────────────────────────
    audit = build_audit(
        pass_records=passes,
        extractor_tier=extractor.value,
        active_projections=projections,
        graph_hash=graph.graph_hash if graph else None,
        input_sha256=sha256,
    )
    ir.audit = audit

    return ir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:80]
    return "Untitled Dish"


def _aggregate_verdict(
    projections: dict[str, ProjectionResult],
) -> HarmonyVerdict:
    if not projections:
        return HarmonyVerdict(
            verdict=HarmonyVerdictLabel.NEUTRAL,
            confidence=0.0,
            explanation="No projections run.",
        )

    polarity_votes: dict[str, int] = {"harmonious": 0, "neutral": 0, "discordant": 0}
    scores: list[float] = []

    for r in projections.values():
        polarity_votes[r.polarity] += 1
        scores.append(r.score)

    avg_score = sum(scores) / len(scores)
    dominant_polarity = max(polarity_votes, key=lambda k: polarity_votes[k])

    # Determine if projections conflict
    non_neutral = {p for p, c in polarity_votes.items() if c > 0 and p != "neutral"}
    if len(non_neutral) > 1:
        label = HarmonyVerdictLabel.PROJECTION_CONFLICT
        confidence = 0.4
        explanation = (
            "Projections disagree: "
            + "; ".join(f"{pid}={r.verdict}" for pid, r in projections.items())
        )
    elif dominant_polarity == "harmonious":
        label = (
            HarmonyVerdictLabel.HARMONIOUS
            if avg_score >= 0.5
            else HarmonyVerdictLabel.COMPLEMENTARY
        )
        confidence = min(0.95, 0.5 + avg_score * 0.5)
        explanation = (
            f"Majority of projections indicate harmony (avg score={avg_score:.2f}). "
            + _best_finding(projections)
        )
    elif dominant_polarity == "discordant":
        label = HarmonyVerdictLabel.DISCORDANT
        confidence = min(0.9, 0.5 + abs(avg_score) * 0.5)
        explanation = (
            f"Majority of projections indicate discord (avg score={avg_score:.2f}). "
            + _worst_finding(projections)
        )
    else:
        label = HarmonyVerdictLabel.NEUTRAL
        confidence = 0.5
        explanation = "Projections are neutral or mixed."

    dominant_proj = max(projections, key=lambda k: abs(projections[k].score))
    return HarmonyVerdict(
        verdict=label,
        confidence=round(confidence, 3),
        explanation=explanation,
        dominant_projection=dominant_proj,
    )


def _best_finding(projections: dict[str, ProjectionResult]) -> str:
    best = max(projections.values(), key=lambda r: r.score)
    return f"Best projection: {best.projection_id} → {best.verdict}."


def _worst_finding(projections: dict[str, ProjectionResult]) -> str:
    worst = min(projections.values(), key=lambda r: r.score)
    return f"Lowest projection: {worst.projection_id} → {worst.verdict}."
