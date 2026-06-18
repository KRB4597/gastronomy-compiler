"""FlavorContrast projection — complementarity principle.

Classic culinary contrast theory: sweet/sour, bitter/fat, acid/richness,
heat/fat.  Also checks for dimensional balance (no single note overwhelming).
"""

from __future__ import annotations

from ..ir.schemas import (
    FLAVOR_DIMENSIONS,
    GastronomyIR,
    PairingFinding,
    ProjectionResult,
)
from .base import BaseProjection

# Pairs that complement each other
_CONTRAST_PAIRS: list[tuple[str, str, float, str]] = [
    ("sweet", "sour",    0.8, "sweet/sour balance — classic counterpoint"),
    ("bitter", "fat",    0.85, "fat suppresses bitterness — tannin mitigation"),
    ("umami", "sour",    0.75, "acid brightens umami depth"),
    ("heat",  "fat",     0.8, "fat carries and tames capsaicin heat"),
    ("salty", "sweet",   0.7, "salt amplifies sweet — salted caramel principle"),
    ("bitter", "sweet",  0.65, "sweet rounds harsh bitterness"),
]

_BALANCE_THRESHOLD = 0.75  # single dimension above this is "dominant"


class FlavorContrastProjection(BaseProjection):
    """Complementary contrast — the classical Western balance theory."""

    projection_id = "flavor_contrast"

    def project(self, ir: GastronomyIR) -> ProjectionResult:
        vec = ir.aggregate_flavor_vector
        findings: list[PairingFinding] = []
        contrast_scores: list[float] = []

        for dim_a, dim_b, weight, explanation in _CONTRAST_PAIRS:
            val_a = abs(getattr(vec, dim_a).value)
            val_b = abs(getattr(vec, dim_b).value)

            if val_a < 0.1 and val_b < 0.1:
                continue  # neither dimension present

            # Contrast quality: both dimensions present and roughly balanced
            presence = min(val_a, val_b)  # how much of the weaker one is present
            balance = 1.0 - abs(val_a - val_b)  # 1 = perfectly balanced
            pair_score = weight * presence * balance

            contrast_scores.append(pair_score)
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type=f"contrast_{dim_a}_{dim_b}",
                score=round(pair_score, 3),
                explanation=f"{explanation} ({dim_a}={val_a:.2f}, {dim_b}={val_b:.2f})",
            ))

        # Dominance check — one overwhelming note without counterbalance
        dominant_dims = vec.dominant_dimensions(threshold=_BALANCE_THRESHOLD)
        for dim in dominant_dims:
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type="dominant_dimension",
                score=-0.2,
                explanation=f"'{dim}' is dominant ({getattr(vec, dim).value:.2f}) — counterbalance recommended",
            ))

        overall = sum(contrast_scores) / len(contrast_scores) if contrast_scores else 0.0
        # Penalise unmitigated dominance
        overall -= 0.15 * len(dominant_dims)
        overall = max(-1.0, min(1.0, overall))

        if overall >= 0.5:
            verdict = "beautifully_balanced"
            polarity = "harmonious"
        elif overall >= 0.25:
            verdict = "well_contrasted"
            polarity = "harmonious"
        elif overall >= 0.05:
            verdict = "partial_contrast"
            polarity = "neutral"
        elif dominant_dims:
            verdict = "one_note_dominant"
            polarity = "discordant"
        else:
            verdict = "flat_profile"
            polarity = "neutral"

        return ProjectionResult(
            projection_id=self.projection_id,
            verdict=verdict,
            polarity=polarity,
            findings=findings,
            score=round(overall, 3),
            explanation=(
                f"Detected {len(contrast_scores)} contrast pair(s); "
                f"{len(dominant_dims)} unmitigated dominant dimension(s). "
                "Score reflects complementarity and balance."
            ),
        )
