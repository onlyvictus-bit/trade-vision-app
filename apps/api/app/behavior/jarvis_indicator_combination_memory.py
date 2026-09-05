from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


INDICATOR_COMBINATION_MEMORY_VERSION = "jarvis-indicator-combination-memory.v1.16"
MINIMUM_SEQUENCE_EVIDENCE = 30


def build_indicator_combination_memory_report(
    *,
    room: dict[str, Any],
    combination_similarity: Any,
) -> dict[str, Any]:
    combo = _as_dict(combination_similarity)
    indicators = room.get("indicator_snapshot", {}) if isinstance(room.get("indicator_snapshot"), dict) else {}
    candle = room.get("candle_structure", {}) if isinstance(room.get("candle_structure"), dict) else {}
    sequential = room.get("sequential_signals", []) if isinstance(room.get("sequential_signals"), list) else []
    sequence = combo.get("sequential_signal_pattern", {}) if isinstance(combo.get("sequential_signal_pattern"), dict) else {}
    matches = combo.get("matches", []) if isinstance(combo.get("matches"), list) else []
    current_signature = _current_signature(indicators, candle, sequential)
    sequence_memory = _sequence_memory(sequence, matches)
    combination_rows = _combination_rows(combo, indicators, candle)
    gates = _gates(combo, sequence_memory, combination_rows)
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    payload = {
        "version": INDICATOR_COMBINATION_MEMORY_VERSION,
        "symbol": room.get("symbol"),
        "timeframe": room.get("timeframe"),
        "current_signature": current_signature,
        "sequence_memory": sequence_memory,
        "combination_rows": combination_rows,
        "gates": gates,
    }
    memory_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "memory_version": INDICATOR_COMBINATION_MEMORY_VERSION,
        "symbol": str(room.get("symbol") or "UNKNOWN").upper(),
        "timeframe": room.get("timeframe"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "memory_hash": memory_hash,
        "current_signature": current_signature,
        "combination_similarity_version": combo.get("combination_similarity_version"),
        "source_output_hash": combo.get("output_hash"),
        "combination_rows": combination_rows,
        "combination_count": len(combination_rows),
        "sequence_memory": sequence_memory,
        "non_same_candle_sequence_detected": bool(sequence_memory.get("non_same_candle_sequence")),
        "historical_match_count": int(combo.get("non_overlap_match_count") or 0),
        "minimum_sample_size": int(combo.get("minimum_match_count") or MINIMUM_SEQUENCE_EVIDENCE),
        "minimum_sample_pass": bool(combo.get("minimum_sample_pass")),
        "evidence_quality": combo.get("evidence_quality", "LOW"),
        "continuation_probability_pct": combo.get("continuation_probability_pct", 0.0),
        "reversal_probability_pct": combo.get("reversal_probability_pct", 0.0),
        "fakeout_probability_pct": combo.get("fakeout_probability_pct", 0.0),
        "range_probability_pct": combo.get("range_probability_pct", 0.0),
        "best_matching_dates": _best_matching_dates(matches),
        "no_trade_reason": _no_trade_reason(combo, sequence_memory),
        "gates": gates,
        "memory_state": "blocked" if blockers else "warning" if warnings else "research_ready",
        "operator_message": _operator_message(blockers, warnings, combo, sequence_memory),
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _current_signature(indicators: dict[str, Any], candle: dict[str, Any], sequential: list[Any]) -> dict[str, Any]:
    return {
        "rsi14": indicators.get("rsi14"),
        "ema_state": indicators.get("ema_state"),
        "vwap_position": indicators.get("vwap_position"),
        "macd_state": indicators.get("macd_state"),
        "volume_z": indicators.get("volume_z"),
        "candle_pattern": candle.get("pattern") or candle.get("candle_behavior"),
        "body_pct": candle.get("body_pct"),
        "upper_wick_pct": candle.get("upper_wick_pct"),
        "lower_wick_pct": candle.get("lower_wick_pct"),
        "sequential_signal_names": [str(item.get("name")) for item in sequential if isinstance(item, dict)],
    }


def _sequence_memory(sequence: dict[str, Any], matches: list[Any]) -> dict[str, Any]:
    ordered = sequence.get("ordered_indicators", []) if isinstance(sequence.get("ordered_indicators"), list) else []
    states = sequence.get("ordered_states", []) if isinstance(sequence.get("ordered_states"), list) else []
    offsets = sequence.get("candle_offsets", []) if isinstance(sequence.get("candle_offsets"), list) else []
    occurrence = int(sequence.get("historical_occurrence_count") or 0)
    return {
        "sequence_id": sequence.get("sequence_id"),
        "sequence_hash": sequence.get("sequence_hash"),
        "ordered_indicators": ordered,
        "ordered_states": states,
        "candle_offsets": offsets,
        "same_candle_required": bool(sequence.get("same_candle_required")),
        "non_same_candle_sequence": bool(offsets) and len(set(offsets)) > 1 and not bool(sequence.get("same_candle_required")),
        "max_candle_span": sequence.get("max_candle_span"),
        "historical_occurrence_count": occurrence,
        "minimum_sample_pass": bool(sequence.get("minimum_sample_pass")) and occurrence >= MINIMUM_SEQUENCE_EVIDENCE,
        "example_historical_dates": _best_matching_dates(matches)[:5],
        "interpretation": _sequence_interpretation(ordered, states, offsets, occurrence),
    }


def _combination_rows(combo: dict[str, Any], indicators: dict[str, Any], candle: dict[str, Any]) -> list[dict[str, Any]]:
    current_values = {
        "independent_indicator": {
            "rsi14": indicators.get("rsi14"),
            "macd_state": indicators.get("macd_state"),
            "vwap_position": indicators.get("vwap_position"),
        },
        "trend_momentum": {
            "ema_state": indicators.get("ema_state"),
            "macd_state": indicators.get("macd_state"),
        },
        "volatility_volume": {
            "atr14": indicators.get("atr14"),
            "volume_z": indicators.get("volume_z"),
        },
        "candle_structure": {
            "pattern": candle.get("pattern"),
            "body_pct": candle.get("body_pct"),
            "upper_wick_pct": candle.get("upper_wick_pct"),
            "lower_wick_pct": candle.get("lower_wick_pct"),
        },
    }
    weight_config = combo.get("weight_config", {}) if isinstance(combo.get("weight_config"), dict) else {}
    rows: list[dict[str, Any]] = []
    for group, values in current_values.items():
        rows.append(
            {
                "group": group,
                "weight": weight_config.get(group),
                "current_values": values,
                "available": any(value is not None for value in values.values()),
                "research_use": "match_current_values_against_historical_outcomes",
            }
        )
    return rows


def _gates(combo: dict[str, Any], sequence_memory: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _gate("IND-COMB-001", "Combination similarity source exists", combo.get("combination_similarity_version") == "behavior-combination-similarity.v0.65", "block", "Use v0.65 combination similarity as source."),
        _gate("IND-COMB-002", "Current indicator values are captured", any(row["available"] for row in rows), "block", "Current indicator values are required."),
        _gate("IND-COMB-003", "Non-same-candle sequence is represented", bool(sequence_memory.get("non_same_candle_sequence")), "downgrade", "Sequential indicator signals must preserve candle offsets."),
        _gate("IND-COMB-004", "Minimum sequence evidence passes", bool(sequence_memory.get("minimum_sample_pass")), "downgrade", "Do not trust sequence probabilities until at least 30 occurrences."),
        _gate("IND-COMB-005", "Combination minimum sample guard passes", bool(combo.get("minimum_sample_pass")), "downgrade", "Combination memory remains low confidence until minimum sample passes."),
        _gate("IND-COMB-006", "Point-in-time safe", bool(combo.get("point_in_time_safe")), "block", "No future candle values may enter combination memory."),
        _gate("IND-COMB-007", "No trading authority", True, "block", "Indicator combination memory is research-only."),
    ]


def _best_matching_dates(matches: list[Any]) -> list[str]:
    dates: list[str] = []
    for item in matches:
        if isinstance(item, dict) and item.get("historical_date"):
            dates.append(str(item["historical_date"]))
    return dates[:10]


def _no_trade_reason(combo: dict[str, Any], sequence_memory: dict[str, Any]) -> str | None:
    if not combo.get("minimum_sample_pass"):
        return "Low evidence. Indicator combination history is not enough."
    if not sequence_memory.get("minimum_sample_pass"):
        return "Sequential indicator pattern has too few historical occurrences."
    return None


def _sequence_interpretation(ordered: list[Any], states: list[Any], offsets: list[Any], occurrence: int) -> str:
    if not ordered:
        return "No ordered indicator sequence is available yet."
    parts = [f"{indicator}@{offset}:{state}" for indicator, offset, state in zip(ordered, offsets, states)]
    return f"Observed ordered sequence {' -> '.join(parts)} with {occurrence} historical occurrences; use as research memory only."


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], combo: dict[str, Any], sequence: dict[str, Any]) -> str:
    if blockers:
        return "Indicator combination memory is blocked until point-in-time current values and source report are valid."
    if warnings:
        return "Indicator combination memory is visible for research, but low evidence or sequence limits block confidence promotion."
    return "Indicator combination memory is research-ready; it still cannot approve trades or route orders."


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return {}
