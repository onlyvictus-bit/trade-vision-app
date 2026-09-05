from __future__ import annotations

from typing import Any


JARVIS_REALTIME_FRESHNESS_VERSION = "jarvis-realtime-freshness.v1.29"
DEFAULT_REALTIME_MAX_AGE_SECONDS = 10.0


def build_realtime_freshness_report(
    *,
    bundle: dict[str, Any],
    latency_budget: dict[str, Any],
    max_age_seconds: float = DEFAULT_REALTIME_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    cache = dict(bundle.get("cache", {}))
    age_seconds = float(cache.get("cache_age_seconds", 0.0))
    cache_fresh = bool(cache.get("cache_fresh", False))
    latency_state = str(latency_budget.get("budget_state", "pending"))
    stale = (not cache_fresh) or age_seconds > max_age_seconds
    aging = (not stale) and age_seconds > max_age_seconds * 0.8
    latency_degraded = latency_state in {"warning", "over_budget"}
    if stale:
        freshness_state = "stale"
        display_action = "WAIT"
        trust_effect = "block_confidence"
    elif aging or latency_degraded:
        freshness_state = "aging"
        display_action = "WAIT"
        trust_effect = "downgrade_confidence"
    else:
        freshness_state = "fresh"
        display_action = "RESEARCH_ONLY"
        trust_effect = "no_promotion"

    checks = [
        _check("FRESH-001", "Cache metadata is present", bool(cache), "block", "Without cache metadata the operator cannot know evidence age."),
        _check("FRESH-002", "Evidence age is within realtime max age", not stale, "block", f"age={age_seconds:.3f}s max={max_age_seconds:.3f}s"),
        _check("FRESH-003", "Latency budget does not force degradation", not latency_degraded, "downgrade", f"latency_state={latency_state}"),
        _check("FRESH-004", "Evidence remains research-only", bundle.get("trade_allowed") is False and bundle.get("order_routing_enabled") is False, "block", "Realtime freshness cannot authorize routing."),
    ]

    return {
        "freshness_version": JARVIS_REALTIME_FRESHNESS_VERSION,
        "assembly_version": bundle.get("assembly_version"),
        "latency_budget_version": latency_budget.get("latency_budget_version"),
        "symbol": bundle.get("symbol"),
        "timeframe": bundle.get("timeframe"),
        "freshness_state": freshness_state,
        "safe_display_action": display_action,
        "trust_effect": trust_effect,
        "evidence_stale": stale,
        "refresh_required": stale or aging,
        "force_wait": stale or aging or latency_degraded,
        "cache_status": cache.get("cache_status", "uncached"),
        "cache_age_seconds": round(age_seconds, 3),
        "max_age_seconds": max_age_seconds,
        "cache_ttl_seconds": cache.get("cache_ttl_seconds"),
        "latency_state": latency_state,
        "next_refresh_after_seconds": 0.0 if stale else round(max(max_age_seconds - age_seconds, 0.0), 3),
        "checks": checks,
        "operator_message": _operator_message(stale=stale, aging=aging, latency_degraded=latency_degraded),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _check(check_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "name": name,
        "passed": passed,
        "effect": effect,
        "reason": reason,
    }


def _operator_message(*, stale: bool, aging: bool, latency_degraded: bool) -> str:
    if stale:
        return "Evidence is stale. Display WAIT and refresh before using any trading idea."
    if aging:
        return "Evidence is near stale. Refresh before promoting confidence or sending any external review packet."
    if latency_degraded:
        return "Evidence is fresh but latency is degraded. Keep the idea research-only and prefer WAIT."
    return "Evidence is fresh enough for research display. It still cannot route orders or override safety gates."
