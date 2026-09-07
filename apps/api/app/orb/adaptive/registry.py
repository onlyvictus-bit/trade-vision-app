"""Scenario registry and deterministic A-G failure coverage."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .contracts import Capability
from .scenario_detection import detect


@lru_cache(maxsize=1)
def source_registry() -> tuple[dict, ...]:
    rows = json.loads(Path(__file__).with_name("source_scenarios.json").read_text(encoding="utf-8"))
    expected = [
        f"{group}{i:02d}"
        for group, n in (("A", 5), ("B", 6), ("C", 4), ("D", 4), ("E", 4), ("F", 4), ("G", 3))
        for i in range(1, n + 1)
    ]
    if sorted(r["scenario_id"] for r in rows) != sorted(expected):
        raise ValueError("SCENARIO_REGISTRY_INCOMPLETE_OR_DUPLICATED")
    return tuple(rows)


def coverage(
    features: dict,
    errors: tuple[str, ...],
    now: int,
    cutoff: int,
    capabilities: tuple[Capability, ...] = (),
) -> dict[str, str]:
    """Return all 30 source scenarios plus 20 controller-risk contracts.

    `cutoff` is retained for API compatibility and controller-contract status;
    source scenario B05 has its own documented 11:30 staleness threshold and is
    calculated from elapsed session minutes by scenario_detection.detect().
    """
    statuses = detect(features, errors, capabilities, now)
    # Preserve the established public status literal while the dedicated
    # detector internally records why dealer gamma is unobservable.
    if statuses.get("F02") == "UNOBSERVABLE_DEALER_SIGN_INPUT":
        statuses["F02"] = "UNOBSERVABLE_EXTERNAL_INPUT"

    # Controller-risk coverage remains separate from the A-G source taxonomy.
    # These are invariant/control states, not invented market predictions.
    for i in range(1, 21):
        statuses[f"X{i:02d}"] = "CONTROLLER_CONTRACT"
    statuses["X09"] = "PATH_ORDER_UNOBSERVABLE" if features.get("two_sided_bar") else "NO_TWO_SIDED_FLAG"
    breadth_present = any(
        c.name in {"BREADTH_SUPPORTS_LONG", "BREADTH_SUPPORTS_SHORT"}
        and c.available_ns <= now < c.expires_ns
        for c in capabilities
    )
    statuses["X18"] = "VERIFIED_MARKET_BREADTH_AVAILABLE" if breadth_present else "MARKET_BREADTH_UNAVAILABLE_NOT_INFERRED"
    statuses["X20"] = "UNKNOWN_BRANCH_RETAINED"
    statuses["X05"] = "ENTRY_WINDOW_EXPIRED" if now >= cutoff else "ENTRY_WINDOW_OPEN"
    return statuses
