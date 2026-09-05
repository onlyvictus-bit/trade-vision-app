from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any

from ..models import CandleBar, CandleSeries, now_iso
from .gemini_provider import build_sample_gemini_review_for_display, gemini_summary_for_jarvis
from .jarvis_decision_arbiter import build_jarvis_arbiter_output
from .openalgo_report_importer import summarize_openalgo_report
from .paper_reality_check import build_paper_reality_check


JARVIS_ROOM_VERSION = "jarvis-decision-room.v0.96"
PACKET_VALIDITY_SECONDS = 60
MINIMUM_SAMPLE_SIZE = 30
MAX_SIMILAR_HISTORY = 5


def build_jarvis_decision_room_state(
    *,
    symbol: str,
    timeframe: str,
    series: CandleSeries | None,
    data_quality: Any | None = None,
    system_mode: str = "MOCK",
    kill_switch_active: bool = False,
    kronos_status: Any | None = None,
    openalgo_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    created_at = datetime.now(timezone.utc)
    valid_until = created_at + timedelta(seconds=PACKET_VALIDITY_SECONDS)
    bars = list(series.bars if series else [])
    latest = bars[-1] if bars else None
    candle_structure = _candle_structure(latest)
    indicators = _indicator_snapshot(bars)
    sequential = _sequential_signals(bars, indicators)
    levels = _levels_and_zones(bars, indicators)
    multi_tf = _multi_timeframe_alignment(bars)
    similar = _similar_history(bars)
    safety = _safety_summary(
        data_quality=data_quality,
        kill_switch_active=kill_switch_active,
        match_count=similar["total_matches_found"],
        alignment_score=multi_tf["alignment_score"],
    )
    decision = _trade_vision_decision(
        latest=latest,
        indicators=indicators,
        levels=levels,
        multi_tf=multi_tf,
        similar=similar,
        safety=safety,
    )
    kronos_summary = _kronos_summary(kronos_status)
    gemini_summary = _gemini_summary()
    openalgo_summary = _openalgo_summary(openalgo_report)
    paper_reality = build_paper_reality_check(
        symbol=normalized_symbol,
        trade_vision_decision=decision,
        openalgo_report=openalgo_report,
    )
    extended_widgets = _extended_widgets(
        symbol=normalized_symbol,
        timeframe=timeframe,
        bars=bars,
        decision=decision,
        indicators=indicators,
        levels=levels,
        similar=similar,
        safety=safety,
        paper_reality=paper_reality,
        openalgo_summary=openalgo_summary,
    )
    system_health = _system_health_matrix(
        data_quality=data_quality,
        safety=safety,
        gemini=gemini_summary,
        kronos=kronos_summary,
        kill_switch_active=kill_switch_active,
        series=series,
    )
    packet_payload = {
        "symbol": normalized_symbol,
        "timeframe": timeframe,
        "created_at": created_at.isoformat(),
        "latest_timestamp_ns": latest.timestamp_ns if latest else None,
        "snapshot_id": series.snapshot_id if series else None,
        "decision": decision["final_trade_decision"],
        "safety": safety["overall_status"],
    }
    packet_id = hashlib.sha256(json.dumps(packet_payload, sort_keys=True).encode("utf-8")).hexdigest()[:32]
    response = {
        "room_version": JARVIS_ROOM_VERSION,
        "packet_metadata": {
            "packet_id": packet_id,
            "schema_version": "jarvis.evidence_packet.v1",
            "created_at": created_at.isoformat(),
            "valid_until": valid_until.isoformat(),
            "packet_validity_window_seconds": PACKET_VALIDITY_SECONDS,
            "seconds_to_expiry_at_creation": PACKET_VALIDITY_SECONDS,
            "is_expired": False,
            "data_provenance": {
                "primary_source": "local_user_csv" if series and any(bar.source == "user_csv" for bar in bars) else "mock_or_existing_snapshot",
                "snapshot_id": series.snapshot_id if series else None,
                "single_source_risk": True,
            },
        },
        "mode": system_mode,
        "symbol": normalized_symbol,
        "timeframe": timeframe,
        "chart_context": _chart_context(bars, decision, levels),
        "candle_structure": candle_structure,
        "indicator_snapshot": indicators,
        "sequential_signals": sequential,
        "levels_and_zones": levels,
        "multi_timeframe_alignment": multi_tf,
        "similar_history": similar,
        "trade_vision_decision": decision,
        "kronos_summary": kronos_summary,
        "gemini_summary": gemini_summary,
        "gemini_review_summary": {},
        "openalgo_summary": openalgo_summary,
        "paper_reality_check": paper_reality,
        "extended_widgets": extended_widgets,
        "safety_summary": safety,
        "system_health_matrix": system_health,
        "ui_contract": _ui_panel_contract(),
        "final_action": decision["final_trade_decision"],
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "notes": [
            "Jarvis v0.96 adds persisted usefulness tracking while keeping existing panels unchanged.",
            "Gemini, Kronos, and OpenAlgo are advisory. Trade Vision safety remains authority.",
            "This response is research-only and cannot route orders.",
        ],
    }
    evidence_packet = {
        "trade_vision_decision": response["trade_vision_decision"],
        "candle_structure": response["candle_structure"],
        "indicator_snapshot": response["indicator_snapshot"],
        "multi_timeframe_alignment": response["multi_timeframe_alignment"],
        "similar_history": response["similar_history"],
        "safety_summary": response["safety_summary"],
        "final_action": response["final_action"],
    }
    response["gemini_review_summary"] = build_sample_gemini_review_for_display(evidence_packet)
    response["decision_arbiter"] = build_jarvis_arbiter_output(
        trade_vision_decision=response["trade_vision_decision"],
        gemini_review=response["gemini_review_summary"],
        kronos_summary=response["kronos_summary"],
        openalgo_summary=response["openalgo_summary"],
        safety_summary=response["safety_summary"],
        multi_timeframe_alignment=response["multi_timeframe_alignment"],
        paper_reality_check=response["paper_reality_check"],
    )
    response["final_action"] = response["decision_arbiter"]["final_action"]
    return response


def _candle_structure(bar: CandleBar | None) -> dict[str, Any]:
    if not bar:
        return {"available": False, "pattern": "no_candle"}
    candle_range = max(bar.high - bar.low, 1e-9)
    body = abs(bar.close - bar.open)
    upper = bar.high - max(bar.open, bar.close)
    lower = min(bar.open, bar.close) - bar.low
    body_pct = body / candle_range * 100.0
    upper_pct = upper / candle_range * 100.0
    lower_pct = lower / candle_range * 100.0
    close_location = (bar.close - bar.low) / candle_range
    pattern = "trend_candle" if body_pct >= 65 else "wick_rejection" if max(upper_pct, lower_pct) >= 45 else "balanced_candle"
    if body_pct <= 15:
        pattern = "compression_or_doji"
    return {
        "available": True,
        "timestamp_ns": bar.timestamp_ns,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "body_pct": round(body_pct, 2),
        "upper_wick_pct": round(upper_pct, 2),
        "lower_wick_pct": round(lower_pct, 2),
        "close_location_value": round(close_location, 4),
        "pattern": pattern,
    }


def _indicator_snapshot(bars: list[CandleBar]) -> dict[str, Any]:
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    volumes = [float(bar.volume or 0.0) for bar in bars]
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(highs, lows, closes, 14)
    vwap = _vwap(bars)
    macd = _ema(closes, 12) - _ema(closes, 26) if len(closes) >= 26 else 0.0
    vol_z = 0.0
    if len(volumes) >= 20:
        window = volumes[-20:]
        stdev = pstdev(window) or 1.0
        vol_z = (window[-1] - mean(window)) / stdev
    price = closes[-1] if closes else 0.0
    return {
        "rsi14": round(rsi14, 2),
        "ema9": round(ema9, 4),
        "ema21": round(ema21, 4),
        "ema_state": "bullish" if ema9 > ema21 else "bearish" if ema9 < ema21 else "neutral",
        "vwap": round(vwap, 4),
        "vwap_position": "above_vwap" if price > vwap else "below_vwap" if price < vwap else "at_vwap",
        "atr14": round(atr14, 4),
        "macd_value": round(macd, 4),
        "macd_state": "positive" if macd > 0 else "negative" if macd < 0 else "neutral",
        "volume_z": round(vol_z, 2),
        "indicator_count_v086": 7,
        "full_indicator_matrix_status": "existing_indicator_registry_drilldown_remains_in_old_panels",
    }


def _sequential_signals(bars: list[CandleBar], indicators: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if len(bars) < 3:
        return signals
    latest = bars[-1]
    previous = bars[-2]
    if indicators["ema_state"] == "bullish":
        signals.append({"name": "EMA9 above EMA21", "timing": "current", "direction": "bullish"})
    if indicators["vwap_position"] == "above_vwap" and previous.close <= indicators["vwap"] <= latest.close:
        signals.append({"name": "VWAP reclaim", "timing": "latest candle", "direction": "bullish"})
    if indicators["rsi14"] >= 60:
        signals.append({"name": "RSI above 60", "timing": "current", "direction": "bullish"})
    if indicators["volume_z"] >= 1.5:
        signals.append({"name": "Volume expansion", "timing": "current", "direction": "participation"})
    for idx, bar in enumerate(bars[-5:], start=max(1, len(bars) - 4)):
        candle_range = max(bar.high - bar.low, 1e-9)
        if abs(bar.close - bar.open) / candle_range <= 0.15:
            signals.append({"name": "Small body compression candle", "timing": f"sequence-{idx}", "direction": "compression"})
    return signals[:8]


def _levels_and_zones(bars: list[CandleBar], indicators: dict[str, Any]) -> dict[str, Any]:
    if not bars:
        return {}
    window = bars[-50:]
    support = min(bar.low for bar in window)
    resistance = max(bar.high for bar in window)
    latest = bars[-1].close
    return {
        "nearest_support": round(support, 4),
        "nearest_resistance": round(resistance, 4),
        "vwap": indicators["vwap"],
        "distance_to_support_pct": round((latest - support) / latest * 100.0, 3) if latest else 0.0,
        "distance_to_resistance_pct": round((resistance - latest) / latest * 100.0, 3) if latest else 0.0,
        "entry_zone_research_only": _entry_zone(latest, indicators["vwap"]),
    }


def _multi_timeframe_alignment(bars: list[CandleBar]) -> dict[str, Any]:
    states = {
        "1m": _trend_state(bars[-20:]),
        "5m": _trend_state(_compress_bars(bars, 5)[-20:]),
        "15m": _trend_state(_compress_bars(bars, 15)[-20:]),
        "1H": "not_available_closed_candle_only",
        "daily": "not_available_closed_candle_only",
    }
    bullish = sum(1 for state in states.values() if state == "bullish")
    bearish = sum(1 for state in states.values() if state == "bearish")
    available = bullish + bearish + sum(1 for state in states.values() if state == "neutral")
    alignment = max(bullish, bearish) / available if available else 0.0
    conflict = "none"
    if bullish and bearish:
        conflict = "lower_timeframe_conflict"
    return {
        "timeframes": states,
        "alignment_score": round(alignment, 3),
        "dominant_conflict": conflict,
        "htf_confirmation_available": False,
        "arbiter_modifier": "downgrade_to_watch_until_closed_htf_confirmation",
    }


def _similar_history(bars: list[CandleBar]) -> dict[str, Any]:
    lookback = 30
    if len(bars) < lookback * 2:
        return {"minimum_sample_pass": False, "total_matches_found": 0, "matches_used": 0, "matches": [], "evidence_quality": "LOW"}
    target = _shape_vector(bars[-lookback:])
    matches: list[dict[str, Any]] = []
    for start in range(0, len(bars) - lookback * 2, lookback):
        sample = bars[start : start + lookback]
        score = _cosine(target, _shape_vector(sample))
        matches.append(
            {
                "start_timestamp_ns": sample[0].timestamp_ns,
                "end_timestamp_ns": sample[-1].timestamp_ns,
                "similarity_score_pct": round(score * 100.0, 2),
                "outcome": "unknown_until_outcome_labeler_links_full_history",
            }
        )
    matches.sort(key=lambda row: row["similarity_score_pct"], reverse=True)
    return {
        "minimum_sample_pass": len(matches) >= MINIMUM_SAMPLE_SIZE,
        "minimum_sample_size": MINIMUM_SAMPLE_SIZE,
        "total_matches_found": len(matches),
        "matches_used": min(len(matches), MAX_SIMILAR_HISTORY),
        "matches": matches[:MAX_SIMILAR_HISTORY],
        "evidence_quality": "STRONG" if len(matches) >= 100 else "MEDIUM" if len(matches) >= MINIMUM_SAMPLE_SIZE else "LOW",
    }


def _trade_vision_decision(
    *,
    latest: CandleBar | None,
    indicators: dict[str, Any],
    levels: dict[str, Any],
    multi_tf: dict[str, Any],
    similar: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, Any]:
    scenario = _scenario_read(latest, indicators, levels, multi_tf, similar, safety)
    if not latest:
        final = "NO_TRADE"
        reason = "No candle evidence is available."
    elif safety["blocking_gates"]:
        final = "NO_TRADE"
        reason = f"Blocked by {', '.join(safety['blocking_gates'])}."
    elif scenario["bias"] == "bearish_rejection":
        final = "WATCH_ONLY"
        reason = "Current candle and indicator evidence show rejection/weakness; do not chase long entries."
    elif not similar["minimum_sample_pass"]:
        final = "WATCH_ONLY"
        reason = "Evidence packet is usable for research, but similar-history minimum sample has not passed."
    elif multi_tf["alignment_score"] < 0.5:
        final = "WAIT"
        reason = "Multi-timeframe agreement is weak; wait for closed higher-timeframe confirmation."
    else:
        final = "WAIT"
        reason = "Research candidate requires retest confirmation before any paper-only consideration."
    entry_low, entry_high = levels.get("entry_zone_research_only", [latest.close if latest else 0.0, latest.close if latest else 0.0])
    atr = max(float(indicators.get("atr14") or 0.0), 0.01)
    stop = entry_low - 2.0 * atr
    target = entry_high + 3.0 * (entry_high - stop)
    wait_for = _wait_conditions(scenario, indicators, levels, similar)
    invalidation = _invalidation_rules(scenario, levels, indicators)
    rejected = _rejected_alternatives(final, scenario, similar, multi_tf, safety)
    confidence_cap = _confidence_cap(similar, safety, multi_tf)
    return {
        "decision_version": "jarvis-trade-vision-decision-guide.v0.87",
        "final_trade_decision": final,
        "scenario_label": scenario["label"],
        "scenario_bias": scenario["bias"],
        "entry_condition": f"Research-only: {wait_for[0] if wait_for else f'wait for retest hold inside {entry_low:.2f}-{entry_high:.2f}'}; no live execution.",
        "best_entry_zone": [round(entry_low, 4), round(entry_high, 4)],
        "stop_loss": round(stop, 4),
        "target": round(target, 4),
        "risk_reward": 3.0,
        "invalidation_level": round(min(levels.get("nearest_support", stop), indicators.get("vwap", stop)), 4),
        "wait_for": wait_for,
        "avoid_if": invalidation,
        "confidence_cap_pct": confidence_cap,
        "no_trade_reason": reason if final in {"NO_TRADE", "WAIT", "WATCH_ONLY"} else None,
        "rejected_alternatives": rejected,
        "reason_tree": [
            f"Scenario: {scenario['label']} ({scenario['bias']}).",
            reason,
            f"Confidence capped at {confidence_cap}% by evidence, safety, and multi-timeframe checks.",
            "Trade allowance remains false until replay, evidence, risk, and human approval gates pass.",
        ],
        "cost_and_execution_note": "v0.87 estimates entry/SL/target only. Full OpenAlgo slippage, brokerage, STT, and fill-quality validation arrives in v0.93-v0.94.",
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _scenario_read(
    latest: CandleBar | None,
    indicators: dict[str, Any],
    levels: dict[str, Any],
    multi_tf: dict[str, Any],
    similar: dict[str, Any],
    safety: dict[str, Any],
) -> dict[str, str]:
    if not latest:
        return {"label": "no active candle evidence", "bias": "blocked"}
    if safety["blocking_gates"]:
        return {"label": "safety blocked", "bias": "blocked"}
    upper_rejection = levels.get("distance_to_resistance_pct", 100.0) <= 0.6 and indicators.get("vwap_position") == "below_vwap"
    bearish_stack = indicators.get("ema_state") == "bearish" and indicators.get("macd_state") == "negative"
    if upper_rejection or bearish_stack:
        return {"label": "wick rejection below VWAP", "bias": "bearish_rejection"}
    if indicators.get("vwap_position") == "above_vwap" and indicators.get("ema_state") == "bullish" and indicators.get("rsi14", 0.0) >= 55:
        return {"label": "VWAP pullback continuation attempt", "bias": "bullish_watch"}
    if similar.get("minimum_sample_pass") is False:
        return {"label": "low-evidence analog match", "bias": "research_only"}
    if multi_tf.get("alignment_score", 0.0) < 0.5:
        return {"label": "multi-timeframe conflict", "bias": "wait_for_confirmation"}
    return {"label": "mixed evidence", "bias": "wait"}


def _wait_conditions(scenario: dict[str, str], indicators: dict[str, Any], levels: dict[str, Any], similar: dict[str, Any]) -> list[str]:
    entry = levels.get("entry_zone_research_only", [0.0, 0.0])
    conditions = [
        f"wait for price to hold/reclaim the research entry zone {entry[0]:.2f}-{entry[1]:.2f}",
        "wait for a closed candle above VWAP before considering any long-side paper candidate",
        "wait for similar-history evidence to reach at least 30 valid matches before trusting probability",
    ]
    if scenario["bias"] == "bearish_rejection":
        conditions.insert(0, "wait for rejection to fail and price to reclaim VWAP with improving EMA/MACD state")
    if indicators.get("volume_z", 0.0) < 0:
        conditions.append("wait for volume participation to return above baseline")
    if similar.get("minimum_sample_pass"):
        conditions = [condition for condition in conditions if "similar-history evidence" not in condition]
    return conditions[:5]


def _invalidation_rules(scenario: dict[str, str], levels: dict[str, Any], indicators: dict[str, Any]) -> list[str]:
    rules = [
        f"avoid if price closes below support {levels.get('nearest_support', 0.0):.2f}",
        f"avoid if price remains below VWAP {indicators.get('vwap', 0.0):.2f}",
        "avoid if a new upper-wick rejection forms near resistance without follow-through",
        "avoid if higher timeframe closed-candle confirmation remains unavailable",
    ]
    if scenario["bias"] == "bearish_rejection":
        rules.insert(0, "avoid long breakout ideas while rejection candle structure remains active")
    return rules[:5]


def _rejected_alternatives(
    final: str,
    scenario: dict[str, str],
    similar: dict[str, Any],
    multi_tf: dict[str, Any],
    safety: dict[str, Any],
) -> list[dict[str, str]]:
    rejected = [
        {"alternative": "BUY_NOW", "rejection_reason": "Jarvis v0.87 does not allow immediate execution; it only provides research guidance."},
        {"alternative": "AI_OVERRIDE", "rejection_reason": "External AI cannot override Trade Vision safety authority."},
    ]
    if scenario["bias"] == "bearish_rejection":
        rejected.append({"alternative": "BUY_BREAKOUT", "rejection_reason": "Current evidence is rejection/weakness, not clean continuation."})
    if not similar.get("minimum_sample_pass"):
        rejected.append({"alternative": "HIGH_CONFIDENCE_PROBABILITY", "rejection_reason": f"Only {similar.get('total_matches_found', 0)} analog windows found; minimum is {MINIMUM_SAMPLE_SIZE}."})
    if multi_tf.get("alignment_score", 0.0) < 0.5:
        rejected.append({"alternative": "TIMEFRAME_CONFIDENT_ENTRY", "rejection_reason": "Multi-timeframe alignment is below the Jarvis decision threshold."})
    if safety.get("blocking_gates"):
        rejected.append({"alternative": final, "rejection_reason": f"Safety blocking gates are active: {', '.join(safety['blocking_gates'])}."})
    return rejected


def _confidence_cap(similar: dict[str, Any], safety: dict[str, Any], multi_tf: dict[str, Any]) -> int:
    cap = 75
    if safety.get("blocking_gates"):
        cap = min(cap, 0)
    if not similar.get("minimum_sample_pass"):
        cap = min(cap, 45)
    if multi_tf.get("alignment_score", 0.0) < 0.5:
        cap = min(cap, 50)
    if safety.get("warning_gates"):
        cap = min(cap, 55)
    return cap


def _safety_summary(*, data_quality: Any | None, kill_switch_active: bool, match_count: int, alignment_score: float) -> dict[str, Any]:
    quality_score = float(getattr(data_quality, "data_quality_score", 0.0) or 0.0) if data_quality is not None else 0.0
    blocking: list[str] = []
    warnings: list[str] = []
    if kill_switch_active:
        blocking.append("KILL_SWITCH")
    if data_quality is not None and bool(getattr(data_quality, "blocks_trade", False)):
        blocking.append("DATA_QUALITY")
    if match_count < MINIMUM_SAMPLE_SIZE:
        warnings.append("MINIMUM_EVIDENCE")
    if alignment_score < 0.5:
        warnings.append("MULTI_TIMEFRAME_CONFLICT")
    return {
        "overall_status": "blocked" if blocking else "warning" if warnings else "research_ready",
        "blocking_gates": blocking,
        "warning_gates": warnings,
        "data_quality_score": round(quality_score, 4),
        "minimum_evidence_pass": match_count >= MINIMUM_SAMPLE_SIZE,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _kronos_summary(status: Any | None) -> dict[str, Any]:
    return {
        "status": getattr(status, "service_status", "reserved") if status else "reserved",
        "mode": getattr(status, "mode", "unknown") if status else "unknown",
        "role": "forecast_prior_only",
        "can_execute_orders": False,
        "can_override_no_trade": False,
    }


def _gemini_summary() -> dict[str, Any]:
    return gemini_summary_for_jarvis()


def _openalgo_summary(report: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summarize_openalgo_report(report)
    summary["role"] = "paper_execution_reality_only"
    summary["can_override_safety"] = False
    return summary


def _system_health_matrix(
    *,
    data_quality: Any | None,
    safety: dict[str, Any],
    gemini: dict[str, Any],
    kronos: dict[str, Any],
    kill_switch_active: bool,
    series: CandleSeries | None,
) -> dict[str, Any]:
    rows = [
        _health_row("data_feed", "healthy" if series and series.bars else "degraded", f"{len(series.bars) if series else 0} bars in active packet."),
        _health_row("data_quality", "healthy" if safety["data_quality_score"] >= 0.90 else "degraded", f"quality={safety['data_quality_score']:.3f}"),
        _health_row("database_snapshot", "healthy" if series and series.snapshot_id else "degraded", f"snapshot={series.snapshot_id if series else None}"),
        _health_row("gemini", "reserved" if gemini["status"] == "unavailable" else "degraded", f"{gemini['configured_key_slots']}/{gemini['fallback_key_slots_supported']} keys configured."),
        _health_row("kronos", "healthy" if kronos["status"] in {"ready", "mock_ready"} else "reserved", f"mode={kronos['mode']}"),
        _health_row("kill_switch", "blocked" if kill_switch_active else "healthy", "active" if kill_switch_active else "inactive"),
        _health_row("order_routing", "blocked", "Trade Vision Jarvis has no live order route."),
    ]
    severe = {row["status"] for row in rows}
    if "blocked" in severe and kill_switch_active:
        overall = "blocked"
    elif safety["blocking_gates"]:
        overall = "blocked"
    elif safety["warning_gates"] or "degraded" in severe:
        overall = "degraded"
    else:
        overall = "healthy"
    return {
        "health_version": "jarvis-system-health.v0.88",
        "overall_health": overall,
        "rows": rows,
        "persistent_banner_required": overall != "healthy",
        "refresh_interval_seconds": 10,
    }


def _health_row(component: str, status: str, detail: str) -> dict[str, str]:
    return {"component": component, "status": status, "detail": detail}


def _extended_widgets(
    *,
    symbol: str,
    timeframe: str,
    bars: list[CandleBar],
    decision: dict[str, Any],
    indicators: dict[str, Any],
    levels: dict[str, Any],
    similar: dict[str, Any],
    safety: dict[str, Any],
    paper_reality: dict[str, Any],
    openalgo_summary: dict[str, Any],
) -> dict[str, Any]:
    latest = bars[-1] if bars else None
    analogs = [
        {
            "label": f"Analog {idx + 1}",
            "timestamp_ns": match["start_timestamp_ns"],
            "similarity_score_pct": match["similarity_score_pct"],
            "outcome": match["outcome"],
            "verify_hint": "Open similar day replay before trusting this analog.",
        }
        for idx, match in enumerate(similar.get("matches", [])[:5])
    ]
    warning_count = len(safety.get("warning_gates", [])) + len(paper_reality.get("jarvis_effect", {}).get("reasons", []))
    block_count = len(safety.get("blocking_gates", []))
    confidence_cap = float(decision.get("confidence_cap_pct", 0.0) or 0.0)
    evidence_quality = similar.get("evidence_quality", "LOW")
    priority_score = _priority_score(confidence_cap, evidence_quality, block_count, warning_count, paper_reality)
    checklist = [
        _check_item("1", "Confirm latest candle context", latest is not None, f"latest={latest.timestamp_ns if latest else None}"),
        _check_item("2", "Review wait condition before entry", bool(decision.get("wait_for")), str((decision.get("wait_for") or ["missing"])[0])),
        _check_item("3", "Check similar-history sample size", bool(similar.get("minimum_sample_pass")), f"{similar.get('total_matches_found', 0)}/{similar.get('minimum_sample_size', MINIMUM_SAMPLE_SIZE)} matches"),
        _check_item("4", "Check execution reality", paper_reality.get("jarvis_effect", {}).get("effect") not in {"WAIT", "NO_TRADE"}, paper_reality.get("jarvis_effect", {}).get("effect", "unknown")),
        _check_item("5", "Confirm OpenAlgo remains report-only", not bool(openalgo_summary.get("order_routing_enabled")), "routing disabled"),
    ]
    return {
        "widgets_version": "jarvis-extended-widgets.v0.95",
        "symbol": symbol,
        "timeframe": timeframe,
        "decision_history": {
            "mode": "session_local_snapshot",
            "items": [
                {
                    "label": "current_packet",
                    "final_action": decision.get("final_trade_decision", "WAIT"),
                    "scenario": decision.get("scenario_label", "unknown"),
                    "confidence_cap_pct": confidence_cap,
                    "paper_reality_effect": paper_reality.get("jarvis_effect", {}).get("effect", "unknown"),
                    "openalgo_status": openalgo_summary.get("status", "reserved"),
                }
            ],
            "retention_note": "v0.95 shows current packet history; v0.96 adds persisted usefulness tracking.",
        },
        "trust_score_dashboard": {
            "trust_score_pct": priority_score,
            "evidence_quality": evidence_quality,
            "similar_matches": similar.get("total_matches_found", 0),
            "warning_count": warning_count,
            "block_count": block_count,
            "confidence_cap_pct": confidence_cap,
            "trust_label": "usable_research" if priority_score >= 60 else "watch_only" if priority_score >= 35 else "low_trust",
        },
        "watchlist_priority_ranker": {
            "rank": 1,
            "priority_score_pct": priority_score,
            "priority_label": "study_now" if priority_score >= 60 else "monitor" if priority_score >= 35 else "low_priority",
            "drivers": _priority_drivers(decision, indicators, levels, similar, paper_reality),
            "cannot_auto_trade": True,
        },
        "analog_timeline": {
            "items": analogs,
            "empty_state": "No similar analog windows are available yet." if not analogs else None,
        },
        "action_checklist": {
            "items": checklist,
            "ready_count": sum(1 for item in checklist if item["passed"]),
            "total_count": len(checklist),
            "operator_message": "Use this checklist to decide what to inspect next. It is not an execution approval.",
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _priority_score(
    confidence_cap: float,
    evidence_quality: str,
    block_count: int,
    warning_count: int,
    paper_reality: dict[str, Any],
) -> int:
    quality_bonus = {"STRONG": 25, "MEDIUM": 12, "LOW": 0}.get(evidence_quality, 0)
    paper_effect = paper_reality.get("jarvis_effect", {}).get("effect", "REVIEW_ONLY")
    paper_penalty = 35 if paper_effect == "NO_TRADE" else 18 if paper_effect == "WAIT" else 0
    raw = confidence_cap + quality_bonus - block_count * 40 - warning_count * 6 - paper_penalty
    return int(max(0, min(round(raw), 100)))


def _priority_drivers(
    decision: dict[str, Any],
    indicators: dict[str, Any],
    levels: dict[str, Any],
    similar: dict[str, Any],
    paper_reality: dict[str, Any],
) -> list[str]:
    drivers = [
        f"scenario={decision.get('scenario_label', 'unknown')}",
        f"vwap={indicators.get('vwap_position', 'unknown')}",
        f"resistance_distance={levels.get('distance_to_resistance_pct', 'unknown')}%",
        f"similar_history={similar.get('evidence_quality', 'LOW')}",
        f"paper_reality={paper_reality.get('jarvis_effect', {}).get('effect', 'unknown')}",
    ]
    return drivers


def _check_item(step: str, label: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "step": step,
        "label": label,
        "passed": bool(passed),
        "detail": detail,
    }


def _ui_panel_contract() -> dict[str, Any]:
    panels = [
        {
            "panel_id": "chart_evidence",
            "title": "Chart Evidence",
            "required": True,
            "uses": ["chart_context", "levels_and_zones", "trade_vision_decision"],
        },
        {
            "panel_id": "evidence_inspector",
            "title": "Evidence Inspector",
            "required": True,
            "uses": ["candle_structure", "indicator_snapshot", "sequential_signals", "similar_history"],
        },
        {
            "panel_id": "trade_vision_decision",
            "title": "Trade Vision Decision",
            "required": True,
            "uses": ["trade_vision_decision", "multi_timeframe_alignment"],
        },
        {
            "panel_id": "external_review_slots",
            "title": "Gemini / Kronos / OpenAlgo",
            "required": True,
            "uses": ["gemini_summary", "kronos_summary", "openalgo_summary"],
        },
        {
            "panel_id": "decision_arbiter_safety",
            "title": "Safety And Arbiter",
            "required": True,
            "uses": ["safety_summary", "system_health_matrix"],
        },
        {
            "panel_id": "extended_widgets",
            "title": "Extended Jarvis Widgets",
            "required": True,
            "uses": ["extended_widgets", "paper_reality_check", "similar_history"],
        },
    ]
    return {
        "ui_contract_version": "jarvis-decision-room-ui.v0.95",
        "core_panel_count": len(panels),
        "core_panels": panels,
        "old_panels_preserved": True,
        "frontend_route": "#jarvis",
    }


def _chart_context(bars: list[CandleBar], decision: dict[str, Any], levels: dict[str, Any]) -> dict[str, Any]:
    recent = bars[-120:]
    return {
        "bar_count": len(bars),
        "visible_bar_count": len(recent),
        "latest_close": recent[-1].close if recent else None,
        "overlays": {
            "entry_zone": decision["best_entry_zone"],
            "stop_loss": decision["stop_loss"],
            "target": decision["target"],
            "support": levels.get("nearest_support"),
            "resistance": levels.get("nearest_resistance"),
            "vwap": levels.get("vwap"),
        },
        "bars": [
            {"timestamp_ns": bar.timestamp_ns, "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close, "volume": bar.volume}
            for bar in recent
        ],
    }


def _entry_zone(price: float, vwap: float) -> list[float]:
    center = vwap if vwap else price
    width = max(price * 0.001, 0.01)
    return [round(center - width, 4), round(center + width, 4)]


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result = value * alpha + result * (1.0 - alpha)
    return result


def _rsi(closes: list[float], period: int) -> float:
    if len(closes) <= period:
        return 50.0
    gains: list[float] = []
    losses: list[float] = []
    for prev, cur in zip(closes[-period - 1 : -1], closes[-period:]):
        delta = cur - prev
        gains.append(max(delta, 0.0))
        losses.append(abs(min(delta, 0.0)))
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> float:
    if len(closes) < 2:
        return 0.0
    trs: list[float] = []
    start = max(1, len(closes) - period)
    for idx in range(start, len(closes)):
        trs.append(max(highs[idx] - lows[idx], abs(highs[idx] - closes[idx - 1]), abs(lows[idx] - closes[idx - 1])))
    return mean(trs) if trs else 0.0


def _vwap(bars: list[CandleBar]) -> float:
    pv = 0.0
    vol = 0.0
    for bar in bars:
        volume = float(bar.volume or 0.0)
        typical = (bar.high + bar.low + bar.close) / 3.0
        pv += typical * volume
        vol += volume
    return pv / vol if vol else (bars[-1].close if bars else 0.0)


def _compress_bars(bars: list[CandleBar], size: int) -> list[CandleBar]:
    compressed: list[CandleBar] = []
    for offset in range(0, len(bars), size):
        chunk = bars[offset : offset + size]
        if len(chunk) < size:
            continue
        compressed.append(
            CandleBar(
                symbol=chunk[-1].symbol,
                timeframe=chunk[-1].timeframe,
                timestamp_ns=chunk[-1].timestamp_ns,
                open=chunk[0].open,
                high=max(bar.high for bar in chunk),
                low=min(bar.low for bar in chunk),
                close=chunk[-1].close,
                volume=sum(float(bar.volume or 0.0) for bar in chunk),
                source=chunk[-1].source,
                sequence_number=len(compressed) + 1,
            )
        )
    return compressed


def _trend_state(bars: list[CandleBar]) -> str:
    if len(bars) < 3:
        return "neutral"
    change = (bars[-1].close - bars[0].open) / bars[0].open
    if change > 0.002:
        return "bullish"
    if change < -0.002:
        return "bearish"
    return "neutral"


def _shape_vector(bars: list[CandleBar]) -> list[float]:
    first = bars[0].open or 1.0
    vector: list[float] = []
    for bar in bars:
        candle_range = max(bar.high - bar.low, 1e-9)
        vector.extend(
            [
                (bar.close - first) / first,
                abs(bar.close - bar.open) / candle_range,
                (bar.high - max(bar.open, bar.close)) / candle_range,
                (min(bar.open, bar.close) - bar.low) / candle_range,
            ]
        )
    return vector


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    lnorm = math.sqrt(sum(a * a for a in left))
    rnorm = math.sqrt(sum(b * b for b in right))
    if lnorm == 0 or rnorm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (lnorm * rnorm)))
