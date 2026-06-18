"""FlavorSimilarity projection — Ahn et al. shared-compound principle.

Ingredients sharing volatile flavor compounds pair well (Western cuisines).
Implemented as cosine similarity on the 9-dim flavor vectors.
"""

from __future__ import annotations

import math

from ..ir.schemas import (
    FLAVOR_DIMENSIONS,
    GastronomyIR,
    Ingredient,
    PairingFinding,
    ProjectionResult,
)
from .base import BaseProjection


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class FlavorSimilarityProjection(BaseProjection):
    """Grounded in Ahn et al. 2011 / FlavorGraph flavor-compound sharing."""

    projection_id = "flavor_similarity"

    def project(self, ir: GastronomyIR) -> ProjectionResult:
        ingredients = ir.ingredients
        if len(ingredients) < 2:
            return ProjectionResult(
                projection_id=self.projection_id,
                verdict="insufficient_ingredients",
                polarity="neutral",
                score=0.0,
                explanation="Fewer than 2 ingredients — cannot assess pairings",
            )

        findings: list[PairingFinding] = []
        pair_scores: list[float] = []

        for i in range(len(ingredients)):
            for j in range(i + 1, len(ingredients)):
                a, b = ingredients[i], ingredients[j]
                vec_a = a.flavor_vector.to_array()
                vec_b = b.flavor_vector.to_array()
                sim = _cosine(vec_a, vec_b)
                pair_scores.append(sim)

                label = (
                    "high_compound_sharing"
                    if sim >= 0.7
                    else "moderate_sharing"
                    if sim >= 0.4
                    else "low_compound_sharing"
                )
                findings.append(PairingFinding(
                    ingredient_ids=[a.id, b.id],
                    finding_type=label,
                    score=sim,
                    explanation=f"{a.name} ↔ {b.name}: cosine={sim:.2f}",
                ))

        avg = sum(pair_scores) / len(pair_scores)

        if avg >= 0.6:
            verdict = "harmonious_by_compound_sharing"
            polarity = "harmonious"
        elif avg >= 0.35:
            verdict = "moderate_compound_affinity"
            polarity = "harmonious"
        elif avg >= 0.15:
            verdict = "diverse_flavor_profile"
            polarity = "neutral"
        else:
            verdict = "low_compound_overlap"
            polarity = "neutral"

        return ProjectionResult(
            projection_id=self.projection_id,
            verdict=verdict,
            polarity=polarity,
            findings=findings,
            score=round(avg, 3),
            explanation=(
                f"Average pairwise cosine similarity={avg:.2f} across "
                f"{len(findings)} ingredient pair(s). "
                "High similarity indicates shared volatile compounds (Western pairing principle)."
            ),
        )
