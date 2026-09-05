from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


JARVIS_REPLAY_DETERMINISM_VERSION = "jarvis-replay-determinism.v0.98"

VOLATILE_KEYS = {
    "api_cost_usd",
    "arbiter_hash",
    "check_hash",
    "check_id",
    "created_at",
    "delivery_id",
    "expires_at",
    "generated_at",
    "imported_at",
    "is_expired",
    "packet_id",
    "record_count",
    "record_hash",
    "report_id",
    "seconds_to_expiry_at_creation",
    "summary_generated_at",
    "updated_at",
    "usefulness_id",
    "valid_until",
}

VOLATILE_SECTIONS = {
    "usefulness_record",
    "usefulness_summary",
}

DETERMINISTIC_SECTIONS = [
    "room_version",
    "mode",
    "symbol",
    "timeframe",
    "packet_metadata",
    "chart_context",
    "candle_structure",
    "indicator_snapshot",
    "sequential_signals",
    "levels_and_zones",
    "multi_timeframe_alignment",
    "similar_history",
    "trade_vision_decision",
    "kronos_summary",
    "gemini_summary",
    "gemini_review_summary",
    "openalgo_summary",
    "paper_reality_check",
    "extended_widgets",
    "safety_summary",
    "system_health_matrix",
    "ui_contract",
    "decision_arbiter",
    "final_action",
    "trade_allowed",
    "order_routing_enabled",
    "live_trading_blocked",
]


def build_jarvis_replay_determinism_report(first_room: dict[str, Any], second_room: dict[str, Any]) -> dict[str, Any]:
    first = canonicalize_jarvis_room(first_room)
    second = canonicalize_jarvis_room(second_room)
    first_hash = _hash(first)
    second_hash = _hash(second)
    diff_paths = _diff_paths(first, second)
    ignored = _ignored_paths(first_room)
    return {
        "determinism_version": JARVIS_REPLAY_DETERMINISM_VERSION,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "symbol": first_room.get("symbol"),
        "timeframe": first_room.get("timeframe"),
        "room_version": first_room.get("room_version"),
        "first_hash": first_hash,
        "second_hash": second_hash,
        "hash_match": first_hash == second_hash,
        "deterministic": first_hash == second_hash and not diff_paths,
        "canonical_section_count": len(first),
        "canonical_sections": sorted(first.keys()),
        "ignored_volatile_fields": sorted(ignored),
        "diff_paths": diff_paths,
        "replay_scope": {
            "includes_chart_context": "chart_context" in first,
            "includes_candle_structure": "candle_structure" in first,
            "includes_indicator_snapshot": "indicator_snapshot" in first,
            "includes_similar_history": "similar_history" in first,
            "includes_trade_vision_decision": "trade_vision_decision" in first,
            "includes_arbiter": "decision_arbiter" in first,
            "ignores_runtime_audit_and_usefulness_records": True,
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def canonicalize_jarvis_room(room: dict[str, Any]) -> dict[str, Any]:
    scoped = {key: room.get(key) for key in DETERMINISTIC_SECTIONS if key in room}
    return _strip_volatile(scoped)


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in VOLATILE_SECTIONS or key in VOLATILE_KEYS:
                continue
            result[key] = _strip_volatile(item)
        return result
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _ignored_paths(value: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in VOLATILE_SECTIONS or key in VOLATILE_KEYS:
                paths.add(path)
                continue
            paths.update(_ignored_paths(item, path))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            paths.update(_ignored_paths(item, f"{prefix}[{idx}]"))
    return paths


def _hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _diff_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if type(left) is not type(right):
        return [prefix or "$"]
    if isinstance(left, dict):
        paths: list[str] = []
        keys = sorted(set(left) | set(right))
        for key in keys:
            path = f"{prefix}.{key}" if prefix else key
            if key not in left or key not in right:
                paths.append(path)
            else:
                paths.extend(_diff_paths(left[key], right[key], path))
        return paths[:50]
    if isinstance(left, list):
        paths = []
        if len(left) != len(right):
            paths.append(f"{prefix}.length" if prefix else "length")
        for idx, (a, b) in enumerate(zip(left, right)):
            paths.extend(_diff_paths(a, b, f"{prefix}[{idx}]"))
        return paths[:50]
    if left != right:
        return [prefix or "$"]
    return []
