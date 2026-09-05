from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


TRADING_DECISION_OUTPUT_VERSION = "jarvis-trading-decision-output.v1.23"


def build_trading_decision_output_report(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    indicator_memory: dict[str, Any],
    candle_memory: dict[str, Any],
    decision_quality_gate: dict[str, Any],
) -> dict[str, Any]:
    decision = jarvis_room.get("trade_vision_decision", {}) if isinstance(jarvis_room.get("trade_vision_decision"), dict) else {}
    chart = jarvis_room.get("chart_context", {}) if isinstance(jarvis_room.get("chart_context"), dict) else {}
    candle = jarvis_room.get("candle_structure", {}) if isinstance(jarvis_room.get("candle_structure"), dict) else {}
    indicators = jarvis_room.get("indicator_snapshot", {}) if isinstance(jarvis_room.get("indicator_snapshot"), dict) else {}
    levels = jarvis_room.get("levels_and_zones", {}) if isinstance(jarvis_room.get("levels_and_zones"), dict) else {}
    similar = jarvis_room.get("similar_history", {}) if isinstance(jarvis_room.get("similar_history"), dict) else {}
    sequential = jarvis_room.get("sequential_signals", []) if isinstance(jarvis_room.get("sequential_signals"), list) else []
    pattern_now = _pattern_now(candle, indicators, levels, decision, candle_memory)
    trade_plan = _trade_plan(decision, decision_quality_gate)
    evidence_rows = _evidence_rows(indicators, candle, levels, indicator_memory, candle_memory)
    similar_cases = _similar_cases(similar, candle_memory, indicator_memory)
    blocker_rows = _blocker_rows(decision, decision_quality_gate)
    output_state = _output_state(decision_quality_gate, decision)
    payload = {
        "version": TRADING_DECISION_OUTPUT_VERSION,
        "symbol": symbol.upper(),
        "output_state": output_state,
        "pattern_now": pattern_now,
        "trade_plan": trade_plan,
        "evidence_rows": evidence_rows,
        "similar_cases": similar_cases[:12],
    }
    return {
        "output_version": TRADING_DECISION_OUTPUT_VERSION,
        "symbol": symbol.upper(),
        "timeframe": jarvis_room.get("timeframe"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_state": output_state,
        "output_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "headline": _headline(output_state, decision, pattern_now, decision_quality_gate),
        "chart_screen_focus": {
            "bar_count": chart.get("bar_count", 0),
            "latest_close": chart.get("latest_close"),
            "display_bars_available": len(chart.get("bars", []) or []),
            "overlay_entry_zone": trade_plan["entry_zone"],
            "overlay_stop_loss": trade_plan["stop_loss"],
            "overlay_target": trade_plan["target"],
            "overlay_invalidation_level": trade_plan["invalidation_level"],
            "show_wait_zone": True,
            "show_similar_markers": bool(similar_cases),
            "show_safety_banner": True,
        },
        "pattern_now": pattern_now,
        "trade_plan": trade_plan,
        "indicator_and_candle_evidence": evidence_rows,
        "sequential_signal_story": _sequential_story(sequential, indicator_memory),
        "similar_history_cases": similar_cases[:12],
        "quality_and_safety": {
            "quality_gate_version": decision_quality_gate.get("quality_gate_version"),
            "quality_state": decision_quality_gate.get("quality_state"),
            "flags": decision_quality_gate.get("quality_flags", []),
            "review_display_allowed": decision_quality_gate.get("review_display_allowed", False),
            "decision_trust_allowed": False,
            "confidence_boost_allowed": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
        "blocker_rows": blocker_rows,
        "explain_like_trader": _explain_like_trader(output_state, pattern_now, trade_plan, evidence_rows, similar_cases, blocker_rows),
        "next_best_actions": _next_best_actions(output_state, trade_plan, blocker_rows, decision_quality_gate),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "broker_order_created": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _pattern_now(
    candle: dict[str, Any],
    indicators: dict[str, Any],
    levels: dict[str, Any],
    decision: dict[str, Any],
    candle_memory: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scenario_label": decision.get("scenario_label") or "unknown",
        "scenario_bias": decision.get("scenario_bias") or "unknown",
        "candle_pattern": candle.get("pattern") or candle_memory.get("effect_label") or "unknown",
        "candle_effect": candle_memory.get("effect_label"),
        "body_pct": candle.get("body_pct"),
        "upper_wick_pct": candle.get("upper_wick_pct"),
        "lower_wick_pct": candle.get("lower_wick_pct"),
        "wick_body_read": _wick_body_read(candle),
        "vwap_position": indicators.get("vwap_position"),
        "ema_state": indicators.get("ema_state"),
        "macd_state": indicators.get("macd_state"),
        "rsi14": indicators.get("rsi14"),
        "volume_z": indicators.get("volume_z"),
        "nearest_support": levels.get("nearest_support"),
        "nearest_resistance": levels.get("nearest_resistance"),
        "structure_read": _structure_read(candle, indicators, levels, decision),
    }


def _trade_plan(decision: dict[str, Any], quality_gate: dict[str, Any]) -> dict[str, Any]:
    quality_state = quality_gate.get("quality_state", "pending")
    final_decision = decision.get("final_trade_decision", "WAIT")
    blocked = quality_state != "research_review_ready" or final_decision in {"NO_TRADE", "WATCH_ONLY", "WAIT"}
    return {
        "final_trade_decision": final_decision,
        "display_action": "WAIT" if blocked else final_decision,
        "entry_type": "wait_for_value_reach_then_retest_confirmation",
        "entry_zone": decision.get("best_entry_zone", []),
        "entry_condition": decision.get("entry_condition", "Wait for verified evidence agreement."),
        "stop_loss": decision.get("stop_loss"),
        "target": decision.get("target"),
        "invalidation_level": decision.get("invalidation_level"),
        "risk_reward": decision.get("risk_reward"),
        "confidence_cap_pct": decision.get("confidence_cap_pct", 0),
        "wait_for": decision.get("wait_for", []),
        "avoid_if": decision.get("avoid_if", []),
        "no_trade_reason": decision.get("no_trade_reason") or quality_gate.get("operator_message"),
        "plan_is_actionable_for_live_trade": False,
        "plan_is_research_only": True,
    }


def _evidence_rows(
    indicators: dict[str, Any],
    candle: dict[str, Any],
    levels: dict[str, Any],
    indicator_memory: dict[str, Any],
    candle_memory: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [
        _row("candle_body_wick", "Candle body/wick", candle.get("pattern"), _wick_body_read(candle), candle_memory.get("evidence_quality")),
        _row("vwap", "VWAP", indicators.get("vwap_position"), f"VWAP {indicators.get('vwap')} and price is {indicators.get('vwap_position')}.", "current"),
        _row("ema", "EMA trend", indicators.get("ema_state"), f"EMA9 {indicators.get('ema9')} vs EMA21 {indicators.get('ema21')}.", "current"),
        _row("rsi", "RSI momentum", indicators.get("rsi14"), f"RSI14 is {indicators.get('rsi14')}; use with memory, not alone.", "current"),
        _row("macd", "MACD", indicators.get("macd_state"), f"MACD value {indicators.get('macd_value')}.", "current"),
        _row("volume", "Volume participation", indicators.get("volume_z"), f"Volume z-score {indicators.get('volume_z')}.", "current"),
        _row("levels", "Support/resistance", f"{levels.get('nearest_support')} / {levels.get('nearest_resistance')}", "Use entry only when price respects the zone and invalidation is clear.", "current"),
        _row("indicator_sequence", "Sequential indicator memory", indicator_memory.get("sequence_memory", {}).get("sequence_id"), indicator_memory.get("sequence_memory", {}).get("interpretation"), indicator_memory.get("evidence_quality")),
        _row("candle_cause_effect", "Candle cause/effect memory", candle_memory.get("effect_label"), candle_memory.get("expected_next_effect"), candle_memory.get("evidence_quality")),
    ]
    return rows


def _similar_cases(similar: dict[str, Any], candle_memory: dict[str, Any], indicator_memory: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for item in similar.get("matches", []) or []:
        if isinstance(item, dict):
            cases.append(
                {
                    "source": "day_shape_memory",
                    "date": _date_from_ns(item.get("start_timestamp_ns")),
                    "similarity_score_pct": item.get("similarity_score_pct"),
                    "outcome": item.get("outcome"),
                    "why_useful": "Similar intraday path shape; outcome labels are still conservative.",
                }
            )
    for item in candle_memory.get("analog_examples", []) or []:
        if isinstance(item, dict):
            cases.append(
                {
                    "source": "candle_cause_effect_memory",
                    "date": item.get("historical_date"),
                    "similarity_score_pct": item.get("similarity_score_pct"),
                    "outcome": item.get("outcome"),
                    "why_useful": f"{item.get('previous_direction')} -> {item.get('current_direction')} -> {item.get('next_direction')}",
                }
            )
    for date in indicator_memory.get("best_matching_dates", []) or []:
        cases.append(
            {
                "source": "indicator_combination_memory",
                "date": date,
                "similarity_score_pct": None,
                "outcome": "indicator_sequence_match",
                "why_useful": "Same or similar ordered indicator/value sequence appeared before.",
            }
        )
    return cases


def _blocker_rows(decision: dict[str, Any], quality_gate: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if decision.get("no_trade_reason"):
        rows.append({"source": "trade_vision_decision", "severity": "block", "reason": decision["no_trade_reason"]})
    for flag in quality_gate.get("quality_flags", []) or []:
        if isinstance(flag, dict):
            rows.append({"source": flag.get("flag_id"), "severity": flag.get("severity"), "reason": flag.get("name"), "repair": flag.get("repair")})
    for gate in quality_gate.get("gates", []) or []:
        if isinstance(gate, dict) and not gate.get("passed"):
            rows.append({"source": gate.get("gate_id"), "severity": gate.get("effect"), "reason": gate.get("name"), "repair": gate.get("reason")})
    return rows[:16]


def _output_state(quality_gate: dict[str, Any], decision: dict[str, Any]) -> str:
    if quality_gate.get("quality_state") == "display_blocked":
        return "blocked_show_safe_evidence_only"
    if decision.get("final_trade_decision") in {"NO_TRADE", "WATCH_ONLY"}:
        return "watch_or_no_trade"
    if quality_gate.get("quality_state") == "manual_review_required":
        return "manual_review_required"
    return "research_decision_output_ready"


def _headline(output_state: str, decision: dict[str, Any], pattern_now: dict[str, Any], quality_gate: dict[str, Any]) -> str:
    if output_state == "blocked_show_safe_evidence_only":
        return "Decision output is blocked; use chart evidence only and do not ask an external engine for action."
    if output_state == "manual_review_required":
        return f"WAIT: {pattern_now['structure_read']} but {quality_gate.get('operator_message', 'manual review is required')}"
    if output_state == "watch_or_no_trade":
        return f"{decision.get('final_trade_decision', 'WATCH_ONLY')}: {decision.get('no_trade_reason') or pattern_now['structure_read']}"
    return f"{decision.get('final_trade_decision', 'WAIT')}: {pattern_now['structure_read']}"


def _sequential_story(sequential: list[Any], indicator_memory: dict[str, Any]) -> dict[str, Any]:
    names = [str(item.get("name")) for item in sequential if isinstance(item, dict) and item.get("name")]
    sequence = indicator_memory.get("sequence_memory", {}) if isinstance(indicator_memory.get("sequence_memory"), dict) else {}
    return {
        "current_sequence": names,
        "historical_sequence": sequence.get("ordered_indicators", []),
        "candle_offsets": sequence.get("candle_offsets", []),
        "non_same_candle_sequence_detected": indicator_memory.get("non_same_candle_sequence_detected", False),
        "interpretation": sequence.get("interpretation") or "No sequential indicator story is available yet.",
    }


def _explain_like_trader(
    output_state: str,
    pattern_now: dict[str, Any],
    trade_plan: dict[str, Any],
    evidence_rows: list[dict[str, Any]],
    similar_cases: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> str:
    evidence = "; ".join(f"{row['label']}={row['state']}" for row in evidence_rows[:5])
    similar = f"{len(similar_cases)} similar cases are available" if similar_cases else "similar history is weak or unavailable"
    blocker = blockers[0]["reason"] if blockers else "no extra blocker beyond research-only mode"
    return (
        f"Current read: {pattern_now['structure_read']}. Evidence: {evidence}. "
        f"Plan: wait for {trade_plan['entry_condition']} with SL {trade_plan['stop_loss']} and target {trade_plan['target']}. "
        f"Memory: {similar}. Safety: {output_state}; main blocker is {blocker}."
    )


def _next_best_actions(output_state: str, trade_plan: dict[str, Any], blockers: list[dict[str, Any]], quality_gate: dict[str, Any]) -> list[str]:
    actions = [
        "Do not route orders from Trade Vision.",
        "Use this output as research and paper/replay evidence only.",
    ]
    if trade_plan.get("wait_for"):
        actions.append(f"Wait for: {trade_plan['wait_for'][0]}")
    if blockers:
        actions.append(f"Fix blocker: {blockers[0].get('reason')}")
    if quality_gate.get("quality_state") != "research_review_ready":
        actions.append("Verify daily/weekly evidence and refresh external review before trusting any guide.")
    return actions


def _structure_read(candle: dict[str, Any], indicators: dict[str, Any], levels: dict[str, Any], decision: dict[str, Any]) -> str:
    parts = [
        str(decision.get("scenario_label") or "mixed structure"),
        str(candle.get("pattern") or "unknown candle"),
        str(indicators.get("vwap_position") or "unknown VWAP"),
        f"near support {levels.get('nearest_support')} / resistance {levels.get('nearest_resistance')}",
    ]
    return ", ".join(parts)


def _wick_body_read(candle: dict[str, Any]) -> str:
    body = candle.get("body_pct")
    upper = candle.get("upper_wick_pct")
    lower = candle.get("lower_wick_pct")
    if body is None:
        return "No candle body/wick data."
    if float(body) >= 65:
        return f"Long body candle ({body}%) with upper wick {upper}% and lower wick {lower}%."
    if float(upper or 0) >= 45:
        return f"Upper-wick rejection candle: body {body}%, upper wick {upper}%."
    if float(lower or 0) >= 45:
        return f"Lower-wick rejection candle: body {body}%, lower wick {lower}%."
    if float(body) <= 15:
        return f"Compression/doji-like candle: body {body}%."
    return f"Balanced candle: body {body}%, upper wick {upper}%, lower wick {lower}%."


def _row(row_id: str, label: str, state: Any, interpretation: Any, evidence_quality: Any) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "label": label,
        "state": state,
        "interpretation": interpretation,
        "evidence_quality": evidence_quality,
        "research_only": True,
    }


def _date_from_ns(value: Any) -> str | None:
    try:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(int(value) / 1_000_000_000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None
