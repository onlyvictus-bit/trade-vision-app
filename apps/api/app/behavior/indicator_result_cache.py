from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from .. import storage
from ..models import now_iso
from .indicator_registry import build_indicator_registry_report
from .nine_candle_hybrid import FEATURE_MANIFEST_VERSION, _runtime_closed_candles, build_evidence_packet
from .real_indicator_adapter import REAL_RUNTIME_PROMOTED_INDICATORS, compute_real_indicator_outputs_with_telemetry


CACHE_SCHEMA_VERSION = "indicator-result-cache.v1"
CACHE_MODULE_VERSION = "indicator-result-cache.v1.64"
ARTIFACT_ROOT = storage.PROJECT_ROOT / "data" / "indicator_result_cache"


def save_indicator_results(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    use_real_indicators: bool = False,
    force_recompute: bool = False,
    anomalous_snapshot: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    normalized = symbol.upper()
    context = _cache_context(normalized, timeframe)
    if anomalous_snapshot:
        return _quarantined_report(normalized, timeframe, context, started)
    existing = _indexed_existing(context) if not force_recompute else {}
    outputs: dict[str, Any] = {}
    telemetry: list[dict[str, Any]] = []
    reused_rows: list[dict[str, Any]] = []
    saved_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    if not use_real_indicators:
        telemetry = [
            {
                "indicator_id": indicator_id,
                "status": "mock_runtime_disabled",
                "latency_ms": 0.0,
                "source_latency_ms": 0.0,
                "output_present": False,
                "error": "real indicator runtime disabled",
                "cache_hit": False,
            }
            for indicator_id in context["indicator_ids"]
        ]
    else:
        reusable_ids = []
        for indicator_id in context["indicator_ids"]:
            cached = existing.get(indicator_id)
            if cached and _artifact_is_valid(cached):
                reused_rows.append(_public_row(cached, cache_integrity_status="verified"))
                reusable_ids.append(indicator_id)
            elif cached:
                failed_rows.append(_public_row(cached, cache_integrity_status="failed"))
        compute_ids = [indicator_id for indicator_id in context["indicator_ids"] if indicator_id not in set(reusable_ids)]
        if compute_ids:
            outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
                _runtime_closed_candles(normalized, timeframe),
                compute_ids,
            )

    for row in telemetry:
        indicator_id = str(row.get("indicator_id"))
        payload = deepcopy(outputs.get(indicator_id))
        try:
            cache_row = _write_indicator_artifact(context, indicator_id, row, payload)
            storage.save_indicator_result_cache_row(cache_row)
            saved_rows.append(_public_row(cache_row, cache_integrity_status="saved"))
        except OSError as exc:
            failed_rows.append(_failed_public_row(context, indicator_id, row, f"artifact_write_failed:{exc}"))

    slow_ids = [
        str(row.get("indicator_id"))
        for row in saved_rows + reused_rows
        if str(row.get("runtime_status")) in {"slow_warn", "slow_blocked"}
    ]
    cache_size_bytes = _artifact_size_bytes()
    report = {
        "cache_version": CACHE_MODULE_VERSION,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "symbol": normalized,
        "timeframe": timeframe,
        "source_snapshot_hash": context["source_snapshot_hash"],
        "source_snapshot_id": context["source_snapshot_id"],
        "indicator_registry_version": context["indicator_registry_version"],
        "feature_manifest_version": context["feature_manifest_version"],
        "promoted_indicator_hash": context["promoted_indicator_hash"],
        "use_real_indicators": use_real_indicators,
        "force_recompute": force_recompute,
        "cache_status": "saved" if saved_rows else ("hit" if reused_rows else "miss"),
        "saved_count": len(saved_rows),
        "reused_count": len(reused_rows),
        "failed_count": len(failed_rows),
        "stored_count": len(storage.list_indicator_result_cache_rows(normalized, timeframe, context["source_snapshot_hash"])),
        "slow_indicator_count": len(slow_ids),
        "slow_indicator_ids": slow_ids,
        "cache_size_bytes": cache_size_bytes,
        "cache_hit_rate": _hit_rate(len(reused_rows), len(saved_rows)),
        "cache_integrity_status": "verified" if not failed_rows else "degraded_recomputed",
        "quarantine_status": "clean_reference_only",
        "anomalous_snapshot_quarantined": False,
        "reference_only": True,
        "rows": saved_rows + reused_rows,
        "failed_rows": failed_rows,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "operator_message": "Indicator cache is a speed and audit layer only. It cannot unlock probability or trading.",
    }
    report["output_hash"] = _hash_json({key: value for key, value in report.items() if key not in {"latency_ms", "output_hash"}})
    return report


def indicator_cache_status(symbol: str = "RELIANCE", timeframe: str = "1m") -> dict[str, Any]:
    started = time.perf_counter()
    normalized = symbol.upper()
    context = _cache_context(normalized, timeframe)
    rows = storage.list_indicator_result_cache_rows(normalized, timeframe, context["source_snapshot_hash"])
    verified = [_public_row(row, cache_integrity_status=_cache_integrity_status(row, context)) for row in rows]
    failed = [row for row in verified if row["cache_integrity_status"] != "verified"]
    return {
        "cache_version": CACHE_MODULE_VERSION,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "symbol": normalized,
        "timeframe": timeframe,
        "source_snapshot_hash": context["source_snapshot_hash"],
        "source_snapshot_id": context["source_snapshot_id"],
        "indicator_registry_version": context["indicator_registry_version"],
        "feature_manifest_version": context["feature_manifest_version"],
        "promoted_indicator_hash": context["promoted_indicator_hash"],
        "cache_status": "hit" if rows else "miss",
        "stored_count": len(rows),
        "verified_count": len(verified) - len(failed),
        "failed_count": len(failed),
        "slow_indicator_count": sum(1 for row in verified if row["runtime_status"] in {"slow_warn", "slow_blocked"}),
        "cache_size_bytes": _artifact_size_bytes(),
        "rows": verified[:50],
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def indicator_cache_results(symbol: str = "RELIANCE", timeframe: str = "1m", limit: int = 100) -> dict[str, Any]:
    started = time.perf_counter()
    normalized = symbol.upper()
    context = _cache_context(normalized, timeframe)
    rows = storage.list_indicator_result_cache_rows(normalized, timeframe, limit=limit)
    results = []
    failed = 0
    for row in rows:
        integrity = _cache_integrity_status(row, context)
        artifact = _read_artifact(row) if integrity == "verified" else None
        if artifact is None:
            failed += 1
        public = _public_row(row, cache_integrity_status=integrity)
        public["artifact"] = artifact
        results.append(public)
    return {
        "cache_version": CACHE_MODULE_VERSION,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "symbol": normalized,
        "timeframe": timeframe,
        "result_count": len(results),
        "failed_count": failed,
        "results": results,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def delete_indicator_cache(cache_id: str) -> dict[str, Any]:
    row = storage.delete_indicator_result_cache_row(cache_id)
    deleted = row is not None
    if row is not None:
        artifact_path = _artifact_path_from_uri(str(row["artifact_uri"]))
        try:
            artifact_path.unlink(missing_ok=True)
        except OSError:
            pass
    return {
        "cache_version": CACHE_MODULE_VERSION,
        "cache_id": cache_id,
        "deleted": deleted,
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _cache_context(symbol: str, timeframe: str) -> dict[str, Any]:
    packet = build_evidence_packet(symbol, timeframe)
    registry = build_indicator_registry_report()
    indicator_ids = sorted(REAL_RUNTIME_PROMOTED_INDICATORS)
    promoted_hash = _hash_text("|".join(indicator_ids))
    first_candle = packet.last_9_candles[0] if packet.last_9_candles else None
    last_candle = packet.last_9_candles[-1] if packet.last_9_candles else None
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "source_snapshot_hash": packet.evidence_packet_hash,
        "source_snapshot_id": packet.evidence_packet_id,
        "candle_start_time": getattr(first_candle, "event_time", None) if first_candle is not None else None,
        "candle_end_time": getattr(last_candle, "event_time", None) if last_candle is not None else None,
        "candle_count": len(packet.last_9_candles),
        "indicator_registry_version": registry.registry_version,
        "feature_manifest_version": FEATURE_MANIFEST_VERSION,
        "promoted_indicator_hash": promoted_hash,
        "indicator_ids": indicator_ids,
        "volatility_context": _volatility_context(symbol, timeframe),
    }


def _indexed_existing(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = storage.list_indicator_result_cache_rows(
        context["symbol"],
        context["timeframe"],
        context["source_snapshot_hash"],
    )
    exact: dict[str, dict[str, Any]] = {}
    for row in rows:
        if (
            row["indicator_registry_version"] == context["indicator_registry_version"]
            and row["feature_manifest_version"] == context["feature_manifest_version"]
            and row["promoted_indicator_hash"] == context["promoted_indicator_hash"]
            and _cache_integrity_status(row, context) == "verified"
        ):
            exact[str(row["indicator_id"])] = row
    return exact


def _write_indicator_artifact(
    context: dict[str, Any],
    indicator_id: str,
    telemetry_row: dict[str, Any],
    payload: Any,
) -> dict[str, Any]:
    created_at = now_iso()
    runtime_status = str(telemetry_row.get("status") or "unknown")
    output_present = bool(telemetry_row.get("output_present", False))
    cache_id = _cache_id(context, indicator_id)
    artifact = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "symbol": context["symbol"],
        "timeframe": context["timeframe"],
        "source_snapshot_hash": context["source_snapshot_hash"],
        "indicator_id": indicator_id,
        "runtime_status": runtime_status,
        "context": {
            "volatility_bucket": context["volatility_context"]["volatility_bucket"],
            "volatility_ood": context["volatility_context"]["volatility_ood"],
            "volatility_threshold_source": context["volatility_context"]["threshold_source"],
        },
        "payload": payload if output_present else {},
        "telemetry": {
            **telemetry_row,
            "cache_id": cache_id,
        },
        "safety": {
            "reference_only": True,
            "can_seed_9c_vector": False,
            "used_for_probability": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        },
    }
    artifact_json = _canonical_json(artifact)
    artifact_sha = _hash_text(artifact_json)
    artifact_path = _artifact_path(cache_id)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(artifact_json, encoding="utf-8")
    return {
        "cache_id": cache_id,
        "symbol": context["symbol"],
        "timeframe": context["timeframe"],
        "source_snapshot_hash": context["source_snapshot_hash"],
        "source_snapshot_id": context["source_snapshot_id"],
        "candle_start_time": context["candle_start_time"],
        "candle_end_time": context["candle_end_time"],
        "candle_count": context["candle_count"],
        "indicator_registry_version": context["indicator_registry_version"],
        "feature_manifest_version": context["feature_manifest_version"],
        "promoted_indicator_hash": context["promoted_indicator_hash"],
        "indicator_id": indicator_id,
        "runtime_status": runtime_status,
        "output_present": output_present,
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "artifact_uri": str(artifact_path.relative_to(storage.PROJECT_ROOT)).replace("\\", "/"),
        "artifact_sha256": artifact_sha,
        "latency_ms": float(telemetry_row.get("source_latency_ms") or telemetry_row.get("latency_ms") or 0.0),
        "created_at": created_at,
    }


def _public_row(row: dict[str, Any], *, cache_integrity_status: str) -> dict[str, Any]:
    return {
        "cache_id": str(row["cache_id"]),
        "symbol": str(row["symbol"]),
        "timeframe": str(row["timeframe"]),
        "source_snapshot_hash": str(row["source_snapshot_hash"]),
        "source_snapshot_id": row.get("source_snapshot_id"),
        "indicator_id": str(row["indicator_id"]),
        "runtime_status": str(row["runtime_status"]),
        "output_present": bool(row["output_present"]),
        "indicator_registry_version": str(row["indicator_registry_version"]),
        "feature_manifest_version": str(row["feature_manifest_version"]),
        "promoted_indicator_hash": str(row["promoted_indicator_hash"]),
        "artifact_uri": str(row["artifact_uri"]),
        "artifact_sha256": str(row["artifact_sha256"]),
        "cache_integrity_status": cache_integrity_status,
        "reference_only": True,
        "can_seed_9c_vector": False,
        "latency_ms": float(row["latency_ms"]),
        "created_at": str(row["created_at"]),
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _failed_public_row(
    context: dict[str, Any],
    indicator_id: str,
    telemetry_row: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "cache_id": _cache_id(context, indicator_id),
        "symbol": context["symbol"],
        "timeframe": context["timeframe"],
        "source_snapshot_hash": context["source_snapshot_hash"],
        "source_snapshot_id": context["source_snapshot_id"],
        "indicator_id": indicator_id,
        "runtime_status": "cache_write_failed",
        "output_present": False,
        "indicator_registry_version": context["indicator_registry_version"],
        "feature_manifest_version": context["feature_manifest_version"],
        "promoted_indicator_hash": context["promoted_indicator_hash"],
        "artifact_uri": "",
        "artifact_sha256": "",
        "cache_integrity_status": "failed",
        "failure_reason": reason,
        "reference_only": True,
        "can_seed_9c_vector": False,
        "latency_ms": float(telemetry_row.get("source_latency_ms") or telemetry_row.get("latency_ms") or 0.0),
        "created_at": now_iso(),
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _artifact_is_valid(row: dict[str, Any]) -> bool:
    path = _artifact_path_from_uri(str(row["artifact_uri"]))
    if not path.exists():
        return False
    payload = path.read_text(encoding="utf-8")
    return _hash_text(payload) == str(row["artifact_sha256"])


def _cache_integrity_status(row: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    if context is not None:
        if str(row.get("indicator_registry_version")) != str(context["indicator_registry_version"]):
            return "stale_registry_version"
        if str(row.get("feature_manifest_version")) != str(context["feature_manifest_version"]):
            return "stale_feature_manifest_version"
        if str(row.get("promoted_indicator_hash")) != str(context["promoted_indicator_hash"]):
            return "stale_promoted_indicator_hash"
        if str(row.get("source_snapshot_hash")) != str(context["source_snapshot_hash"]):
            return "stale_source_snapshot"
    if not _artifact_is_valid(row):
        return "failed"
    if context is not None and _artifact_volatility_is_stale(row, context):
        return "stale_volatility_bucket"
    return "verified"


def _read_artifact(row: dict[str, Any]) -> dict[str, Any] | None:
    if not _artifact_is_valid(row):
        return None
    try:
        return json.loads(_artifact_path_from_uri(str(row["artifact_uri"])).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _artifact_volatility_is_stale(row: dict[str, Any], context: dict[str, Any]) -> bool:
    try:
        artifact = json.loads(_artifact_path_from_uri(str(row["artifact_uri"])).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, KeyError):
        return True
    stored = artifact.get("context", {})
    current = context.get("volatility_context", {})
    stored_bucket = stored.get("volatility_bucket")
    current_bucket = current.get("volatility_bucket")
    if stored_bucket in {None, "unknown"} or current_bucket in {None, "unknown"}:
        return False
    return (
        str(stored_bucket) != str(current_bucket)
        or bool(stored.get("volatility_ood", False)) != bool(current.get("volatility_ood", False))
    )


def _artifact_path(cache_id: str) -> Path:
    return ARTIFACT_ROOT / f"{cache_id}.json"


def _artifact_path_from_uri(uri: str) -> Path:
    path = Path(uri)
    return path if path.is_absolute() else storage.PROJECT_ROOT / path


def _cache_id(context: dict[str, Any], indicator_id: str) -> str:
    raw = "|".join(
        [
            context["symbol"],
            context["timeframe"],
            context["source_snapshot_hash"],
            indicator_id,
            context["indicator_registry_version"],
            context["feature_manifest_version"],
            context["promoted_indicator_hash"],
        ]
    )
    return _hash_text(raw)


def _artifact_size_bytes() -> int:
    if not ARTIFACT_ROOT.exists():
        return 0
    return sum(path.stat().st_size for path in ARTIFACT_ROOT.glob("*.json") if path.is_file())


def _hit_rate(reused: int, saved: int) -> float:
    total = reused + saved
    return round(reused / total, 6) if total else 0.0


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _hash_json(value: Any) -> str:
    return _hash_text(_canonical_json(value))


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _volatility_context(symbol: str, timeframe: str) -> dict[str, Any]:
    try:
        from .nine_candle_history import build_path_analog_report

        status = build_path_analog_report(symbol, timeframe, limit=1).get("volatility_status", {})
        return {
            "volatility_bucket": str(status.get("volatility_bucket", "unknown")),
            "volatility_ood": bool(status.get("volatility_ood", False)),
            "threshold_source": str(status.get("threshold_source", "unavailable")),
        }
    except Exception:
        return {
            "volatility_bucket": "unknown",
            "volatility_ood": False,
            "threshold_source": "unavailable",
        }


def _quarantined_report(
    symbol: str,
    timeframe: str,
    context: dict[str, Any],
    started: float,
) -> dict[str, Any]:
    report = {
        "cache_version": CACHE_MODULE_VERSION,
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "symbol": symbol,
        "timeframe": timeframe,
        "source_snapshot_hash": context["source_snapshot_hash"],
        "source_snapshot_id": context["source_snapshot_id"],
        "indicator_registry_version": context["indicator_registry_version"],
        "feature_manifest_version": context["feature_manifest_version"],
        "promoted_indicator_hash": context["promoted_indicator_hash"],
        "use_real_indicators": False,
        "force_recompute": False,
        "cache_status": "anomalous_snapshot_quarantined",
        "saved_count": 0,
        "reused_count": 0,
        "failed_count": 0,
        "stored_count": len(storage.list_indicator_result_cache_rows(symbol, timeframe, context["source_snapshot_hash"])),
        "slow_indicator_count": 0,
        "slow_indicator_ids": [],
        "cache_size_bytes": _artifact_size_bytes(),
        "cache_hit_rate": 0.0,
        "cache_integrity_status": "quarantined_reference_only",
        "quarantine_status": "anomalous_snapshot_quarantined",
        "anomalous_snapshot_quarantined": True,
        "reference_only": True,
        "can_seed_9c_vector": False,
        "rows": [],
        "failed_rows": [],
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "no_future_leakage": True,
        "future_bar_blocked": True,
        "closed_candle_only": True,
        "used_for_probability": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "operator_message": "Anomalous snapshot quarantined. No indicator cache artifact was persisted or reused.",
    }
    report["output_hash"] = _hash_json({key: value for key, value in report.items() if key not in {"latency_ms", "output_hash"}})
    return report
