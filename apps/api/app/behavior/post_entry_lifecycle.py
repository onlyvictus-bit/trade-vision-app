from __future__ import annotations

import math
from statistics import mean

from ..models import CandleBar, PostEntryLifecycleGate, PostEntryLifecycleReport, PostEntryLifecycleRequest


POST_ENTRY_LIFECYCLE_VERSION = "post-entry-lifecycle-manager.v1.74"
EPSILON = 1e-9


def build_post_entry_lifecycle_report(request: PostEntryLifecycleRequest) -> PostEntryLifecycleReport:
    bars = sorted(request.series.bars, key=lambda bar: (bar.timestamp_ns, bar.sequence_number))
    entry_index = _entry_index(bars, request.entry_sequence_number)
    entry_bar = bars[entry_index] if bars else None
    post_bars = bars[entry_index + 1 :] if bars else []
    latest = bars[-1] if bars else None
    direction = request.direction if request.direction in {"long", "short"} else "long"
    entry_price = request.entry_price or (entry_bar.close if entry_bar else _latest_close(bars))
    atr = request.atr or _atr(bars, 14) or max(entry_price * 0.005, EPSILON)
    initial_stop = request.initial_stop_loss or _default_stop(entry_price, atr, direction)
    risk = _risk(entry_price, initial_stop, direction)
    target_1 = request.target_1 or _target(entry_price, risk, direction, 1.0)
    target_2 = request.target_2 or _target(entry_price, risk, direction, 2.0)
    mfe_r = _mfe_r(post_bars, entry_price, risk, direction)
    mae_r = _mae_r(post_bars, entry_price, risk, direction)
    current_r = _current_r(latest, entry_price, risk, direction)
    one_r_reached = mfe_r >= 1.0
    target_1_reached = _target_hit(post_bars, target_1, direction)
    target_2_reached = _target_hit(post_bars, target_2, direction)
    stop_after_entry = _stop_hit(post_bars, initial_stop, direction)
    thesis_weakening, downgrade_reason = _thesis_weakening(request, latest, direction)
    current_stop = _current_stop(
        request=request,
        latest=latest,
        entry_price=entry_price,
        initial_stop=initial_stop,
        atr=atr,
        direction=direction,
        one_r_reached=one_r_reached,
        thesis_weakening=thesis_weakening,
    )
    invalidated = stop_after_entry or _latest_stop_hit(latest, current_stop, direction)
    trade_state = _trade_state(
        post_entry_count=len(post_bars),
        invalidated=invalidated,
        target_2_reached=target_2_reached,
        thesis_weakening=thesis_weakening,
        target_1_reached=target_1_reached,
        one_r_reached=one_r_reached,
    )
    thesis_status = _thesis_status(trade_state)
    add_on_allowed = _add_on_allowed(request, thesis_weakening, invalidated)
    confidence = _confidence_adjustment(request, trade_state, thesis_weakening, invalidated)
    trailing_stop = _trailing_stop(post_bars, current_stop, atr, direction, request.trailing_atr_multiple) if one_r_reached else None
    gates = _gates(request, post_bars, one_r_reached, target_1_reached, thesis_weakening, invalidated, add_on_allowed)
    return PostEntryLifecycleReport(
        lifecycle_version=POST_ENTRY_LIFECYCLE_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        direction=direction,  # type: ignore[arg-type]
        closed_candle_only=True,
        source_bar_count=len(bars),
        post_entry_bar_count=len(post_bars),
        entry_sequence_number=entry_bar.sequence_number if entry_bar else 0,
        entry_price=round(entry_price, 6),
        initial_stop_loss=round(initial_stop, 6),
        current_stop_loss=round(current_stop, 6),
        target_1=round(target_1, 6),
        target_2=round(target_2, 6),
        mfe_r=round(mfe_r, 6),
        mae_r=round(mae_r, 6),
        r_multiple_current=round(current_r, 6),
        trade_state=trade_state,  # type: ignore[arg-type]
        current_thesis_status=thesis_status,  # type: ignore[arg-type]
        exit_plan=_exit_plan(trade_state, direction, current_stop, target_2),
        partial_exit_plan=_partial_exit_plan(target_1_reached, request.partial_exit_fraction),
        trailing_stop=None if trailing_stop is None else round(trailing_stop, 6),
        invalidation_trigger=_invalidation_trigger(request, direction, current_stop),
        thesis_downgrade_reason=downgrade_reason,
        add_on_allowed=add_on_allowed,
        confidence_adjustment=confidence,  # type: ignore[arg-type]
        simulation_actions=_simulation_actions(trade_state, one_r_reached, target_1_reached, thesis_weakening, current_stop, trailing_stop),
        no_future_leakage=True,
        simulation_only=True,
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        reasons=_reasons(trade_state, thesis_status, one_r_reached, target_1_reached, add_on_allowed),
        failure_questions=_failure_questions(request, trade_state, thesis_weakening),
        gates=gates,
    )


def _entry_index(bars: list[CandleBar], sequence_number: int | None) -> int:
    if not bars:
        return 0
    if sequence_number is not None:
        for index, bar in enumerate(bars):
            if bar.sequence_number == sequence_number:
                return min(index, len(bars) - 1)
    return max(0, len(bars) - 6)


def _default_stop(entry: float, atr: float, direction: str) -> float:
    return entry - atr if direction == "long" else entry + atr


def _target(entry: float, risk: float, direction: str, multiple: float) -> float:
    return entry + risk * multiple if direction == "long" else entry - risk * multiple


def _risk(entry: float, stop: float, direction: str) -> float:
    value = entry - stop if direction == "long" else stop - entry
    return max(value, entry * 0.001, EPSILON)


def _mfe_r(bars: list[CandleBar], entry: float, risk: float, direction: str) -> float:
    if not bars:
        return 0.0
    best = max(bar.high for bar in bars) if direction == "long" else min(bar.low for bar in bars)
    return max(0.0, (best - entry) / risk if direction == "long" else (entry - best) / risk)


def _mae_r(bars: list[CandleBar], entry: float, risk: float, direction: str) -> float:
    if not bars:
        return 0.0
    worst = min(bar.low for bar in bars) if direction == "long" else max(bar.high for bar in bars)
    return max(0.0, (entry - worst) / risk if direction == "long" else (worst - entry) / risk)


def _current_r(latest: CandleBar | None, entry: float, risk: float, direction: str) -> float:
    if latest is None:
        return 0.0
    return (latest.close - entry) / risk if direction == "long" else (entry - latest.close) / risk


def _target_hit(bars: list[CandleBar], target: float, direction: str) -> bool:
    if direction == "long":
        return any(bar.high >= target for bar in bars)
    return any(bar.low <= target for bar in bars)


def _stop_hit(bars: list[CandleBar], stop: float, direction: str) -> bool:
    if direction == "long":
        return any(bar.low <= stop for bar in bars)
    return any(bar.high >= stop for bar in bars)


def _latest_stop_hit(latest: CandleBar | None, stop: float, direction: str) -> bool:
    if latest is None:
        return False
    return latest.low <= stop if direction == "long" else latest.high >= stop


def _thesis_weakening(request: PostEntryLifecycleRequest, latest: CandleBar | None, direction: str) -> tuple[bool, str]:
    if latest is None:
        return False, "no closed post-entry candle available"
    vwap = request.current_vwap or request.vwap
    if vwap is not None:
        if direction == "long" and latest.close < vwap:
            return True, "VWAP lost after long entry"
        if direction == "short" and latest.close > vwap:
            return True, "VWAP reclaimed against short entry"
    if direction == "long" and request.structure_signal in {"utad", "fakeout", "trap"}:
        return True, f"{request.structure_signal.upper()} after long entry"
    if direction == "short" and request.structure_signal in {"spring", "fakeout", "trap"}:
        return True, f"{request.structure_signal.upper()} after short entry"
    if direction == "long" and request.divergence_signal == "bearish":
        return True, "bearish divergence after long entry"
    if direction == "short" and request.divergence_signal == "bullish":
        return True, "bullish divergence after short entry"
    if request.regime_state == "flipped":
        return True, "market regime flipped against entry thesis"
    if request.regime_state == "weakening":
        return True, "market regime is weakening"
    return False, "thesis intact"


def _current_stop(
    *,
    request: PostEntryLifecycleRequest,
    latest: CandleBar | None,
    entry_price: float,
    initial_stop: float,
    atr: float,
    direction: str,
    one_r_reached: bool,
    thesis_weakening: bool,
) -> float:
    stop = initial_stop
    if one_r_reached:
        buffer = atr * request.breakeven_buffer_atr
        stop = max(stop, entry_price + buffer) if direction == "long" else min(stop, entry_price - buffer)
    if thesis_weakening and latest is not None:
        tighten = latest.close - atr * 0.50 if direction == "long" else latest.close + atr * 0.50
        stop = max(stop, tighten) if direction == "long" else min(stop, tighten)
    return stop


def _trailing_stop(bars: list[CandleBar], current_stop: float, atr: float, direction: str, multiple: float) -> float | None:
    if not bars:
        return None
    recent = bars[-5:]
    if direction == "long":
        swing = min(bar.low for bar in recent)
        atr_stop = bars[-1].close - atr * multiple
        return max(current_stop, min(swing, atr_stop))
    swing = max(bar.high for bar in recent)
    atr_stop = bars[-1].close + atr * multiple
    return min(current_stop, max(swing, atr_stop))


def _trade_state(
    *,
    post_entry_count: int,
    invalidated: bool,
    target_2_reached: bool,
    thesis_weakening: bool,
    target_1_reached: bool,
    one_r_reached: bool,
) -> str:
    if post_entry_count <= 0:
        return "ENTRY_READY"
    if invalidated:
        return "INVALIDATED"
    if target_2_reached:
        return "EXITED"
    if thesis_weakening:
        return "THESIS_WEAKENING"
    if target_1_reached:
        return "PARTIAL_EXIT"
    if one_r_reached:
        return "TRAILING"
    return "ENTERED"


def _thesis_status(trade_state: str) -> str:
    if trade_state == "ENTRY_READY":
        return "not_entered"
    if trade_state == "THESIS_WEAKENING":
        return "weakening"
    if trade_state == "INVALIDATED":
        return "invalidated"
    if trade_state == "EXITED":
        return "exited"
    return "intact"


def _add_on_allowed(request: PostEntryLifecycleRequest, thesis_weakening: bool, invalidated: bool) -> bool:
    return bool(request.add_on_requested and not thesis_weakening and not invalidated and request.regime_state in {"aligned", "unknown"})


def _confidence_adjustment(request: PostEntryLifecycleRequest, trade_state: str, thesis_weakening: bool, invalidated: bool) -> str:
    if invalidated or trade_state == "EXITED":
        return "exit_required"
    if request.regime_state == "flipped" or (request.add_on_requested and thesis_weakening):
        return "block_add_on"
    if thesis_weakening:
        return "reduce"
    return "maintain"


def _exit_plan(trade_state: str, direction: str, stop: float, target_2: float) -> str:
    if trade_state == "INVALIDATED":
        return "Simulation state invalidated; no add-on; exit thesis in paper review."
    if trade_state == "EXITED":
        return "Simulation target-2 reached; mark lifecycle exited."
    return f"Maintain {direction} thesis only while closed candles respect stop {stop:.4f}; final target {target_2:.4f}."


def _partial_exit_plan(target_1_reached: bool, fraction: float) -> str:
    if target_1_reached:
        return f"Simulation-only partial exit of {fraction:.0%} at target-1; move remainder to trailing review."
    return "No partial exit yet; wait for target-1 or thesis downgrade."


def _invalidation_trigger(request: PostEntryLifecycleRequest, direction: str, stop: float) -> str:
    vwap = request.current_vwap or request.vwap
    vwap_text = f" or close below VWAP {vwap:.4f}" if direction == "long" and vwap else (f" or close above VWAP {vwap:.4f}" if vwap else "")
    return f"{direction} thesis invalidates on closed candle through stop {stop:.4f}{vwap_text}."


def _simulation_actions(trade_state: str, one_r_reached: bool, target_1_reached: bool, thesis_weakening: bool, stop: float, trailing: float | None) -> list[str]:
    actions: list[str] = []
    if one_r_reached:
        actions.append(f"move_stop_to_breakeven_or_better:{stop:.4f}")
    if target_1_reached:
        actions.append("record_simulated_partial_exit")
    if trailing is not None:
        actions.append(f"set_simulated_trailing_stop:{trailing:.4f}")
    if thesis_weakening:
        actions.append("tighten_stop_and_block_add_on")
    if trade_state in {"INVALIDATED", "EXITED"}:
        actions.append(f"mark_{trade_state.lower()}")
    return actions or ["monitor_closed_candle_thesis"]


def _gates(
    request: PostEntryLifecycleRequest,
    post_bars: list[CandleBar],
    one_r_reached: bool,
    target_1_reached: bool,
    thesis_weakening: bool,
    invalidated: bool,
    add_on_allowed: bool,
) -> list[PostEntryLifecycleGate]:
    return [
        _gate("LIFE-001", "After 1R reached stop moves to breakeven or better", one_r_reached, "info" if one_r_reached else "warn", f"one_r_reached={one_r_reached}."),
        _gate("LIFE-002", "Partial exit is simulation only", target_1_reached, "info" if target_1_reached else "warn", f"target_1_reached={target_1_reached}; trade_allowed=false."),
        _gate("LIFE-003", "VWAP loss marks thesis weakening", not thesis_weakening or (request.current_vwap is not None or request.vwap is not None), "warn" if thesis_weakening else "info", f"thesis_weakening={thesis_weakening}."),
        _gate("LIFE-004", "Trap signal tightens lifecycle risk", request.structure_signal not in {"utad", "spring", "fakeout", "trap"} or thesis_weakening, "warn" if request.structure_signal in {"utad", "spring", "fakeout", "trap"} else "info", f"structure_signal={request.structure_signal}."),
        _gate("LIFE-005", "Regime flip blocks add-on", request.regime_state != "flipped" and add_on_allowed or request.regime_state != "flipped", "block" if request.regime_state == "flipped" else "info", f"regime_state={request.regime_state}; add_on_allowed={add_on_allowed}."),
        _gate("LIFE-006", "Post-entry logic remains simulation only", True, "info", "simulation_only=true; order_routing_enabled=false."),
        _gate("V174-SAFE-001", "Closed post-entry bars exist", len(post_bars) >= request.minimum_post_entry_bars, "block" if len(post_bars) < request.minimum_post_entry_bars else "info", f"post_entry_bar_count={len(post_bars)}."),
        _gate("V174-SAFE-002", "Invalidated thesis cannot add on", not invalidated and add_on_allowed or not invalidated, "block" if invalidated else "info", f"invalidated={invalidated}; add_on_allowed={add_on_allowed}."),
    ]


def _reasons(trade_state: str, thesis_status: str, one_r_reached: bool, target_1_reached: bool, add_on_allowed: bool) -> list[str]:
    return [
        f"Post-entry state is {trade_state}; thesis status is {thesis_status}.",
        f"One-R reached={one_r_reached}; target-1 reached={target_1_reached}; add-on allowed={add_on_allowed}.",
        "Lifecycle actions are simulation-only guidance and cannot modify broker or OpenAlgo state.",
    ]


def _failure_questions(request: PostEntryLifecycleRequest, trade_state: str, thesis_weakening: bool) -> list[str]:
    questions = [
        "Has a closed candle proven the thesis wrong after entry?",
        "Should the stop be tightened, moved to breakeven, or left unchanged?",
        "Should partial profit be simulated or should the remaining thesis trail?",
    ]
    if thesis_weakening:
        questions.append("Which evidence weakened the thesis: VWAP loss, trap signal, divergence, or regime flip?")
    if request.add_on_requested and trade_state != "ENTERED":
        questions.append("Is add-on blocked because the lifecycle is no longer a clean entered state?")
    return questions


def _gate(gate_id: str, name: str, passed: bool, severity: str, evidence: str, remediation: str | None = None) -> PostEntryLifecycleGate:
    return PostEntryLifecycleGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation=remediation,
    )


def _latest_close(bars: list[CandleBar]) -> float:
    return bars[-1].close if bars else 1.0


def _atr(bars: list[CandleBar], period: int) -> float:
    if not bars:
        return 0.0
    ranges: list[float] = []
    previous_close: float | None = None
    for bar in bars[-period:]:
        if previous_close is None:
            ranges.append(max(bar.high - bar.low, 0.0))
        else:
            ranges.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)))
        previous_close = bar.close
    clean = [item for item in ranges if math.isfinite(item)]
    return mean(clean) if clean else 0.0
