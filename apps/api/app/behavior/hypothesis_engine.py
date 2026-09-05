from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .level_confluence import build_level_confluence_report
from .level_memory_extended import build_level_memory_report
from .level_proximity import build_level_proximity_report
from .regime_gate import build_regime_gate_report


HYPOTHESIS_VERSION = "9c-hypothesis-engine.v1"
HYPOTHESIS_IDS = ("continuation", "reversal", "fakeout")


def build_hypothesis_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    proximity = build_level_proximity_report(symbol, timeframe, use_real_indicators)
    confluence = build_level_confluence_report(symbol, timeframe, use_real_indicators, proximity=proximity)
    level_memory = build_level_memory_report(symbol, timeframe, use_real_indicators, proximity=proximity)
    regime = build_regime_gate_report(symbol, timeframe, use_real_indicators, proximity=proximity)

    context = _context(proximity, confluence, level_memory, regime)
    raw = {
        "continuation": _continuation_score(context),
        "reversal": _reversal_score(context),
        "fakeout": _fakeout_score(context),
    }
    probabilities = _normalize(raw)
    hypotheses = [_hypothesis(hypothesis_id, probabilities[hypothesis_id], raw[hypothesis_id], context) for hypothesis_id in HYPOTHESIS_IDS]
    hypotheses.sort(key=lambda item: (-item["raw_probability"], item["id"]))
    report = {
        "hypothesis_version": HYPOTHESIS_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "evidence_packet_id": proximity["evidence_packet_id"],
        "evidence_packet_hash": proximity["evidence_packet_hash"],
        "regime_id": regime["regime_id"],
        "regime_group": regime["regime_group"],
        "market_state": regime["market_state"],
        "primary_hypothesis": hypotheses[0],
        "hypotheses": hypotheses,
        "probability_sum": round(sum(item["raw_probability"] for item in hypotheses), 6),
        "low_confidence": all(score <= 0.0 for score in raw.values()),
        "calculation_warnings": _warnings(hypotheses),
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "output_hash": "",
    }
    report["output_hash"] = _hash_report(report)
    return report


def _context(proximity: dict[str, Any], confluence: dict[str, Any], level_memory: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    latest_close = float(proximity["latest_close"])
    support = _nearest_level(proximity["records"], "above")
    resistance = _nearest_level(proximity["records"], "below")
    strongest_zone = confluence.get("strongest_zone")
    strongest_level = level_memory.get("strongest_level")
    return {
        "latest_close": latest_close,
        "support": support,
        "resistance": resistance,
        "strongest_zone": strongest_zone,
        "strongest_level": strongest_level,
        "market_state": regime["market_state"],
        "condition_tags": set(regime["condition_tags"]),
        "final_signal_bias": regime["final_signal_bias"],
        "classifier_blocks_trade": regime["classifier_blocks_trade"],
        "classifier_no_trade_reason": regime["classifier_no_trade_reason"],
    }


def _continuation_score(context: dict[str, Any]) -> float:
    score = 0.20
    if context["final_signal_bias"] == "long":
        score += 0.22
    if "opening_drive_continuation" in context["condition_tags"] or "vwap_support_trend" in context["condition_tags"]:
        score += 0.20
    if context["support"] and context["support"]["distance_atr"] <= 1.0:
        score += 0.14
    if context["strongest_zone"] and context["strongest_zone"]["zone_type"] == "support":
        score += 0.12
    if context["strongest_level"] and context["strongest_level"]["last_test_result"] == "held":
        score += 0.10
    if context["classifier_blocks_trade"]:
        score -= 0.26
    return _clamp(score)


def _reversal_score(context: dict[str, Any]) -> float:
    score = 0.18
    if context["final_signal_bias"] in {"short", "avoid"}:
        score += 0.15
    if "opening_drive_reversal" in context["condition_tags"] or "vwap_rejection" in context["condition_tags"]:
        score += 0.22
    if context["resistance"] and context["resistance"]["distance_atr"] <= 1.0:
        score += 0.18
    if context["strongest_zone"] and context["strongest_zone"]["zone_type"] == "resistance":
        score += 0.12
    if "distribution" in context["condition_tags"]:
        score += 0.10
    return _clamp(score)


def _fakeout_score(context: dict[str, Any]) -> float:
    score = 0.12
    if "fake_breakout" in context["condition_tags"]:
        score += 0.30
    if "choppy_avoid" in context["condition_tags"] or "manipulated_looking" in context["condition_tags"]:
        score += 0.25
    if context["strongest_zone"] and context["strongest_zone"]["zone_type"] == "mixed":
        score += 0.14
    if context["classifier_blocks_trade"]:
        score += 0.18
    return _clamp(score)


def _hypothesis(hypothesis_id: str, probability: float, rule_score: float, context: dict[str, Any]) -> dict[str, Any]:
    direction = {"continuation": "LONG", "reversal": "SHORT", "fakeout": "WAIT"}[hypothesis_id]
    support = context["support"]
    resistance = context["resistance"]
    latest_close = context["latest_close"]
    if direction == "LONG":
        invalidation = float(support["level_price"]) if support else round(latest_close * 0.995, 4)
        confirmation = float(resistance["level_price"]) if resistance else round(latest_close * 1.004, 4)
    elif direction == "SHORT":
        invalidation = float(resistance["level_price"]) if resistance else round(latest_close * 1.005, 4)
        confirmation = float(support["level_price"]) if support else round(latest_close * 0.996, 4)
    else:
        invalidation = latest_close
        confirmation = latest_close
    factors = _factors(hypothesis_id, context)
    return {
        "id": hypothesis_id,
        "direction": direction,
        "thesis_text": _thesis(hypothesis_id),
        "rule_score": round(rule_score, 6),
        "supporting_factors": factors["supporting"],
        "opposing_factors": factors["opposing"],
        "invalidation_level": round(float(invalidation), 4),
        "confirmation_trigger": round(float(confirmation), 4),
        "analog_evidence": {
            "regime_scoped": True,
            "same_regime_required": True,
            "source": "9c-hypothesis-engine.v1",
        },
        "raw_probability": round(probability, 6),
    }


def _factors(hypothesis_id: str, context: dict[str, Any]) -> dict[str, list[str]]:
    support = []
    oppose = []
    if context["support"]:
        support.append(f"Nearest support level exists: {context['support']['level_name']} at {context['support']['level_price']}.")
    if context["resistance"]:
        support.append(f"Nearest resistance level exists: {context['resistance']['level_name']} at {context['resistance']['level_price']}.")
    support.append(f"Market state is {context['market_state']}.")
    if context["strongest_zone"]:
        support.append(f"Strongest confluence zone is {context['strongest_zone']['zone_type']} with strength {context['strongest_zone']['zone_strength']}.")
    if context["classifier_blocks_trade"]:
        oppose.append(context["classifier_no_trade_reason"] or "Classifier currently blocks aggressive action.")
    if hypothesis_id == "continuation" and "fake_breakout" in context["condition_tags"]:
        oppose.append("Fakeout condition opposes continuation.")
    if hypothesis_id == "reversal" and context["final_signal_bias"] == "long":
        oppose.append("Current signal bias is long, which opposes reversal.")
    if hypothesis_id == "fakeout" and not context["classifier_blocks_trade"]:
        oppose.append("Classifier does not currently block trade research.")
    return {"supporting": support, "opposing": oppose}


def _thesis(hypothesis_id: str) -> str:
    if hypothesis_id == "continuation":
        return "Continuation if price respects nearby support/confluence and confirms through resistance."
    if hypothesis_id == "reversal":
        return "Reversal if resistance rejection or VWAP failure dominates the next closed candle."
    return "Fakeout or no-trade if structure is mixed, manipulated-looking, or classifier blocks action."


def _normalize(raw: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in raw.values())
    if total <= 1e-9:
        return {key: round(1.0 / len(raw), 6) for key in raw}
    normalized = {key: max(value, 0.0) / total for key, value in raw.items()}
    drift = 1.0 - sum(round(value, 6) for value in normalized.values())
    keys = list(normalized)
    result = {key: round(value, 6) for key, value in normalized.items()}
    result[keys[0]] = round(result[keys[0]] + drift, 6)
    return result


def _nearest_level(records: list[dict[str, Any]], side: str) -> dict[str, Any] | None:
    rows = [record for record in records if record["side"] == side]
    if not rows:
        return None
    return sorted(rows, key=lambda row: row["distance_atr"])[0]


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _warnings(hypotheses: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    probability_sum = sum(item["raw_probability"] for item in hypotheses)
    if abs(probability_sum - 1.0) > 0.001:
        warnings.append("probability_sum_out_of_bounds")
    for item in hypotheses:
        if not 0.0 <= item["rule_score"] <= 1.0:
            warnings.append("rule_score_out_of_bounds")
        if item["invalidation_level"] is None or item["confirmation_trigger"] is None:
            warnings.append("missing_trade_boundary")
    return sorted(set(warnings))


def _hash_report(report: dict[str, Any]) -> str:
    stable = {k: v for k, v in report.items() if k not in {"latency_ms", "output_hash"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
