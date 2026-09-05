from __future__ import annotations

import hashlib
import json
import time
from statistics import median
from typing import Any

from .level_proximity import build_level_proximity_report


CONFLUENCE_VERSION = "9c-level-confluence.v1"


def build_level_confluence_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
    proximity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    proximity = proximity or build_level_proximity_report(symbol, timeframe, use_real_indicators)
    zones = _cluster_zones(proximity)
    zones.sort(key=lambda item: (-item["zone_strength"], item["distance_atr"], item["zone_price"]))
    report = {
        "confluence_version": CONFLUENCE_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "runtime_state": proximity["runtime_state"],
        "feature_manifest_version": proximity["feature_manifest_version"],
        "source_registry_version": proximity["source_registry_version"],
        "evidence_packet_id": proximity["evidence_packet_id"],
        "evidence_packet_hash": proximity["evidence_packet_hash"],
        "latest_close": proximity["latest_close"],
        "atr": proximity["atr"],
        "cluster_threshold_atr": proximity["atr_band"],
        "zone_count": len(zones),
        "zones": zones,
        "strongest_zone": zones[0] if zones else None,
        "calculation_warnings": _warnings(zones),
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


def _cluster_zones(proximity: dict[str, Any]) -> list[dict[str, Any]]:
    records = sorted(proximity.get("records", []), key=lambda item: item["level_price"])
    if not records:
        return []
    atr = max(float(proximity.get("atr") or 0.0), max(abs(float(proximity["latest_close"])) * 0.001, 1e-9))
    threshold_points = float(proximity.get("atr_band", 0.5)) * atr
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [records[0]]
    for record in records[1:]:
        prices = [float(item["level_price"]) for item in current] + [float(record["level_price"])]
        if max(prices) - min(prices) <= threshold_points:
            current.append(record)
            continue
        clusters.append(current)
        current = [record]
    clusters.append(current)
    return [_zone(index, cluster, float(proximity["latest_close"]), atr) for index, cluster in enumerate(clusters, start=1)]


def _zone(index: int, cluster: list[dict[str, Any]], latest_close: float, atr: float) -> dict[str, Any]:
    prices = [float(item["level_price"]) for item in cluster]
    zone_price = float(median(prices))
    side = _zone_side(latest_close, zone_price)
    support_count = sum(1 for item in cluster if item["side"] == "above")
    resistance_count = sum(1 for item in cluster if item["side"] == "below")
    conflict_count = min(support_count, resistance_count)
    contributing_count = len(cluster)
    strength = min(5, max(1, contributing_count + (1 if any(item["within_atr_band"] for item in cluster) else 0) - conflict_count))
    distance_atr = abs(latest_close - zone_price) / max(atr, 1e-9)
    return {
        "zone_id": f"zone-{index:02d}",
        "zone_price": round(zone_price, 4),
        "zone_type": "mixed" if conflict_count else side,
        "distance_atr": round(distance_atr, 6),
        "contributing_levels": [item["level_name"] for item in cluster],
        "contributing_prices": [round(float(item["level_price"]), 4) for item in cluster],
        "contributing_count": contributing_count,
        "zone_strength": strength,
        "zone_freshness": "point_in_time",
        "net_agreement": support_count - resistance_count,
        "support_count": support_count,
        "resistance_count": resistance_count,
        "conflict_count": conflict_count,
        "point_in_time_safe": all(item.get("point_in_time_safe", True) for item in cluster),
    }


def _zone_side(latest_close: float, zone_price: float) -> str:
    if abs(latest_close - zone_price) <= 1e-9:
        return "at_level"
    return "support" if latest_close > zone_price else "resistance"


def _warnings(zones: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for zone in zones:
        if zone["contributing_count"] != len(zone["contributing_levels"]):
            warnings.append("contributing_count_mismatch")
        if not 1 <= int(zone["zone_strength"]) <= 5:
            warnings.append("zone_strength_out_of_range")
    return sorted(set(warnings))


def _hash_report(report: dict[str, Any]) -> str:
    stable = {k: v for k, v in report.items() if k not in {"latency_ms", "output_hash"}}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
