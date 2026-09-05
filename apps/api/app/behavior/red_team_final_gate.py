from __future__ import annotations

from typing import Any

from .indicator_result_cache import save_indicator_results
from .nine_candle_history import _volatility_status
from .nine_candle_reasoning_arbiter import build_reasoning_arbiter_report


RED_TEAM_ID = "TV-PROD-RED-001"
RED_TEAM_VERSION = "tv-prod-red-001.v1"


def build_tv_prod_red_001_report(symbol: str = "RELIANCE", timeframe: str = "1m") -> dict[str, Any]:
    normalized = symbol.upper()
    historical_windows = _historical_volatility_fixture()
    current = {"atr": 2.4, "feature_manifest_version": "nine-candle-feature-manifest.v1"}
    volatility = _volatility_status(current, historical_windows)
    raw_match_count = len(historical_windows)
    matched_after_vol_bucketing = int(volatility["volatility_bucket_window_count"])
    path_report = {
        "volatility_ood": volatility["volatility_ood"],
        "temporal_diversity_score": 0.60,
        "raw_match_window_count": raw_match_count,
        "matched_after_vol_bucketing": matched_after_vol_bucketing,
    }
    ood_report = {
        "ood_flag": True,
        "shape_ood": False,
        "volatility_ood": volatility["volatility_ood"],
    }
    analog_report = {
        "winner_similarity": 0.91,
        "failure_similarity": 0.12,
    }
    arbiter = build_reasoning_arbiter_report(
        normalized,
        timeframe,
        analog_report=analog_report,
        path_report=path_report,
        ood_report=ood_report,
        condition_tags=["manipulated_looking"],
        subsystem_votes={"analog": "LONG", "risk": "LONG", "htf": "LONG", "ood": "WAIT"},
    )
    cache = save_indicator_results(
        normalized,
        timeframe,
        use_real_indicators=True,
        force_recompute=True,
        anomalous_snapshot=True,
    )
    decision = "WAIT" if arbiter["override_to_wait"] or volatility["volatility_ood"] else "WATCH"
    checks = [
        _check("volatility_ood", volatility["volatility_ood"], "volatility_ood must fire before analog confidence."),
        _check("manipulated_flag_consulted", "manipulated_looking" in arbiter["consulted_flags"], "arbiter must consult manipulated_looking."),
        _check(
            "volatility_bucket_reduces_matches",
            matched_after_vol_bucketing < raw_match_count,
            f"matched_after_vol_bucketing={matched_after_vol_bucketing} raw_match_count={raw_match_count}.",
        ),
        _check("continuation_boost_zero", float(arbiter["continuation_boost"]) <= 0.0, "continuation boost must not be positive."),
        _check("decision_wait_or_watch", decision in {"WAIT", "WATCH"}, f"decision={decision}."),
        _check("paper_candidate_blocked", arbiter["paper_candidate_allowed"] is False, "paper candidate must be blocked."),
        _check(
            "cache_quarantined",
            cache["cache_status"] == "anomalous_snapshot_quarantined",
            f"cache_status={cache['cache_status']}.",
        ),
        _check("live_trading_blocked", cache["live_trading_blocked"] is True, "live trading must remain blocked."),
        _check("trade_disallowed", cache["trade_allowed"] is False, "trade_allowed must remain false."),
        _check("order_routing_disabled", cache["order_routing_enabled"] is False, "order routing must remain disabled."),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "red_team_id": RED_TEAM_ID,
        "red_team_version": RED_TEAM_VERSION,
        "symbol": normalized,
        "timeframe": timeframe,
        "scenario": "2.4x ATR manipulated-wick day",
        "passed": passed,
        "release_blocking": not passed,
        "decision": decision,
        "paper_candidate_allowed": False,
        "raw_match_count": raw_match_count,
        "matched_after_vol_bucketing": matched_after_vol_bucketing,
        "volatility_status": volatility,
        "arbiter": arbiter,
        "cache_status": cache["cache_status"],
        "cache_reference_only": cache["reference_only"],
        "checks": checks,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _historical_volatility_fixture() -> list[dict[str, Any]]:
    windows = []
    for index in range(24):
        atr = 0.82 + (index % 8) * 0.035
        windows.append(
            {
                "window_id": f"redteam-hist-{index:02d}",
                "atr": round(atr, 6),
                "volatility_bucket": "normal",
                "feature_manifest_version": "nine-candle-feature-manifest.v1",
            }
        )
    return windows


def _check(check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"check_id": check_id, "passed": bool(passed), "evidence": evidence}
