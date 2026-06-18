"""NutritionalBalance projection — macro and food-group coverage.

Checks protein/fat/carb representation, vegetable presence, and flags
problematic macro combinations.  Grounded in USDA FoodData Central food
group classifications.
"""

from __future__ import annotations

from ..ir.schemas import (
    FoodGroup,
    GastronomyIR,
    PairingFinding,
    ProjectionResult,
)
from .base import BaseProjection


class NutritionalBalanceProjection(BaseProjection):
    projection_id = "nutritional_balance"

    def project(self, ir: GastronomyIR) -> ProjectionResult:
        groups = [i.food_group for i in ir.ingredients]
        group_set = set(groups)

        findings: list[PairingFinding] = []
        score = 0.5  # start neutral

        has_protein = any(g in (FoodGroup.PROTEIN, FoodGroup.SEAFOOD) for g in groups)
        has_veg = FoodGroup.VEGETABLE in group_set or FoodGroup.FRUIT in group_set
        has_fat = FoodGroup.FAT in group_set or FoodGroup.DAIRY in group_set
        has_carb = FoodGroup.CARBOHYDRATE in group_set
        fat_count = sum(1 for g in groups if g in (FoodGroup.FAT, FoodGroup.DAIRY))
        carb_count = sum(1 for g in groups if g == FoodGroup.CARBOHYDRATE)

        if has_protein:
            score += 0.1
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type="protein_present",
                score=0.1,
                explanation="Protein source present",
            ))

        if has_veg:
            score += 0.15
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type="vegetable_present",
                score=0.15,
                explanation="Vegetable or fruit present — fibre and micronutrients",
            ))
        else:
            score -= 0.2
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type="lacks_vegetables",
                score=-0.2,
                explanation="No vegetable or fruit detected — micronutrient gap",
            ))

        if has_fat and has_carb and fat_count >= 2 and carb_count >= 2:
            score -= 0.2
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type="high_fat_high_carb",
                score=-0.2,
                explanation="Multiple fat + multiple carb sources — dense macro combination",
            ))

        if has_protein and has_veg and has_fat:
            score += 0.1
            findings.append(PairingFinding(
                ingredient_ids=[],
                finding_type="macro_triangle",
                score=0.1,
                explanation="Protein + vegetable + fat present — complete macro triangle",
            ))

        score = max(-1.0, min(1.0, score))

        if score >= 0.6:
            verdict = "nutritionally_balanced"
            polarity = "harmonious"
        elif score >= 0.3:
            verdict = "reasonable_balance"
            polarity = "harmonious"
        elif not has_veg and fat_count >= 2:
            verdict = "fat_heavy_no_greens"
            polarity = "discordant"
        elif not has_protein:
            verdict = "protein_absent"
            polarity = "neutral"
        else:
            verdict = "partial_balance"
            polarity = "neutral"

        groups_repr = ", ".join(sorted({g.value for g in group_set}))
        return ProjectionResult(
            projection_id=self.projection_id,
            verdict=verdict,
            polarity=polarity,
            findings=findings,
            score=round(score, 3),
            explanation=(
                f"Food groups present: {groups_repr}. "
                f"Protein={'✓' if has_protein else '✗'} "
                f"Veg={'✓' if has_veg else '✗'} "
                f"Fat={'✓' if has_fat else '✗'} "
                f"Carb={'✓' if has_carb else '✗'}"
            ),
        )
