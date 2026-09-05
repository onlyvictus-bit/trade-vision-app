from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..models import BehaviorDataQualityIssue, BehaviorDataQualityResult, CandleBar, CandleSeries, now_iso
from .point_in_time_guard import timeframe_duration_ns

# NSE session (platform is NSE-locked; see OrbSessionDefinition). Used to
# classify close->open boundaries as expected market closure, not data gaps.
_IST = timezone(timedelta(hours=5, minutes=30))
_SESSION_OPEN = 9 * 60 + 15      # 09:15 local minutes-of-day
_SESSION_CLOSE = 15 * 60 + 30    # 15:30 local minutes-of-day
_BOUNDARY_TOLERANCE_STEPS = 2


def _local_minutes_of_day(timestamp_ns: int) -> int:
    local = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=_IST)
    return local.hour * 60 + local.minute


def _is_expected_session_closure(previous_ns: int, current_ns: int, step_ns: int) -> bool:
    """True when a timestamp gap spans an exchange session boundary
    (overnight, weekend, or holiday closure) rather than missing intraday data."""
    step_minutes = max(1, step_ns // 60_000_000_000)
    prev_local = datetime.fromtimestamp(previous_ns / 1_000_000_000, tz=_IST)
    curr_local = datetime.fromtimestamp(current_ns / 1_000_000_000, tz=_IST)
    if prev_local.date() == curr_local.date():
        return False  # same-day gap = genuinely missing intraday bars
    prev_minutes = prev_local.hour * 60 + prev_local.minute
    curr_minutes = curr_local.hour * 60 + curr_local.minute
    near_close = prev_minutes >= _SESSION_CLOSE - _BOUNDARY_TOLERANCE_STEPS * step_minutes
    near_open = curr_minutes <= _SESSION_OPEN + _BOUNDARY_TOLERANCE_STEPS * step_minutes
    return near_close and near_open


def scan_data_quality(series: CandleSeries) -> BehaviorDataQualityResult:
    issues: list[BehaviorDataQualityIssue] = []
    seen_timestamps: set[int] = set()
    previous_timestamp: int | None = None
    previous_close: float | None = None

    missing_volume_count = 0
    invalid_ohlc_count = 0
    duplicate_timestamp_count = 0
    non_monotonic_count = 0
    gap_count = 0
    session_closure_gap_count = 0
    abnormal_print_count = 0
    split_suspect_count = 0
    expected_step_ns = timeframe_duration_ns(series.timeframe)

    for bar in series.bars:
        if _invalid_ohlc(bar):
            invalid_ohlc_count += 1
            issues.append(
                BehaviorDataQualityIssue(
                    code="invalid_ohlc",
                    severity="blocker",
                    message="OHLC is impossible: high must be >= open/close/low and low must be <= open/close/high.",
                    sequence_number=bar.sequence_number,
                    timestamp_ns=bar.timestamp_ns,
                )
            )

        if bar.volume is None:
            missing_volume_count += 1
            issues.append(
                BehaviorDataQualityIssue(
                    code="missing_volume",
                    severity="warning",
                    message="Volume is missing; volume z-score, absorption, and effort/result matching must be disabled.",
                    sequence_number=bar.sequence_number,
                    timestamp_ns=bar.timestamp_ns,
                )
            )

        if bar.timestamp_ns in seen_timestamps:
            duplicate_timestamp_count += 1
            issues.append(
                BehaviorDataQualityIssue(
                    code="duplicate_timestamp",
                    severity="blocker",
                    message="Duplicate candle timestamp would corrupt sequence memory and replay determinism.",
                    sequence_number=bar.sequence_number,
                    timestamp_ns=bar.timestamp_ns,
                )
            )
        seen_timestamps.add(bar.timestamp_ns)

        if previous_timestamp is not None:
            delta = bar.timestamp_ns - previous_timestamp
            if delta <= 0:
                non_monotonic_count += 1
                issues.append(
                    BehaviorDataQualityIssue(
                        code="non_monotonic_timestamp",
                        severity="blocker",
                        message="Candle timestamps must be strictly increasing in the supplied order.",
                        sequence_number=bar.sequence_number,
                        timestamp_ns=bar.timestamp_ns,
                    )
                )
            elif delta > expected_step_ns * 1.5:
                if _is_expected_session_closure(previous_timestamp, bar.timestamp_ns, expected_step_ns):
                    # Exchange closure (overnight / weekend / holiday): expected
                    # for externally loaded history, not a data-quality defect.
                    session_closure_gap_count += 1
                    issues.append(
                        BehaviorDataQualityIssue(
                            code="session_closure_gap",
                            severity="info",
                            message="Timestamp gap spans an exchange session boundary (market closure).",
                            sequence_number=bar.sequence_number,
                            timestamp_ns=bar.timestamp_ns,
                        )
                    )
                else:
                    gap_count += 1
                    issues.append(
                        BehaviorDataQualityIssue(
                            code="data_gap",
                            severity="warning",
                            message=f"Timestamp gap detected: {delta} ns exceeds expected {expected_step_ns} ns cadence.",
                            sequence_number=bar.sequence_number,
                            timestamp_ns=bar.timestamp_ns,
                        )
                    )

        if bar.close > 0 and ((bar.high - bar.low) / bar.close) > 0.25:
            abnormal_print_count += 1
            issues.append(
                BehaviorDataQualityIssue(
                    code="abnormal_print",
                    severity="warning",
                    message="Single candle range exceeds 25% of close; verify bad tick, circuit move, or special event.",
                    sequence_number=bar.sequence_number,
                    timestamp_ns=bar.timestamp_ns,
                )
            )

        if previous_close is not None and previous_close > 0:
            ratio = bar.close / previous_close
            if ratio >= 2.0 or ratio <= 0.5:
                split_suspect_count += 1
                issues.append(
                    BehaviorDataQualityIssue(
                        code="split_or_adjustment_suspect",
                        severity="blocker",
                        message="Close-to-close jump suggests split/bonus/corporate action adjustment risk.",
                        sequence_number=bar.sequence_number,
                        timestamp_ns=bar.timestamp_ns,
                    )
                )

        previous_timestamp = bar.timestamp_ns
        previous_close = bar.close

    blocker_count = sum(1 for issue in issues if issue.severity == "blocker")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    score = max(0.0, round(1.0 - blocker_count * 0.18 - warning_count * 0.035, 4))
    blocks_trade = blocker_count > 0 or score < 0.85
    valid_bars = max(0, len(series.bars) - invalid_ohlc_count - duplicate_timestamp_count - non_monotonic_count)

    return BehaviorDataQualityResult(
        symbol=series.symbol.upper(),
        timeframe=series.timeframe,
        checked_at=now_iso(),
        total_bars=len(series.bars),
        valid_bars=valid_bars,
        data_quality_score=score,
        missing_volume_count=missing_volume_count,
        invalid_ohlc_count=invalid_ohlc_count,
        duplicate_timestamp_count=duplicate_timestamp_count,
        non_monotonic_count=non_monotonic_count,
        gap_count=gap_count,
        session_closure_gap_count=session_closure_gap_count,
        abnormal_print_count=abnormal_print_count,
        split_suspect_count=split_suspect_count,
        volume_matching_enabled=missing_volume_count == 0,
        blocks_trade=blocks_trade,
        issues=issues,
    )


def _invalid_ohlc(bar: CandleBar) -> bool:
    return (
        bar.low > bar.high
        or bar.high < bar.open
        or bar.high < bar.close
        or bar.low > bar.open
        or bar.low > bar.close
    )
