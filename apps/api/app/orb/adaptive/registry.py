"""Preserve all source rules as UNVERIFIED text, never execute their prose."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def source_registry() -> tuple[dict, ...]:
    rows = json.loads(Path(__file__).with_name("source_scenarios.json").read_text(encoding="utf-8"))
    expected = [f"{group}{i:02d}" for group, n in (("A",5),("B",6),("C",4),("D",4),("E",4),("F",4),("G",3)) for i in range(1,n+1)]
    if sorted(r["scenario_id"] for r in rows) != sorted(expected):
        raise ValueError("SCENARIO_REGISTRY_INCOMPLETE_OR_DUPLICATED")
    return tuple(rows)


def coverage(features: dict, errors: tuple[str, ...], now: int, cutoff: int) -> dict[str, str]:
    # Not having a detector is explicitly different from observing no failure.
    statuses = {r["scenario_id"]: "UNOBSERVABLE_EXTERNAL_INPUT" for r in source_registry()}
    flags = {
        "A01": features.get("chop_risk", False),
        "A04": str(features.get("gap_class", "")).startswith("LARGE_"),
        "B01": features.get("failure_count", 0) > 0,
        "B02": features.get("or_width_atr", 0) > 1.0,
        "B03": features.get("range_locked", False) and features.get("or_width_atr", 0) < .25,
        "B04": features.get("first_bar_range_atr", 0) > 2,
        "B05": now >= cutoff,
        "B06": features.get("failure_count", 0) >= 2,
        "D03": False,  # cash feasibility handled by plan; actual depth unknown
        "E01": bool(errors),
    }
    for key, value in flags.items():
        statuses[key] = "UNOBSERVABLE_INVALID_INPUT" if errors and key not in {"E01", "B05"} else "OBSERVED_PRICE_OR_CLOCK_FLAG" if value else "NOT_OBSERVED_IN_VALID_PREFIX"
    statuses["D03"] = "ECONOMICS_CHECKED_DEPTH_UNOBSERVABLE"
    statuses["E02"] = "BROKER_OUT_OF_SCOPE_PAPER_CLOCK_ENFORCED"
    statuses["E03"] = "CAUSAL_PREFIX_GUARD_ENFORCED"
    statuses["E04"] = "SHARED_AFRE_EXECUTION_ENGINE_LEGACY_NOT_MIGRATED"
    statuses["G01"] = "UNESTIMATED_REQUIRES_MATURED_REAL_OUTCOMES"
    statuses["G02"] = "REGISTERED_CHRONOLOGICAL_PROOF_REQUIRED"
    statuses["G03"] = "SUPPORT_GATES_REQUIRED_NOT_A_PROBABILITY"
    # Controller-risk coverage is listed separately; these are contracts, not
    # invented forecasts that each risk is presently occurring.
    for i in range(1,21):
        statuses[f"X{i:02d}"] = "CONTROLLER_CONTRACT"
    statuses["X09"] = "PATH_ORDER_UNOBSERVABLE" if features.get("two_sided_bar") else "NO_TWO_SIDED_FLAG"
    statuses["X18"] = "MARKET_BREADTH_NOT_IMPLEMENTED_NOT_INFERRED"
    statuses["X20"] = "UNKNOWN_BRANCH_RETAINED"
    return statuses
