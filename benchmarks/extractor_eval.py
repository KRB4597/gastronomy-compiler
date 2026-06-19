"""Extractor bake-off: which NLP strategy reads ingredients best?

A gold corpus of dish descriptions, each annotated with which ingredients are
present and which are explicitly absent (negated), grouped by the phenomenon
that separates good extractors from bad ones:

  normal     — plain ingredient lists (baseline)
  negation   — "no butter" / "without parmesan" must NOT extract that ingredient
  inflection — plurals ("tomatoes", "eggs") should still register
  synonym    — out-of-vocabulary names ("prawns" ~ shrimp)

Each contender returns the set of ingredients it found; for a "present"
ingredient it should be in the set, for an "absent" one it should not.  We
report accuracy overall and per category.

Run:
    python -m benchmarks.extractor_eval
"""
from __future__ import annotations

from .contenders import all_contenders

# (text, category, present-ingredients, absent-ingredients)
GOLD: list[tuple[str, str, set[str], set[str]]] = [
    # --- normal -------------------------------------------------------------
    ("Butter, garlic, and tomato.", "normal", {"butter", "garlic", "tomato"}, set()),
    ("Miso soup with mushroom and nori.", "normal", {"miso", "mushroom", "nori"}, set()),
    ("Seared salmon with lemon.", "normal", {"salmon", "lemon"}, set()),
    # --- negation -----------------------------------------------------------
    ("No butter, just olive oil.", "negation", {"olive oil"}, {"butter"}),
    ("Pasta without parmesan.", "negation", {"pasta"}, {"parmesan"}),
    ("This dish has no garlic.", "negation", set(), {"garlic"}),
    ("Salmon, but never with cream.", "negation", {"salmon"}, {"cream"}),
    # --- inflection (plurals) ----------------------------------------------
    ("Roasted tomatoes with mushrooms.", "inflection", {"tomato", "mushroom"}, set()),
    ("Scrambled eggs and onions.", "inflection", {"egg", "onion"}, set()),
    # --- synonym / out-of-vocabulary ---------------------------------------
    ("Sauteed prawns.", "synonym", {"shrimp"}, set()),
    ("A whole roasted hen.", "synonym", {"chicken"}, set()),
]


def _judge(found: set[str], present: set[str], absent: set[str]) -> tuple[int, int]:
    correct = total = 0
    for ing in present:
        total += 1
        correct += int(ing in found)
    for ing in absent:
        total += 1
        correct += int(ing not in found)
    return correct, total


def run() -> int:
    contenders = [c for c in all_contenders() if c.available()]
    skipped = [c.name for c in all_contenders() if not c.available()]
    if skipped:
        print(f"(skipped unavailable contenders: {', '.join(skipped)})\n")

    categories: list[str] = []
    for _, cat, _, _ in GOLD:
        if cat not in categories:
            categories.append(cat)

    results = {c.name: {cat: [0, 0] for cat in categories + ["ALL"]} for c in contenders}
    for text, cat, present, absent in GOLD:
        for c in contenders:
            corr, tot = _judge(c.score(text), present, absent)
            for bucket in (cat, "ALL"):
                results[c.name][bucket][0] += corr
                results[c.name][bucket][1] += tot

    names = [c.name for c in contenders]
    w = 11
    header = f"{'category':<12}" + "".join(f"{n:>{w}}" for n in names)
    print("Extractor bake-off - ingredient extraction accuracy by phenomenon")
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for cat in categories + ["ALL"]:
        if cat == "ALL":
            print("-" * len(header))
        row = f"{cat:<12}"
        for n in names:
            c, t = results[n][cat]
            row += f"{(c / t if t else 0):>{w}.0%}"
        print(row)
    print("=" * len(header))

    overall = {n: results[n]["ALL"][0] / results[n]["ALL"][1] for n in names}
    winner = max(overall, key=overall.get)
    print(f"\nWinner overall: {winner} ({overall[winner]:.0%})")
    print("Read per-row to see where each tool wins (e.g. negation, inflection).")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
