from ...ir.schemas import DimensionScore, FoodGroup, GastronomyIR, TechniqueType, _direction
from ..base import FlavorModule


class SweetFM(FlavorModule):
    dimension = "sweet"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.sweet.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # Caramelization boosts perceived sweetness → then converts to bitter
        caramel_tech = any(
            t.technique_type == TechniqueType.CARAMELIZATION for t in ir.techniques
        )
        if caramel_tech:
            base = max(0.0, base - 0.1)  # sugar converts; net sweetness drops slightly

        v = max(-1.0, min(1.0, base))
        return DimensionScore(
            value=v,
            confidence=0.75,
            direction=_direction(v),
            explanation=f"Aggregate sweet from {len(values)} ingredient(s); caramelization={'yes' if caramel_tech else 'no'}",
        )
