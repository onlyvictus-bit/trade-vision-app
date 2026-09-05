from __future__ import annotations

import hashlib
import json
import time
from statistics import mean
from typing import Any

from .indicator_runtime_bridge import build_indicator_runtime_report


PROXIMITY_VERSION = "9c-level-proximity.v1"
ATR_BAND = 0.50
EPSILON = 1e-9


def build_level_proximity_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    runtime = build_indicator_runtime_report(symbol, timeframe, use_real_indicators)
    candles = runtime.get("evidence_packet", {}).get("last_9_candles") or _packet_candles_from_runtime(symbol, timeframe)
    latest_close = float(candles[-1]["close"])
    atr = _average_true_range(candles)
    atr_zero_fallback = atr <= EPSILON
    safe_atr = atr if not atr_zero_fallback else max(abs(latest_close) * 0.001, EPSILON)

    records = [
        _proximity_record(candidate, latest_close, safe_atr, atr_zero_fallback)
        for candidate in runtime.get("level_candidates", [])
    ]
    records.sort(key=lambda item: (item["distance_atr"], item["distance_pct"], item["level_name"]))
    report = {
        "proximity_version": PROXIMITY_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "runtime_state": runtime["runtime_state"],
        "feature_manifest_version": runtime["feature_manifest_version"],
        "source_registry_version": runtime["source_registry_version"],
        "evidence_packet_id": runtime["evidence_packet_id"],
        "evidence_packet_hash": runtime["evidence_packet_hash"],
        "latest_close": round(latest_close, 4),
        "atr": round(atr, 6),
        "atr_zero_fallback": atr_zero_fallback,
        "atr_band": ATR_BAND,
        "records": records,
        "nearest_level": records[0] if records else None,
        "within_band_count": sum(1 for item in records if item["within_atr_band"]),
        "calculation_warnings": _calculation_warnings(records, atr_zero_fallback),
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


def _packet_candles_from_runtime(symbol: str, timeframe: str) -> list[dict[str, Any]]:
    from .nine_candle_hybrid import build_evidence_packet

    return build_evidence_packet(symbol, timeframe).model_dump(mode="json")["last_9_candles"]


def _average_true_range(candles: list[dict[str, Any]]) -> float:
    ranges: list[float] = []
    previous_close: float | None = None
    for candle in candles:
        high = float(candle["high"])
        low = float(candle["low"])
        close = float(candle["close"])
        if previous_close is None:
            ranges.append(max(high - low, 0.0))
        else:
            ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close), 0.0))
        previous_close = close
    return mean(ranges) if ranges else 0.0


def _proximity_record(candidate: dict[str, Any], latest_close: float, atr: float, atr_zero_fallback: bool) -> dict[str, Any]:
    level_price = float(candidate["level_price"])
    signed_distance = latest_close - level_price
    absolute_distance = abs(signed_distance)
    distance_pct = (absolute_distance / max(abs(latest_close), EPSILON)) * 100.0
    distance_atr = absolute_distance / max(atr, EPSILON)
    side = _side(latest_close, level_price)
    return {
        "level_name": str(candidate["level_name"]),
        "level_price": round(level_price, 4),
        "level_type": str(candidate.get("level_type", "unknown")),
        "source_indicator": str(candidate.get("source_indicator", candidate.get("source", "unknown"))),
        "source_state": str(candidate.get("source_state", "unknown")),
        "latest_close": round(latest_close, 4),
        "signed_distance": round(signed_distance, 6),
        "distance_points": round(absolute_distance, 6),
        "distance_pct": round(distance_pct, 6),
        "distance_atr": round(distance_atr, 6),
        "side": side,
        "within_atr_band": distance_atr <= ATR_BAND,
        "atr_zero_fallback": atr_zero_fallback,
        "freshness": "point_in_time",
        "point_in_time_safe": bool(candidate.get("point_in_time_safe", True)),
        "missing_mask": bool(candidate.get("missing_mask", False)),
    }


def _side(latest_close: float, level_price: float) -> str:
    if abs(latest_close - level_price) <= EPSILON:
        return "at_level"
    return "above" if latest_close > level_price else "below"


def _calculation_warnings(records: list[dict[str, Any]], atr_zero_fallback: bool) -> list[str]:
    warnings: list[str] = []
    if atr_zero_fallback:
        warnings.append("atr_zero_fallback_used")
    if any(item["distance_atr"] < 0 for item in records):
        warnings.append("invalid_negative_distance_atr")
    for item in records:
        if item["side"] == "above" and item["latest_close"] <= item["level_price"]:
            warnings.append("side_label_inconsistent")
        if item["side"] == "below" and item["latest_close"] >= item["level_price"]:
            warnings.append("side_label_inconsistent")
    return sorted(set(warnings))


def _hash_report(report: dict[str, Any]) -> str:
    stable = {k: v for k, v in report.items() if k not in {"latency_ms", "output_hash"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
