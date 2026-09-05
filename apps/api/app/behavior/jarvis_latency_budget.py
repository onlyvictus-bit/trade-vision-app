from __future__ import annotations

from typing import Any


JARVIS_LATENCY_BUDGET_VERSION = "jarvis-latency-budget.v1.27"


def _stage_recommendation(stage: str) -> str:
    recommendations = {
        "decision_room": "Cache imported candle snapshots and chart-derived evidence for the active symbol/timeframe.",
        "combination_similarity": "Use bounded lookback windows before enabling larger historical scans.",
        "indicator_memory": "Precompute indicator-combination memory from immutable snapshots.",
        "candle_memory": "Precompute candle cause/effect memory and refresh it after replay imports.",
        "external_ai_reliability": "Reuse the latest verified external-AI reliability score until fresh review history arrives.",
        "openalgo_transport": "Keep transport checks out of realtime decision loops unless operator handoff is active.",
        "openalgo_handoff": "Treat handoff readiness as a cached safety gate until paper execution is requested.",
        "chart_overlay_qa": "Run full chart-overlay QA on refresh or replay step, not on every evidence poll.",
    }
    return recommendations.get(stage, "Move this stage to cached or asynchronous refresh before realtime use.")


def build_jarvis_latency_budget_report(bundle: dict[str, Any]) -> dict[str, Any]:
    stage_timings = list(bundle.get("stage_timings", []))
    cache = dict(bundle.get("cache", {}))
    total_latency_ms = round(float(bundle.get("total_latency_ms", sum(float(item.get("elapsed_ms", 0.0)) for item in stage_timings))), 3)
    total_budget_ms = float(bundle.get("total_budget_ms", 1_500.0))
    slow_stages = [item for item in stage_timings if item.get("status") != "within_budget"]
    budget_state = "over_budget" if total_latency_ms > total_budget_ms else "warning" if slow_stages else "within_budget"
    recommendations = [
        {
            "stage": item.get("stage", "unknown"),
            "status": item.get("status", "warning"),
            "recommendation": _stage_recommendation(str(item.get("stage", "unknown"))),
        }
        for item in slow_stages
    ]
    if not recommendations:
        recommendations.append(
            {
                "stage": "decision_room",
                "status": "within_budget",
                "recommendation": "Keep the decision room in research/paper mode and continue measuring latency before OpenAlgo handoff.",
            }
        )

    fast_path_safe = (
        bundle.get("trade_allowed") is False
        and bundle.get("order_routing_enabled") is False
        and bundle.get("live_trading_blocked") is True
    )
    return {
        "latency_budget_version": JARVIS_LATENCY_BUDGET_VERSION,
        "assembly_version": bundle.get("assembly_version"),
        "symbol": bundle.get("symbol"),
        "timeframe": bundle.get("timeframe"),
        "budget_state": budget_state,
        "total_latency_ms": total_latency_ms,
        "total_budget_ms": total_budget_ms,
        "slow_stage_count": len(slow_stages),
        "cache_status": cache.get("cache_status", "uncached"),
        "cache_age_seconds": cache.get("cache_age_seconds", 0.0),
        "cache_ttl_seconds": cache.get("cache_ttl_seconds"),
        "cache_fresh": bool(cache.get("cache_fresh", False)),
        "stage_timings": stage_timings,
        "slow_stages": slow_stages,
        "degradation_recommendations": recommendations,
        "fast_path_safe": fast_path_safe,
        "operator_message": (
            "Evidence assembly is measured and safe for research/paper review only. "
            "Slow or stale stages must degrade to WAIT, never to live execution."
        ),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
