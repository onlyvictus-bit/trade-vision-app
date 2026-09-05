from __future__ import annotations

import hashlib
import json
from typing import Any


ARBITER_VERSION = "9c-reasoning-arbiter.v0.74"
AUDIT_VERSION = "9c-decision-audit.v0.74"
DRIFT_VERSION = "9c-calibration-drift-monitor.v0.74"


def build_reasoning_arbiter_report(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    *,
    analog_report: dict[str, Any] | None = None,
    path_report: dict[str, Any] | None = None,
    ood_report: dict[str, Any] | None = None,
    condition_tags: list[str] | None = None,
    subsystem_votes: dict[str, str] | None = None,
) -> dict[str, Any]:
    tags = set(condition_tags or [])
    votes = subsystem_votes or _default_votes(analog_report, ood_report)
    consulted_flags = _consulted_flags(tags, path_report, ood_report)
    disagreement = build_subsystem_disagreement_report(votes)
    hard_flags = {"manipulated_looking", "fake_breakout", "volatility_ood", "shape_ood"}
    override_flags = sorted(flag for flag in consulted_flags if flag in hard_flags)
    override_to_wait = bool(override_flags) or disagreement["disagreement_state"] == "hard_conflict"
    return {
        "arbiter_version": ARBITER_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "consulted_flags": consulted_flags,
        "subsystem_votes": votes,
        "disagreement": disagreement,
        "override_to_wait": override_to_wait,
        "override_reason": _override_reason(override_flags, disagreement),
        "continuation_boost": 0.0 if override_to_wait else _continuation_boost(analog_report),
        "paper_candidate_allowed": False,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


def build_subsystem_disagreement_report(votes: dict[str, str]) -> dict[str, Any]:
    normalized = {key: str(value).upper() for key, value in sorted(votes.items())}
    directional = {value for value in normalized.values() if value in {"LONG", "SHORT"}}
    wait_count = sum(1 for value in normalized.values() if value in {"WAIT", "NO_TRADE", "BLOCK"})
    hard_conflict = len(directional) > 1 or "BLOCK" in normalized.values()
    soft_conflict = not hard_conflict and wait_count > 0 and bool(directional)
    if hard_conflict:
        state = "hard_conflict"
        penalty = 1.0
    elif soft_conflict:
        state = "soft_conflict"
        penalty = 0.45
    else:
        state = "aligned"
        penalty = 0.0
    return {
        "disagreement_version": "9c-subsystem-disagreement.v0.74",
        "votes": normalized,
        "disagreement_state": state,
        "confidence_penalty": penalty,
        "confidence_action": "force_wait" if hard_conflict else ("cap_watch" if soft_conflict else "none"),
    }


def build_decision_audit_record(
    symbol: str,
    timeframe: str,
    *,
    arbiter_report: dict[str, Any],
    decision: str,
    safety_gates: list[dict[str, str]],
) -> dict[str, Any]:
    payload = {
        "audit_version": AUDIT_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "decision": decision,
        "arbiter": {
            "consulted_flags": arbiter_report.get("consulted_flags", []),
            "override_to_wait": bool(arbiter_report.get("override_to_wait", False)),
            "override_reason": arbiter_report.get("override_reason", ""),
            "subsystem_votes": arbiter_report.get("subsystem_votes", {}),
        },
        "gates": safety_gates,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    payload["audit_hash"] = _stable_hash(payload)
    return payload


def build_calibration_drift_report(
    *,
    predicted_error_rate: float = 0.08,
    realized_error_rate: float = 0.11,
    latency_ms: float = 90.0,
    max_error_gap: float = 0.15,
    max_latency_ms: float = 500.0,
) -> dict[str, Any]:
    error_gap = abs(float(realized_error_rate) - float(predicted_error_rate))
    active = error_gap > max_error_gap or latency_ms > max_latency_ms
    drift_types = []
    if error_gap > max_error_gap:
        drift_types.extend(["prediction_drift", "label_drift"])
    if latency_ms > max_latency_ms:
        drift_types.append("latency_drift")
    return {
        "drift_version": DRIFT_VERSION,
        "feature_drift": False,
        "prediction_drift": "prediction_drift" in drift_types,
        "label_drift": "label_drift" in drift_types,
        "latency_drift": "latency_drift" in drift_types,
        "execution_cost_drift": False,
        "predicted_error_rate": round(float(predicted_error_rate), 6),
        "realized_error_rate": round(float(realized_error_rate), 6),
        "error_gap": round(error_gap, 6),
        "latency_ms": round(float(latency_ms), 3),
        "active_drift_block": active,
        "gate": {
            "gate_id": "9C-G018",
            "name": "Calibration drift monitor",
            "status": "wait" if active else "pass",
            "evidence": f"error_gap={round(error_gap, 6)} latency_ms={round(float(latency_ms), 3)} drift_types={drift_types}.",
        },
        "calibrator_action": "demote_to_rule_only" if active else "keep_mock_blocked",
    }


def _default_votes(analog_report: dict[str, Any] | None, ood_report: dict[str, Any] | None) -> dict[str, str]:
    winner = float((analog_report or {}).get("winner_similarity", 0.0))
    failure = float((analog_report or {}).get("failure_similarity", 0.0))
    ood_flag = bool((ood_report or {}).get("ood_flag", False))
    return {
        "analog": "LONG" if winner > failure else "WAIT",
        "ood": "WAIT" if ood_flag else "LONG",
        "risk": "WAIT",
        "htf": "WAIT",
    }


def _consulted_flags(
    tags: set[str],
    path_report: dict[str, Any] | None,
    ood_report: dict[str, Any] | None,
) -> list[str]:
    flags = set(tags)
    if bool((path_report or {}).get("volatility_ood", False)) or bool((ood_report or {}).get("volatility_ood", False)):
        flags.add("volatility_ood")
    if bool((ood_report or {}).get("shape_ood", False)):
        flags.add("shape_ood")
    if float((path_report or {}).get("temporal_diversity_score", 1.0) or 0.0) < 0.25:
        flags.add("low_temporal_diversity")
    return sorted(flags)


def _override_reason(override_flags: list[str], disagreement: dict[str, Any]) -> str:
    if override_flags:
        return "Safety spine override: " + ", ".join(override_flags) + " forces WAIT."
    if disagreement["disagreement_state"] == "hard_conflict":
        return "Subsystem hard conflict forces WAIT."
    if disagreement["disagreement_state"] == "soft_conflict":
        return "Subsystem disagreement caps confidence at WATCH."
    return "No arbiter override."


def _continuation_boost(analog_report: dict[str, Any] | None) -> float:
    winner = float((analog_report or {}).get("winner_similarity", 0.0))
    failure = float((analog_report or {}).get("failure_similarity", 0.0))
    return round(max(0.0, winner - failure), 6)


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
