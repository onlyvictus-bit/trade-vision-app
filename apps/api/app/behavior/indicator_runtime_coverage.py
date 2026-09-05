from __future__ import annotations

import hashlib
import json
from typing import Any

from .indicator_registry import build_indicator_registry_report
from .real_indicator_adapter import REAL_RUNTIME_PROMOTED_INDICATORS


COVERAGE_VERSION = "9c-indicator-runtime-coverage.v1"


def build_indicator_runtime_coverage_report() -> dict[str, Any]:
    registry = build_indicator_registry_report()
    self_metadata, self_error = _load_self_indicator_metadata()
    pta_metadata, pta_error = _load_pta_indicator_metadata()
    vendor_by_source = {
        "self_indc": self_metadata,
        "pta_signal_markers": pta_metadata,
    }
    rows = []
    for index, entry in enumerate(registry.entries):
        indicator_id = entry.indicator_id
        source = str(entry.source)
        vendor_metadata = vendor_by_source.get(source, {})
        vendor_present = indicator_id in vendor_metadata
        promoted_for_runtime = indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS
        if source == "self_indc" and vendor_present and promoted_for_runtime:
            support_state = "promoted"
        elif source in {"self_indc", "pta_signal_markers"} and vendor_present:
            support_state = "supported_not_promoted"
        elif source == "pta_signal_markers" and pta_error:
            support_state = "adapter_missing"
        else:
            support_state = "unsupported"
        rows.append(
            {
                "indicator_id": indicator_id,
                "manifest_slot": index,
                "source": source,
                "family": entry.family,
                "registry_status": entry.status,
                "callable_name": entry.callable_name,
                "vendor_present": vendor_present,
                "vendor_visual_type": str(vendor_metadata.get(indicator_id, {}).get("visual_type", "")) if vendor_present else None,
                "vendor_category": str(vendor_metadata.get(indicator_id, {}).get("category", "")) if vendor_present else None,
                "promoted_for_runtime": promoted_for_runtime,
                "runtime_support_state": support_state,
                "probability_enabled": False,
                "blocking_reasons": _blocking_reasons(source, vendor_present, promoted_for_runtime, support_state),
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
            }
        )
    counts = _counts(rows)
    report = {
        "coverage_version": COVERAGE_VERSION,
        "registry_version": registry.registry_version,
        "feature_manifest_version": "nine-candle-feature-manifest.v1",
        "total_manifest_slots": len(rows),
        "self_indicator_slots": registry.self_indicator_count,
        "pta_marker_slots": registry.pta_marker_count,
        "vendor_self_registry_count": len(self_metadata),
        "vendor_pta_registry_count": len(pta_metadata),
        "vendor_self_supported_count": sum(1 for row in rows if row["source"] == "self_indc" and row["vendor_present"]),
        "vendor_pta_supported_count": sum(1 for row in rows if row["source"] == "pta_signal_markers" and row["vendor_present"]),
        "runtime_promoted_count": counts.get("promoted", 0),
        "supported_not_promoted_count": counts.get("supported_not_promoted", 0),
        "adapter_missing_count": counts.get("adapter_missing", 0),
        "unsupported_count": counts.get("unsupported", 0),
        "probability_enabled_count": 0,
        "runtime_support_counts": counts,
        "coverage_rows": rows,
        "vendor_metadata_error": self_error,
        "vendor_self_metadata_error": self_error,
        "vendor_pta_metadata_error": pta_error,
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "output_hash": "",
    }
    report["output_hash"] = _hash(
        json.dumps({key: value for key, value in report.items() if key != "output_hash"}, sort_keys=True, default=str, separators=(",", ":"))
    )
    return report


def _load_self_indicator_metadata() -> tuple[dict[str, dict[str, Any]], str | None]:
    try:
        from app.vendor.stock_app.shared.indicators.self_indc import indicator_metadata

        metadata = indicator_metadata()
        return {str(key): dict(value) for key, value in metadata.items()}, None
    except Exception as exc:  # pragma: no cover - environment dependent.
        return {}, f"{type(exc).__name__}: {exc}"


def _load_pta_indicator_metadata() -> tuple[dict[str, dict[str, Any]], str | None]:
    try:
        from app.vendor.stock_app.shared.indicators.pta_signal_markers import PTA_SIGNAL_METADATA

        return {str(key): dict(value) for key, value in PTA_SIGNAL_METADATA.items()}, None
    except Exception as exc:  # pragma: no cover - environment dependent.
        return {}, f"{type(exc).__name__}: {exc}"


def _blocking_reasons(source: str, vendor_present: bool, promoted_for_runtime: bool, support_state: str) -> list[str]:
    reasons = ["probability_disabled_until_pit_stability_calibration_and_backtest_pass"]
    if source == "pta_signal_markers" and support_state == "adapter_missing":
        reasons.append("pta_runtime_adapter_missing")
    if source == "self_indc" and not vendor_present:
        reasons.append("self_indicator_missing_from_vendor_registry")
    if vendor_present and not promoted_for_runtime:
        reasons.append("supported_but_not_promoted_for_9c_runtime")
    if support_state == "promoted":
        reasons.append("explanation_only_until_evidence_promotion")
    return reasons


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row["runtime_support_state"])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
