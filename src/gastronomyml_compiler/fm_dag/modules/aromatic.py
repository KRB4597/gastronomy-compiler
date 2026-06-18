from ...ir.schemas import DimensionScore, GastronomyIR, TechniqueType, _direction
from ..base import FlavorModule

_AROMA_TECHS = {
    TechniqueType.MAILLARD,
    TechniqueType.ROASTING,
    TechniqueType.GRILLING,
    TechniqueType.SMOKING,
    TechniqueType.CARAMELIZATION,
    TechniqueType.REDUCTION,
}


class AromaticFM(FlavorModule):
    """Volatile aromatic complexity.  Maillard/roasting generates new compounds."""

    dimension = "aromatic"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.aromatic.value for i in ir.ingredients]
        if not values:
            return DimensionScore(value=0.0, direction="absent")

        base = sum(values) / len(values)

        # High-heat / Maillard techniques generate new aromatic compounds
        aroma_tech_count = sum(
            1 for t in ir.techniques if t.technique_type in _AROMA_TECHS
        )
        bonus = min(0.3, 0.1 * aroma_tech_count)
        adjusted = min(1.0, base + bonus)

        v = max(-1.0, min(1.0, adjusted))
        return DimensionScore(
            value=v,
            confidence=0.75,
            direction=_direction(v),
            explanation=f"Aromatic base={base:.2f} + technique bonus={bonus:.2f}",
        )
