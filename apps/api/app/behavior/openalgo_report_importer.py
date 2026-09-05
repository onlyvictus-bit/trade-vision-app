from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5


OPENALGO_REPORT_IMPORTER_VERSION = "openalgo-report-importer.v0.93"
SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "broker_credential",
    "cookie",
    "password",
    "secret",
    "session",
    "token",
)


def import_openalgo_report(payload: dict[str, Any]) -> dict[str, Any]:
    raw_report = payload.get("report", payload)
    if not isinstance(raw_report, dict):
        raise ValueError("OpenAlgo report import expects a JSON object.")
    imported_at = datetime.now(timezone.utc).isoformat()
    sanitized_report, redacted_paths = _sanitize(raw_report)
    canonical_hash = _hash(sanitized_report)
    report_id = str(uuid5(NAMESPACE_URL, f"tradevision:openalgo-report:{canonical_hash}"))
    symbol = str(_first_value(sanitized_report, ["symbol", "tradingsymbol", "instrument"]) or payload.get("symbol") or "UNKNOWN").upper()
    report_type = str(payload.get("report_type") or _first_value(sanitized_report, ["report_type", "type", "source"]) or "openalgo_execution_report")
    extracted = _extract_evidence(sanitized_report)
    safety = _safety_result(sanitized_report, extracted, redacted_paths)
    imported = {
        "importer_version": OPENALGO_REPORT_IMPORTER_VERSION,
        "report_id": report_id,
        "imported_at": imported_at,
        "symbol": symbol,
        "report_type": report_type,
        "source": str(payload.get("source") or "openalgo_or_trading_bot"),
        "report_hash": canonical_hash,
        "raw_report_stored": False,
        "sanitized_report": sanitized_report,
        "redacted_field_paths": redacted_paths,
        "extracted_evidence": extracted,
        "safety_result": safety,
        "jarvis_effect": _jarvis_effect(safety, extracted),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "broker_credentials_present": False,
        "broker_order_created": False,
        "live_trading_blocked": True,
        "notes": [
            "v0.93 imports OpenAlgo/trading-bot reports as evidence only.",
            "Imported reports can downgrade Jarvis confidence but cannot create or approve orders.",
            "Secret-like fields are redacted before storage and response.",
        ],
    }
    return imported


def summarize_openalgo_report(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "status": "reserved_for_report_import",
            "report_importer_version": OPENALGO_REPORT_IMPORTER_VERSION,
            "latest_report_id": None,
            "report_available": False,
            "effect": "no_openalgo_report",
            "live_broker_routing_in_trade_vision": False,
            "can_execute_orders": False,
            "trade_allowed": False,
            "order_routing_enabled": False,
            "live_trading_blocked": True,
        }
    safety = report.get("safety_result", {})
    extracted = report.get("extracted_evidence", {})
    return {
        "status": "report_imported",
        "report_importer_version": report.get("importer_version", OPENALGO_REPORT_IMPORTER_VERSION),
        "latest_report_id": report.get("report_id"),
        "report_available": True,
        "imported_at": report.get("imported_at"),
        "report_hash": report.get("report_hash"),
        "symbol": report.get("symbol"),
        "report_type": report.get("report_type"),
        "effect": report.get("jarvis_effect", {}).get("effect", "review_only"),
        "fill_quality": extracted.get("fill_quality", "unknown"),
        "slippage_bps": extracted.get("slippage_bps"),
        "rejection_reasons": safety.get("rejection_reasons", []),
        "warnings": safety.get("warnings", []),
        "live_broker_routing_in_trade_vision": False,
        "can_execute_orders": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _sanitize(value: Any, path: str = "$") -> tuple[Any, list[str]]:
    redacted: list[str] = []
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if _is_secret_key(str(key)):
                clean[key] = "[REDACTED]"
                redacted.append(child_path)
                continue
            child_value, child_redacted = _sanitize(item, child_path)
            clean[key] = child_value
            redacted.extend(child_redacted)
        return clean, redacted
    if isinstance(value, list):
        items: list[Any] = []
        for index, item in enumerate(value):
            child_value, child_redacted = _sanitize(item, f"{path}[{index}]")
            items.append(child_value)
            redacted.extend(child_redacted)
        return items, redacted
    return value, redacted


def _is_secret_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(fragment in lowered for fragment in SECRET_KEY_FRAGMENTS)


def _extract_evidence(report: dict[str, Any]) -> dict[str, Any]:
    fill_price = _to_float(_first_value(report, ["fill_price", "average_price", "avg_price", "executed_price"]))
    intended_price = _to_float(_first_value(report, ["intended_price", "signal_price", "entry_price", "limit_price"]))
    slippage_bps = None
    if fill_price is not None and intended_price and intended_price > 0:
        slippage_bps = round((fill_price - intended_price) / intended_price * 10_000, 3)
    explicit_slippage = _to_float(_first_value(report, ["slippage_bps", "slippage"]))
    if explicit_slippage is not None:
        slippage_bps = explicit_slippage
    latency_ms = _to_float(_first_value(report, ["latency_ms", "execution_latency_ms", "round_trip_ms"]))
    status = str(_first_value(report, ["status", "order_status", "execution_status"]) or "unknown").lower()
    fill_quality = "unknown"
    if status in {"rejected", "cancelled", "failed"}:
        fill_quality = "failed"
    elif slippage_bps is not None and abs(slippage_bps) > 20:
        fill_quality = "poor"
    elif slippage_bps is not None and abs(slippage_bps) > 8:
        fill_quality = "acceptable"
    elif status in {"filled", "complete", "executed"}:
        fill_quality = "good"
    return {
        "status": status,
        "side": str(_first_value(report, ["side", "transaction_type", "action"]) or "unknown").upper(),
        "quantity": _to_float(_first_value(report, ["quantity", "qty", "filled_quantity"])),
        "intended_price": intended_price,
        "fill_price": fill_price,
        "slippage_bps": slippage_bps,
        "latency_ms": latency_ms,
        "fill_quality": fill_quality,
        "fees": _to_float(_first_value(report, ["fees", "brokerage", "cost", "charges"])),
        "rejection_reason": _first_value(report, ["rejection_reason", "reject_reason", "error", "message"]),
    }


def _safety_result(report: dict[str, Any], extracted: dict[str, Any], redacted_paths: list[str]) -> dict[str, Any]:
    rejection_reasons: list[str] = []
    warnings: list[str] = []
    if bool(_first_value(report, ["broker_order_created", "order_created"])):
        rejection_reasons.append("Report says a broker order was created outside Trade Vision; treat as review-only and require reconciliation.")
    if bool(_first_value(report, ["order_routing_enabled", "live_routing_enabled"])):
        rejection_reasons.append("Report says order routing was enabled; Jarvis must not promote this evidence.")
    if bool(_first_value(report, ["live_trading_allowed", "live_trading_enabled"])):
        rejection_reasons.append("Report says live trading was enabled; Jarvis blocks confidence boost.")
    if redacted_paths:
        warnings.append("Secret-like fields were redacted from the imported report.")
    slippage = extracted.get("slippage_bps")
    if isinstance(slippage, (int, float)) and abs(float(slippage)) > 20:
        warnings.append("High slippage detected in OpenAlgo report.")
    if extracted.get("fill_quality") in {"failed", "poor"}:
        warnings.append(f"Fill quality is {extracted.get('fill_quality')}.")
    safe_for_research = not rejection_reasons
    return {
        "safe_for_research_review": safe_for_research,
        "accepted_for_jarvis_evidence": True,
        "confidence_boost_allowed": safe_for_research and not warnings,
        "rejection_reasons": rejection_reasons,
        "warnings": warnings,
        "redaction_count": len(redacted_paths),
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def _jarvis_effect(safety: dict[str, Any], extracted: dict[str, Any]) -> dict[str, Any]:
    if safety.get("rejection_reasons"):
        effect = "downgrade_to_wait"
    elif extracted.get("fill_quality") in {"failed", "poor"}:
        effect = "downgrade_execution_confidence"
    elif safety.get("warnings"):
        effect = "warn_only"
    else:
        effect = "review_only"
    return {
        "effect": effect,
        "can_upgrade_trade": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _first_value(value: Any, names: list[str]) -> Any:
    if isinstance(value, dict):
        lowered = {str(key).lower(): item for key, item in value.items()}
        for name in names:
            if name.lower() in lowered:
                return lowered[name.lower()]
        for item in value.values():
            found = _first_value(item, names)
            if found is not None:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_value(item, names)
            if found is not None:
                return found
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
