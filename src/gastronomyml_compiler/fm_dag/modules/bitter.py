from ...ir.schemas import DimensionScore, GastronomyIR, _direction
from ..base import FlavorModule


class BitterFM(FlavorModule):
    dimension = "bitter"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.bitter.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # Fat suppresses perceived bitterness (fat carries bitter compounds away)
        fat_avg = sum(i.flavor_vector.fat.value for i in ir.ingredients) / len(ir.ingredients)
        adjusted = base * max(0.5, 1.0 - 0.3 * fat_avg)

        v = max(-1.0, min(1.0, adjusted))
        return DimensionScore(
            value=v,
            confidence=0.7,
            direction=_direction(v),
            explanation=f"Aggregate bitter; fat suppression factor={max(0.5, 1.0 - 0.3 * fat_avg):.2f}",
        )
