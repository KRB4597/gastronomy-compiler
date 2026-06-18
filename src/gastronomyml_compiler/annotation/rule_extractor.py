"""Tier 2 rule-based extractor — deterministic pattern library.

Analogous to ErisML rule_extractor.py.  Identifies ingredients, techniques,
and flavor facts from natural-language text using regex + a built-in flavor
profile library derived from FlavorDB2 / geometric-gastronomy principles.
"""

from __future__ import annotations

import re
import uuid

from ..ir.schemas import (
    CookingTechnique,
    FlavorFact,
    FlavorFactKind,
    FlavorTransformation,
    FlavorVector,
    FoodGroup,
    Ingredient,
    PairingRule,
    PairingRuleType,
    Recipe,
    RecipeStep,
    TechniqueType,
)
from .base import BaseExtractor, ExtractorResult


# ---------------------------------------------------------------------------
# Ingredient flavor profile library
# (values: dict[dimension → score in [-1,1]])
# Sourced from FlavorDB2 compound data + geometric-gastronomy principles
# ---------------------------------------------------------------------------

INGREDIENT_LIBRARY: dict[str, dict] = {
    # ── Fats & dairy ──────────────────────────────────────────────────────
    "butter": {"sweet": 0.2, "salty": 0.15, "fat": 0.9, "aromatic": 0.35, "texture": 0.5,
               "group": FoodGroup.FAT},
    "cream": {"sweet": 0.25, "fat": 0.85, "texture": 0.6,
              "group": FoodGroup.DAIRY},
    "olive oil": {"fat": 0.8, "bitter": 0.3, "aromatic": 0.4,
                  "group": FoodGroup.FAT},
    "sesame oil": {"fat": 0.7, "aromatic": 0.8, "bitter": 0.1,
                   "group": FoodGroup.FAT},
    "coconut": {"fat": 0.8, "sweet": 0.5, "aromatic": 0.6,
                "group": FoodGroup.FAT},
    "lard": {"fat": 0.9, "aromatic": 0.3, "group": FoodGroup.FAT},
    "cheese": {"fat": 0.7, "salty": 0.5, "umami": 0.65, "sour": 0.3, "aromatic": 0.5,
               "group": FoodGroup.DAIRY},
    "parmesan": {"fat": 0.5, "salty": 0.6, "umami": 0.9, "aromatic": 0.6,
                 "group": FoodGroup.DAIRY},
    "parmigiano": {"fat": 0.5, "salty": 0.6, "umami": 0.9, "aromatic": 0.6,
                   "group": FoodGroup.DAIRY},
    "cream cheese": {"fat": 0.7, "sour": 0.4, "sweet": 0.2, "group": FoodGroup.DAIRY},
    "yogurt": {"sour": 0.65, "fat": 0.3, "group": FoodGroup.DAIRY},
    "milk": {"fat": 0.3, "sweet": 0.3, "group": FoodGroup.DAIRY},
    "egg": {"fat": 0.4, "umami": 0.4, "texture": 0.5, "group": FoodGroup.PROTEIN},
    "egg yolk": {"fat": 0.6, "umami": 0.45, "texture": 0.5, "group": FoodGroup.PROTEIN},
    # ── Proteins ──────────────────────────────────────────────────────────
    "duck": {"umami": 0.7, "fat": 0.7, "sweet": 0.15, "aromatic": 0.35,
             "group": FoodGroup.PROTEIN},
    "chicken": {"umami": 0.5, "fat": 0.3, "group": FoodGroup.PROTEIN},
    "beef": {"umami": 0.85, "fat": 0.55, "aromatic": 0.3, "group": FoodGroup.PROTEIN},
    "pork": {"umami": 0.6, "fat": 0.6, "sweet": 0.1, "group": FoodGroup.PROTEIN},
    "pork belly": {"fat": 0.9, "umami": 0.65, "sweet": 0.15, "group": FoodGroup.PROTEIN},
    "chashu": {"fat": 0.75, "umami": 0.7, "sweet": 0.25, "salty": 0.3, "aromatic": 0.4,
               "group": FoodGroup.PROTEIN},
    "lamb": {"umami": 0.65, "fat": 0.55, "aromatic": 0.35, "group": FoodGroup.PROTEIN},
    "bacon": {"umami": 0.75, "salty": 0.7, "fat": 0.65, "aromatic": 0.5,
              "group": FoodGroup.PROTEIN},
    "anchovies": {"umami": 0.95, "salty": 0.8, "aromatic": 0.4,
                  "group": FoodGroup.SEAFOOD},
    "anchovy": {"umami": 0.95, "salty": 0.8, "aromatic": 0.4,
                "group": FoodGroup.SEAFOOD},
    "fish": {"umami": 0.6, "fat": 0.3, "group": FoodGroup.SEAFOOD},
    "salmon": {"umami": 0.6, "fat": 0.7, "aromatic": 0.3, "group": FoodGroup.SEAFOOD},
    "tuna": {"umami": 0.7, "fat": 0.4, "group": FoodGroup.SEAFOOD},
    "shrimp": {"umami": 0.6, "sweet": 0.25, "salty": 0.2, "group": FoodGroup.SEAFOOD},
    "scallop": {"umami": 0.7, "sweet": 0.45, "fat": 0.2, "group": FoodGroup.SEAFOOD},
    # ── Umami-rich vegetables / fungi ─────────────────────────────────────
    "mushroom": {"umami": 0.8, "aromatic": 0.65, "bitter": 0.15, "texture": 0.4,
                 "group": FoodGroup.FUNGUS},
    "tomato": {"sour": 0.5, "sweet": 0.4, "umami": 0.65, "aromatic": 0.4,
               "group": FoodGroup.VEGETABLE},
    "spinach": {"bitter": 0.3, "umami": 0.3, "group": FoodGroup.VEGETABLE},
    "kale": {"bitter": 0.55, "group": FoodGroup.VEGETABLE},
    "romaine": {"bitter": 0.25, "texture": 0.3, "group": FoodGroup.VEGETABLE},
    "lettuce": {"bitter": 0.2, "texture": 0.25, "group": FoodGroup.VEGETABLE},
    "bamboo": {"bitter": 0.2, "texture": 0.5, "group": FoodGroup.VEGETABLE},
    "nori": {"umami": 0.6, "salty": 0.3, "aromatic": 0.4, "group": FoodGroup.VEGETABLE},
    # ── Aromatics ─────────────────────────────────────────────────────────
    "garlic": {"aromatic": 0.9, "umami": 0.45, "heat": 0.3, "bitter": 0.1,
               "group": FoodGroup.VEGETABLE},
    "onion": {"sweet": 0.4, "aromatic": 0.7, "umami": 0.3, "group": FoodGroup.VEGETABLE},
    "shallot": {"sweet": 0.45, "aromatic": 0.75, "umami": 0.3, "group": FoodGroup.VEGETABLE},
    "scallion": {"aromatic": 0.6, "sweet": 0.2, "group": FoodGroup.VEGETABLE},
    "ginger": {"heat": 0.6, "aromatic": 0.8, "sour": 0.1, "group": FoodGroup.SPICE},
    "thyme": {"aromatic": 0.8, "bitter": 0.15, "group": FoodGroup.HERB},
    "rosemary": {"aromatic": 0.9, "bitter": 0.3, "group": FoodGroup.HERB},
    "basil": {"aromatic": 0.8, "sweet": 0.2, "group": FoodGroup.HERB},
    "mint": {"aromatic": 0.9, "bitter": 0.1, "heat": 0.2, "group": FoodGroup.HERB},
    "parsley": {"aromatic": 0.65, "bitter": 0.1, "group": FoodGroup.HERB},
    "cilantro": {"aromatic": 0.75, "group": FoodGroup.HERB},
    "tarragon": {"aromatic": 0.8, "sweet": 0.15, "group": FoodGroup.HERB},
    "chives": {"aromatic": 0.6, "group": FoodGroup.HERB},
    # ── Fermented / umami condiments ──────────────────────────────────────
    "miso": {"umami": 0.95, "salty": 0.7, "sweet": 0.2, "aromatic": 0.45,
             "group": FoodGroup.CONDIMENT},
    "soy sauce": {"umami": 0.9, "salty": 0.8, "aromatic": 0.3,
                  "group": FoodGroup.CONDIMENT},
    "soy": {"umami": 0.9, "salty": 0.8, "group": FoodGroup.CONDIMENT},
    "mirin": {"sweet": 0.7, "umami": 0.3, "aromatic": 0.3, "group": FoodGroup.CONDIMENT},
    "sake": {"sour": 0.2, "sweet": 0.3, "umami": 0.2, "aromatic": 0.4,
             "group": FoodGroup.LIQUID},
    "worcestershire": {"umami": 0.75, "salty": 0.5, "sour": 0.3, "aromatic": 0.4,
                       "group": FoodGroup.CONDIMENT},
    "fish sauce": {"umami": 0.9, "salty": 0.85, "group": FoodGroup.CONDIMENT},
    "tahini": {"fat": 0.7, "bitter": 0.3, "aromatic": 0.5, "group": FoodGroup.CONDIMENT},
    "mustard": {"heat": 0.5, "sour": 0.3, "aromatic": 0.5, "bitter": 0.2,
                "group": FoodGroup.CONDIMENT},
    "dijon": {"heat": 0.55, "sour": 0.35, "aromatic": 0.5, "bitter": 0.2,
              "group": FoodGroup.CONDIMENT},
    # ── Acids ─────────────────────────────────────────────────────────────
    "lemon": {"sour": 0.9, "aromatic": 0.65, "sweet": 0.1, "bitter": 0.15,
              "group": FoodGroup.FRUIT},
    "lime": {"sour": 0.85, "aromatic": 0.7, "bitter": 0.1, "group": FoodGroup.FRUIT},
    "orange": {"sweet": 0.6, "sour": 0.4, "aromatic": 0.65, "group": FoodGroup.FRUIT},
    "vinegar": {"sour": 0.9, "aromatic": 0.4, "group": FoodGroup.CONDIMENT},
    "wine": {"sour": 0.5, "aromatic": 0.7, "bitter": 0.2, "sweet": 0.1,
             "group": FoodGroup.LIQUID},
    "port": {"sweet": 0.6, "sour": 0.3, "aromatic": 0.65, "group": FoodGroup.LIQUID},
    "cherry": {"sweet": 0.65, "sour": 0.4, "aromatic": 0.5, "group": FoodGroup.FRUIT},
    # ── Sweeteners ────────────────────────────────────────────────────────
    "sugar": {"sweet": 1.0, "group": FoodGroup.SWEETENER},
    "honey": {"sweet": 0.9, "aromatic": 0.35, "group": FoodGroup.SWEETENER},
    "maple syrup": {"sweet": 0.9, "aromatic": 0.55, "group": FoodGroup.SWEETENER},
    "caramel": {"sweet": 0.8, "bitter": 0.2, "aromatic": 0.5, "group": FoodGroup.SWEETENER},
    # ── Spices / heat ─────────────────────────────────────────────────────
    "chili": {"heat": 0.9, "aromatic": 0.4, "group": FoodGroup.SPICE},
    "chili oil": {"heat": 0.85, "fat": 0.5, "aromatic": 0.5, "group": FoodGroup.SPICE},
    "black pepper": {"heat": 0.5, "aromatic": 0.55, "bitter": 0.2, "group": FoodGroup.SPICE},
    "cayenne": {"heat": 0.9, "group": FoodGroup.SPICE},
    "paprika": {"sweet": 0.3, "heat": 0.4, "aromatic": 0.6, "group": FoodGroup.SPICE},
    "cumin": {"aromatic": 0.8, "bitter": 0.2, "group": FoodGroup.SPICE},
    "coriander": {"aromatic": 0.8, "group": FoodGroup.SPICE},
    "turmeric": {"bitter": 0.35, "aromatic": 0.6, "group": FoodGroup.SPICE},
    "curry powder": {"heat": 0.5, "aromatic": 0.9, "bitter": 0.2, "group": FoodGroup.SPICE},
    "cardamom": {"aromatic": 0.9, "sweet": 0.2, "heat": 0.2, "group": FoodGroup.SPICE},
    "cinnamon": {"sweet": 0.4, "aromatic": 0.85, "heat": 0.2, "group": FoodGroup.SPICE},
    "star anise": {"aromatic": 0.9, "sweet": 0.25, "group": FoodGroup.SPICE},
    "sesame": {"fat": 0.5, "aromatic": 0.75, "bitter": 0.1, "group": FoodGroup.SPICE},
    # ── Carbs ─────────────────────────────────────────────────────────────
    "potato": {"sweet": 0.2, "texture": 0.7, "group": FoodGroup.CARBOHYDRATE},
    "pasta": {"texture": 0.6, "sweet": 0.1, "group": FoodGroup.CARBOHYDRATE},
    "noodle": {"texture": 0.6, "group": FoodGroup.CARBOHYDRATE},
    "ramen": {"texture": 0.6, "umami": 0.1, "group": FoodGroup.CARBOHYDRATE},
    "rice": {"sweet": 0.2, "texture": 0.5, "group": FoodGroup.CARBOHYDRATE},
    "bread": {"sweet": 0.2, "texture": 0.5, "aromatic": 0.3, "group": FoodGroup.CARBOHYDRATE},
    "sourdough": {"sour": 0.5, "aromatic": 0.5, "texture": 0.5, "group": FoodGroup.CARBOHYDRATE},
    "crouton": {"salty": 0.3, "fat": 0.3, "texture": 0.7, "aromatic": 0.4,
                "group": FoodGroup.CARBOHYDRATE},
    # ── Miscellaneous ─────────────────────────────────────────────────────
    "chocolate": {"bitter": 0.7, "sweet": 0.5, "fat": 0.4, "aromatic": 0.6,
                  "group": FoodGroup.SWEETENER},
    "coffee": {"bitter": 0.9, "aromatic": 0.8, "group": FoodGroup.LIQUID},
    "vanilla": {"sweet": 0.6, "aromatic": 0.9, "group": FoodGroup.SPICE},
    "almond": {"fat": 0.6, "sweet": 0.3, "bitter": 0.2, "aromatic": 0.4,
               "group": FoodGroup.PROTEIN},
    "walnut": {"fat": 0.7, "bitter": 0.4, "aromatic": 0.3, "group": FoodGroup.PROTEIN},
    "pine nut": {"fat": 0.7, "sweet": 0.2, "aromatic": 0.3, "group": FoodGroup.PROTEIN},
    "capers": {"sour": 0.6, "salty": 0.7, "aromatic": 0.4, "group": FoodGroup.CONDIMENT},
    "salt": {"salty": 1.0, "group": FoodGroup.CONDIMENT},
    "broth": {"umami": 0.55, "salty": 0.3, "aromatic": 0.3, "group": FoodGroup.LIQUID},
    "dashi": {"umami": 0.85, "salty": 0.2, "aromatic": 0.4, "group": FoodGroup.LIQUID},
    "bone": {"umami": 0.6, "fat": 0.3, "group": FoodGroup.PROTEIN},
}

# ---------------------------------------------------------------------------
# Technique library
# ---------------------------------------------------------------------------

TECHNIQUE_LIBRARY: dict[str, dict] = {
    "roast": {"type": TechniqueType.ROASTING,
              "delta": {"aromatic": 0.3, "bitter": 0.1, "umami": 0.15}},
    "sear": {"type": TechniqueType.MAILLARD,
             "delta": {"aromatic": 0.35, "umami": 0.2, "bitter": 0.1}},
    "brown": {"type": TechniqueType.MAILLARD,
              "delta": {"aromatic": 0.3, "umami": 0.15, "bitter": 0.1}},
    "carameliz": {"type": TechniqueType.CARAMELIZATION,
                  "delta": {"sweet": -0.2, "bitter": 0.25, "aromatic": 0.35}},
    "ferment": {"type": TechniqueType.FERMENTATION,
                "delta": {"umami": 0.3, "sour": 0.25, "aromatic": 0.2}},
    "braise": {"type": TechniqueType.BRAISING,
               "delta": {"umami": 0.25, "fat": 0.1, "aromatic": 0.15}},
    "confit": {"type": TechniqueType.CONFITING,
               "delta": {"fat": 0.2, "umami": 0.15, "aromatic": 0.1}},
    "emulsif": {"type": TechniqueType.EMULSIFICATION,
                "delta": {"fat": 0.15, "texture": 0.3}},
    "reduc": {"type": TechniqueType.REDUCTION,
              "delta": {"umami": 0.2, "sweet": 0.1, "aromatic": 0.15}},
    "grill": {"type": TechniqueType.GRILLING,
              "delta": {"aromatic": 0.35, "bitter": 0.1, "umami": 0.15}},
    "sauté": {"type": TechniqueType.SAUTEING,
              "delta": {"aromatic": 0.2, "fat": 0.1}},
    "saute": {"type": TechniqueType.SAUTEING,
              "delta": {"aromatic": 0.2, "fat": 0.1}},
    "smoke": {"type": TechniqueType.SMOKING,
              "delta": {"aromatic": 0.4, "bitter": 0.15}},
    "marinate": {"type": TechniqueType.MARINATING,
                 "delta": {"sour": 0.1, "aromatic": 0.2}},
    "cure": {"type": TechniqueType.CURING,
             "delta": {"salty": 0.2, "umami": 0.1}},
    "fry": {"type": TechniqueType.FRYING,
            "delta": {"fat": 0.2, "texture": 0.3, "aromatic": 0.15}},
    "blanch": {"type": TechniqueType.BLANCHING,
               "delta": {"bitter": -0.1}},
    "steam": {"type": TechniqueType.STEAMING, "delta": {}},
    "poach": {"type": TechniqueType.POACHING, "delta": {}},
    "simmer": {"type": TechniqueType.REDUCTION,
               "delta": {"umami": 0.1, "aromatic": 0.1}},
    "toast": {"type": TechniqueType.MAILLARD,
              "delta": {"aromatic": 0.25, "bitter": 0.1}},
    "render": {"type": TechniqueType.SAUTEING,
               "delta": {"fat": 0.15, "aromatic": 0.2}},
    "deglaze": {"type": TechniqueType.REDUCTION,
                "delta": {"aromatic": 0.2, "sour": 0.1}},
    "whisk": {"type": TechniqueType.EMULSIFICATION,
              "delta": {"texture": 0.2}},
    "bake": {"type": TechniqueType.ROASTING,
             "delta": {"aromatic": 0.2}},
}

# ---------------------------------------------------------------------------
# Cuisine detection keywords
# ---------------------------------------------------------------------------

CUISINE_KEYWORDS: dict[str, list[str]] = {
    "french": ["confit", "gastrique", "sauté", "braise", "beurre", "gratin", "roux",
               "mirepoix", "fond", "port", "bordeaux"],
    "japanese": ["miso", "dashi", "mirin", "sake", "ramen", "nori", "soy sauce",
                 "bonito", "kombu", "yuzu", "wasabi"],
    "italian": ["parmesan", "parmigiano", "pasta", "basil", "oregano", "prosciutto",
                "risotto", "polenta", "balsamic"],
    "mediterranean": ["olive oil", "lemon", "capers", "tahini", "harissa", "za'atar",
                      "sumac", "feta", "pita"],
    "indian": ["curry", "turmeric", "cardamom", "cumin", "coriander", "garam masala",
               "ghee", "paneer", "naan"],
    "chinese": ["soy sauce", "star anise", "five spice", "hoisin", "sesame oil",
                "wok", "scallion", "ginger"],
}

DIETARY_KEYWORDS: dict[str, list[str]] = {
    "vegan": ["tofu", "tempeh", "plant", "soy milk"],
    "vegetarian": ["vegetarian"],
    "gluten-free": ["gluten-free", "gluten free"],
    "dairy-free": ["dairy-free", "dairy free", "non-dairy"],
}

# ---------------------------------------------------------------------------
# Pairing rules — known positive pairs
# ---------------------------------------------------------------------------

POSITIVE_PAIRS: list[tuple[str, str, str]] = [
    ("duck", "cherry", "acid cuts fat, sweet enhances game"),
    ("parmesan", "anchovy", "glutamate + inosinate umami synergy"),
    ("beef", "mushroom", "inosinate + glutamate synergy"),
    ("tomato", "basil", "aromatic compound bridge (linalool)"),
    ("lemon", "butter", "acid brightens richness"),
    ("garlic", "olive oil", "aromatic compound affinity"),
    ("miso", "pork", "fermented umami + inosinate synergy"),
    ("soy sauce", "ginger", "aromatic compound bridge"),
    ("chocolate", "coffee", "bitter compound affinity"),
    ("cream", "vanilla", "fat carries aromatic"),
    ("capers", "anchovy", "salty-umami amplification"),
    ("wine", "mushroom", "aromatic / terroir affinity"),
]

NEGATIVE_PAIRS: list[tuple[str, str, str]] = [
    ("fish", "cheese", "competing protein textures + aromatic clash"),
    ("chocolate", "onion", "incompatible volatile compounds"),
    ("coffee", "fish", "bitter tannins + fish oil clash"),
]


# ---------------------------------------------------------------------------
# Rule extractor
# ---------------------------------------------------------------------------

class RuleExtractor(BaseExtractor):
    """Tier 2 deterministic extractor."""

    def extract(self, text: str) -> ExtractorResult:
        lower = text.lower()

        ingredients = self._extract_ingredients(text, lower)
        techniques = self._extract_techniques(text, lower, ingredients)
        flavor_facts = self._extract_flavor_facts(ingredients)
        pairing_rules = self._extract_pairing_rules(ingredients)
        recipe = self._extract_recipe(text, lower, techniques, ingredients)
        cuisine = self._detect_cuisine(lower)
        meal_type = self._detect_meal_type(lower)
        dietary = self._detect_dietary(lower)

        return ExtractorResult(
            ingredients=ingredients,
            techniques=techniques,
            recipes=[recipe] if recipe else [],
            pairing_rules=pairing_rules,
            flavor_facts=flavor_facts,
            cuisine_hint=cuisine,
            meal_type_hint=meal_type,
            dietary_flags=dietary,
            extractor_metadata={"tier": "rule"},
        )

    # ------------------------------------------------------------------ #
    # Ingredient extraction (Passes 2–3)
    # ------------------------------------------------------------------ #

    def _extract_ingredients(self, text: str, lower: str) -> list[Ingredient]:
        found: list[Ingredient] = []
        seen: set[str] = set()

        for name, profile in INGREDIENT_LIBRARY.items():
            # whole-word match
            if re.search(r"\b" + re.escape(name) + r"\b", lower):
                if name in seen:
                    continue
                seen.add(name)
                flavor_scores = {k: v for k, v in profile.items() if k != "group"}
                fv = FlavorVector.from_dict(flavor_scores)
                ing = Ingredient(
                    id=f"ing_{len(found)}",
                    name=name,
                    canonical_name=name,
                    food_group=profile.get("group", FoodGroup.UNKNOWN),
                    flavor_vector=fv,
                )
                found.append(ing)

        return found

    # ------------------------------------------------------------------ #
    # Technique extraction (Pass 4)
    # ------------------------------------------------------------------ #

    def _extract_techniques(
        self, text: str, lower: str, ingredients: list[Ingredient]
    ) -> list[CookingTechnique]:
        found: list[CookingTechnique] = []
        seen_types: set[TechniqueType] = set()

        for verb, tspec in TECHNIQUE_LIBRARY.items():
            if re.search(r"\b" + re.escape(verb), lower):
                ttype = tspec["type"]
                if ttype in seen_types:
                    continue
                seen_types.add(ttype)

                # heuristically attribute to protein / primary ingredient
                applies_to = [
                    i.id for i in ingredients
                    if i.food_group in (FoodGroup.PROTEIN, FoodGroup.SEAFOOD)
                ][:2]

                found.append(CookingTechnique(
                    id=f"tech_{len(found)}",
                    name=verb,
                    technique_type=ttype,
                    applies_to=applies_to,
                    transformation=FlavorTransformation(
                        dimension_deltas=tspec.get("delta", {}),
                        description=f"{verb} technique",
                    ),
                ))

        return found

    # ------------------------------------------------------------------ #
    # Flavor facts (Pass 5)
    # ------------------------------------------------------------------ #

    def _extract_flavor_facts(
        self, ingredients: list[Ingredient]
    ) -> list[FlavorFact]:
        facts: list[FlavorFact] = []
        ing_map = {i.name: i for i in ingredients}

        # Umami synergy: glutamate-rich + inosinate-rich
        glutamate_ids = [
            i.id for i in ingredients
            if i.flavor_vector.umami.value >= 0.7 and i.food_group
            in (FoodGroup.CONDIMENT, FoodGroup.FUNGUS, FoodGroup.VEGETABLE)
        ]
        inosinate_ids = [
            i.id for i in ingredients
            if i.flavor_vector.umami.value >= 0.5 and i.food_group
            in (FoodGroup.PROTEIN, FoodGroup.SEAFOOD)
        ]
        if glutamate_ids and inosinate_ids:
            facts.append(FlavorFact(
                id=f"ff_{len(facts)}",
                fact_kind=FlavorFactKind.UMAMI_SYNERGY,
                subject_ids=glutamate_ids[:1] + inosinate_ids[:1],
                dimension="umami",
                severity="significant",
                confidence=0.85,
                explanation="Glutamate (plant/fungal) + inosinate (animal) synergy amplifies umami up to 8×",
            ))

        # Acid-fat balance
        acid_ids = [i.id for i in ingredients if i.flavor_vector.sour.value >= 0.5]
        fat_ids = [i.id for i in ingredients if i.flavor_vector.fat.value >= 0.6]
        if acid_ids and fat_ids:
            facts.append(FlavorFact(
                id=f"ff_{len(facts)}",
                fact_kind=FlavorFactKind.ACID_FAT_BALANCE,
                subject_ids=acid_ids[:1] + fat_ids[:1],
                dimension="sour",
                severity="moderate",
                confidence=0.8,
                explanation="Acid element brightens and cuts perceived richness",
            ))

        # Known positive compound pairs
        for a_name, b_name, explanation in POSITIVE_PAIRS:
            if a_name in ing_map and b_name in ing_map:
                facts.append(FlavorFact(
                    id=f"ff_{len(facts)}",
                    fact_kind=FlavorFactKind.COMPOUND_BRIDGE,
                    subject_ids=[ing_map[a_name].id, ing_map[b_name].id],
                    severity="moderate",
                    confidence=0.75,
                    explanation=explanation,
                ))

        # Known negative pairs
        for a_name, b_name, explanation in NEGATIVE_PAIRS:
            if a_name in ing_map and b_name in ing_map:
                facts.append(FlavorFact(
                    id=f"ff_{len(facts)}",
                    fact_kind=FlavorFactKind.CLASH,
                    subject_ids=[ing_map[a_name].id, ing_map[b_name].id],
                    severity="moderate",
                    confidence=0.7,
                    explanation=explanation,
                ))

        return facts

    # ------------------------------------------------------------------ #
    # Pairing rules (Pass 6)
    # ------------------------------------------------------------------ #

    def _extract_pairing_rules(
        self, ingredients: list[Ingredient]
    ) -> list[PairingRule]:
        rules: list[PairingRule] = []
        ing_map = {i.name: i for i in ingredients}

        for a_name, b_name, explanation in POSITIVE_PAIRS:
            if a_name in ing_map and b_name in ing_map:
                rules.append(PairingRule(
                    id=f"rule_{len(rules)}",
                    rule_type=PairingRuleType.RECOMMENDATION,
                    modality="pairs_with",
                    subject_id=ing_map[a_name].id,
                    object_id=ing_map[b_name].id,
                    confidence=0.75,
                    source="compound_similarity",
                    explanation=explanation,
                ))

        for a_name, b_name, explanation in NEGATIVE_PAIRS:
            if a_name in ing_map and b_name in ing_map:
                rules.append(PairingRule(
                    id=f"rule_{len(rules)}",
                    rule_type=PairingRuleType.PROHIBITION,
                    modality="avoids",
                    subject_id=ing_map[a_name].id,
                    object_id=ing_map[b_name].id,
                    confidence=0.7,
                    source="compound_clash",
                    explanation=explanation,
                ))

        # Acid enhances fat
        for ing in ingredients:
            if ing.flavor_vector.sour.value >= 0.5:
                for fat_ing in ingredients:
                    if fat_ing.id != ing.id and fat_ing.flavor_vector.fat.value >= 0.6:
                        rules.append(PairingRule(
                            id=f"rule_{len(rules)}",
                            rule_type=PairingRuleType.RECOMMENDATION,
                            modality="contrasts_with",
                            subject_id=ing.id,
                            object_id=fat_ing.id,
                            confidence=0.7,
                            source="contrast",
                            explanation="Acid contrasts with fat for balance",
                        ))
                        break  # one per acid source

        return rules

    # ------------------------------------------------------------------ #
    # Recipe sketch (Pass 6)
    # ------------------------------------------------------------------ #

    def _extract_recipe(
        self,
        text: str,
        lower: str,
        techniques: list[CookingTechnique],
        ingredients: list[Ingredient],
    ) -> Recipe | None:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return None

        steps = []
        for i, tech in enumerate(techniques[:8]):
            steps.append(RecipeStep(
                order=i,
                instruction=f"Apply {tech.name} technique",
                technique_id=tech.id,
                ingredient_ids=tech.applies_to,
            ))

        return Recipe(
            id="recipe_0",
            name=lines[0][:80],
            steps=steps,
            status="sketch",
        )

    # ------------------------------------------------------------------ #
    # Context detection (Pass 5)
    # ------------------------------------------------------------------ #

    def _detect_cuisine(self, lower: str) -> str | None:
        scores: dict[str, int] = {}
        for cuisine, keywords in CUISINE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > 0:
                scores[cuisine] = score
        if not scores:
            return None
        return max(scores, key=lambda k: scores[k])

    def _detect_meal_type(self, lower: str) -> str | None:
        for mt in ["appetizer", "starter", "main", "entree", "dessert", "sauce", "side"]:
            if mt in lower:
                return mt
        return None

    def _detect_dietary(self, lower: str) -> list[str]:
        flags = []
        for flag, keywords in DIETARY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                flags.append(flag)
        return flags
