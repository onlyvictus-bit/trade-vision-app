from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from typing import Any

from .indicator_registry import build_indicator_registry_report
from .nine_candle_hybrid import _runtime_closed_candles, build_evidence_packet
from .real_indicator_adapter import REAL_RUNTIME_PROMOTED_INDICATORS, compute_real_indicator_outputs_with_telemetry


PROMOTION_REPORT_VERSION = "9c-indicator-promotion-gates.v1"
_CACHE: dict[str, dict[str, Any]] = {}


def build_indicator_promotion_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    normalized_symbol = symbol.upper()
    registry = build_indicator_registry_report()
    packet = build_evidence_packet(normalized_symbol, timeframe)
    cache_key = _hash(
        f"{normalized_symbol}|{timeframe}|{registry.registry_version}|"
        f"{packet.feature_manifest_version}|{packet.evidence_packet_hash}|{use_real_indicators}"
    )
    if cache_key in _CACHE:
        cached = deepcopy(_CACHE[cache_key])
        cached["cache_hit"] = True
        cached["latency_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
        return cached

    telemetry_by_id: dict[str, dict[str, Any]] = {}
    runtime_state = "mock_default"
    runtime_errors: list[str] = []
    if use_real_indicators:
        try:
            promoted = sorted(REAL_RUNTIME_PROMOTED_INDICATORS)
            _, telemetry = compute_real_indicator_outputs_with_telemetry(
                _runtime_closed_candles(normalized_symbol, timeframe),
                promoted,
            )
            telemetry_by_id = {str(row["indicator_id"]): dict(row) for row in telemetry}
            runtime_state = "real_indicator_runtime"
        except Exception as exc:  # pragma: no cover - optional legacy dependency failures vary locally.
            runtime_state = "safe_missing_fallback"
            runtime_errors.append(f"{type(exc).__name__}: {exc}")

    rows = [
        _promotion_row(entry, index, use_real_indicators, runtime_state, telemetry_by_id)
        for index, entry in enumerate(registry.entries)
    ]
    state_counts = _count_by(rows, "current_state")
    cache_hit_count = sum(1 for row in rows if bool(row.get("runtime_cache_hit", False)))
    slow_indicator_ids = [
        str(row["indicator_id"])
        for row in rows
        if str(row.get("runtime_status")) in {"slow_warn", "slow_blocked"}
    ]
    report = {
        "promotion_report_version": PROMOTION_REPORT_VERSION,
        "symbol": normalized_symbol,
        "timeframe": timeframe,
        "use_real_indicators": use_real_indicators,
        "runtime_state": runtime_state,
        "registry_version": registry.registry_version,
        "feature_manifest_version": packet.feature_manifest_version,
        "evidence_packet_id": packet.evidence_packet_id,
        "evidence_packet_hash": packet.evidence_packet_hash,
        "total_indicators": len(rows),
        "promoted_for_runtime_count": sum(1 for row in rows if row["promoted_for_runtime"]),
        "masked_count": state_counts.get("masked", 0),
        "explanation_only_count": state_counts.get("explanation_only", 0),
        "probability_eligible_count": state_counts.get("probability_eligible", 0),
        "state_counts": state_counts,
        "runtime_status_counts": _count_by(rows, "runtime_status"),
        "runtime_cache_hit_count": cache_hit_count,
        "runtime_cache_miss_count": max(0, sum(1 for row in rows if row["promoted_for_runtime"]) - cache_hit_count),
        "slow_indicator_count": len(slow_indicator_ids),
        "slow_indicator_ids": slow_indicator_ids,
        "promotion_rows": rows,
        "promotion_policy": {
            "default_state": "masked",
            "real_indicator_runtime": "opt_in_only",
            "probability_gate": "blocked_until_pit_stability_evidence_calibration_and_backtest_pass",
            "mock_runtime": "never_probability_eligible",
        },
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "cache_hit": False,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "runtime_errors": runtime_errors,
        "output_hash": "",
    }
    report["output_hash"] = _hash(
        json.dumps(
            {key: value for key, value in report.items() if key not in {"latency_ms", "output_hash"}},
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
    )
    _CACHE[cache_key] = deepcopy(report)
    return report


def _promotion_row(
    entry: Any,
    manifest_slot: int,
    use_real_indicators: bool,
    runtime_state: str,
    telemetry_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    indicator_id = str(getattr(entry, "indicator_id"))
    promoted_for_runtime = indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS
    telemetry = telemetry_by_id.get(indicator_id, {})
    runtime_status = _runtime_status(indicator_id, use_real_indicators, runtime_state, telemetry)
    output_present = bool(telemetry.get("output_present", False))
    latency_ms = telemetry.get("latency_ms")
    source_latency_ms = telemetry.get("source_latency_ms", latency_ms)
    runtime_cache_hit = bool(telemetry.get("cache_hit", False))
    pit_gate = "pass" if bool(getattr(entry, "closed_bar_only", False)) and bool(getattr(entry, "point_in_time_safe", False)) else "fail"
    latency_gate = _latency_gate(runtime_status)
    output_gate = "pass" if output_present and runtime_status in {"computed", "slow_warn"} else "fail"
    evidence_gate = "pending"
    probability_gate = "blocked"
    blocking_reasons = _blocking_reasons(
        entry=entry,
        promoted_for_runtime=promoted_for_runtime,
        use_real_indicators=use_real_indicators,
        runtime_state=runtime_state,
        runtime_status=runtime_status,
        pit_gate=pit_gate,
        latency_gate=latency_gate,
        output_gate=output_gate,
        evidence_gate=evidence_gate,
    )
    current_state = _current_state(
        entry=entry,
        runtime_status=runtime_status,
        pit_gate=pit_gate,
        latency_gate=latency_gate,
        output_gate=output_gate,
        evidence_gate=evidence_gate,
        blocking_reasons=blocking_reasons,
    )
    return {
        "indicator_id": indicator_id,
        "display_name": str(getattr(entry, "display_name", indicator_id)),
        "family": str(getattr(entry, "family", "unknown")),
        "source": str(getattr(entry, "source", "unknown")),
        "registry_status": str(getattr(entry, "status", "unknown")),
        "current_state": current_state,
        "manifest_slot": manifest_slot,
        "promoted_for_runtime": promoted_for_runtime,
        "runtime_status": runtime_status,
        "latency_ms": latency_ms,
        "source_latency_ms": source_latency_ms,
        "runtime_cache_hit": runtime_cache_hit,
        "pit_gate": pit_gate,
        "latency_gate": latency_gate,
        "output_gate": output_gate,
        "evidence_gate": evidence_gate,
        "probability_gate": probability_gate,
        "used_for_probability": bool(getattr(entry, "used_for_probability", False)),
        "live_trading_blocked": True,
        "blocking_reasons": blocking_reasons,
        "notes": _notes(current_state, runtime_status, evidence_gate),
    }


def _runtime_status(
    indicator_id: str,
    use_real_indicators: bool,
    runtime_state: str,
    telemetry: dict[str, Any],
) -> str:
    if indicator_id not in REAL_RUNTIME_PROMOTED_INDICATORS:
        return "not_promoted"
    if not use_real_indicators:
        return "runtime_disabled"
    if runtime_state != "real_indicator_runtime":
        return runtime_state
    return str(telemetry.get("status", "not_checked"))


def _latency_gate(runtime_status: str) -> str:
    if runtime_status == "slow_warn":
        return "warn"
    if runtime_status == "slow_blocked":
        return "fail"
    if runtime_status in {"computed", "no_output", "error"}:
        return "pass"
    return "pending"


def _blocking_reasons(
    entry: Any,
    promoted_for_runtime: bool,
    use_real_indicators: bool,
    runtime_state: str,
    runtime_status: str,
    pit_gate: str,
    latency_gate: str,
    output_gate: str,
    evidence_gate: str,
) -> list[str]:
    reasons: list[str] = []
    if not promoted_for_runtime:
        reasons.append("not_promoted_for_local_runtime")
    if not use_real_indicators:
        reasons.append("real_indicator_runtime_disabled")
    if runtime_state == "safe_missing_fallback":
        reasons.append("real_indicator_runtime_failed_safe")
    if runtime_status in {"error", "no_output", "slow_blocked", "safe_missing_fallback"}:
        reasons.append(f"runtime_status_{runtime_status}")
    if pit_gate != "pass":
        reasons.append("pit_gate_failed")
    if latency_gate == "fail":
        reasons.append("latency_gate_failed")
    if output_gate != "pass":
        reasons.append("output_not_available_for_vector")
    if evidence_gate != "pass":
        reasons.append("probability_evidence_pending")
    if not bool(getattr(entry, "used_for_probability", False)):
        reasons.append("registry_probability_disabled")
    return sorted(set(reasons))


def _current_state(
    entry: Any,
    runtime_status: str,
    pit_gate: str,
    latency_gate: str,
    output_gate: str,
    evidence_gate: str,
    blocking_reasons: list[str],
) -> str:
    if (
        bool(getattr(entry, "used_for_probability", False))
        and runtime_status in {"computed", "slow_warn"}
        and pit_gate == "pass"
        and latency_gate in {"pass", "warn"}
        and output_gate == "pass"
        and evidence_gate == "pass"
    ):
        return "probability_eligible"
    explanation_blockers = {
        "not_promoted_for_local_runtime",
        "real_indicator_runtime_disabled",
        "real_indicator_runtime_failed_safe",
        "pit_gate_failed",
        "latency_gate_failed",
        "output_not_available_for_vector",
    }
    if runtime_status in {"computed", "slow_warn"} and not explanation_blockers.intersection(blocking_reasons):
        return "explanation_only"
    return "masked"


def _notes(current_state: str, runtime_status: str, evidence_gate: str) -> list[str]:
    if current_state == "probability_eligible":
        return ["Indicator passed runtime, PIT, latency, output, evidence, and registry probability gates."]
    if current_state == "explanation_only":
        return [
            "Indicator output is available for chart/Jarvis explanation.",
            f"Probability remains blocked because evidence_gate={evidence_gate}.",
        ]
    return [f"Indicator is masked for 9C probability use; runtime_status={runtime_status}."]


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
