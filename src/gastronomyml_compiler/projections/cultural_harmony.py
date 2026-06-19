"""CulturalHarmony projection — tradition-based pairing norms.

Each cuisine tradition carries its own norm set.  The detected (or declared)
cuisine is scored against its canonical rules.  Fusion dishes get a separate
verdict rather than being penalised.
"""

from __future__ import annotations

from ..ir.schemas import (
    FoodGroup,
    GastronomyIR,
    PairingFinding,
    ProjectionResult,
)
from .base import BaseProjection

# Format: {cuisine: {"positive": [(a, b, score, note)], "negative": [(a, b, score, note)]}}
_NORMS: dict[str, dict] = {
    "french": {
        "positive": [
            ("butter", "thyme",     0.9, "beurre aux herbes — foundational"),
            ("wine",   "mushroom",  0.85, "wine-mushroom affinity"),
            ("duck",   "cherry",    0.9, "canard aux cerises — classic"),
            ("cream",  "mushroom",  0.8, "sauce normande style"),
            ("butter", "lemon",     0.85, "beurre blanc principle"),
            ("lemon",  "fish",      0.8, "acid with fish"),
        ],
        "negative": [
            ("fish", "cheese", -0.7, "traditionally avoided in French cuisine"),
        ],
        "required_groups": [],
    },
    "japanese": {
        "positive": [
            ("miso",      "pork",       0.95, "miso-braised pork — inosinate synergy"),
            ("soy sauce", "ginger",     0.85, "fundamental aromatic bridge"),
            ("miso",      "mushroom",   0.9, "glutamate layering"),
            ("nori",      "rice",       0.8, "foundational composition"),
            ("sesame",    "soy sauce",  0.75, "goma-shoyu"),
            ("scallion",  "soy sauce",  0.75, "negi-shoyu"),
        ],
        "negative": [
            ("dairy", "fish", -0.6, "avoided in traditional Japanese cooking"),
        ],
        "required_groups": [],
    },
    "mediterranean": {
        "positive": [
            ("olive oil", "lemon",   0.95, "foundational dressing"),
            ("garlic",    "lemon",   0.9, "lemon-garlic — classic"),
            ("capers",    "anchovy", 0.85, "puttanesca backbone"),
            ("tomato",    "basil",   0.9, "caprese principle"),
            ("olive oil", "tomato",  0.85, "soffritto base"),
        ],
        "negative": [],
        "required_groups": [],
    },
    "indian": {
        "positive": [
            ("turmeric",    "cumin",      0.9, "spice foundation"),
            ("ginger",      "garlic",     0.9, "adrak-lehsun — aromatic base"),
            ("cumin",       "coriander",  0.85, "dhania-jeera"),
            ("coconut",     "chili",      0.8, "fat tames heat"),
            ("cardamom",    "cream",      0.8, "fat carries sweet aromatics"),
        ],
        "negative": [],
        "required_groups": [],
    },
    "italian": {
        "positive": [
            ("parmesan",  "basil",    0.9, "pesto backbone"),
            ("tomato",    "basil",    0.95, "foundational"),
            ("garlic",    "olive oil", 0.9, "soffritto base"),
            ("anchovies", "capers",   0.85, "puttanesca"),
            ("pasta",     "parmesan", 0.8, "cacio e pepe"),
        ],
        "negative": [
            ("cream", "seafood", -0.5, "cream+seafood is debated in authentic Italian"),
        ],
        "required_groups": [],
    },
    "chinese": {
        "positive": [
            ("soy sauce", "sesame oil",  0.9, "wei-xian base"),
            ("ginger",    "scallion",    0.85, "cong-jiang aromatic base"),
            ("soy sauce", "star anise",  0.8, "master-stock spice"),
        ],
        "negative": [],
        "required_groups": [],
    },
}


class CulturalHarmonyProjection(BaseProjection):
    """Tradition-aware pairing assessment."""

    projection_id = "cultural_harmony"

    def project(self, ir: GastronomyIR) -> ProjectionResult:
        cuisine = ir.document.cuisine
        ing_names = {i.name for i in ir.ingredients}
        ing_groups = {i.food_group for i in ir.ingredients}

        # Detect if dish spans multiple traditions (fusion).
        #
        # A shared/foundational pair (e.g. ("tomato","basil") appears in both the
        # italian and mediterranean norm sets) is NOT evidence of cross-cultural
        # blending — every cuisine that lists it would "match", mislabeling a pure
        # single-cuisine dish as fusion.  So fusion must rest on cuisine-DISTINCTIVE
        # pairs: pairs that belong to exactly one tradition's norm set.
        pair_owner_count: dict[tuple[str, str], int] = {}
        for norms in _NORMS.values():
            for a, b, _, _ in norms["positive"]:
                pair_owner_count[(a, b)] = pair_owner_count.get((a, b), 0) + 1

        # Per cuisine, count matched pairs that are distinctive to it.
        matched_cuisines = []  # (cuisine, distinctive_hits)
        for c, norms in _NORMS.items():
            distinctive_hits = sum(
                1 for a, b, _, _ in norms["positive"]
                if a in ing_names and b in ing_names and pair_owner_count[(a, b)] == 1
            )
            if distinctive_hits > 0:
                matched_cuisines.append((c, distinctive_hits))

        matched_cuisines.sort(key=lambda x: -x[1])
        # Genuine fusion: at least two traditions each carry distinctive evidence,
        # and the runner-up's evidence is comparable to the leader's (a dish that is
        # overwhelmingly one cuisine with a single stray distinctive pair from
        # another is not fusion).
        is_fusion = (
            len(matched_cuisines) > 1
            and matched_cuisines[1][1] >= matched_cuisines[0][1] * 0.5
        )

        primary_cuisine = cuisine
        if not primary_cuisine and matched_cuisines:
            primary_cuisine = matched_cuisines[0][0]

        norms = _NORMS.get(primary_cuisine or "", {"positive": [], "negative": []})

        findings: list[PairingFinding] = []
        pos_scores: list[float] = []
        neg_scores: list[float] = []

        for a, b, score, note in norms.get("positive", []):
            if a in ing_names and b in ing_names:
                pos_scores.append(score)
                findings.append(PairingFinding(
                    ingredient_ids=[],
                    finding_type="cultural_affinity",
                    score=score,
                    explanation=f"{a} + {b}: {note}",
                ))

        for a, b, score, note in norms.get("negative", []):
            if a in ing_names and b in ing_names:
                neg_scores.append(abs(score))
                findings.append(PairingFinding(
                    ingredient_ids=[],
                    finding_type="cultural_violation",
                    score=score,
                    explanation=f"{a} + {b}: {note}",
                ))

        if not findings:
            if is_fusion:
                verdict = "fusion_blend"
                polarity = "neutral"
                overall = 0.3
            else:
                verdict = "tradition_undetermined"
                polarity = "neutral"
                overall = 0.0
        else:
            pos_avg = sum(pos_scores) / len(pos_scores) if pos_scores else 0.0
            neg_avg = sum(neg_scores) / len(neg_scores) if neg_scores else 0.0
            overall = max(-1.0, min(1.0, pos_avg - neg_avg))

            if is_fusion and pos_avg > 0.4:
                verdict = "cross_cultural_harmony"
                polarity = "harmonious"
            elif overall >= 0.7:
                verdict = "culturally_coherent"
                polarity = "harmonious"
            elif overall >= 0.3:
                verdict = "tradition_aligned"
                polarity = "harmonious"
            elif neg_avg > pos_avg:
                verdict = "cultural_tension"
                polarity = "discordant"
            else:
                verdict = "partial_tradition_match"
                polarity = "neutral"

        cuisine_label = primary_cuisine or "undetermined"
        fusion_note = f" (fusion: {', '.join(c for c, _ in matched_cuisines)})" if is_fusion else ""
        return ProjectionResult(
            projection_id=self.projection_id,
            verdict=verdict,
            polarity=polarity,
            findings=findings,
            score=round(overall, 3),
            explanation=(
                f"Cuisine: {cuisine_label}{fusion_note}. "
                f"{len(pos_scores)} positive norm(s), {len(neg_scores)} violation(s) found."
            ),
        )
