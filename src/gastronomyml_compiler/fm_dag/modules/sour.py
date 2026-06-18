from ...ir.schemas import DimensionScore, GastronomyIR, TechniqueType, _direction
from ..base import FlavorModule


class SourFM(FlavorModule):
    dimension = "sour"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.sour.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # Fermentation adds acidity
        ferment = any(t.technique_type == TechniqueType.FERMENTATION for t in ir.techniques)
        if ferment:
            base = min(1.0, base + 0.15)

        v = max(-1.0, min(1.0, base))
        return DimensionScore(
            value=v,
            confidence=0.75,
            direction=_direction(v),
            explanation=f"Aggregate acid; fermentation={'yes' if ferment else 'no'}",
        )
