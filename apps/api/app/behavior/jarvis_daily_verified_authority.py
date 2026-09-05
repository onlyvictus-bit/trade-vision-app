from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


DAILY_VERIFIED_AUTHORITY_VERSION = "jarvis-daily-verified-authority.v1.15"

REQUIRED_HTF_TIMEFRAMES = ("daily", "weekly")


def build_daily_verified_authority_report(
    *,
    symbol: str,
    room: dict[str, Any],
    stale_after_seconds: int = 86_400,
) -> dict[str, Any]:
    bounded_stale = max(300, min(stale_after_seconds, 604_800))
    multi_tf = room.get("multi_timeframe_alignment", {}) if isinstance(room.get("multi_timeframe_alignment"), dict) else {}
    timeframes = multi_tf.get("timeframes", {}) if isinstance(multi_tf.get("timeframes"), dict) else {}
    packet = room.get("packet_metadata", {}) if isinstance(room.get("packet_metadata"), dict) else {}
    generated_at = datetime.now(timezone.utc).isoformat()
    records = [_authority_record(tf, timeframes.get(tf), multi_tf, packet, bounded_stale) for tf in REQUIRED_HTF_TIMEFRAMES]
    htf_available = bool(multi_tf.get("htf_confirmation_available"))
    missing = [record for record in records if not record["available"]]
    stale = [record for record in records if record["stale"]]
    gates = [
        _gate("DAILY-AUTH-001", "Daily closed-candle evidence is present", _record(records, "daily")["available"], "block", "Daily context must come from a closed daily candle."),
        _gate("DAILY-AUTH-002", "Weekly closed-candle evidence is present", _record(records, "weekly")["available"], "block", "Weekly context must come from a closed weekly candle."),
        _gate("DAILY-AUTH-003", "Higher-timeframe confirmation flag is available", htf_available, "downgrade", "HTF confirmation is unavailable, so decision trust must be capped."),
        _gate("DAILY-AUTH-004", "Daily/weekly evidence is fresh enough", not stale, "downgrade", "Stale daily/weekly evidence cannot be used for decision trust."),
        _gate("DAILY-AUTH-005", "Only closed-candle daily data can be cited", True, "block", "No incomplete daily/weekly candle may enter decision evidence."),
        _gate("DAILY-AUTH-006", "No trading authority is granted", True, "block", "Daily authority is evidence-only and cannot create orders."),
    ]
    blockers = [gate for gate in gates if gate["effect"] == "block" and not gate["passed"]]
    warnings = [gate for gate in gates if gate["effect"] == "downgrade" and not gate["passed"]]
    state = "blocked" if blockers else "warning" if warnings else "verified"
    payload = {
        "version": DAILY_VERIFIED_AUTHORITY_VERSION,
        "symbol": symbol.upper(),
        "timeframes": records,
        "gates": gates,
        "packet_id": packet.get("packet_id"),
    }
    authority_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "authority_version": DAILY_VERIFIED_AUTHORITY_VERSION,
        "symbol": symbol.upper(),
        "timeframe": room.get("timeframe"),
        "generated_at": generated_at,
        "authority_hash": authority_hash,
        "packet_id": packet.get("packet_id"),
        "source": "Jarvis multi_timeframe_alignment",
        "closed_candle_only": True,
        "required_timeframes": list(REQUIRED_HTF_TIMEFRAMES),
        "timeframe_records": records,
        "daily_available": _record(records, "daily")["available"],
        "weekly_available": _record(records, "weekly")["available"],
        "htf_confirmation_available": htf_available,
        "missing_timeframes": [record["timeframe"] for record in missing],
        "stale_timeframes": [record["timeframe"] for record in stale],
        "citable_evidence_keys": [
            "multi_timeframe_alignment",
            "multi_timeframe_alignment.timeframes.daily",
            "multi_timeframe_alignment.timeframes.weekly",
            "multi_timeframe_alignment.htf_confirmation_available",
            "daily_verified_authority.timeframe_records",
        ],
        "blocked_claim_types": [
            "uncited_daily_bias",
            "uncited_weekly_bias",
            "incomplete_daily_candle_claim",
            "incomplete_weekly_candle_claim",
        ],
        "gates": gates,
        "authority_state": state,
        "decision_trust_allowed": state == "verified",
        "decision_confidence_cap_pct": 45 if blockers else 60 if warnings else 100,
        "operator_message": _operator_message(state, missing, stale),
        "external_ai_daily_claims_allowed": state == "verified",
        "external_ai_must_cite_keys": True,
        "confidence_boost_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _authority_record(
    timeframe: str,
    state: Any,
    multi_tf: dict[str, Any],
    packet: dict[str, Any],
    stale_after_seconds: int,
) -> dict[str, Any]:
    state_text = str(state or "not_available_closed_candle_only")
    unavailable = state_text.startswith("not_available") or state_text in {"", "none", "null"}
    timestamp = packet.get("created_at")
    age = _age_seconds(timestamp)
    return {
        "timeframe": timeframe,
        "state": state_text,
        "available": not unavailable,
        "closed_candle_only": True,
        "source_key": f"multi_timeframe_alignment.timeframes.{timeframe}",
        "source_created_at": timestamp,
        "age_seconds": age,
        "stale_after_seconds": stale_after_seconds,
        "stale": age is None or age > stale_after_seconds,
        "citable": not unavailable and age is not None and age <= stale_after_seconds,
        "alignment_score": multi_tf.get("alignment_score"),
    }


def _record(records: list[dict[str, Any]], timeframe: str) -> dict[str, Any]:
    for record in records:
        if record["timeframe"] == timeframe:
            return record
    return {"timeframe": timeframe, "available": False, "stale": True}


def _age_seconds(value: Any) -> int | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()))
    except ValueError:
        return None


def _gate(gate_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _operator_message(state: str, missing: list[dict[str, Any]], stale: list[dict[str, Any]]) -> str:
    if state == "blocked":
        missing_names = ", ".join(record["timeframe"] for record in missing) or "unknown"
        return f"Daily verified authority is blocked because closed-candle evidence is missing for: {missing_names}."
    if stale:
        stale_names = ", ".join(record["timeframe"] for record in stale)
        return f"Daily verified authority is warning because evidence is stale for: {stale_names}."
    if state == "warning":
        return "Daily/weekly evidence exists, but higher-timeframe confirmation is incomplete; cap decision trust."
    return "Daily and weekly closed-candle authority is verified for review use only."
