from __future__ import annotations

from ..models import CandleSeries, TimeframeAlignmentRecord, TimeframeSyncRequest, TimeframeSyncResult, TimeframeValue
from .point_in_time_guard import timeframe_duration_ns


def synchronize_timeframes(request: TimeframeSyncRequest) -> TimeframeSyncResult:
    records: list[TimeframeAlignmentRecord] = []
    reasons: list[str] = []
    usable_cutoff_by_timeframe: dict[str, int | None] = {}
    latest_close_times: list[int] = []

    seen_timeframes: set[str] = set()
    for series in request.series:
        record = _align_series(series, request.decision_time_ns)
        records.append(record)
        seen_timeframes.add(record.timeframe)
        usable_cutoff_by_timeframe[record.timeframe] = record.latest_closed_timestamp_ns
        if record.latest_closed_candle_close_ns is not None:
            latest_close_times.append(record.latest_closed_candle_close_ns)
        if record.blocked_future_bars:
            reasons.append(f"{record.timeframe}: future bars ignored at decision time.")
        if record.blocked_incomplete_bars:
            reasons.append(f"{record.timeframe}: incomplete candles ignored until close.")
        if not record.aligned:
            reasons.append(f"{record.timeframe}: no usable closed candle at decision time.")

    missing_required = [timeframe for timeframe in request.required_timeframes if timeframe not in seen_timeframes]
    for timeframe in missing_required:
        usable_cutoff_by_timeframe[timeframe] = None
        reasons.append(f"{timeframe}: required timeframe missing from synchronization request.")

    unusable_required = [
        record.timeframe
        for record in records
        if record.timeframe in request.required_timeframes and record.usable_bars == 0
    ]
    passed = not missing_required and not unusable_required
    if not reasons:
        reasons.append("All supplied timeframes have at least one closed candle available at the decision time.")

    return TimeframeSyncResult(
        symbol=request.symbol.upper(),
        decision_time_ns=request.decision_time_ns,
        execution_time_ns=request.execution_time_ns,
        required_timeframes=request.required_timeframes,
        records=records,
        usable_cutoff_by_timeframe=usable_cutoff_by_timeframe,
        latest_common_close_time_ns=min(latest_close_times) if latest_close_times else None,
        passed=passed,
        blocks_trade=not passed,
        reasons=reasons,
    )


def _align_series(series: CandleSeries, decision_time_ns: int) -> TimeframeAlignmentRecord:
    duration_ns = timeframe_duration_ns(series.timeframe)
    usable_bars = 0
    blocked_future_bars = 0
    blocked_incomplete_bars = 0
    latest_closed_timestamp_ns: int | None = None
    latest_closed_candle_close_ns: int | None = None

    for bar in sorted(series.bars, key=lambda item: item.timestamp_ns):
        candle_close_ns = bar.timestamp_ns + duration_ns
        if bar.timestamp_ns > decision_time_ns:
            blocked_future_bars += 1
            continue
        if candle_close_ns > decision_time_ns:
            blocked_incomplete_bars += 1
            continue
        usable_bars += 1
        latest_closed_timestamp_ns = bar.timestamp_ns
        latest_closed_candle_close_ns = candle_close_ns

    aligned = usable_bars > 0
    if aligned:
        reason = "Latest usable candle is fully closed and causally available."
    else:
        reason = "No fully closed candle is available at the decision time."

    return TimeframeAlignmentRecord(
        timeframe=series.timeframe,
        input_bars=len(series.bars),
        usable_bars=usable_bars,
        blocked_future_bars=blocked_future_bars,
        blocked_incomplete_bars=blocked_incomplete_bars,
        latest_closed_timestamp_ns=latest_closed_timestamp_ns,
        latest_closed_candle_close_ns=latest_closed_candle_close_ns,
        aligned=aligned,
        reason=reason,
    )


def make_series(
    *,
    symbol: str,
    timeframe: TimeframeValue,
    timestamps_ns: list[int],
    base_price: float = 100.0,
) -> CandleSeries:
    from ..models import CandleBar

    duration = timeframe_duration_ns(timeframe)
    bars = [
        CandleBar(
            symbol=symbol.upper(),
            timeframe=timeframe,
            timestamp_ns=timestamp_ns,
            open=base_price + idx,
            high=base_price + idx + 1,
            low=base_price + idx - 1,
            close=base_price + idx + 0.25,
            volume=1000.0 + idx,
            source="mock",
            sequence_number=idx + 1,
        )
        for idx, timestamp_ns in enumerate(timestamps_ns)
    ]
    return CandleSeries(symbol=symbol.upper(), timeframe=timeframe, bars=bars, snapshot_id=f"manual-{timeframe}-{duration}")
