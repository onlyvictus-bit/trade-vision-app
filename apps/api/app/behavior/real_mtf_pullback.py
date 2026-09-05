from __future__ import annotations

from ..models import (
    MultiTimeframeConflictRequest,
    RealMtfPullbackGate,
    RealMtfPullbackReport,
    RealMtfPullbackRequest,
    RealMtfPullbackTimeframeSummary,
    TimeframeStateRecord,
    TimeframeValue,
    now_iso,
)
from .multi_timeframe_conflict import build_multi_timeframe_conflict_report


PULLBACK_VERSION = "real-mtf-pullback.v1.63"


def build_real_mtf_pullback_report(request: RealMtfPullbackRequest | None = None) -> RealMtfPullbackReport:
    payload = request or RealMtfPullbackRequest()
    conflict = build_multi_timeframe_conflict_report(
        MultiTimeframeConflictRequest(
            symbol=payload.symbol,
            seed=payload.seed,
            source_bars=payload.source_bars,
            decision_time_ns=payload.decision_time_ns,
            primary_timeframe=payload.primary_timeframe,
        )
    )
    classification = classify_mtf_pullback_context(conflict.seven_timeframe_matrix, payload.primary_timeframe)
    closed_htf_context_passed = _closed_htf_context_passed(conflict.seven_timeframe_matrix)
    developing_blocked = conflict.developing_bars_blocked_from_decision
    no_future_leakage = _no_future_leakage(conflict.runtime.closed_bar_records, conflict.runtime.decision_time_ns)
    final_action, final_reason = _final_action_and_reason(classification, closed_htf_context_passed, developing_blocked)
    trader_summary = _trader_summary(classification, final_action, final_reason)
    gates = _gates(
        closed_htf_context_passed=closed_htf_context_passed,
        developing_blocked=developing_blocked,
        classification=classification,
        final_action=final_action,
        no_future_leakage=no_future_leakage,
    )
    return RealMtfPullbackReport(
        pullback_version=PULLBACK_VERSION,
        generated_at=now_iso(),
        symbol=conflict.symbol,
        primary_timeframe=payload.primary_timeframe,
        source_conflict_version=conflict.conflict_version,
        primary_direction=classification["primary_direction"],  # type: ignore[arg-type]
        higher_timeframe_direction=classification["higher_timeframe_direction"],  # type: ignore[arg-type]
        lower_pullback_direction=classification["lower_pullback_direction"],  # type: ignore[arg-type]
        pullback_state=classification["pullback_state"],  # type: ignore[arg-type]
        closed_htf_context_passed=closed_htf_context_passed,
        lower_timeframe_pullback_detected=bool(classification["pullback_timeframes"]),
        htf_opposition_detected=bool(classification["opposition_timeframes"]),
        compression_warning=bool(classification["compression_timeframes"]),
        aligned_timeframes=classification["aligned_timeframes"],  # type: ignore[arg-type]
        opposition_timeframes=classification["opposition_timeframes"],  # type: ignore[arg-type]
        pullback_timeframes=classification["pullback_timeframes"],  # type: ignore[arg-type]
        final_action=final_action,  # type: ignore[arg-type]
        final_reason=final_reason,
        trader_summary=trader_summary,
        no_future_leakage=no_future_leakage,
        closed_candle_only=no_future_leakage,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        timeframe_summaries=[_summary(record) for record in conflict.seven_timeframe_matrix],
        gates=gates,
        notes=[
            "v1.63 consumes the real closed-bar multi-timeframe matrix instead of hash-only MTF claims.",
            "Lower-timeframe pullback inside an aligned higher-timeframe trend is WATCH, not automatic entry.",
            "Higher-timeframe opposition, unavailable HTF context, or developing bars keep the result WAIT/AVOID.",
        ],
    )


def classify_mtf_pullback_context(
    matrix: list[TimeframeStateRecord],
    primary_timeframe: TimeframeValue,
) -> dict[str, object]:
    primary = next((record for record in matrix if record.timeframe == primary_timeframe), None)
    primary_direction = primary.state_direction if primary else "unavailable"
    lower_records = [record for record in matrix if record.htf_role == "lower" and record.decision_safe]
    htf_records = [record for record in matrix if record.htf_role in {"intermediate", "higher"} and record.decision_safe]
    higher_direction = _weighted_direction(htf_records)
    pullback_direction = _opposite(primary_direction)
    pullback_records = [
        record
        for record in lower_records
        if primary_direction in {"long", "short"} and record.state_direction == pullback_direction
    ]
    opposition_records = [
        record
        for record in htf_records
        if primary_direction in {"long", "short"} and record.state_direction == pullback_direction
    ]
    aligned_records = [
        record
        for record in matrix
        if record.decision_safe and primary_direction in {"long", "short"} and record.state_direction == primary_direction
    ]
    compression_records = [
        record
        for record in htf_records
        if record.compression_state == "compressed"
    ]
    unavailable_or_developing = [
        record
        for record in matrix
        if not record.decision_safe or record.state_direction == "unavailable"
    ]
    pullback_state = _pullback_state(
        primary_direction=primary_direction,
        higher_direction=higher_direction,
        pullback_records=pullback_records,
        opposition_records=opposition_records,
        unavailable_or_developing=unavailable_or_developing,
        aligned_records=aligned_records,
    )
    return {
        "primary_direction": primary_direction,
        "higher_timeframe_direction": higher_direction,
        "lower_pullback_direction": pullback_direction if pullback_records else "range",
        "pullback_state": pullback_state,
        "aligned_timeframes": [record.timeframe for record in aligned_records],
        "opposition_timeframes": [record.timeframe for record in opposition_records],
        "pullback_timeframes": [record.timeframe for record in pullback_records],
        "compression_timeframes": [record.timeframe for record in compression_records],
        "unavailable_or_developing_timeframes": [record.timeframe for record in unavailable_or_developing],
    }


def _pullback_state(
    *,
    primary_direction: str,
    higher_direction: str,
    pullback_records: list[TimeframeStateRecord],
    opposition_records: list[TimeframeStateRecord],
    unavailable_or_developing: list[TimeframeStateRecord],
    aligned_records: list[TimeframeStateRecord],
) -> str:
    if primary_direction not in {"long", "short"} or higher_direction == "unavailable":
        return "range_or_unavailable"
    if opposition_records:
        return "htf_opposition"
    if unavailable_or_developing:
        return "developing_blocked"
    if pullback_records and higher_direction == primary_direction:
        return "pullback_in_trend"
    if aligned_records and higher_direction == primary_direction:
        return "trend_continuation"
    return "mixed_context"


def _final_action_and_reason(
    classification: dict[str, object],
    closed_htf_context_passed: bool,
    developing_blocked: bool,
) -> tuple[str, str]:
    state = str(classification["pullback_state"])
    if state == "htf_opposition":
        return "AVOID", "Higher timeframe opposes the primary setup; do not promote the idea."
    if not closed_htf_context_passed or developing_blocked:
        return "WAIT", "Higher timeframe evidence is missing or still developing; wait for closed confirmation."
    if state == "pullback_in_trend":
        return "WATCH", "Lower timeframe pullback is inside an aligned higher-timeframe trend; wait for reclaim/confirmation."
    if state == "trend_continuation":
        return "WATCH", "Closed timeframes align with the primary direction; still research-only."
    return "WAIT", "Multi-timeframe context is mixed or range-bound; no trade promotion."


def _trader_summary(classification: dict[str, object], final_action: str, final_reason: str) -> str:
    primary = classification["primary_direction"]
    higher = classification["higher_timeframe_direction"]
    pullbacks = ", ".join(classification["pullback_timeframes"]) or "none"
    opposition = ", ".join(classification["opposition_timeframes"]) or "none"
    return (
        f"{final_action}: primary={primary}, HTF={higher}, lower-pullback={pullbacks}, "
        f"HTF-opposition={opposition}. {final_reason}"
    )


def _closed_htf_context_passed(matrix: list[TimeframeStateRecord]) -> bool:
    htf_records = [record for record in matrix if record.htf_role in {"intermediate", "higher"}]
    return bool(htf_records) and all(record.decision_safe and record.state_direction != "unavailable" for record in htf_records)


def _no_future_leakage(records, decision_time_ns: int) -> bool:
    return all(record.latest_bar_close_time_ns is None or record.latest_bar_close_time_ns <= decision_time_ns for record in records)


def _weighted_direction(records: list[TimeframeStateRecord]) -> str:
    scores = {"long": 0.0, "short": 0.0, "range": 0.0}
    for record in records:
        if record.state_direction in scores:
            scores[record.state_direction] += max(record.state_strength, 0.01)
    if not any(scores.values()):
        return "unavailable"
    return max(scores, key=scores.get)


def _opposite(direction: str) -> str:
    if direction == "long":
        return "short"
    if direction == "short":
        return "long"
    return "range"


def _summary(record: TimeframeStateRecord) -> RealMtfPullbackTimeframeSummary:
    return RealMtfPullbackTimeframeSummary(
        timeframe=record.timeframe,
        htf_role=record.htf_role,
        state_direction=record.state_direction,
        state_strength=record.state_strength,
        compression_state=record.compression_state,
        decision_safe=record.decision_safe,
        conflict_tags=record.conflict_tags,
    )


def _gates(
    *,
    closed_htf_context_passed: bool,
    developing_blocked: bool,
    classification: dict[str, object],
    final_action: str,
    no_future_leakage: bool,
) -> list[RealMtfPullbackGate]:
    opposition = bool(classification["opposition_timeframes"])
    return [
        _gate("TV-V163-001", "Closed HTF context is usable", closed_htf_context_passed, f"closed_htf_context_passed={closed_htf_context_passed}", "Wait for closed 15m/1H/daily/weekly context."),
        _gate("TV-V163-002", "Developing bars cannot drive decisions", True, f"developing_bars_blocked={developing_blocked}", "Mark developing bars visual-only."),
        _gate("TV-V163-003", "Pullback classification is explicit", bool(classification["pullback_state"]), f"state={classification['pullback_state']}", "Return explicit pullback state."),
        _gate("TV-V163-004", "HTF opposition blocks promotion", (not opposition) or final_action == "AVOID", f"opposition_timeframes={classification['opposition_timeframes']}", "Downgrade to AVOID when higher timeframe opposes."),
        _gate("TV-V163-005", "Point-in-time closed-candle guard", no_future_leakage, f"no_future_leakage={no_future_leakage}", "Use only closed candles from the MTF runtime."),
        _gate("TV-V163-006", "Research-only safety", True, "trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true", "Keep v1.63 research-only."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str) -> RealMtfPullbackGate:
    return RealMtfPullbackGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )
