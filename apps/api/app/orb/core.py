from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from statistics import mean

from ..behavior.point_in_time_guard import timeframe_duration_ns
from ..models import (
    CandleBar,
    OrbBuildRequest,
    OrbBuildResult,
    OrbFeatureRecord,
    OrbOpeningRange,
    OrbSignalCandidate,
)


ORB_VERSION = "orb-core.v1.89"
EPSILON = 1e-9


def build_orb_candidate(request: OrbBuildRequest) -> OrbBuildResult:
    duration_ns = timeframe_duration_ns(request.series.timeframe)
    warnings: list[str] = []
    closed = _closed_unique_bars(request, duration_ns, warnings)
    session_bars = _latest_session_bars(request, closed)
    opening_range = _opening_range(request, session_bars, duration_ns, warnings)
    post_range = (
        [
            bar
            for bar in session_bars
            if opening_range and bar.timestamp_ns >= opening_range.lock_time_ns
        ]
        if opening_range
        else []
    )
    signal = _signal_candidate(request, opening_range, post_range, duration_ns)
    features = _features(request, opening_range, post_range, session_bars)
    gates = _gates(request, closed, session_bars, opening_range, signal)
    result_payload = {
        "orb_version": ORB_VERSION,
        "symbol": request.series.symbol.upper(),
        "timeframe": request.series.timeframe,
        "decision_time_ns": request.decision_time_ns,
        "source_snapshot_hash": request.source_snapshot_hash,
        "session": request.session.model_dump(mode="json"),
        "config": request.config.model_dump(mode="json"),
        "opening_range": (
            opening_range.model_dump(mode="json") if opening_range else None
        ),
        "signal": signal.model_dump(mode="json"),
        "features": features.model_dump(mode="json"),
        "warnings": warnings,
    }
    return OrbBuildResult(
        **result_payload,
        range_locked=bool(opening_range and opening_range.locked),
        setup_available=signal.signal_type != "NO_SETUP",
        no_future_leakage=all(
            bar.timestamp_ns + duration_ns <= request.decision_time_ns
            for bar in closed
        ),
        deterministic_hash=_hash(result_payload),
        gates=gates,
    )


def _closed_unique_bars(
    request: OrbBuildRequest,
    duration_ns: int,
    warnings: list[str],
) -> list[CandleBar]:
    ordered = sorted(
        request.series.bars,
        key=lambda bar: (bar.timestamp_ns, bar.sequence_number),
    )
    unique: dict[int, CandleBar] = {}
    for bar in ordered:
        if bar.symbol.upper() != request.series.symbol.upper():
            warnings.append(
                f"Excluded symbol-mismatched bar at {bar.timestamp_ns}."
            )
            continue
        if bar.timeframe != request.series.timeframe:
            warnings.append(
                f"Excluded timeframe-mismatched bar at {bar.timestamp_ns}."
            )
            continue
        if bar.timestamp_ns + duration_ns > request.decision_time_ns:
            warnings.append(
                f"Excluded incomplete/future bar at {bar.timestamp_ns}."
            )
            continue
        if bar.timestamp_ns in unique:
            warnings.append(f"Excluded duplicate timestamp {bar.timestamp_ns}.")
            continue
        unique[bar.timestamp_ns] = bar
    return list(unique.values())


def _latest_session_bars(
    request: OrbBuildRequest,
    bars: list[CandleBar],
) -> list[CandleBar]:
    in_session = [
        bar
        for bar in bars
        if _in_session(
            _local_datetime(bar.timestamp_ns, request.session.timezone_offset_minutes),
            request.session.open_time,
            request.session.close_time,
        )
    ]
    if not in_session:
        return []
    latest_date = _local_datetime(
        in_session[-1].timestamp_ns,
        request.session.timezone_offset_minutes,
    ).date()
    return [
        bar
        for bar in in_session
        if _local_datetime(
            bar.timestamp_ns,
            request.session.timezone_offset_minutes,
        ).date()
        == latest_date
    ]


def _opening_range(
    request: OrbBuildRequest,
    session_bars: list[CandleBar],
    duration_ns: int,
    warnings: list[str],
) -> OrbOpeningRange | None:
    if not session_bars:
        warnings.append("No fully closed bars exist inside the configured session.")
        return None
    if request.config.range_mode == "bar_count":
        if len(session_bars) < request.config.orb_bar_count:
            warnings.append(
                f"Opening range needs {request.config.orb_bar_count} closed bars; "
                f"only {len(session_bars)} are available."
            )
            return None
        range_bars = session_bars[: request.config.orb_bar_count]
        lock_time_ns = range_bars[-1].timestamp_ns + duration_ns
        start_local = _local_hhmm(
            range_bars[0].timestamp_ns,
            request.session.timezone_offset_minutes,
        )
        end_local = _local_hhmm(
            lock_time_ns,
            request.session.timezone_offset_minutes,
        )
    else:
        range_bars = [
            bar
            for bar in session_bars
            if _clock_in_window(
                _local_datetime(
                    bar.timestamp_ns,
                    request.session.timezone_offset_minutes,
                ),
                request.config.range_start,
                request.config.range_end,
            )
            and _local_hhmm(
                bar.timestamp_ns + duration_ns,
                request.session.timezone_offset_minutes,
            )
            <= request.config.range_end
        ]
        if not range_bars:
            warnings.append("No fully closed bars exist inside the OR clock window.")
            return None
        local_date = _local_datetime(
            range_bars[0].timestamp_ns,
            request.session.timezone_offset_minutes,
        ).date()
        lock_time_ns = _local_clock_to_utc_ns(
            local_date,
            request.config.range_end,
            request.session.timezone_offset_minutes,
        )
        if request.decision_time_ns < lock_time_ns:
            warnings.append("Opening-range clock window is not locked yet.")
            return None
        start_local = request.config.range_start
        end_local = request.config.range_end

    high = max(bar.high for bar in range_bars)
    low = min(bar.low for bar in range_bars)
    width = max(high - low, 0.0)
    midpoint = max((high + low) / 2.0, EPSILON)
    volume = sum(float(bar.volume or 0.0) for bar in range_bars)
    vwap = _vwap(range_bars)
    return OrbOpeningRange(
        local_session_date=str(
            _local_datetime(
                range_bars[0].timestamp_ns,
                request.session.timezone_offset_minutes,
            ).date()
        ),
        range_mode=request.config.range_mode,
        range_start_local=start_local,
        range_end_local=end_local,
        opening_range_high=round(high, 8),
        opening_range_low=round(low, 8),
        opening_range_width=round(width, 8),
        opening_range_width_pct=round(width / midpoint * 100.0, 8),
        range_volume=round(volume, 4),
        range_vwap=None if vwap is None else round(vwap, 8),
        range_bar_count=len(range_bars),
        first_bar_timestamp_ns=range_bars[0].timestamp_ns,
        last_bar_timestamp_ns=range_bars[-1].timestamp_ns,
        lock_time_ns=lock_time_ns,
        locked=request.decision_time_ns >= lock_time_ns,
    )


def _signal_candidate(
    request: OrbBuildRequest,
    opening_range: OrbOpeningRange | None,
    bars: list[CandleBar],
    duration_ns: int,
) -> OrbSignalCandidate:
    if opening_range is None or not opening_range.locked:
        return _no_setup("Opening range is not locked.")
    eligible = [
        bar
        for bar in bars
        if _local_hhmm(
            bar.timestamp_ns,
            request.session.timezone_offset_minutes,
        )
        <= request.config.entry_cutoff
    ]
    if not eligible:
        return _no_setup("No fully closed post-range bar exists before the entry cutoff.")

    high_trigger = opening_range.opening_range_high * (
        1.0 + request.config.breakout_buffer_pct / 100.0
    )
    low_trigger = opening_range.opening_range_low * (
        1.0 - request.config.breakout_buffer_pct / 100.0
    )
    range_volume_mean = opening_range.range_volume / max(
        opening_range.range_bar_count, 1
    )
    for bar in eligible:
        volume_confirmed = (
            not request.config.require_volume_confirmation
            or float(bar.volume or 0.0) >= range_volume_mean
        )
        vwap = opening_range.range_vwap
        long_vwap = (
            not request.config.require_vwap_confirmation
            or vwap is not None
            and bar.close >= vwap
        )
        short_vwap = (
            not request.config.require_vwap_confirmation
            or vwap is not None
            and bar.close <= vwap
        )
        close_above = bar.close > high_trigger
        close_below = bar.close < low_trigger
        high_breach = bar.high > high_trigger
        low_breach = bar.low < low_trigger

        if request.config.strategy_family in {"orb_breakout", "hybrid_orb"}:
            if (
                request.config.direction in {"long", "both"}
                and (close_above if request.config.require_close_confirmation else high_breach)
                and volume_confirmed
                and long_vwap
            ):
                return _trade_signal(
                    "BREAKOUT_LONG",
                    "LONG",
                    bar,
                    duration_ns,
                    high_trigger,
                    opening_range.opening_range_low,
                    request.config.reward_risk_ratio,
                    volume_confirmed,
                    long_vwap,
                    close_above,
                    "Closed breakout above the locked opening-range high.",
                )
            if (
                request.config.direction in {"short", "both"}
                and (close_below if request.config.require_close_confirmation else low_breach)
                and volume_confirmed
                and short_vwap
            ):
                return _trade_signal(
                    "BREAKDOWN_SHORT",
                    "SHORT",
                    bar,
                    duration_ns,
                    low_trigger,
                    opening_range.opening_range_high,
                    request.config.reward_risk_ratio,
                    volume_confirmed,
                    short_vwap,
                    close_below,
                    "Closed breakdown below the locked opening-range low.",
                )

        if request.config.strategy_family in {"orr_reversal", "hybrid_orb"}:
            if (
                request.config.direction in {"short", "both"}
                and high_breach
                and bar.close < opening_range.opening_range_high
                and volume_confirmed
            ):
                return _trade_signal(
                    "REVERSAL_SHORT",
                    "SHORT",
                    bar,
                    duration_ns,
                    bar.close,
                    bar.high,
                    request.config.reward_risk_ratio,
                    volume_confirmed,
                    short_vwap,
                    True,
                    "Price swept above ORH and closed back inside the range.",
                )
            if (
                request.config.direction in {"long", "both"}
                and low_breach
                and bar.close > opening_range.opening_range_low
                and volume_confirmed
            ):
                return _trade_signal(
                    "REVERSAL_LONG",
                    "LONG",
                    bar,
                    duration_ns,
                    bar.close,
                    bar.low,
                    request.config.reward_risk_ratio,
                    volume_confirmed,
                    long_vwap,
                    True,
                    "Price swept below ORL and closed back inside the range.",
                )
    return _no_setup("No configured ORB/ORR setup completed before the entry cutoff.")


def _trade_signal(
    signal_type: str,
    side: str,
    bar: CandleBar,
    duration_ns: int,
    entry: float,
    stop: float,
    reward_risk: float,
    volume_confirmed: bool,
    vwap_confirmed: bool,
    close_confirmed: bool,
    reason: str,
) -> OrbSignalCandidate:
    risk = abs(entry - stop)
    target = entry + risk * reward_risk if side == "LONG" else entry - risk * reward_risk
    return OrbSignalCandidate(
        signal_type=signal_type,  # type: ignore[arg-type]
        side=side,  # type: ignore[arg-type]
        signal_timestamp_ns=bar.timestamp_ns,
        signal_close_time_ns=bar.timestamp_ns + duration_ns,
        trigger_price=round(entry, 8),
        entry_price=round(entry, 8),
        stop_price=round(stop, 8),
        target_price=round(target, 8),
        invalidation=(
            "Close below the opening-range low/stop."
            if side == "LONG"
            else "Close above the opening-range high/stop."
        ),
        reward_risk_ratio=reward_risk,
        volume_confirmed=volume_confirmed,
        vwap_confirmed=vwap_confirmed,
        close_confirmed=close_confirmed,
        reason=reason,
    )


def _no_setup(reason: str) -> OrbSignalCandidate:
    return OrbSignalCandidate(
        signal_type="NO_SETUP",
        side="NONE",
        invalidation="No setup exists to invalidate.",
        volume_confirmed=False,
        vwap_confirmed=False,
        close_confirmed=False,
        reason=reason,
    )


def _features(
    request: OrbBuildRequest,
    opening_range: OrbOpeningRange | None,
    post_range: list[CandleBar],
    source_bars: list[CandleBar],
) -> OrbFeatureRecord:
    latest = post_range[-1] if post_range else (source_bars[-1] if source_bars else None)
    if opening_range is None or latest is None:
        return OrbFeatureRecord(
            session_phase="opening_range_building",
            post_range_bar_count=len(post_range),
            latest_close_vs_orh_pct=0.0,
            latest_close_vs_orl_pct=0.0,
            opening_range_width_atr=0.0,
            post_range_volume_ratio=0.0,
            false_break_high=False,
            false_break_low=False,
            source_bar_count=len(source_bars),
        )
    ranges = [max(bar.high - bar.low, 0.0) for bar in source_bars[-14:]]
    atr = mean(ranges) if ranges else 0.0
    range_volume_mean = opening_range.range_volume / max(opening_range.range_bar_count, 1)
    post_volume = mean([float(bar.volume or 0.0) for bar in post_range]) if post_range else 0.0
    return OrbFeatureRecord(
        session_phase=_session_phase(
            _local_hhmm(
                latest.timestamp_ns,
                request.session.timezone_offset_minutes,
            )
        ),
        post_range_bar_count=len(post_range),
        latest_close_vs_orh_pct=round(
            _pct(latest.close, opening_range.opening_range_high), 8
        ),
        latest_close_vs_orl_pct=round(
            _pct(latest.close, opening_range.opening_range_low), 8
        ),
        opening_range_width_atr=round(
            opening_range.opening_range_width / max(atr, EPSILON), 8
        ),
        post_range_volume_ratio=round(
            post_volume / max(range_volume_mean, EPSILON), 8
        ),
        false_break_high=any(
            bar.high > opening_range.opening_range_high
            and bar.close < opening_range.opening_range_high
            for bar in post_range
        ),
        false_break_low=any(
            bar.low < opening_range.opening_range_low
            and bar.close > opening_range.opening_range_low
            for bar in post_range
        ),
        source_bar_count=len(source_bars),
    )


def _gates(request, closed, session_bars, opening_range, signal) -> list[dict]:
    return [
        _gate("ORB-001", "NSE session definition locked", request.session.exchange == "NSE", "Only the explicit NSE 09:15-15:30 session is enabled in v1.89."),
        _gate("ORB-002", "Closed-candle point-in-time input", all(bar.timestamp_ns + timeframe_duration_ns(request.series.timeframe) <= request.decision_time_ns for bar in closed), f"closed_bars={len(closed)}"),
        _gate("ORB-003", "Session bars available", bool(session_bars), f"session_bars={len(session_bars)}"),
        _gate("ORB-004", "Opening range locked before signal", bool(opening_range and opening_range.locked), f"range_locked={bool(opening_range and opening_range.locked)}"),
        _gate("ORB-005", "Signal occurs after range lock", signal.signal_timestamp_ns is None or opening_range is not None and signal.signal_timestamp_ns >= opening_range.lock_time_ns, f"signal_timestamp_ns={signal.signal_timestamp_ns}"),
        _gate("ORB-SAFE-001", "Research-only; no order route", True, "trade_allowed=false; paper_execution_attempted=false; order_routing_enabled=false"),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> dict:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": passed,
        "evidence": evidence,
        "remediation": None if passed else "Keep result at NO_SETUP and supply fully closed, correctly aligned session data.",
    }


def _local_datetime(timestamp_ns: int, offset_minutes: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc) + timedelta(minutes=offset_minutes)


def _local_hhmm(timestamp_ns: int, offset_minutes: int) -> str:
    return _local_datetime(timestamp_ns, offset_minutes).strftime("%H:%M")


def _in_session(local_dt: datetime, start: str, end: str) -> bool:
    hhmm = local_dt.strftime("%H:%M")
    return start <= hhmm < end


def _clock_in_window(local_dt: datetime, start: str, end: str) -> bool:
    hhmm = local_dt.strftime("%H:%M")
    return start <= hhmm < end


def _local_clock_to_utc_ns(local_date, hhmm: str, offset_minutes: int) -> int:
    hour, minute = (int(item) for item in hhmm.split(":"))
    local_naive = datetime(
        local_date.year,
        local_date.month,
        local_date.day,
        hour,
        minute,
    )
    utc_dt = (local_naive - timedelta(minutes=offset_minutes)).replace(tzinfo=timezone.utc)
    return int(utc_dt.timestamp() * 1_000_000_000)


def _vwap(bars: list[CandleBar]) -> float | None:
    total_volume = sum(float(bar.volume or 0.0) for bar in bars)
    if total_volume <= EPSILON:
        return None
    return sum(
        ((bar.high + bar.low + bar.close) / 3.0) * float(bar.volume or 0.0)
        for bar in bars
    ) / total_volume


def _pct(value: float, reference: float) -> float:
    return (value - reference) / max(abs(reference), EPSILON) * 100.0


def _session_phase(hhmm: str) -> str:
    if hhmm < "09:30":
        return "opening_drive"
    if hhmm < "10:15":
        return "establishment"
    if hhmm < "13:30":
        return "midday"
    if hhmm < "15:00":
        return "afternoon_trend"
    return "closing_auction"


def _hash(value: dict) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
