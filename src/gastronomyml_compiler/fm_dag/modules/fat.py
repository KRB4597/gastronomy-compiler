from ...ir.schemas import DimensionScore, GastronomyIR, TechniqueType, _direction
from ..base import FlavorModule


class FatFM(FlavorModule):
    """Fat carries flavor compounds and lengthens finish."""

    dimension = "fat"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.fat.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # Confit / braising adds fat contribution
        fat_techs = {TechniqueType.CONFITING, TechniqueType.BRAISING, TechniqueType.FRYING}
        if any(t.technique_type in fat_techs for t in ir.techniques):
            base = min(1.0, base + 0.1)

        v = max(-1.0, min(1.0, base))
        return DimensionScore(
            value=v,
            confidence=0.8,
            direction=_direction(v),
            explanation=f"Aggregate fat; technique-augmented={base:.2f}",
        )
