from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from math import isfinite
from typing import Any


CANDLE_CAUSE_EFFECT_MEMORY_VERSION = "jarvis-candle-cause-effect-memory.v1.17"
MINIMUM_CANDLE_EFFECT_EVIDENCE = 30


def build_candle_cause_effect_memory_report(
    *,
    room: dict[str, Any],
    minimum_sample_size: int = MINIMUM_CANDLE_EFFECT_EVIDENCE,
) -> dict[str, Any]:
    chart = room.get("chart_context", {}) if isinstance(room.get("chart_context"), dict) else {}
    bars = [_normalize_bar(item) for item in chart.get("bars", []) if isinstance(item, dict)]
    bars = [bar for bar in bars if bar is not None]
    previous = _candle_anatomy(bars[-2]) if len(bars) >= 2 else {}
    current = _candle_anatomy(bars[-1]) if len(bars) >= 1 else {}
    cause_effect = _cause_effect_features(previous, current)
    effect_label = _effect_label(previous, current, cause_effect)
    analogs = _historical_analogs(bars, previous, current)
    probabilities = _probabilities(analogs)
    historical_match_count = len(analogs)
    minimum_sample_pass = historical_match_count >= int(minimum_sample_size)
    gates = _gates(bars, previous, current, cause_effect, historical_match_count, minimum_sample_pass)
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    payload = {
        "version": CANDLE_CAUSE_EFFECT_MEMORY_VERSION,
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "current_pair": _current_pair(previous, current),
        "cause_effect_features": cause_effect,
        "effect_label": effect_label,
        "analogs": analogs[:10],
    }
    memory_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "memory_version": CANDLE_CAUSE_EFFECT_MEMORY_VERSION,
        "symbol": str(room.get("symbol") or "UNKNOWN").upper(),
        "timeframe": room.get("timeframe"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "memory_hash": memory_hash,
        "current_pair": _current_pair(previous, current),
        "previous_candle_anatomy": previous,
        "current_candle_anatomy": current,
        "cause_effect_features": cause_effect,
        "effect_label": effect_label,
        "historical_match_count": historical_match_count,
        "minimum_sample_size": int(minimum_sample_size),
        "minimum_sample_pass": minimum_sample_pass,
        "evidence_quality": _evidence_quality(historical_match_count, minimum_sample_pass),
        "best_matching_dates": _best_matching_dates(analogs),
        "analog_examples": analogs[:8],
        "continuation_probability_pct": probabilities["continuation"],
        "reversal_probability_pct": probabilities["reversal"],
        "fakeout_probability_pct": probabilities["fakeout"],
        "range_probability_pct": probabilities["range"],
        "expected_next_effect": _expected_next_effect(probabilities, minimum_sample_pass),
        "no_trade_reason": None if minimum_sample_pass else "Low evidence. Candle cause/effect history is not enough.",
        "gates": gates,
        "memory_state": "blocked" if blockers else "warning" if warnings else "research_ready",
        "operator_message": _operator_message(blockers, warnings, effect_label),
        "point_in_time_safe": True,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _normalize_bar(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        bar = {
            "timestamp_ns": int(item.get("timestamp_ns") or 0),
            "open": float(item.get("open")),
            "high": float(item.get("high")),
            "low": float(item.get("low")),
            "close": float(item.get("close")),
            "volume": float(item.get("volume") or 0.0),
        }
    except (TypeError, ValueError):
        return None
    values = [bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"]]
    if not all(isfinite(value) for value in values):
        return None
    if bar["high"] < max(bar["open"], bar["close"]) or bar["low"] > min(bar["open"], bar["close"]) or bar["high"] < bar["low"]:
        return None
    return bar


def _candle_anatomy(bar: dict[str, Any]) -> dict[str, Any]:
    candle_range = max(float(bar["high"]) - float(bar["low"]), 1e-9)
    body = abs(float(bar["close"]) - float(bar["open"]))
    upper = float(bar["high"]) - max(float(bar["open"]), float(bar["close"]))
    lower = min(float(bar["open"]), float(bar["close"])) - float(bar["low"])
    body_pct = round((body / candle_range) * 100.0, 4)
    upper_pct = round((max(upper, 0.0) / candle_range) * 100.0, 4)
    lower_pct = round((max(lower, 0.0) / candle_range) * 100.0, 4)
    close_location = round(((float(bar["close"]) - float(bar["low"])) / candle_range) * 100.0, 4)
    direction = "bullish" if bar["close"] > bar["open"] else "bearish" if bar["close"] < bar["open"] else "doji"
    wick_dominance = "upper" if upper_pct > lower_pct + 15 else "lower" if lower_pct > upper_pct + 15 else "balanced"
    no_upper_wick = upper_pct <= 2.5
    no_lower_wick = lower_pct <= 2.5
    return {
        "timestamp_ns": bar["timestamp_ns"],
        "open": round(bar["open"], 4),
        "high": round(bar["high"], 4),
        "low": round(bar["low"], 4),
        "close": round(bar["close"], 4),
        "volume": round(bar["volume"], 4),
        "range": round(candle_range, 6),
        "body_pct": body_pct,
        "upper_wick_pct": upper_pct,
        "lower_wick_pct": lower_pct,
        "close_location_value": close_location,
        "direction": direction,
        "wick_dominance": "no_wick" if no_upper_wick and no_lower_wick else wick_dominance,
        "no_upper_wick": no_upper_wick,
        "no_lower_wick": no_lower_wick,
        "marubozu_like": body_pct >= 90.0 and no_upper_wick and no_lower_wick,
        "long_body": body_pct >= 65.0,
        "small_body": body_pct <= 25.0,
    }


def _cause_effect_features(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if not previous or not current:
        return {"available": False}
    previous_range = max(float(previous.get("range") or 0.0), 1e-9)
    current_range = max(float(current.get("range") or 0.0), 1e-9)
    return {
        "available": True,
        "body_pct_delta": round(float(current["body_pct"]) - float(previous["body_pct"]), 4),
        "upper_wick_pct_delta": round(float(current["upper_wick_pct"]) - float(previous["upper_wick_pct"]), 4),
        "lower_wick_pct_delta": round(float(current["lower_wick_pct"]) - float(previous["lower_wick_pct"]), 4),
        "range_expansion_ratio": round(current_range / previous_range, 4),
        "close_shift": round(float(current["close"]) - float(previous["close"]), 4),
        "direction_changed": previous.get("direction") != current.get("direction"),
        "previous_no_wick": bool(previous.get("no_upper_wick")) and bool(previous.get("no_lower_wick")),
        "current_no_wick": bool(current.get("no_upper_wick")) and bool(current.get("no_lower_wick")),
        "previous_upper_rejection": float(previous.get("upper_wick_pct") or 0.0) >= 35.0,
        "previous_lower_rejection": float(previous.get("lower_wick_pct") or 0.0) >= 35.0,
        "current_upper_rejection": float(current.get("upper_wick_pct") or 0.0) >= 35.0,
        "current_lower_rejection": float(current.get("lower_wick_pct") or 0.0) >= 35.0,
        "long_body_to_pullback": bool(previous.get("long_body")) and bool(current.get("direction") != previous.get("direction")),
    }


def _effect_label(previous: dict[str, Any], current: dict[str, Any], features: dict[str, Any]) -> str:
    if not features.get("available"):
        return "insufficient_candle_pair"
    if features["previous_upper_rejection"] and current.get("direction") == "bearish":
        return "upper_wick_rejection_followed_by_bearish_effect"
    if features["previous_lower_rejection"] and current.get("direction") == "bullish":
        return "lower_wick_rejection_followed_by_bullish_effect"
    if features["previous_no_wick"] and previous.get("direction") == current.get("direction"):
        return "no_wick_trend_follow_through"
    if features["long_body_to_pullback"]:
        return "long_body_followed_by_pullback"
    if float(previous.get("body_pct") or 0.0) <= 25.0 and float(current.get("body_pct") or 0.0) >= 55.0:
        return "compression_to_expansion"
    if features["direction_changed"]:
        return "direction_change_after_prior_candle"
    return "mixed_candle_effect"


def _historical_analogs(bars: list[dict[str, Any]], previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    if len(bars) < 5 or not previous or not current:
        return []
    target_vector = _pair_vector(previous, current)
    analogs: list[dict[str, Any]] = []
    for idx in range(1, len(bars) - 2):
        first = _candle_anatomy(bars[idx - 1])
        second = _candle_anatomy(bars[idx])
        next_bar = _candle_anatomy(bars[idx + 1])
        distance = _distance(target_vector, _pair_vector(first, second))
        similarity = max(0.0, 100.0 - distance)
        if similarity < 42.0:
            continue
        outcome = _outcome_label(first, second, next_bar)
        analogs.append(
            {
                "historical_timestamp_ns": second["timestamp_ns"],
                "historical_date": _timestamp_ns_to_date(second["timestamp_ns"]),
                "similarity_score_pct": round(similarity, 2),
                "previous_direction": first["direction"],
                "current_direction": second["direction"],
                "next_direction": next_bar["direction"],
                "outcome": outcome,
                "body_pair": [first["body_pct"], second["body_pct"]],
                "wick_pair": [
                    {"upper": first["upper_wick_pct"], "lower": first["lower_wick_pct"]},
                    {"upper": second["upper_wick_pct"], "lower": second["lower_wick_pct"]},
                ],
            }
        )
    analogs.sort(key=lambda item: item["similarity_score_pct"], reverse=True)
    return analogs[:80]


def _pair_vector(previous: dict[str, Any], current: dict[str, Any]) -> list[float]:
    return [
        float(previous.get("body_pct") or 0.0),
        float(previous.get("upper_wick_pct") or 0.0),
        float(previous.get("lower_wick_pct") or 0.0),
        float(previous.get("close_location_value") or 0.0),
        float(current.get("body_pct") or 0.0),
        float(current.get("upper_wick_pct") or 0.0),
        float(current.get("lower_wick_pct") or 0.0),
        float(current.get("close_location_value") or 0.0),
        15.0 if previous.get("direction") != current.get("direction") else 0.0,
    ]


def _distance(left: list[float], right: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / max(len(left), 1)


def _outcome_label(first: dict[str, Any], second: dict[str, Any], next_bar: dict[str, Any]) -> str:
    move = float(next_bar["close"]) - float(second["close"])
    threshold = max(float(second.get("range") or 0.0) * 0.15, float(second["close"]) * 0.0002)
    if abs(move) <= threshold:
        return "range"
    if (second["direction"] == "bullish" and move > 0) or (second["direction"] == "bearish" and move < 0):
        return "continuation"
    if (second.get("upper_wick_pct", 0.0) >= 35.0 and move < 0) or (second.get("lower_wick_pct", 0.0) >= 35.0 and move > 0):
        return "fakeout"
    if first["direction"] != second["direction"] or (move > 0 and second["direction"] == "bearish") or (move < 0 and second["direction"] == "bullish"):
        return "reversal"
    return "range"


def _probabilities(analogs: list[dict[str, Any]]) -> dict[str, float]:
    total = max(len(analogs), 1)
    counts = {"continuation": 0, "reversal": 0, "fakeout": 0, "range": 0}
    for item in analogs:
        outcome = item.get("outcome")
        if outcome in counts:
            counts[outcome] += 1
    return {key: round((value / total) * 100.0, 2) for key, value in counts.items()}


def _expected_next_effect(probabilities: dict[str, float], minimum_sample_pass: bool) -> str:
    leader = max(probabilities.items(), key=lambda item: item[1])[0]
    if not minimum_sample_pass:
        return f"low_evidence_{leader}_lean"
    return f"{leader}_most_common_after_similar_candle_pairs"


def _current_pair(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return {
        "previous_timestamp_ns": previous.get("timestamp_ns"),
        "current_timestamp_ns": current.get("timestamp_ns"),
        "previous_direction": previous.get("direction"),
        "current_direction": current.get("direction"),
        "previous_body_pct": previous.get("body_pct"),
        "current_body_pct": current.get("body_pct"),
        "previous_upper_wick_pct": previous.get("upper_wick_pct"),
        "current_upper_wick_pct": current.get("upper_wick_pct"),
        "previous_lower_wick_pct": previous.get("lower_wick_pct"),
        "current_lower_wick_pct": current.get("lower_wick_pct"),
    }


def _evidence_quality(match_count: int, minimum_sample_pass: bool) -> str:
    if match_count >= 100:
        return "HIGH"
    if minimum_sample_pass:
        return "MEDIUM"
    if match_count > 0:
        return "LOW"
    return "NONE"


def _best_matching_dates(analogs: list[dict[str, Any]]) -> list[str]:
    dates: list[str] = []
    for item in analogs:
        date = str(item.get("historical_date") or "")
        if date and date not in dates:
            dates.append(date)
    return dates[:10]


def _timestamp_ns_to_date(timestamp_ns: int) -> str:
    if timestamp_ns <= 0:
        return "unknown"
    try:
        return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return "unknown"


def _gates(
    bars: list[dict[str, Any]],
    previous: dict[str, Any],
    current: dict[str, Any],
    cause_effect: dict[str, Any],
    historical_match_count: int,
    minimum_sample_pass: bool,
) -> list[dict[str, Any]]:
    return [
        _gate("CANDLE-EFFECT-001", "At least two candles are available", len(bars) >= 2, "block", "Need previous and current candle to compare cause/effect."),
        _gate("CANDLE-EFFECT-002", "Previous/current candle anatomy computed", bool(previous and current), "block", "Both candles must have body, wick, range, and close-location features."),
        _gate("CANDLE-EFFECT-003", "Wick/body/no-wick cause-effect features computed", bool(cause_effect.get("available")), "block", "Need wick/body deltas before judging candle influence."),
        _gate("CANDLE-EFFECT-004", "Historical analog pairs exist", historical_match_count > 0, "downgrade", "Past adjacent candle pairs are needed to compare current effect."),
        _gate("CANDLE-EFFECT-005", "Minimum evidence guard passes", minimum_sample_pass, "downgrade", "Do not trust candle effect probability until at least 30 analog pairs."),
        _gate("CANDLE-EFFECT-006", "Point-in-time safe", True, "block", "Only previous/current/past candles are used; future current-session candles are excluded."),
        _gate("CANDLE-EFFECT-007", "No trading authority", True, "block", "Candle cause/effect memory is research-only."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], effect_label: str) -> str:
    if blockers:
        return "Candle cause/effect memory is blocked until previous/current candle anatomy is valid."
    if warnings:
        return f"Candle cause/effect memory found {effect_label}, but low evidence prevents confidence promotion."
    return f"Candle cause/effect memory is research-ready for {effect_label}; it still cannot approve trades or route orders."
