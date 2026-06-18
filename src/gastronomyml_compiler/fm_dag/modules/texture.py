from ...ir.schemas import DimensionScore, GastronomyIR, TechniqueType, _direction
from ..base import FlavorModule

_CRISP_TECHS = {TechniqueType.FRYING, TechniqueType.ROASTING, TechniqueType.GRILLING}
_SOFT_TECHS = {TechniqueType.BRAISING, TechniqueType.CONFITING, TechniqueType.POACHING}


class TextureFM(FlavorModule):
    """Mouthfeel and body.  Frying → crispness; braising → silky; emulsification → creamy."""

    dimension = "texture"

    def score(self, ir: GastronomyIR) -> DimensionScore:
        values = [i.flavor_vector.texture.value for i in ir.ingredients]
        base = sum(values) / len(values) if values else 0.0

        crisp = any(t.technique_type in _CRISP_TECHS for t in ir.techniques)
        soft = any(t.technique_type in _SOFT_TECHS for t in ir.techniques)
        emulsify = any(t.technique_type == TechniqueType.EMULSIFICATION for t in ir.techniques)

        if crisp:
            base = min(1.0, base + 0.2)
        if soft:
            base = min(1.0, base + 0.15)
        if emulsify:
            base = min(1.0, base + 0.2)

        v = max(-1.0, min(1.0, base))
        note = ", ".join(filter(None, [
            "crisp" if crisp else None,
            "silky" if soft else None,
            "creamy" if emulsify else None,
        ])) or "neutral"
        return DimensionScore(
            value=v,
            confidence=0.7,
            direction=_direction(v),
            explanation=f"Texture: {note}",
        )
