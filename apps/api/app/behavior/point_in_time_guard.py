from __future__ import annotations

from ..models import PointInTimeGuardRequest, PointInTimeGuardResult, TimeframeValue


_NANOSECONDS_PER_MINUTE = 60_000_000_000
_TIMEFRAME_DURATION_NS: dict[str, int] = {
    "1m": _NANOSECONDS_PER_MINUTE,
    "3m": 3 * _NANOSECONDS_PER_MINUTE,
    "5m": 5 * _NANOSECONDS_PER_MINUTE,
    "15m": 15 * _NANOSECONDS_PER_MINUTE,
    "30m": 30 * _NANOSECONDS_PER_MINUTE,
    "1H": 60 * _NANOSECONDS_PER_MINUTE,
    "4H": 4 * 60 * _NANOSECONDS_PER_MINUTE,
    "daily": 24 * 60 * _NANOSECONDS_PER_MINUTE,
    "weekly": 7 * 24 * 60 * _NANOSECONDS_PER_MINUTE,
}


def timeframe_duration_ns(timeframe: TimeframeValue) -> int:
    return _TIMEFRAME_DURATION_NS[timeframe]


def run_point_in_time_guard(request: PointInTimeGuardRequest) -> PointInTimeGuardResult:
    duration_ns = timeframe_duration_ns(request.source_timeframe)
    allowed_bars = 0
    future_bar_blocked = 0
    incomplete_candle_blocked = 0
    latest_allowed_timestamp_ns: int | None = None
    reasons: list[str] = []

    for bar in request.series.bars:
        candle_close_ns = bar.timestamp_ns + duration_ns
        blocked = False
        if bar.timestamp_ns > request.decision_time_ns:
            future_bar_blocked += 1
            blocked = True
        if candle_close_ns > request.decision_time_ns:
            incomplete_candle_blocked += 1
            blocked = True
        if blocked:
            continue
        allowed_bars += 1
        latest_allowed_timestamp_ns = bar.timestamp_ns

    blocked_bars = len(request.series.bars) - allowed_bars
    if future_bar_blocked:
        reasons.append("Future bar timestamp detected. Causal feature whitelist failed.")
    if incomplete_candle_blocked:
        reasons.append("Incomplete candle detected. Higher/lower timeframe value cannot be used before close.")
    if allowed_bars == 0 and request.series.bars:
        reasons.append("No candle remains available at the decision time.")
    if not reasons:
        reasons.append("All supplied candles are closed and available at the decision time.")

    passed = blocked_bars == 0
    return PointInTimeGuardResult(
        symbol=request.series.symbol.upper(),
        source_timeframe=request.source_timeframe,
        decision_time_ns=request.decision_time_ns,
        execution_time_ns=request.execution_time_ns,
        timeframe_duration_ns=duration_ns,
        allowed_bars=allowed_bars,
        blocked_bars=blocked_bars,
        future_bar_blocked=future_bar_blocked,
        incomplete_candle_blocked=incomplete_candle_blocked,
        latest_allowed_timestamp_ns=latest_allowed_timestamp_ns,
        passed=passed,
        blocks_trade=not passed,
        reasons=reasons,
    )
