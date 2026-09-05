from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from typing import Any

from ..models import CandleBar, CandleSeries, ConditionClassifierRequest
from .condition_classifier import classify_conditions
from .level_proximity import build_level_proximity_report
from .nine_candle_hybrid import build_evidence_packet, calculate_regime_identifiers


REGIME_GATE_VERSION = "9c-regime-gate.v1"


def build_regime_gate_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
    proximity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    packet = build_evidence_packet(symbol, timeframe)
    proximity = proximity or build_level_proximity_report(symbol, timeframe, use_real_indicators)
    classifier = classify_conditions(
        ConditionClassifierRequest(
            series=_series_from_packet(packet.model_dump(mode="json")),
            vwap=_level_price(packet.levels, "VWAP"),
            support_level=_nearest_price(proximity["records"], side="above"),
            resistance_level=_nearest_price(proximity["records"], side="below"),
            session_phase=packet.session_phase,
        )
    )
    direction = _direction_from_classifier(classifier.final_signal_bias, classifier.blocks_trade)
    volatility = _volatility_group(proximity["atr"], proximity["latest_close"])
    regime = calculate_regime_identifiers(
        market_direction=direction,
        volatility_regime=volatility,
        session_regime=packet.session_phase,
        trend_strength=_trend_strength(classifier.market_state, classifier.final_signal_bias),
        liquidity_regime="liquid",
    )
    regime_match_required = True
    report = {
        "regime_gate_version": REGIME_GATE_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "evidence_packet_id": packet.evidence_packet_id,
        "evidence_packet_hash": packet.evidence_packet_hash,
        "classifier_version": classifier.classifier_version,
        "market_state": classifier.market_state,
        "condition_tags": classifier.condition_tags,
        "final_signal_bias": classifier.final_signal_bias,
        "classifier_blocks_trade": classifier.blocks_trade,
        "classifier_no_trade_reason": classifier.no_trade_reason,
        "regime_id": regime["regime_id"],
        "regime_group": regime["regime_group"],
        "broader_regime_group": f"{direction}_{volatility}",
        "regime_match_required": regime_match_required,
        "analog_scope": {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "regime_id": regime["regime_id"],
            "regime_group": regime["regime_group"],
            "session_phase": packet.session_phase,
            "feature_manifest_version": packet.feature_manifest_version,
        },
        "gates": [
            {
                "gate_id": "9C-RG001",
                "name": "Regime classified",
                "status": "pass" if classifier.market_state != "unclassified" else "wait",
                "evidence": f"market_state={classifier.market_state}",
            },
            {
                "gate_id": "9C-RG002",
                "name": "Avoid-state block",
                "status": "wait" if classifier.blocks_trade else "pass",
                "evidence": classifier.no_trade_reason or "Classifier does not block trade research.",
            },
        ],
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


def _series_from_packet(packet: dict[str, Any]) -> CandleSeries:
    bars = []
    for candle in packet["last_9_candles"]:
        bars.append(
            CandleBar(
                symbol=packet["symbol"],
                timeframe=packet["timeframe"],
                timestamp_ns=_timestamp_ns(candle["event_time"]),
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle["volume"]),
                source="mock",
                sequence_number=int(candle["sequence_number"]),
            )
        )
    return CandleSeries(
        symbol=packet["symbol"],
        timeframe=packet["timeframe"],
        bars=bars,
        snapshot_id=packet["source_snapshot_id"],
        schema_version="candles.9c.evidence.v1",
    )


def _timestamp_ns(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1_000_000_000)


def _level_price(levels: list[Any], name: str) -> float | None:
    for level in levels:
        row = level if isinstance(level, dict) else dict(level)
        if str(row.get("level_name", "")).upper() == name.upper():
            return float(row["level_price"])
    return None


def _nearest_price(records: list[dict[str, Any]], *, side: str) -> float | None:
    rows = [row for row in records if row["side"] == side]
    if not rows:
        return None
    return float(sorted(rows, key=lambda row: row["distance_atr"])[0]["level_price"])


def _direction_from_classifier(final_signal_bias: str, blocks_trade: bool) -> str:
    if blocks_trade:
        return "range_or_avoid"
    if final_signal_bias == "long":
        return "trend_up"
    if final_signal_bias == "short":
        return "trend_down"
    return "range_or_avoid"


def _volatility_group(atr: float, latest_close: float) -> str:
    atr_pct = atr / max(abs(latest_close), 1e-9)
    if atr_pct >= 0.012:
        return "high_vol"
    if atr_pct <= 0.0025:
        return "low_vol"
    return "normal_vol"


def _trend_strength(market_state: str, final_signal_bias: str) -> str:
    if market_state in {"breakout_day", "opening_drive_continuation", "vwap_support_trend"}:
        return "strongtrend"
    if market_state in {"range_balance_day", "choppy_avoid", "manipulated_looking"}:
        return "weaktrend"
    return "moderate"


def _hash_report(report: dict[str, Any]) -> str:
    stable = {k: v for k, v in report.items() if k not in {"latency_ms", "output_hash"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
