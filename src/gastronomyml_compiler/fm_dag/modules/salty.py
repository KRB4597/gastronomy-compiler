from ...ir.schemas import DimensionScore, GastronomyIR, _direction
from ..base import FlavorModule


class SaltyFM(FlavorModule):
    dimension = "salty"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.salty.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        # Saltiness is amplified by umami-rich ingredients
        umami_avg = sum(i.flavor_vector.umami.value for i in ir.ingredients) / len(ir.ingredients)
        base = sum(values) / len(values)
        # High umami context makes salt perception more efficient
        adjusted = base * (1.0 + 0.1 * umami_avg)
        v = max(-1.0, min(1.0, adjusted))
        return DimensionScore(
            value=v,
            confidence=0.8,
            direction=_direction(v),
            explanation=f"Aggregate salt; umami context amplifier={1.0 + 0.1 * umami_avg:.2f}",
        )
