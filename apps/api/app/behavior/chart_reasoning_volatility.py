from __future__ import annotations

import math
from statistics import mean, pstdev

from ..models import ChartReasoningGate, ChartReasoningReport, ChartReasoningRequest, CandleAnatomyRequest, CandleBar
from .candle_anatomy import analyze_candles


CHART_REASONING_VERSION = "behavior-chart-reasoning-volatility.v1.70"


def build_chart_reasoning_report(request: ChartReasoningRequest) -> ChartReasoningReport:
    bars = sorted(request.series.bars, key=lambda bar: (bar.timestamp_ns, bar.sequence_number))
    anatomy = analyze_candles(CandleAnatomyRequest(series=request.series, atr_period=request.atr_period))
    latest = anatomy.latest
    latest_bar = bars[-1] if bars else None
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    ranges = [max(bar.high - bar.low, 0.0) for bar in bars]
    bodies = [abs(bar.close - bar.open) for bar in bars]
    volumes = [float(bar.volume or 0.0) for bar in bars]
    prior_ranges = ranges[:-1]

    current_atr = _mean(ranges[-request.atr_period :])
    atr_percentile = _percentile_rank(current_atr, _rolling_means(prior_ranges, request.atr_period))
    hv_series = _historical_volatility(closes)
    current_hv = hv_series[-1] if hv_series else 0.0
    hv_percentile = _percentile_rank(current_hv, hv_series[:-1])
    bb_widths = _bb_widths(closes, request.bb_period)
    current_bb_width = bb_widths[-1] if bb_widths else 0.0
    bb_width_percentile = _percentile_rank(current_bb_width, bb_widths[:-1])
    hurst = _hurst_exponent(closes[-request.hurst_window :])
    fractal_dimension = _clamp(2.0 - hurst, 1.0, 2.0)
    fractal_noise_score = _clamp((fractal_dimension - 1.0), 0.0, 1.0)
    micro_slope = _linear_slope(closes[-9:]) / max(current_atr, 1e-9)
    body_acceleration = _linear_slope(bodies[-5:]) / max(_mean(bodies[-5:]), 1e-9)
    candle_mass_index = _safe_ratio(ranges[-1] if ranges else 0.0, bodies[-1] if bodies else 0.0)
    rejection_index = _latest_rejection_index(latest)
    ema20 = _ema(closes, 20)
    ema9 = _ema(closes, 9)
    ema50 = _ema(closes, 50)
    ema_distance_atr = _safe_ratio((closes[-1] - ema20), current_atr) if closes else 0.0
    ema_tangled = abs(ema9 - ema20) <= current_atr * 0.15 and abs(ema20 - ema50) <= current_atr * 0.25
    contraction_count = _contraction_count(ranges[-request.vcp_window :])
    volume_dryup_score = _volume_dryup(volumes[-request.vcp_window :])
    vcp_state = _vcp_state(contraction_count, volume_dryup_score, request.vcp_window)
    volatility_regime = _volatility_regime(atr_percentile, bb_width_percentile, hv_percentile)
    trend_persistence_score = _trend_persistence_score(hurst, micro_slope, ema_distance_atr, fractal_noise_score)
    hidden_bullish, hidden_bearish = _hidden_divergence(closes)
    oscillator_state = _oscillator_exhaustion(closes)
    trend_health = _trend_health(trend_persistence_score, ema_tangled, volatility_regime)
    chop_risk = _chop_risk(hurst, fractal_noise_score, ema_tangled, bb_width_percentile)
    momentum_cleanliness = _momentum_cleanliness(rejection_index, body_acceleration, ema_tangled)
    rubber_band_risk = _rubber_band_risk(ema_distance_atr)
    mean_reversion_state = _mean_reversion_state(hurst, fractal_noise_score, bb_width_percentile)
    time_symmetry_cluster = _time_symmetry_cluster(highs, lows)
    gates = _gates(
        bars=bars,
        request=request,
        no_future_leakage=True,
        atr_percentile=atr_percentile,
        bb_width_percentile=bb_width_percentile,
        vcp_state=vcp_state,
        fractal_noise_score=fractal_noise_score,
    )
    reasons = [
        f"Chart reasoning uses {len(bars)} closed candles and does not create order authority.",
        f"Volatility regime is {volatility_regime}; ATR percentile {atr_percentile:.2f}, BB-width percentile {bb_width_percentile:.2f}.",
        f"Trend persistence score is {trend_persistence_score:.2f}; chop risk is {chop_risk}.",
        f"VCP state is {vcp_state} with {contraction_count} contraction steps and {volume_dryup_score:.2f} volume dry-up.",
    ]
    if rejection_index >= 2.0:
        reasons.append("Large wick/body rejection is present; breakout confidence must be downgraded unless later evidence confirms.")
    if ema_tangled:
        reasons.append("EMA geometry is tangled; single breakout candles should not be trusted as clean trend proof.")

    return ChartReasoningReport(
        reasoning_version=CHART_REASONING_VERSION,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        closed_candle_only=True,
        source_bar_count=len(bars),
        latest_timestamp_ns=latest_bar.timestamp_ns if latest_bar else None,
        latest_sequence_number=latest_bar.sequence_number if latest_bar else None,
        trend_health=trend_health,
        chop_risk=chop_risk,
        rejection_index=round(rejection_index, 6),
        rubber_band_risk=rubber_band_risk,
        momentum_cleanliness=momentum_cleanliness,
        mean_reversion_state=mean_reversion_state,
        time_symmetry_cluster=time_symmetry_cluster,
        fractal_noise_score=round(fractal_noise_score, 6),
        volatility_regime=volatility_regime,
        hv_percentile=round(hv_percentile, 6),
        bb_width_percentile=round(bb_width_percentile, 6),
        vcp_state=vcp_state,
        contraction_count=contraction_count,
        volume_dryup_score=round(volume_dryup_score, 6),
        trend_persistence_score=round(trend_persistence_score, 6),
        hurst_exponent=round(hurst, 6),
        fractal_dimension=round(fractal_dimension, 6),
        micro_trend_slope=round(micro_slope, 6),
        candle_acceleration=round(body_acceleration, 6),
        candle_mass_index=round(min(candle_mass_index, 999.0), 6),
        ema_distance_atr=round(ema_distance_atr, 6),
        ema_tangled=ema_tangled,
        hidden_bullish_divergence=hidden_bullish,
        hidden_bearish_divergence=hidden_bearish,
        oscillator_exhaustion=oscillator_state,
        atr_percentile=round(atr_percentile, 6),
        current_atr=round(max(current_atr, 0.0), 6),
        current_bb_width=round(max(current_bb_width, 0.0), 6),
        no_future_leakage=True,
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        reasons=reasons,
        failure_questions=_failure_questions(len(bars), current_atr, hv_series, bb_widths),
        gates=gates,
    )


def _mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-9:
        return 0.0
    return numerator / denominator


def _clamp(value: float, minimum: float, maximum: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return minimum
    return max(minimum, min(maximum, value))


def _percentile_rank(value: float, history: list[float]) -> float:
    clean = [item for item in history if not math.isnan(item) and not math.isinf(item)]
    if not clean:
        return 50.0
    below = sum(1 for item in clean if item <= value)
    return _clamp((below / len(clean)) * 100.0, 0.0, 100.0)


def _rolling_means(values: list[float], window: int) -> list[float]:
    if len(values) < window:
        return []
    return [mean(values[index - window : index]) for index in range(window, len(values) + 1)]


def _historical_volatility(closes: list[float], window: int = 20) -> list[float]:
    if len(closes) < window + 1:
        return []
    returns = []
    for index in range(1, len(closes)):
        previous = closes[index - 1]
        returns.append(_safe_ratio(closes[index] - previous, previous))
    output: list[float] = []
    for index in range(window, len(returns) + 1):
        sample = returns[index - window : index]
        output.append(pstdev(sample) * math.sqrt(252.0))
    return output


def _bb_widths(closes: list[float], window: int) -> list[float]:
    if len(closes) < window:
        return []
    widths: list[float] = []
    for index in range(window, len(closes) + 1):
        sample = closes[index - window : index]
        center = mean(sample)
        width = 4.0 * pstdev(sample)
        widths.append(_clamp(_safe_ratio(width, center), 0.0, 100.0))
    return widths


def _hurst_exponent(values: list[float]) -> float:
    if len(values) < 16 or max(values) - min(values) <= 1e-9:
        return 0.5
    lags = [2, 4, 8, 16]
    tau: list[float] = []
    usable_lags: list[int] = []
    for lag in lags:
        if lag >= len(values):
            continue
        diffs = [values[index] - values[index - lag] for index in range(lag, len(values))]
        deviation = pstdev(diffs) if len(diffs) > 1 else 0.0
        if deviation > 1e-9:
            tau.append(math.log(deviation))
            usable_lags.append(lag)
    if len(tau) < 2:
        return 0.5
    slope = _linear_slope(tau, [math.log(lag) for lag in usable_lags])
    return _clamp(slope, 0.0, 1.0)


def _linear_slope(values: list[float], x_values: list[float] | None = None) -> float:
    if len(values) < 2:
        return 0.0
    xs = x_values if x_values is not None else [float(index) for index in range(len(values))]
    x_mean = mean(xs)
    y_mean = mean(values)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator <= 1e-9:
        return 0.0
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denominator


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    ema = values[0]
    for value in values[1:]:
        ema = value * alpha + ema * (1.0 - alpha)
    return ema


def _latest_rejection_index(latest) -> float:
    if latest is None:
        return 0.0
    wick_pct = max(latest.upper_wick_pct, latest.lower_wick_pct)
    return _safe_ratio(wick_pct, max(latest.body_pct, 1.0))


def _contraction_count(ranges: list[float]) -> int:
    if len(ranges) < 3:
        return 0
    count = 0
    previous = ranges[0]
    for value in ranges[1:]:
        if value < previous * 0.88:
            count += 1
        previous = value
    return count


def _volume_dryup(volumes: list[float]) -> float:
    if len(volumes) < 6:
        return 0.0
    first = mean(volumes[: len(volumes) // 2])
    second = mean(volumes[len(volumes) // 2 :])
    return _clamp(1.0 - _safe_ratio(second, max(first, 1e-9)), 0.0, 1.0)


def _vcp_state(contraction_count: int, volume_dryup_score: float, window: int) -> str:
    if contraction_count >= max(3, window // 4) and volume_dryup_score >= 0.25:
        return "vcp_contraction_with_volume_dryup"
    if contraction_count >= max(2, window // 5):
        return "price_contraction_without_volume_dryup"
    return "no_clean_vcp"


def _volatility_regime(atr_percentile: float, bb_width_percentile: float, hv_percentile: float) -> str:
    if atr_percentile >= 95.0 or hv_percentile >= 95.0:
        return "extreme_volatility_ood"
    if atr_percentile >= 75.0 or bb_width_percentile >= 75.0 or hv_percentile >= 75.0:
        return "expanding_volatility"
    if atr_percentile <= 35.0 and bb_width_percentile <= 25.0:
        return "compressed_volatility"
    return "normal_volatility"


def _trend_persistence_score(hurst: float, micro_slope: float, ema_distance_atr: float, fractal_noise_score: float) -> float:
    trend_component = _clamp((hurst - 0.45) / 0.35, 0.0, 1.0)
    slope_component = _clamp(abs(micro_slope) / 0.35, 0.0, 1.0)
    ema_component = _clamp(abs(ema_distance_atr) / 1.5, 0.0, 1.0)
    clean_component = 1.0 - fractal_noise_score
    return _clamp(mean([trend_component, slope_component, ema_component, clean_component]), 0.0, 1.0)


def _hidden_divergence(closes: list[float]) -> tuple[bool, bool]:
    if len(closes) < 20:
        return False, False
    momentum = [closes[index] - closes[index - 5] for index in range(5, len(closes))]
    price_recent = closes[-10:]
    momentum_recent = momentum[-10:]
    price_slope = _linear_slope(price_recent)
    momentum_slope = _linear_slope(momentum_recent)
    return price_slope > 0 and momentum_slope < 0, price_slope < 0 and momentum_slope > 0


def _oscillator_exhaustion(closes: list[float]) -> str:
    if len(closes) < 3:
        return "unknown"
    short_return = _safe_ratio(closes[-1] - closes[-3], closes[-3])
    if short_return >= 0.025:
        return "upside_exhaustion_possible"
    if short_return <= -0.025:
        return "downside_exhaustion_possible"
    return "normal"


def _trend_health(score: float, ema_tangled: bool, volatility_regime: str) -> str:
    if ema_tangled:
        return "tangled_chop"
    if volatility_regime == "extreme_volatility_ood":
        return "unstable_extreme_volatility"
    if score >= 0.68:
        return "persistent_trend"
    if score >= 0.45:
        return "developing_trend"
    return "weak_or_choppy"


def _chop_risk(hurst: float, fractal_noise_score: float, ema_tangled: bool, bb_width_percentile: float) -> str:
    if ema_tangled or hurst < 0.45 or fractal_noise_score >= 0.60:
        return "high"
    if bb_width_percentile <= 25.0:
        return "compression_watch"
    return "low"


def _momentum_cleanliness(rejection_index: float, acceleration: float, ema_tangled: bool) -> str:
    if rejection_index >= 2.0:
        return "rejection_polluted"
    if ema_tangled:
        return "ema_tangled"
    if acceleration < -0.15:
        return "decelerating"
    return "clean"


def _rubber_band_risk(ema_distance_atr: float) -> str:
    distance = abs(ema_distance_atr)
    if distance >= 2.5:
        return "extreme_extension"
    if distance >= 1.5:
        return "extended"
    return "normal"


def _mean_reversion_state(hurst: float, fractal_noise_score: float, bb_width_percentile: float) -> str:
    if hurst < 0.45 and fractal_noise_score >= 0.55:
        return "mean_reversion_preferred"
    if bb_width_percentile <= 20.0:
        return "compression_before_expansion"
    return "trend_following_allowed"


def _time_symmetry_cluster(highs: list[float], lows: list[float]) -> str:
    if len(highs) < 13:
        return "insufficient_history"
    swing_points: list[int] = []
    for index in range(2, len(highs) - 2):
        if highs[index] == max(highs[index - 2 : index + 3]) or lows[index] == min(lows[index - 2 : index + 3]):
            swing_points.append(index)
    if len(swing_points) < 3:
        return "no_cluster"
    intervals = [swing_points[index] - swing_points[index - 1] for index in range(1, len(swing_points))]
    fib_hits = sum(1 for interval in intervals[-5:] if interval in {8, 13, 21, 34, 55})
    return "fib_time_cluster" if fib_hits >= 2 else "no_cluster"


def _gates(
    *,
    bars: list[CandleBar],
    request: ChartReasoningRequest,
    no_future_leakage: bool,
    atr_percentile: float,
    bb_width_percentile: float,
    vcp_state: str,
    fractal_noise_score: float,
) -> list[ChartReasoningGate]:
    monotonic = all(
        (bars[index].timestamp_ns, bars[index].sequence_number) > (bars[index - 1].timestamp_ns, bars[index - 1].sequence_number)
        for index in range(1, len(bars))
    )
    return [
        _gate("MAX-008", "No future candle enters morphology calculation", no_future_leakage, "block", "Only supplied closed candles are consumed."),
        _gate("MAX-004", "EMA tangled state is visible", True, "info", "EMA geometry is reported as evidence, not an execution trigger."),
        _gate("VOL-001", "ATR percentile uses prior closed data", len(bars) >= request.atr_period + 2, "warn", f"ATR percentile={atr_percentile:.2f}."),
        _gate("VOL-002", "BB-width compression is classified", True, "info", f"BB-width percentile={bb_width_percentile:.2f}."),
        _gate("VCP-001", "VCP contraction state computed", True, "info", vcp_state),
        _gate("FRA-001", "Fractal noise score bounded", 0.0 <= fractal_noise_score <= 1.0, "warn", f"fractal_noise_score={fractal_noise_score:.2f}."),
        _gate("V170-SEQ-001", "Candle ordering is monotonic", monotonic, "block", "Duplicate or non-monotonic candles corrupt chart reasoning."),
    ]


def _gate(gate_id: str, name: str, passed: bool, severity: str, evidence: str) -> ChartReasoningGate:
    return ChartReasoningGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
        remediation=None if passed else "Keep result as WAIT-only evidence until the source data and baseline are valid.",
    )


def _failure_questions(bar_count: int, atr: float, hv_series: list[float], bb_widths: list[float]) -> list[str]:
    questions = [
        "Are all bars confirmed closed before the decision timestamp?",
        "Is the ATR/volatility baseline long enough for this symbol and timeframe?",
        "Does a flat or low-variance period make trend persistence unreliable?",
        "Could a single manipulated wick be inflating rejection or range metrics?",
        "Does this chart-only layer conflict with higher-timeframe or market-regime evidence?",
    ]
    if bar_count < 30:
        questions.append("Low candle count: treat all outputs as weak research context only.")
    if atr <= 1e-9:
        questions.append("ATR is nearly zero: distance and overextension metrics may be untrustworthy.")
    if len(hv_series) < 5 or len(bb_widths) < 5:
        questions.append("Volatility percentile baseline is thin: avoid probability promotion.")
    return questions
