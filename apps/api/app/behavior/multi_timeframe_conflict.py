from __future__ import annotations

from ..models import (
    MultiTimeframeConflictExplanation,
    MultiTimeframeConflictGate,
    MultiTimeframeConflictReport,
    MultiTimeframeConflictRequest,
    SevenTimeframeFeatureRuntimeRequest,
    TimeframeStateRecord,
    TimeframeValue,
    now_iso,
)
from .timeframe_feature_builder import (
    ALL_TIMEFRAMES,
    build_closed_aggregate_bars,
    build_seven_timeframe_feature_runtime,
    build_source_rows_for_runtime,
)


CONFLICT_VERSION = "multi-timeframe-conflict.v0.72"
LOWER_TIMEFRAMES = ["1m", "3m", "5m"]
HIGHER_TIMEFRAMES = ["15m", "30m", "1H", "4H", "daily", "weekly"]


def build_multi_timeframe_conflict_report(
    request: MultiTimeframeConflictRequest,
) -> MultiTimeframeConflictReport:
    runtime = build_seven_timeframe_feature_runtime(
        SevenTimeframeFeatureRuntimeRequest(
            symbol=request.symbol,
            seed=request.seed,
            source_bars=request.source_bars,
            decision_time_ns=request.decision_time_ns,
        )
    )
    source_rows = build_source_rows_for_runtime(symbol=request.symbol.upper(), seed=request.seed, bars=request.source_bars)
    aggregates_by_timeframe = {
        timeframe: build_closed_aggregate_bars(source_rows, timeframe, runtime.decision_time_ns)
        for timeframe in ALL_TIMEFRAMES
    }
    primary_direction = _primary_direction(request.primary_timeframe, aggregates_by_timeframe)
    matrix = [_state_record(record, primary_direction, aggregates_by_timeframe.get(record.timeframe, [])) for record in runtime.closed_bar_records]
    explanations = _explanations(matrix, request.primary_timeframe)
    unavailable = [record.timeframe for record in matrix if record.state_direction == "unavailable"]
    decision_safe = [record for record in matrix if record.decision_safe]
    aligned = [record for record in decision_safe if record.aligned_with_primary]
    alignment_score = len(aligned) / len(decision_safe) if decision_safe else 0.0
    block_explanations = [item for item in explanations if item.severity == "block"]
    full_alignment = bool(decision_safe) and alignment_score >= 0.86 and not block_explanations
    developing_blocked = any(record.developing_bar_visible and not record.developing_bar_decision_safe for record in matrix)
    final_state = _final_state(primary_direction, alignment_score, block_explanations, unavailable)
    blocks_trade = final_state in {"avoid", "unavailable"} or bool(block_explanations)
    gates = _gates(matrix, explanations, developing_blocked)
    return MultiTimeframeConflictReport(
        conflict_version=CONFLICT_VERSION,
        generated_at=now_iso(),
        symbol=runtime.symbol,
        primary_timeframe=request.primary_timeframe,
        runtime=runtime,
        seven_timeframe_matrix=matrix,
        conflict_explanations=explanations,
        lower_timeframes=LOWER_TIMEFRAMES,  # type: ignore[arg-type]
        higher_timeframes=HIGHER_TIMEFRAMES,  # type: ignore[arg-type]
        unavailable_timeframes=unavailable,
        full_alignment=full_alignment,
        developing_bars_blocked_from_decision=developing_blocked,
        alignment_score=round(alignment_score, 4),
        final_mtf_state=final_state,  # type: ignore[arg-type]
        blocks_trade=blocks_trade,
        no_trade_reason="NO TRADE: multi-timeframe conflict blocks confidence." if blocks_trade else None,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v1.82 expands the closed-bar matrix to include 30m and 4H while preserving the legacy seven_timeframe_matrix field name.",
            "Developing higher-timeframe bars may be displayed but are never decision-safe.",
            "Multi-timeframe conflict is explicit and reduces action to WAIT/NO_TRADE instead of boosting confidence.",
        ],
    )


def _state_record(record, primary_direction: str, aggregates: list[dict[str, float | int | str]]) -> TimeframeStateRecord:
    developing = record.blocked_incomplete_source_bars > 0
    unavailable = record.closed_bars <= 0
    direction = _direction_from_aggregates(aggregates) if not unavailable else "unavailable"
    role = _role(record.timeframe)
    compression = _compression_state_from_aggregates(aggregates) if not unavailable else "unavailable"
    conflict_tags: list[str] = []
    if unavailable:
        conflict_tags.append("timeframe_data_unavailable")
    if developing:
        conflict_tags.append("developing_bar_blocked")
    if direction != "unavailable" and direction != "range" and direction != primary_direction:
        conflict_tags.append("direction_conflict")
    if compression == "compressed" and role == "higher":
        conflict_tags.append("timeframe_compression_conflict")
    return TimeframeStateRecord(
        timeframe=record.timeframe,
        htf_role=role,  # type: ignore[arg-type]
        closed_bars=record.closed_bars,
        latest_bar_close_time_ns=record.latest_bar_close_time_ns,
        developing_bar_visible=developing,
        developing_bar_decision_safe=False,
        state_direction=direction,  # type: ignore[arg-type]
        state_strength=_strength_from_aggregates(aggregates, record.closed_bars),
        compression_state=compression,  # type: ignore[arg-type]
        aligned_with_primary=direction in {primary_direction, "range"} and not unavailable,
        conflict_tags=conflict_tags,
        decision_safe=not unavailable and not developing,
    )


def _explanations(
    matrix: list[TimeframeStateRecord],
    primary_timeframe: TimeframeValue,
) -> list[MultiTimeframeConflictExplanation]:
    explanations: list[MultiTimeframeConflictExplanation] = []
    unavailable = [record.timeframe for record in matrix if record.state_direction == "unavailable"]
    developing = [record.timeframe for record in matrix if record.developing_bar_visible]
    directional_conflicts = [record for record in matrix if "direction_conflict" in record.conflict_tags]
    compression = [record.timeframe for record in matrix if "timeframe_compression_conflict" in record.conflict_tags]
    if unavailable:
        explanations.append(
            _explanation(
                "timeframe_data_unavailable",
                "block",
                unavailable,
                "One or more required timeframes have no closed bar and cannot confirm the setup.",
                "BLOCK_CONFIDENCE",
            )
        )
    if developing:
        explanations.append(
            _explanation(
                "developing_bar_blocked",
                "watch",
                developing,
                "Developing bars are visible for context but cannot enter historical matching or calibrated probability.",
                "WAIT",
            )
        )
    if directional_conflicts:
        conflict_timeframes = [record.timeframe for record in directional_conflicts]
        has_higher = any(record.htf_role == "higher" for record in directional_conflicts)
        has_intermediate = any(record.htf_role == "intermediate" for record in directional_conflicts)
        higher_or_intermediate_aligned = any(
            record.htf_role in {"intermediate", "higher"}
            and record.aligned_with_primary
            and record.decision_safe
            for record in matrix
        )
        is_lower_pullback = (
            all(record.htf_role == "lower" for record in directional_conflicts)
            and higher_or_intermediate_aligned
        )
        conflict_type = (
            "lower_timeframe_pullback_inside_higher_timeframe_trend"
            if is_lower_pullback
            else "higher_timeframe_reversal_with_lower_timeframe_continuation_lag"
            if has_higher or has_intermediate
            else "lower_timeframe_pullback_inside_higher_timeframe_trend"
        )
        severity = "watch" if conflict_type == "lower_timeframe_pullback_inside_higher_timeframe_trend" else "block"
        explanations.append(
            _explanation(
                conflict_type,
                severity,
                conflict_timeframes,
                f"{primary_timeframe} does not align with {', '.join(conflict_timeframes)} based on closed-bar slope.",
                "WAIT" if severity == "watch" else "NO_TRADE",
            )
        )
    if compression:
        explanations.append(
            _explanation(
                "timeframe_compression_conflict",
                "watch",
                compression,
                "Higher timeframe compression reduces breakout confidence until expansion confirms.",
                "WAIT",
            )
        )
    if not explanations:
        explanations.append(
            _explanation(
                "full_alignment",
                "info",
                [record.timeframe for record in matrix],
                "All decision-safe timeframes are aligned or neutral.",
                "ALLOW_RESEARCH",
            )
        )
    return explanations


def _gates(
    matrix: list[TimeframeStateRecord],
    explanations: list[MultiTimeframeConflictExplanation],
    developing_blocked: bool,
) -> list[MultiTimeframeConflictGate]:
    return [
        _gate("TV-V072-001", "Required timeframe matrix produced", len(matrix) == len(ALL_TIMEFRAMES), f"matrix_timeframes={len(matrix)}", "Build every required timeframe record."),
        _gate("TV-V072-002", "Developing bars are not decision-safe", all(not record.developing_bar_decision_safe for record in matrix if record.developing_bar_visible), f"developing_blocked={developing_blocked}", "Mark developing bars as visual-only."),
        _gate("TV-V072-003", "Conflict explanations published", bool(explanations), f"explanations={len(explanations)}", "Publish explicit conflict explanations."),
        _gate("TV-V072-004", "Unavailable timeframe is explicit", all("timeframe_data_unavailable" in record.conflict_tags for record in matrix if record.state_direction == "unavailable"), "Unavailable records carry conflict tags.", "Tag unavailable timeframe data."),
        _gate("TV-V072-005", "Research-only safety", True, "trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true", "Keep MTF conflict research-only."),
    ]


def _explanation(
    conflict_type: str,
    severity: str,
    timeframes: list[str],
    explanation: str,
    action: str,
) -> MultiTimeframeConflictExplanation:
    return MultiTimeframeConflictExplanation(
        conflict_type=conflict_type,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        timeframes=timeframes,  # type: ignore[arg-type]
        explanation=explanation,
        recommended_action=action,  # type: ignore[arg-type]
    )


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str) -> MultiTimeframeConflictGate:
    return MultiTimeframeConflictGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _primary_direction(timeframe: str, aggregates_by_timeframe: dict[str, list[dict[str, float | int | str]]]) -> str:
    return _direction_from_aggregates(aggregates_by_timeframe.get(timeframe, []))


def _direction_from_aggregates(aggregates: list[dict[str, float | int | str]]) -> str:
    if len(aggregates) < 2:
        return "range"
    first = float(aggregates[0]["close"])
    latest = float(aggregates[-1]["close"])
    if first <= 0:
        return "range"
    slope_pct = (latest - first) / first * 100.0
    if slope_pct > 0.08:
        return "long"
    if slope_pct < -0.08:
        return "short"
    return "range"


def _compression_state_from_aggregates(aggregates: list[dict[str, float | int | str]]) -> str:
    if len(aggregates) < 4:
        return "normal"
    ranges = [max(0.0, float(item["high"]) - float(item["low"])) for item in aggregates[-8:]]
    baseline = sum(ranges[:-1]) / max(len(ranges[:-1]), 1)
    latest = ranges[-1]
    if baseline <= 0:
        return "normal"
    ratio = latest / baseline
    if ratio <= 0.75:
        return "compressed"
    if ratio >= 1.35:
        return "expanding"
    return "normal"


def _role(timeframe: str) -> str:
    if timeframe in {"1m", "3m", "5m"}:
        return "lower"
    if timeframe in {"15m", "30m", "1H"}:
        return "intermediate"
    return "higher"


def _strength_from_aggregates(aggregates: list[dict[str, float | int | str]], closed_bars: int) -> float:
    if closed_bars <= 0:
        return 0.0
    if len(aggregates) < 2:
        return 0.35
    first = float(aggregates[0]["close"])
    latest = float(aggregates[-1]["close"])
    if first <= 0:
        return 0.35
    slope_abs = abs((latest - first) / first * 100.0)
    raw = 0.35 + min(slope_abs / 1.5, 0.55)
    return round(min(0.95, raw), 4)


def _final_state(primary_direction: str, alignment_score: float, blockers: list, unavailable: list) -> str:
    if unavailable:
        return "unavailable"
    if blockers:
        return "avoid"
    if alignment_score < 0.58:
        return "mixed"
    return "supports_long" if primary_direction == "long" else "supports_short" if primary_direction == "short" else "mixed"
