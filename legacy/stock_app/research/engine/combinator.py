"""
research.engine.combinator — Smart combo generator with pruning
================================================================
Generates 1-to-N signal combinations and filters by domain rules
to keep total combos < 5,000.
"""
from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Set, Tuple

from research.signals.base import SignalDefinition, SignalRegistry


def is_valid_combo(signals: List[SignalDefinition]) -> bool:
    """Apply domain pruning rules to a candidate combination."""
    cats = [s.category for s in signals]
    cat_set = set(cats)

    # Rule 1: Max 2 from same category
    if any(cats.count(c) > 2 for c in cat_set):
        return False

    # Rule 2: 3+ signals MUST include at least 1 trend
    if len(signals) >= 3 and "trend" not in cat_set:
        return False

    # Rule 3: Volume can't be standalone
    if all(c == "volume" for c in cats):
        return False

    # Rule 4: Max 1 pattern indicator
    if cats.count("pattern") > 1:
        return False

    # Rule 5: No redundant combos (same-subcategory pairs with overlapping tags)
    tag_sets = [set(s.tags) for s in signals]
    for i, j in combinations(range(len(signals)), 2):
        if signals[i].category == signals[j].category:
            overlap = tag_sets[i] & tag_sets[j]
            if len(overlap) > 1:
                return False

    # Rule 6: Don't mix opposing directions in a 2-signal combo
    if len(signals) == 2:
        dirs = {s.direction for s in signals}
        if "bullish" in dirs and "bearish" in dirs:
            return False

    return True


def generate_combos(
    reg: SignalRegistry,
    max_signals: int = 3,
    direction: str = "long",
    categories: List[str] | None = None,
    exclude_categories: List[str] | None = None,
) -> List[Tuple[str, ...]]:
    """
    Generate all valid signal combinations up to *max_signals*.

    Parameters
    ----------
    reg : SignalRegistry
        Populated signal registry.
    max_signals : int
        Maximum signals per combo (1-4).
    direction : str
        "long" → only bullish signals, "short" → only bearish, "both" → all.
    categories : list or None
        Restrict to these categories. None = all.
    exclude_categories : list or None
        Categories to explicitly ignore.

    Returns
    -------
    List of tuples of signal names.
    """
    # Filter signals by direction and category
    all_sigs = reg.list_all()

    if direction == "long":
        all_sigs = [s for s in all_sigs if s.direction == "bullish"]
    elif direction == "short":
        all_sigs = [s for s in all_sigs if s.direction == "bearish"]

    if categories:
        cat_set = set(categories)
        all_sigs = [s for s in all_sigs if s.category in cat_set]

    if exclude_categories:
        excl_set = set(exclude_categories)
        all_sigs = [s for s in all_sigs if s.category not in excl_set]

    combos: List[Tuple[str, ...]] = []

    for n in range(1, min(max_signals, 4) + 1):
        for combo_sigs in combinations(all_sigs, n):
            if is_valid_combo(list(combo_sigs)):
                combos.append(tuple(s.name for s in combo_sigs))

    return combos


def estimate_total_backtests(
    n_combos: int,
    n_rr_ratios: int = 5,
) -> int:
    """Estimate total number of backtests (combos × R:R ratios)."""
    return n_combos * n_rr_ratios
