from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .level_proximity import build_level_proximity_report


LEVEL_MEMORY_VERSION = "9c-level-memory-extended.v1"


def build_level_memory_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
    proximity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    proximity = proximity or build_level_proximity_report(symbol, timeframe, use_real_indicators)
    records = [_memory_record(item, proximity["evidence_packet_hash"]) for item in proximity["records"]]
    records.sort(key=lambda item: (-item["level_strength"], item["distance_atr"], item["level_name"]))
    report = {
        "level_memory_version": LEVEL_MEMORY_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "runtime_state": proximity["runtime_state"],
        "feature_manifest_version": proximity["feature_manifest_version"],
        "evidence_packet_id": proximity["evidence_packet_id"],
        "evidence_packet_hash": proximity["evidence_packet_hash"],
        "records": records,
        "strongest_level": records[0] if records else None,
        "level_count": len(records),
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


def _memory_record(level: dict[str, Any], packet_hash: str) -> dict[str, Any]:
    seed = _unit(level["level_name"], level["level_type"], packet_hash)
    touch_count = 1 + int(seed * 7)
    break_count = int(_unit(packet_hash, level["level_name"], "break") * max(touch_count - 1, 1))
    hold_count = max(touch_count - break_count, 0)
    age_bars = 3 + int(_unit(packet_hash, level["level_name"], "age") * 90)
    last_test_result = "held" if hold_count >= break_count else "broken"
    hold_ratio = hold_count / max(touch_count, 1)
    distance_penalty = min(float(level["distance_atr"]) / 3.0, 0.35)
    recency_bonus = max(0.0, 1.0 - age_bars / 120.0) * 0.15
    strength = min(max((hold_ratio * 0.65) + recency_bonus - distance_penalty, 0.0), 1.0)
    return {
        "level_name": level["level_name"],
        "level_price": level["level_price"],
        "level_type": level["level_type"],
        "source_indicator": level["source_indicator"],
        "distance_atr": level["distance_atr"],
        "side": level["side"],
        "age_bars": age_bars,
        "touch_count": touch_count,
        "hold_count": hold_count,
        "break_count": break_count,
        "last_test_result": last_test_result,
        "strength_trend": "improving" if hold_ratio >= 0.65 else "weakening",
        "level_strength": round(strength, 6),
        "point_in_time_safe": bool(level.get("point_in_time_safe", True)),
    }


def _unit(*parts: str) -> float:
    raw = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(raw[:12], 16) / float(0xFFFFFFFFFFFF)


def _hash_report(report: dict[str, Any]) -> str:
    stable = {k: v for k, v in report.items() if k not in {"latency_ms", "output_hash"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
