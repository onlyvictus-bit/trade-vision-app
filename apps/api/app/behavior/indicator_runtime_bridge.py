from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from typing import Any

from .indicator_registry import build_indicator_registry_report
from .nine_candle_hybrid import build_evidence_packet, _runtime_closed_candles
from .real_indicator_adapter import (
    REAL_RUNTIME_PROMOTED_INDICATORS,
    compute_pta_marker_outputs_with_telemetry,
    compute_real_indicator_outputs_with_telemetry,
)


RUNTIME_VERSION = "9c-indicator-runtime-bridge.v1"
LEVEL_FAMILIES = {"levels", "support_resistance", "structure", "vwap_value_area", "liquidity_order_flow_proxy", "trendline", "vwap"}
_CACHE: dict[str, dict[str, Any]] = {}


def build_indicator_runtime_report(symbol: str = "RELIANCE", timeframe: str = "1m", use_real_indicators: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    packet = build_evidence_packet(symbol, timeframe)
    registry = build_indicator_registry_report()
    selected = [indicator_id for indicator_id in _selected_indicator_ids(registry.entries) if indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS]
    vector_promoted = sorted(
        str(entry.indicator_id)
        for entry in registry.entries
        if str(entry.indicator_id) in REAL_RUNTIME_PROMOTED_INDICATORS
    )
    vector_promoted_not_level_selected = sorted(set(vector_promoted) - set(selected))
    pta_selected = [str(entry.indicator_id) for entry in registry.entries if str(entry.source) == "pta_signal_markers"]
    cache_key = _hash(f"{symbol.upper()}|{timeframe}|{packet.evidence_packet_hash}|{use_real_indicators}|{registry.registry_version}")
    if cache_key in _CACHE:
        cached = deepcopy(_CACHE[cache_key])
        cached["cache_hit"] = True
        cached["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        return cached

    runtime_state = "mock_default"
    errors: list[str] = []
    computed_outputs: dict[str, Any] = {}
    telemetry: list[dict[str, object]] = []
    pta_outputs: dict[str, Any] = {}
    pta_telemetry: list[dict[str, object]] = []
    pta_dependency: dict[str, object] = {
        "dependency": "pandas_ta_classic",
        "dependency_available": False,
        "compute_source": "not_requested",
    }
    if use_real_indicators:
        try:
            computed_outputs, telemetry = compute_real_indicator_outputs_with_telemetry(_runtime_closed_candles(symbol.upper(), timeframe), selected)
            runtime_state = "real_indicator_runtime"
        except Exception as exc:  # pragma: no cover - exact exception depends on optional legacy deps.
            runtime_state = "safe_missing_fallback"
            errors.append(f"{type(exc).__name__}: {exc}")
        try:
            pta_outputs, pta_telemetry, pta_dependency = compute_pta_marker_outputs_with_telemetry(
                _runtime_closed_candles(symbol.upper(), timeframe),
                pta_selected,
            )
        except Exception as exc:  # pragma: no cover - exact exception depends on optional legacy deps.
            pta_dependency = {
                "dependency": "pandas_ta_classic",
                "dependency_available": False,
                "compute_source": "vendor.stock_app.shared.indicators.pta_signal_markers",
                "error": f"{type(exc).__name__}: {exc}",
            }

    candidates = _extract_level_candidates(packet, computed_outputs, runtime_state)
    telemetry_counts = _telemetry_counts(telemetry)
    cache_hit_count = sum(1 for row in telemetry if bool(row.get("cache_hit", False)))
    slow_indicator_ids = [
        str(row.get("indicator_id"))
        for row in telemetry
        if str(row.get("status")) in {"slow_warn", "slow_blocked"}
    ]
    pta_accounting = _pta_accounting(
        selected_count=len(pta_selected),
        telemetry=pta_telemetry,
        materialized_output_count=len(pta_outputs),
        requested=use_real_indicators,
    )
    report = {
        "runtime_version": RUNTIME_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "runtime_state": runtime_state,
        "feature_manifest_version": packet.feature_manifest_version,
        "source_registry_version": packet.source_registry_version,
        "evidence_packet_id": packet.evidence_packet_id,
        "evidence_packet_hash": packet.evidence_packet_hash,
        # Backward-compatible fields. They mean level-runtime selected indicators,
        # not the full promoted 9C vector bridge.
        "selected_indicator_count": len(selected),
        "selected_indicator_ids": selected,
        "level_runtime_selected_count": len(selected),
        "level_runtime_selected_ids": selected,
        "vector_promoted_indicator_count": len(vector_promoted),
        "vector_promoted_indicator_ids": vector_promoted,
        "vector_promoted_not_level_selected_count": len(vector_promoted_not_level_selected),
        "vector_promoted_not_level_selected_ids": vector_promoted_not_level_selected,
        "runtime_scope_notes": [
            "selected_indicator_count is preserved for compatibility and means level-runtime selected indicators",
            "vector_promoted_indicator_count is the full set used by the 9C real-indicator vector path",
            "PTA marker outputs are probed for availability only and remain excluded from 9C probability",
        ],
        "indicator_telemetry": telemetry,
        "indicator_telemetry_counts": telemetry_counts,
        "indicator_cache_hit_count": cache_hit_count,
        "indicator_cache_miss_count": max(0, len(telemetry) - cache_hit_count),
        "slow_indicator_count": len(slow_indicator_ids),
        "slow_indicator_ids": slow_indicator_ids,
        "pta_marker_selected_count": len(pta_selected),
        "pta_marker_probe_count": pta_accounting["probe_count"],
        "pta_marker_computed_count": pta_accounting["computed_count"],
        "pta_marker_no_signal_count": pta_accounting["no_signal_count"],
        "pta_marker_dependency_unavailable_count": pta_accounting["dependency_unavailable_count"],
        "pta_marker_error_count": pta_accounting["error_count"],
        # Legacy field retained as materialized outputs only (computed + no-signal).
        # It must never be interpreted as probe completeness.
        "pta_marker_output_count": len(pta_outputs),
        "pta_marker_accounting": pta_accounting,
        "pta_marker_telemetry": pta_telemetry,
        "pta_marker_telemetry_counts": _telemetry_counts(pta_telemetry),
        "pta_marker_dependency": pta_dependency,
        "pta_markers_used_for_probability": False,
        "pta_markers_used_for_9c_vector": False,
        "level_candidates": candidates,
        "missing_outputs": _missing_outputs(selected, computed_outputs, runtime_state),
        "cache_key_hash": cache_key,
        "cache_hit": False,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "errors": errors,
        "output_hash": "",
    }
    report["output_hash"] = _hash(json.dumps({k: v for k, v in report.items() if k not in {"latency_ms", "output_hash"}}, sort_keys=True, default=str, separators=(",", ":")))
    _CACHE[cache_key] = deepcopy(report)
    return report


def _selected_indicator_ids(entries: list[Any]) -> list[str]:
    ids: list[str] = []
    for entry in entries:
        family = str(getattr(entry, "family", "")).lower()
        indicator_id = str(getattr(entry, "indicator_id", ""))
        if family in LEVEL_FAMILIES or any(token in indicator_id for token in ("cpr", "pvt", "pivot", "vwap", "fib", "trendln", "mp_va")):
            ids.append(indicator_id)
    return sorted(set(ids))


def _extract_level_candidates(packet: Any, computed_outputs: dict[str, Any], runtime_state: str) -> list[dict[str, Any]]:
    latest_close = float(packet.last_9_candles[-1]["close"])
    candidates = [
        {
            "level_name": str(level["level_name"]),
            "level_price": float(level["level_price"]),
            "level_type": str(level["level_type"]),
            "source_indicator": str(level["source"]),
            "source_state": "packet",
            "missing_mask": False,
            "point_in_time_safe": True,
        }
        for level in packet.levels
    ]
    if runtime_state == "real_indicator_runtime":
        for indicator_id, payload in computed_outputs.items():
            candidates.extend(_scan_numeric_levels(indicator_id, payload, latest_close))
    return _dedupe_levels(candidates)


def _scan_numeric_levels(indicator_id: str, payload: Any, latest_close: float) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for path, value in _walk_values(payload):
        if isinstance(value, (int, float)) and value == value and abs(float(value)) > 0:
            numeric = float(value)
            if 0.50 * latest_close <= numeric <= 1.50 * latest_close:
                found.append(
                    {
                        "level_name": f"{indicator_id}.{path[-1]}",
                        "level_price": round(numeric, 4),
                        "level_type": "runtime_level",
                        "source_indicator": indicator_id,
                        "source_state": "real_runtime",
                        "missing_mask": False,
                        "point_in_time_safe": True,
                    }
                )
    return found[:12]


def _walk_values(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        rows: list[tuple[tuple[str, ...], Any]] = []
        for key, child in value.items():
            rows.extend(_walk_values(child, path + (str(key),)))
        return rows
    if isinstance(value, list):
        if value and all(not isinstance(item, (dict, list)) for item in value):
            return [(path + ("last",), value[-1])]
        rows = []
        for index, child in enumerate(value[-3:]):
            rows.extend(_walk_values(child, path + (str(index),)))
        return rows
    return [(path, value)]


def _dedupe_levels(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, float]] = set()
    deduped: list[dict[str, Any]] = []
    for item in candidates:
        key = (str(item["level_name"]), round(float(item["level_price"]), 4))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _missing_outputs(selected: list[str], computed_outputs: dict[str, Any], runtime_state: str) -> list[dict[str, Any]]:
    if runtime_state != "real_indicator_runtime":
        return [{"indicator_id": key, "missing_mask": True, "reason": "real indicator runtime disabled"} for key in selected]
    return [
        {"indicator_id": key, "missing_mask": True, "reason": "indicator returned no output"}
        for key in selected
        if key not in computed_outputs or computed_outputs.get(key) in ({}, [], None)
    ]


def _pta_accounting(
    *,
    selected_count: int,
    telemetry: list[dict[str, object]],
    materialized_output_count: int,
    requested: bool,
) -> dict[str, object]:
    counts = _telemetry_counts(telemetry)
    probe_count = len(telemetry)
    computed_count = int(counts.get("computed", 0))
    no_signal_count = int(counts.get("no_signal", 0))
    dependency_unavailable_count = int(counts.get("dependency_unavailable", 0))
    error_count = int(counts.get("error", 0))
    classified_count = computed_count + no_signal_count + dependency_unavailable_count + error_count
    expected_materialized_count = computed_count + no_signal_count
    accounting_pass = (
        probe_count == classified_count
        and materialized_output_count == expected_materialized_count
        and ((not requested and probe_count == 0) or (requested and probe_count == selected_count))
    )
    return {
        "selected_count": selected_count,
        "probe_count": probe_count,
        "computed_count": computed_count,
        "no_signal_count": no_signal_count,
        "dependency_unavailable_count": dependency_unavailable_count,
        "error_count": error_count,
        "materialized_output_count": materialized_output_count,
        "accounting_pass": accounting_pass,
    }


def _telemetry_counts(telemetry: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in telemetry:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
