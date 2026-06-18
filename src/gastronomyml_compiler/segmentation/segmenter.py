"""Pass 1 — split text into typed segments.

Heuristic segment typing analogous to ErisML segmenter.py.
"""

from __future__ import annotations

import re

from ..ir.schemas import Segment, SegmentType

_TECHNIQUE_VERBS = re.compile(
    r"\b(roast|sauté|sautee|braise|ferment|grill|steam|fry|frie|blanch|marinate|"
    r"cure|smoke|poach|confit|reduce|carameliz|emulsif|whisk|blend|fold|"
    r"simmer|boil|bake|deglaze|toast|sear|render|brown|crisp)\w*\b",
    re.IGNORECASE,
)

_INGREDIENT_PATTERNS = re.compile(
    r"\b(\d+[\s/\d]*(?:cup|tbsp|tsp|tablespoon|teaspoon|oz|g|lb|kg|ml|l|clove|"
    r"slice|piece|handful|bunch|sprig|pinch|dash)s?)\b",
    re.IGNORECASE,
)

_GARNISH_KEYWORDS = re.compile(
    r"\b(garnish|finish|top|drizzle|sprinkle|serve with)\b", re.IGNORECASE
)

_CONTEXT_KEYWORDS = re.compile(
    r"\b(french|japanese|italian|mediterranean|indian|chinese|thai|mexican|korean|"
    r"appetizer|starter|main|entree|dessert|sauce|side|vegetarian|vegan|"
    r"gluten.free|dairy.free)\b",
    re.IGNORECASE,
)


def segment_text(text: str) -> list[Segment]:
    """Split text on blank lines and assign a SegmentType heuristically."""
    raw_paragraphs = re.split(r"\n\s*\n", text.strip())
    segments: list[Segment] = []
    cursor = 0

    for i, para in enumerate(raw_paragraphs):
        para = para.strip()
        if not para:
            cursor += len(para) + 2
            continue

        seg_type = _classify(para)
        start = text.find(para, cursor)
        end = start + len(para)

        segments.append(Segment(
            id=f"seg_{i}",
            text=para,
            segment_type=seg_type,
            start_char=start,
            end_char=end,
        ))
        cursor = end

    return segments


def _classify(para: str) -> SegmentType:
    tech_hits = len(_TECHNIQUE_VERBS.findall(para))
    ing_hits = len(_INGREDIENT_PATTERNS.findall(para))

    if _GARNISH_KEYWORDS.search(para):
        return SegmentType.GARNISH
    if _CONTEXT_KEYWORDS.search(para) and tech_hits == 0:
        return SegmentType.CONTEXT
    if tech_hits >= 2:
        return SegmentType.TECHNIQUE
    if ing_hits >= 2:
        return SegmentType.INGREDIENT_LIST
    if tech_hits >= 1:
        return SegmentType.INSTRUCTION
    return SegmentType.DESCRIPTION
