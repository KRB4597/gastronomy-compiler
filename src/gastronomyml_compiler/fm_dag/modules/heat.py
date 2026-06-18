from ...ir.schemas import DimensionScore, FoodGroup, GastronomyIR, _direction
from ..base import FlavorModule


class HeatFM(FlavorModule):
    """Capsaicin / pungency.  Fat context reduces perceived heat."""

    dimension = "heat"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.heat.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # Fat tames heat perception
        fat_avg = sum(i.flavor_vector.fat.value for i in ir.ingredients) / len(ir.ingredients)
        adjusted = base * max(0.6, 1.0 - 0.2 * fat_avg)

        v = max(-1.0, min(1.0, adjusted))
        return DimensionScore(
            value=v,
            confidence=0.75,
            direction=_direction(v),
            explanation=f"Heat after fat mitigation: {adjusted:.2f}",
        )
