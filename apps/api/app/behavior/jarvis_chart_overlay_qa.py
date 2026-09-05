from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


CHART_OVERLAY_QA_VERSION = "jarvis-chart-overlay-qa.v1.25"


def build_chart_overlay_qa_report(
    *,
    symbol: str,
    jarvis_room: dict[str, Any],
    trading_decision_output: dict[str, Any],
) -> dict[str, Any]:
    chart = jarvis_room.get("chart_context", {}) if isinstance(jarvis_room.get("chart_context"), dict) else {}
    bars = chart.get("bars", []) if isinstance(chart.get("bars"), list) else []
    overlays = chart.get("overlays", {}) if isinstance(chart.get("overlays"), dict) else {}
    focus = trading_decision_output.get("chart_screen_focus", {}) if isinstance(trading_decision_output.get("chart_screen_focus"), dict) else {}
    blockers = trading_decision_output.get("blocker_rows", []) if isinstance(trading_decision_output.get("blocker_rows"), list) else []
    similar = trading_decision_output.get("similar_history_cases", []) if isinstance(trading_decision_output.get("similar_history_cases"), list) else []
    labels = _overlay_labels(focus, overlays)
    checks = _checks(bars, focus, overlays, labels, blockers, similar, trading_decision_output)
    blockers_failed = [check for check in checks if check["effect"] == "block" and not check["passed"]]
    warnings = [check for check in checks if check["effect"] == "warn" and not check["passed"]]
    qa_state = "failed" if blockers_failed else "warning" if warnings else "passed"
    primitives = _render_primitives(focus, overlays, blockers, similar)
    payload = {
        "version": CHART_OVERLAY_QA_VERSION,
        "symbol": symbol.upper(),
        "qa_state": qa_state,
        "labels": labels,
        "checks": checks,
        "primitives": primitives,
    }
    return {
        "qa_version": CHART_OVERLAY_QA_VERSION,
        "symbol": symbol.upper(),
        "timeframe": jarvis_room.get("timeframe"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "qa_state": qa_state,
        "qa_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "chart_nonblank": len(bars) > 0,
        "bar_count": len(bars),
        "overlay_labels": labels,
        "render_primitives": primitives,
        "similar_marker_count": min(len(similar), 5),
        "blocker_chip_count": min(len(blockers), 4),
        "checks": checks,
        "operator_message": _operator_message(qa_state, blockers_failed, warnings),
        "frontend_test_hooks": {
            "chart_root": "jarvis-decision-chart",
            "entry_zone": "jarvis-chart-entry-zone",
            "stop_line": "jarvis-chart-stop-line",
            "target_line": "jarvis-chart-target-line",
            "invalidation_line": "jarvis-chart-invalidation-line",
            "vwap_line": "jarvis-chart-vwap-line",
            "similar_marker": "jarvis-chart-similar-marker",
            "blocker_chip": "jarvis-chart-blocker-chip",
        },
        "trade_allowed": False,
        "order_routing_enabled": False,
        "broker_order_created": False,
        "live_trading_blocked": True,
        "can_execute_orders": False,
        "can_export_to_openalgo": False,
        "can_override_no_trade": False,
        "can_override_risk": False,
    }


def _checks(
    bars: list[Any],
    focus: dict[str, Any],
    overlays: dict[str, Any],
    labels: list[dict[str, Any]],
    blockers: list[Any],
    similar: list[Any],
    output: dict[str, Any],
) -> list[dict[str, Any]]:
    entry = focus.get("overlay_entry_zone")
    return [
        _check("CHART-QA-001", "Chart has candles", len(bars) > 0, "block", "A blank chart cannot support decision review."),
        _check("CHART-QA-002", "Entry zone is drawable", isinstance(entry, list) and len(entry) == 2 and all(_is_number(value) for value in entry), "block", "Entry zone must contain two numeric prices."),
        _check("CHART-QA-003", "Stop line is drawable", _is_number(focus.get("overlay_stop_loss")), "block", "Stop-loss line must be numeric."),
        _check("CHART-QA-004", "Target line is drawable", _is_number(focus.get("overlay_target")), "block", "Target line must be numeric."),
        _check("CHART-QA-005", "Invalidation line is drawable", _is_number(focus.get("overlay_invalidation_level")), "block", "Invalidation line must be numeric."),
        _check("CHART-QA-006", "VWAP line is drawable", _is_number(overlays.get("vwap")), "warn", "VWAP overlay should be visible for decision context."),
        _check("CHART-QA-007", "Overlay labels are present", {"Entry", "SL", "Target", "Invalid", "VWAP"}.issubset({str(label.get("label")) for label in labels}), "block", "All core overlay labels must be visible."),
        _check("CHART-QA-008", "Similar markers are available when evidence exists", len(similar) == 0 or focus.get("show_similar_markers") is True, "warn", "Similar-case markers should appear when similar cases exist."),
        _check("CHART-QA-009", "Blocker chips are available", len(blockers) > 0, "warn", "Decision blockers should be visible below the chart."),
        _check("CHART-QA-010", "Chart overlay remains research-only", output.get("trade_allowed") is False and output.get("order_routing_enabled") is False and output.get("live_trading_blocked") is True, "block", "Chart overlays cannot grant trading authority."),
    ]


def _overlay_labels(focus: dict[str, Any], overlays: dict[str, Any]) -> list[dict[str, Any]]:
    entry = focus.get("overlay_entry_zone")
    return [
        {"label": "Entry", "value": entry, "visible": isinstance(entry, list) and len(entry) == 2},
        {"label": "SL", "value": focus.get("overlay_stop_loss"), "visible": _is_number(focus.get("overlay_stop_loss"))},
        {"label": "Target", "value": focus.get("overlay_target"), "visible": _is_number(focus.get("overlay_target"))},
        {"label": "Invalid", "value": focus.get("overlay_invalidation_level"), "visible": _is_number(focus.get("overlay_invalidation_level"))},
        {"label": "VWAP", "value": overlays.get("vwap"), "visible": _is_number(overlays.get("vwap"))},
    ]


def _render_primitives(focus: dict[str, Any], overlays: dict[str, Any], blockers: list[Any], similar: list[Any]) -> dict[str, Any]:
    return {
        "entry_zone_band": {
            "test_id": "jarvis-chart-entry-zone",
            "prices": focus.get("overlay_entry_zone", []),
            "expected": True,
        },
        "horizontal_lines": [
            {"test_id": "jarvis-chart-target-line", "label": "Target", "price": focus.get("overlay_target")},
            {"test_id": "jarvis-chart-stop-line", "label": "SL", "price": focus.get("overlay_stop_loss")},
            {"test_id": "jarvis-chart-invalidation-line", "label": "Invalid", "price": focus.get("overlay_invalidation_level")},
            {"test_id": "jarvis-chart-vwap-line", "label": "VWAP", "price": overlays.get("vwap")},
        ],
        "similar_markers": [
            {"test_id": "jarvis-chart-similar-marker", "source": item.get("source"), "date": item.get("date")}
            for item in similar[:5]
            if isinstance(item, dict)
        ],
        "blocker_chips": [
            {"test_id": "jarvis-chart-blocker-chip", "source": item.get("source"), "severity": item.get("severity")}
            for item in blockers[:4]
            if isinstance(item, dict)
        ],
    }


def _operator_message(qa_state: str, blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if qa_state == "failed":
        return f"Chart overlay QA failed: {blockers[0]['name']}. Keep decision screen in safe review mode."
    if qa_state == "warning":
        return f"Chart overlay QA passed core checks with warning: {warnings[0]['name']}."
    return "Chart overlay QA passed; chart overlays are available for research display only."


def _check(check_id: str, name: str, passed: bool, effect: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "name": name,
        "passed": bool(passed),
        "effect": effect,
        "reason": reason,
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
