from ...ir.schemas import DimensionScore, FlavorFactKind, FoodGroup, GastronomyIR, _direction
from ..base import FlavorModule


class UmamiFM(FlavorModule):
    """Glutamate + inosinate synergy is the key insight: up to 8× amplification."""

    dimension = "umami"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.umami.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # Check for umami synergy fact (glutamate + inosinate)
        synergy = any(
            ff.fact_kind == FlavorFactKind.UMAMI_SYNERGY for ff in ir.flavor_facts
        )
        if synergy:
            # Synergy boosts perceived umami significantly
            base = min(1.0, base * 1.4)

        v = max(-1.0, min(1.0, base))
        return DimensionScore(
            value=v,
            confidence=0.85 if synergy else 0.7,
            direction=_direction(v),
            explanation=(
                "Glutamate+inosinate synergy detected — umami amplified"
                if synergy
                else f"Aggregate umami from {len(values)} ingredient(s)"
            ),
        )
