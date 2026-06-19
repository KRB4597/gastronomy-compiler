"""Benchmark / evaluation harness for gastronomy-compiler.

Two independent evaluations, each against a different kind of ground truth:

  * run_recipes        — does the compiler's harmony verdict track how much
                         humans actually *liked* a dish? (graded-recipe ratings)
  * run_flavor_pairing — does the compiler's flavor_similarity score track how
                         many flavor compounds two ingredients *share*?
                         (the Ahn et al. 2011 food-pairing principle)

Nothing here is imported by the compiler itself. Run:

    python -m benchmarks.run_recipes
    python -m benchmarks.run_flavor_pairing
"""
