"""Causal, current-session-only features. No indicator vote double counting."""
from __future__ import annotations

from statistics import mean
from .contracts import Bar, MarketSnapshot, Policy, Side, MINUTE, NS, clock_ns


def wilder_atr(daily_hlc: tuple[tuple[float, float, float], ...], period: int = 14) -> float:
    """True range with SMA seed and Wilder recurrence, never truncated EWM seed.

    Caller must supply *earlier, complete, comparable* session bars. The first
    row is the previous-close seed, not one of the period true ranges.
    """
    if period < 1 or len(daily_hlc) < period + 1:
        raise ValueError("ATR_REQUIRES_PERIOD_PLUS_ONE_PRIOR_SESSIONS")
    for high, low, close in daily_hlc:
        if not all(__import__('math').isfinite(v) and v > 0 for v in (high, low, close)) or not low <= close <= high:
            raise ValueError("INVALID_DAILY_OHLC")
    trs = [max(h - l, abs(h - daily_hlc[i - 1][2]), abs(l - daily_hlc[i - 1][2]))
           for i, (h, l, c) in enumerate(daily_hlc) if i]
    atr = mean(trs[:period])
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def validate_prefix(s: MarketSnapshot, p: Policy) -> tuple[str, ...]:
    errors = list(s.data_blockers)
    start = clock_ns(s.session_date, p.open_minute)
    end = clock_ns(s.session_date, 930)
    previous = None
    source = None
    for b in s.bars:
        if b.minutes != p.feature_minutes:
            errors.append("NATIVE_FEATURE_RESOLUTION_MISMATCH")
        if b.open_ns < start or b.close_ns > end or (b.open_ns - start) % (p.feature_minutes * MINUTE):
            errors.append("BAR_OUTSIDE_ALIGNED_SESSION")
        expected = start if previous is None else previous.close_ns
        if b.open_ns != expected:
            errors.append("MISSING_DUPLICATE_OR_REORDERED_FEATURE_INTERVAL")
        if b.revision != 0:
            errors.append("REVISION_REQUIRES_SEPARATE_RECONCILIATION_RUN")
        if source is not None and b.source_id != source:
            errors.append("UNVERIFIED_MIXED_FEATURE_SOURCES")
        previous, source = b, b.source_id
    if s.bars and s.as_of_ns - s.bars[-1].close_ns > p.max_feature_lag_seconds * NS:
        errors.append("STALE_FEATURE_PREFIX")
    for name in p.required_capabilities:
        c = next((c for c in s.capabilities if c.name == name), None)
        if c is None or c.available_ns > s.as_of_ns or c.expires_ns <= s.as_of_ns or c.status != "VALID":
            errors.append("REQUIRED_CAPABILITY_UNAVAILABLE:" + name)
    for c in s.capabilities:
        if c.available_ns <= s.as_of_ns < c.expires_ns and c.blocks_new_entry:
            errors.append("VERIFIED_REFERENCE_BLOCK:" + c.name)
    return tuple(dict.fromkeys(errors))


def extract(s: MarketSnapshot, p: Policy) -> dict:
    bars = s.bars
    if not bars:
        return {"range_locked": False, "gap_ever_touched_pdc": False, "failure_count": 0}
    prior = s.prior
    opening = bars[0].open
    gap = (opening - prior.close) / prior.close * 100
    gap_atr = abs(opening - prior.close) / prior.atr14
    direction = Side.LONG if gap > 0 else Side.SHORT
    sign = direction.sign
    pivot = (prior.high + prior.low + prior.close) / 3
    raw_bc = (prior.high + prior.low) / 2
    raw_tc = 2 * pivot - raw_bc
    lower, upper = sorted((raw_bc, raw_tc))
    cpw = upper - lower
    gap_touched = any(b.low <= prior.close if sign > 0 else b.high >= prior.close for b in bars)
    volume = sum(b.volume for b in bars)
    vwap = sum((b.high + b.low + b.close) / 3 * b.volume for b in bars) / volume if volume > 0 else None
    # Exact source-plan definition: large gap is strictly greater than 1.5x
    # prior ATR. No hidden percentage floor is allowed across symbols.
    large_cut = 1.5 * prior.atr14 / prior.close * 100
    gap_class = "FLAT" if abs(gap) <= p.gap_flat_pct + 1e-12 else ("LARGE_" if gap_atr > 1.5 else "") + ("GAP_UP" if sign > 0 else "GAP_DOWN")
    count = p.range_minutes // p.feature_minutes
    locked = len(bars) >= count and bars[count - 1].close_ns == clock_ns(s.session_date, 555 + p.range_minutes)
    result = {
        "first_bar_range_atr": (bars[0].high-bars[0].low)/prior.atr14,
        "range_locked": locked, "gap_pct": gap, "gap_atr": gap_atr, "large_gap_threshold_pct": large_cut, "gap_class": gap_class,
        "gap_direction": direction.value, "gap_ever_touched_pdc": gap_touched,
        "elapsed_minutes": (s.as_of_ns-clock_ns(s.session_date,555))//MINUTE,
        "session_open": opening, "latest_close": bars[-1].close, "session_vwap": vwap, "cpr_pivot": pivot,
        "cpr_lower": lower, "cpr_upper": upper, "cpr_width_atr": cpw / prior.atr14,
        "cpr_class": "NARROW" if cpw / prior.atr14 < .5 else "WIDE" if cpw / prior.atr14 > 1 or cpw / prior.close * 100 > .6 else "NORMAL",
        "failure_count": 0, "outside_count": 0, "failure_index": -1,
        "last_failure_event": None, "fade_ready": False, "retest_ready": False,
        "chop_risk": False, "two_sided_bar": False, "extension_or": 0.0,
    }
    if not locked:
        return result
    opening_bars, post = bars[:count], bars[count:]
    high = max(b.high for b in opening_bars)
    low = min(b.low for b in opening_bars)
    width = high - low
    result.update(or_high=high, or_low=low, or_width=width,
                  or_width_atr=width / prior.atr14, lock_ns=opening_bars[-1].close_ns,
                  or_volume_mean=mean(b.volume for b in opening_bars))
    if width <= 0 or not post:
        return result
    boundary = high if sign > 0 else low
    trigger = boundary + sign * p.buffer_ticks * prior.tick_size
    outside_count, failures, last_failure = 0, 0, -1
    last_failed_bar = None
    excursion = high if sign > 0 else low
    episode_start = post[0].event_id
    had_break = False
    episode_active = False
    for i, b in enumerate(post):
        outside = (b.close - trigger) * sign > 0
        if outside and not episode_active:
            episode_start = b.event_id
        if outside:
            episode_active = True
        excursion = max(excursion, b.high) if sign > 0 else min(excursion, b.low)
        if episode_active and (b.close - boundary) * sign <= 0:
            failures += 1
            episode_active = False
            last_failure = i
            last_failed_bar = b
        swept = b.high > trigger if sign > 0 else b.low < trigger
        if not outside and swept and last_failed_bar is None:
            last_failure, last_failed_bar = i, b
        outside_count = outside_count + 1 if outside else 0
        had_break = had_break or outside
    latest = post[-1]
    previous = post[-2] if len(post) > 1 else None
    outside = (latest.close - trigger) * sign > 0
    both = latest.high > high + p.buffer_ticks * prior.tick_size and latest.low < low - p.buffer_ticks * prior.tick_size
    tolerance = p.retest_tolerance_or * width
    retest = bool(previous and (previous.close - trigger) * sign > 0 and outside and not both and
                  (boundary - tolerance <= latest.low <= boundary + tolerance if sign > 0 else
                   boundary - tolerance <= latest.high <= boundary + tolerance))
    fade_ready = bool(last_failed_bar and last_failure < len(post) - 1 and not outside and not both and not gap_touched and
                      (latest.close < opening and latest.close < last_failed_bar.low if sign > 0 else
                       latest.close > opening and latest.close > last_failed_bar.high))
    overlaps = [max(0., min(a.high, b.high) - max(a.low, b.low)) / max(min(a.high-a.low, b.high-b.low), prior.tick_size)
                for a, b in zip(post[-6:], post[-6:][1:])]
    overlap = mean(overlaps) if overlaps else 0.
    path_range = max(latest.high - latest.low, prior.tick_size)
    body = abs(latest.close - latest.open) / path_range
    upper_wick = (latest.high - max(latest.close, latest.open)) / path_range
    lower_wick = (min(latest.close, latest.open) - latest.low) / path_range
    trend_efficiency = abs(post[-1].close - post[0].open) / max(sum(b.high-b.low for b in post), prior.tick_size)
    result.update(
        outside_count=outside_count, outside=outside, failure_count=failures,
        failure_index=last_failure, last_failure_event=None if last_failed_bar is None else last_failed_bar.event_id,
        episode_id=episode_start, had_break=had_break, fade_ready=fade_ready, retest_ready=retest,
        excursion=excursion, boundary=boundary, trigger=trigger,
        two_sided_bar=both, overlap_ratio=overlap, trend_efficiency=trend_efficiency,
        chop_risk=failures >= 2 or overlap > .70 and trend_efficiency < .15,
        extension_or=max(0., (latest.close - boundary) * sign / width),
        volume_ratio=latest.volume / max(result["or_volume_mean"], 1e-9),
        body_ratio=body, upper_wick_ratio=upper_wick, lower_wick_ratio=lower_wick,
        close_location=(latest.close-latest.low)/path_range,
        inside_bar=bool(previous and latest.high <= previous.high and latest.low >= previous.low),
        outside_bar=bool(previous and latest.high >= previous.high and latest.low <= previous.low),
        engulfing_body=bool(previous and min(latest.open, latest.close) <= min(previous.open, previous.close)
                            and max(latest.open, latest.close) >= max(previous.open, previous.close)
                            and (latest.close-latest.open)*(previous.close-previous.open) < 0),
        observed_expansion=(latest.high-latest.low)/prior.atr14,
    )
    return result
