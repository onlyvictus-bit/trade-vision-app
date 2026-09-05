from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5


PAPER_REALITY_CHECK_VERSION = "paper-execution-reality-check.v0.94"
DEFAULT_BROKERAGE_PER_SIDE_PCT = 0.01
DEFAULT_TAX_AND_FEES_PCT = 0.035
DEFAULT_BUFFER_BPS = 2.5


def build_paper_reality_check(
    *,
    symbol: str,
    trade_vision_decision: dict[str, Any],
    openalgo_report: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    generated_at = datetime.now(timezone.utc).isoformat()
    decision = trade_vision_decision.get("final_trade_decision", "WAIT")
    entry = _entry_price(trade_vision_decision)
    stop = _to_float(trade_vision_decision.get("stop_loss"))
    target = _to_float(trade_vision_decision.get("target"))
    side = _side_from_decision(decision)
    report_evidence = (openalgo_report or {}).get("extracted_evidence", {})
    fill_price = _to_float(report_evidence.get("fill_price")) or entry
    slippage_bps = _to_float(report_evidence.get("slippage_bps")) or 0.0
    latency_ms = _to_float(report_evidence.get("latency_ms")) or 0.0
    fill_quality = str(report_evidence.get("fill_quality") or "not_available")
    quantity = int(_to_float(report_evidence.get("quantity")) or 0)
    fees = _to_float(report_evidence.get("fees"))
    fee_pct = _fee_pct(fill_price, quantity, fees)
    all_in_cost_bps = round(abs(slippage_bps) + (fee_pct * 100.0) + DEFAULT_BUFFER_BPS, 4)
    original_rr = _risk_reward(entry, stop, target, side)
    adjusted_rr = _risk_reward(fill_price, stop, target, side)
    target_after_costs = _target_after_costs(fill_price, target, all_in_cost_bps, side)
    stop_after_costs = _stop_after_costs(fill_price, stop, all_in_cost_bps, side)
    degradation = _rr_degradation(original_rr, adjusted_rr)
    gates = _gates(
        decision=decision,
        openalgo_report=openalgo_report,
        entry=entry,
        stop=stop,
        target=target,
        adjusted_rr=adjusted_rr,
        all_in_cost_bps=all_in_cost_bps,
        fill_quality=fill_quality,
        latency_ms=latency_ms,
    )
    impact = _impact(gates, degradation, adjusted_rr)
    payload = {
        "version": PAPER_REALITY_CHECK_VERSION,
        "symbol": normalized_symbol,
        "decision": decision,
        "entry": entry,
        "fill": fill_price,
        "stop": stop,
        "target": target,
        "cost": all_in_cost_bps,
        "rr": adjusted_rr,
        "impact": impact,
        "gates": gates,
    }
    check_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return {
        "reality_check_version": PAPER_REALITY_CHECK_VERSION,
        "check_id": str(uuid5(NAMESPACE_URL, f"tradevision:v094:paper-reality:{check_hash}")),
        "generated_at": generated_at,
        "symbol": normalized_symbol,
        "source_report_id": openalgo_report.get("report_id") if openalgo_report else None,
        "decision": decision,
        "side": side,
        "entry_price": entry,
        "observed_fill_price": fill_price,
        "stop_loss": stop,
        "target": target,
        "quantity": quantity,
        "slippage_bps": round(slippage_bps, 4),
        "latency_ms": round(latency_ms, 3),
        "fee_pct_estimate": round(fee_pct, 6),
        "all_in_cost_bps": all_in_cost_bps,
        "fill_quality": fill_quality,
        "original_risk_reward": original_rr,
        "adjusted_risk_reward": adjusted_rr,
        "rr_degradation_pct": degradation,
        "target_after_costs": target_after_costs,
        "stop_after_costs": stop_after_costs,
        "gates": gates,
        "jarvis_effect": impact,
        "check_hash": check_hash,
        "paper_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "broker_order_created": False,
        "live_trading_blocked": True,
        "notes": [
            "v0.94 compares Trade Vision entry/SL/target against imported execution evidence.",
            "This is a paper/research reality check only; it cannot place, approve, or export orders.",
            "Bad fill, high cost, low R:R, or missing report downgrades action instead of promoting it.",
        ],
    }


def _entry_price(decision: dict[str, Any]) -> float | None:
    zone = decision.get("best_entry_zone")
    if isinstance(zone, list) and zone:
        values = [_to_float(item) for item in zone]
        values = [item for item in values if item is not None]
        if values:
            return round(sum(values) / len(values), 4)
    return _to_float(decision.get("entry_price"))


def _side_from_decision(decision: str) -> str:
    return "SELL" if "SELL" in str(decision).upper() else "BUY"


def _risk_reward(entry: float | None, stop: float | None, target: float | None, side: str) -> float | None:
    if entry is None or stop is None or target is None:
        return None
    risk = entry - stop if side == "BUY" else stop - entry
    reward = target - entry if side == "BUY" else entry - target
    if risk <= 0 or reward <= 0:
        return 0.0
    return round(reward / risk, 4)


def _target_after_costs(fill: float | None, target: float | None, all_in_cost_bps: float, side: str) -> float | None:
    if fill is None or target is None:
        return None
    cost_price = fill * all_in_cost_bps / 10_000.0
    return round(target - cost_price if side == "BUY" else target + cost_price, 4)


def _stop_after_costs(fill: float | None, stop: float | None, all_in_cost_bps: float, side: str) -> float | None:
    if fill is None or stop is None:
        return None
    cost_price = fill * all_in_cost_bps / 10_000.0
    return round(stop + cost_price if side == "BUY" else stop - cost_price, 4)


def _rr_degradation(original_rr: float | None, adjusted_rr: float | None) -> float | None:
    if original_rr is None or adjusted_rr is None or original_rr <= 0:
        return None
    return round(max(0.0, (original_rr - adjusted_rr) / original_rr * 100.0), 4)


def _fee_pct(fill_price: float | None, quantity: int, fees: float | None) -> float:
    if fill_price and quantity > 0 and fees is not None:
        turnover = fill_price * quantity
        if turnover > 0:
            return min(max(fees / turnover * 100.0, 0.0), 5.0)
    return DEFAULT_BROKERAGE_PER_SIDE_PCT * 2.0 + DEFAULT_TAX_AND_FEES_PCT


def _gates(
    *,
    decision: str,
    openalgo_report: dict[str, Any] | None,
    entry: float | None,
    stop: float | None,
    target: float | None,
    adjusted_rr: float | None,
    all_in_cost_bps: float,
    fill_quality: str,
    latency_ms: float,
) -> list[dict[str, Any]]:
    return [
        _gate("PAPER-RC-001", "OpenAlgo report available", openalgo_report is not None, "downgrade", "No imported report is available for execution reality."),
        _gate("PAPER-RC-002", "Trade candidate price structure available", entry is not None and stop is not None and target is not None, "block", "Entry, stop, and target are required for paper reality check."),
        _gate("PAPER-RC-003", "Decision is not NO_TRADE", decision != "NO_TRADE", "block", "NO_TRADE cannot be promoted by execution evidence."),
        _gate("PAPER-RC-004", "Adjusted R:R remains >= 1.5", adjusted_rr is not None and adjusted_rr >= 1.5, "downgrade", "After fill/costs, R:R is too weak."),
        _gate("PAPER-RC-005", "All-in execution cost <= 35 bps", all_in_cost_bps <= 35.0, "downgrade", "Execution costs are too high for confidence boost."),
        _gate("PAPER-RC-006", "Fill quality not poor or failed", fill_quality not in {"poor", "failed"}, "downgrade", f"Fill quality is {fill_quality}."),
        _gate("PAPER-RC-007", "Latency <= 750 ms", latency_ms <= 750.0, "downgrade", "Execution latency is too high."),
    ]


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": passed,
        "effect": effect,
        "reason": reason,
    }


def _impact(gates: list[dict[str, Any]], degradation: float | None, adjusted_rr: float | None) -> dict[str, Any]:
    blocking = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    downgrade = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    if blocking:
        effect = "NO_TRADE"
    elif downgrade:
        effect = "WAIT"
    else:
        effect = "REVIEW_ONLY"
    confidence_modifier_pct = 0.0
    if effect == "WAIT":
        confidence_modifier_pct = -min(35.0, 10.0 + float(degradation or 0.0))
    if effect == "NO_TRADE":
        confidence_modifier_pct = -100.0
    if adjusted_rr is not None and adjusted_rr < 2.0 and effect == "REVIEW_ONLY":
        confidence_modifier_pct = -5.0
    return {
        "effect": effect,
        "confidence_modifier_pct": round(confidence_modifier_pct, 4),
        "can_upgrade_trade": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
        "reasons": [gate["reason"] for gate in blocking + downgrade],
    }


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
