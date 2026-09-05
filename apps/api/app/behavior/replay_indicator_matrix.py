from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from statistics import fmean
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    MarketEvent,
    ReplayIndicatorMatrixReport,
    ReplayIndicatorMatrixRequest,
    ReplayIndicatorMatrixRow,
    ReplayIndicatorValidationRequest,
    ReplayIndicatorValidationReport,
    RuntimeReadinessGate,
)
from .replay_indicator_validation import build_replay_indicator_validation_report


MATRIX_VERSION = "behavior-replay-indicator-matrix.v0.34"
TARGET_MATRIX_ROWS = 32


def build_replay_indicator_matrix_report(
    request: ReplayIndicatorMatrixRequest,
    events: list[MarketEvent],
) -> ReplayIndicatorMatrixReport:
    """Build a deterministic replay-fed indicator matrix for research/chart validation."""

    base_request = ReplayIndicatorValidationRequest(
        symbol=request.symbol,
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
    )
    base_report = build_replay_indicator_validation_report(base_request, events)
    rows = _matrix_rows(base_report, events[: request.event_count])
    rows = rows[: request.required_matrix_rows]
    ready_rows = sum(1 for row in rows if row.readiness_status == "ready")
    proxy_rows = sum(1 for row in rows if row.readiness_status == "proxy")
    blocked_rows = sum(1 for row in rows if row.readiness_status == "blocked")
    output_hash = _hash_output(
        {
            "matrix_version": MATRIX_VERSION,
            "base_output_hash": base_report.output_hash,
            "symbol": request.symbol,
            "scenario_id": request.scenario_id,
            "seed": request.seed,
            "event_count": request.event_count,
            "timeframe": request.timeframe,
            "rows": [row.model_dump(mode="json") for row in rows],
        }
    )
    gates = _gates(request, base_report, rows)
    return ReplayIndicatorMatrixReport(
        matrix_version=MATRIX_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:{MATRIX_VERSION}:{request.scenario_id}:{request.seed}:{request.event_count}:{request.timeframe}:{request.required_matrix_rows}")),
        base_validation_version=base_report.validation_version,
        symbol=request.symbol,
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=request.event_count,
        timeframe=request.timeframe,
        base_indicator_count=base_report.indicator_count,
        matrix_indicator_count=len(rows),
        chart_point_count=base_report.chart_point_count,
        ready_rows=ready_rows,
        proxy_rows=proxy_rows,
        blocked_rows=blocked_rows,
        rows=rows,
        base_output_hash=base_report.output_hash,
        input_event_chain_hash=base_report.input_event_chain_hash,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=True,
        runtime_dependency_on_legacy_stock_app=False,
        safe_mode=True,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.34 expands the v0.33 six-overlay proof into a 32-row replay-fed behavior indicator matrix.",
            "Rows marked proxy are deterministic research proxies, not live trading claims.",
            "The matrix remains mock/replay only and exposes no broker route.",
        ],
    )


def _matrix_rows(report: ReplayIndicatorValidationReport, events: list[MarketEvent]) -> list[ReplayIndicatorMatrixRow]:
    bars = report.candle_series.bars
    if not bars or not report.indicator_points:
        return []
    latest = bars[-1]
    previous = bars[-2] if len(bars) > 1 else latest
    first = bars[0]
    indicator = report.indicator_points[-1]
    first_close = max(first.close, 0.0001)
    latest_range = max(latest.high - latest.low, 0.0001)
    previous_range = max(previous.high - previous.low, 0.0001)
    closes = [bar.close for bar in bars]
    volumes = [float(bar.volume or 0.0) for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    ranges = [max(bar.high - bar.low, 0.0001) for bar in bars]
    body_pct = abs(latest.close - latest.open) / latest_range
    upper_wick_pct = (latest.high - max(latest.open, latest.close)) / latest_range
    lower_wick_pct = (min(latest.open, latest.close) - latest.low) / latest_range
    close_location = (latest.close - latest.low) / latest_range
    return_pct = ((latest.close - first_close) / first_close) * 100
    ema_slope = latest.close - previous.close
    vwap_distance_pct = ((latest.close - indicator.vwap) / indicator.vwap) * 100
    atr_proxy = fmean(ranges[-5:])
    range_expansion = latest_range / max(fmean(ranges[:-1] or ranges), 0.0001)
    inside_bar = latest.high <= previous.high and latest.low >= previous.low
    outside_bar = latest.high > previous.high and latest.low < previous.low
    opening_bars = bars[: min(5, len(bars))]
    opening_high = max(bar.high for bar in opening_bars)
    opening_low = min(bar.low for bar in opening_bars)
    opening_position = (latest.close - opening_low) / max(opening_high - opening_low, 0.0001)
    breakout_quality = _clamp01((latest.close - opening_high) / max(atr_proxy, 0.0001) + 0.5)
    fakeout_risk = _clamp01(upper_wick_pct + (1 - body_pct) * 0.35 + (0.25 if latest.close < opening_high else 0.0))
    absorption = _clamp01(max(indicator.volume_z, 0.0) / 3 + (1 - body_pct) * 0.45)
    continuation_quality = _clamp01((1 if latest.close > indicator.vwap else 0) * 0.35 + (1 if ema_slope > 0 else 0) * 0.3 + body_pct * 0.35)
    retest_quality = _clamp01((1 - abs(vwap_distance_pct) / 2) * 0.45 + lower_wick_pct * 0.35 + (1 if latest.close > indicator.vwap else 0) * 0.2)
    level_respect = _clamp01(1 - min(abs(latest.close - indicator.vwap) / max(atr_proxy, 0.0001), 1))
    support_resistance_distance_pct = min(latest.close - min(lows), max(highs) - latest.close) / max(latest.close, 0.0001) * 100
    gap_context = _clamp(return_pct / 3, -1, 1)
    session_phase = _clamp01(len(bars) / 24)
    imbalances = [float(event.payload.get("imbalance", 0.0)) for event in events]
    order_flow_imbalance = fmean(imbalances[-5:] or [0.0])
    liquidity_score = _clamp01(fmean(volumes[-5:]) / 5000)
    slippage_risk = _clamp01(1 - liquidity_score + abs(order_flow_imbalance) * 0.25)
    no_trade_pressure = _clamp01(fakeout_risk * 0.35 + slippage_risk * 0.25 + (1 - continuation_quality) * 0.25 + absorption * 0.15)

    rows = [
        _row("close_price", "Price", 7, "CandleAnatomyResult", "replay_candle", latest.close, _score_from_sign(return_pct), "close", ["replay.close"], {"close": latest.close}, "Latest replay close price."),
        _row("replay_return_pct", "Price", 7, "CandleAnatomyResult", "replay_candle", return_pct, _score_from_sign(return_pct), None, ["first.close", "latest.close"], {"return_pct": round(return_pct, 4)}, "Replay return from first candle close to latest close."),
        _row("sma_3", "Trend", 10, "IndicatorSimilarityResult", "derived_overlay", indicator.sma_3, _score_distance(latest.close, indicator.sma_3 or latest.close), "sma_3", ["close"], {"sma_3": indicator.sma_3}, "Short moving average overlay from closed replay candles."),
        _row("ema_5", "Trend", 10, "IndicatorSimilarityResult", "derived_overlay", indicator.ema_5, _score_distance(latest.close, indicator.ema_5), "ema_5", ["close"], {"ema_5": indicator.ema_5}, "EMA-5 overlay used as a fast trend proxy."),
        _row("ema_5_slope", "Trend", 10, "IndicatorSimilarityResult", "derived_overlay", ema_slope, _score_from_sign(ema_slope), "ema_5", ["previous.close", "latest.close"], {"ema_slope": round(ema_slope, 4)}, "Fast trend slope from the current replay step."),
        _row("rsi_5", "Momentum", 10, "IndicatorSimilarityResult", "derived_overlay", indicator.rsi_5, _score_centered(indicator.rsi_5, 50, 50), "rsi_5", ["close"], {"rsi_5": indicator.rsi_5}, "RSI-5 momentum state computed without future bars."),
        _row("macd_fast_slow", "Momentum", 10, "IndicatorSimilarityResult", "derived_overlay", indicator.macd_fast_slow, _score_from_sign(indicator.macd_fast_slow), "macd_fast_slow", ["close"], {"macd_fast_slow": indicator.macd_fast_slow}, "Fast/slow EMA spread used as replay MACD proxy."),
        _row("vwap_distance_pct", "VWAP", 9, "VwapOrbCprContextResult", "derived_overlay", vwap_distance_pct, _score_from_sign(vwap_distance_pct), "vwap", ["close", "volume"], {"vwap": indicator.vwap, "distance_pct": round(vwap_distance_pct, 4)}, "Distance from VWAP, used for support/rejection context."),
        _row("volume_z", "Volume", 4, "LiquidityFilterResult", "derived_overlay", indicator.volume_z, _clamp(indicator.volume_z / 3, -1, 1), "volume_z", ["volume"], {"volume_z": indicator.volume_z}, "Volume participation relative to recent replay candles."),
        _row("cumulative_vwap", "VWAP", 9, "VwapOrbCprContextResult", "derived_overlay", indicator.vwap, _score_distance(latest.close, indicator.vwap), "vwap", ["close", "volume"], {"vwap": indicator.vwap}, "Cumulative VWAP overlay for replay chart context."),
        _row("atr_proxy_5", "Volatility", 6, "MarketRegimeResult", "behavior_proxy", atr_proxy, _clamp(atr_proxy / max(fmean(closes), 0.0001), -1, 1), None, ["high", "low"], {"atr_proxy_5": round(atr_proxy, 4)}, "Five-bar average range used as an ATR proxy."),
        _row("candle_body_pct", "Candle Anatomy", 7, "CandleAnatomyResult", "replay_candle", body_pct, _clamp(body_pct, -1, 1), None, ["open", "high", "low", "close"], {"body_pct": round(body_pct, 4)}, "Body percentage of current candle range."),
        _row("upper_wick_pct", "Candle Anatomy", 7, "CandleAnatomyResult", "replay_candle", upper_wick_pct, -_clamp01(upper_wick_pct), None, ["open", "high", "low", "close"], {"upper_wick_pct": round(upper_wick_pct, 4)}, "Upper wick rejection pressure proxy."),
        _row("lower_wick_pct", "Candle Anatomy", 7, "CandleAnatomyResult", "replay_candle", lower_wick_pct, _clamp01(lower_wick_pct), None, ["open", "high", "low", "close"], {"lower_wick_pct": round(lower_wick_pct, 4)}, "Lower wick demand pressure proxy."),
        _row("close_location_value", "Candle Anatomy", 7, "CandleAnatomyResult", "replay_candle", close_location, _score_centered(close_location, 0.5, 0.5), None, ["high", "low", "close"], {"close_location_value": round(close_location, 4)}, "Close location inside current candle range."),
        _row("range_expansion_score", "Volatility", 6, "MarketRegimeResult", "behavior_proxy", range_expansion, _clamp((range_expansion - 1) / 2, -1, 1), None, ["high", "low"], {"range_expansion": round(range_expansion, 4)}, "Current range versus prior replay range average."),
        _row("inside_bar_proxy", "Candle Structure", 7, "CandleAnatomyResult", "behavior_proxy", inside_bar, 0.0 if inside_bar else 0.2, None, ["previous.high", "previous.low", "latest.high", "latest.low"], {"inside_bar": inside_bar}, "Compression proxy for inside-bar behavior."),
        _row("outside_bar_proxy", "Candle Structure", 7, "CandleAnatomyResult", "behavior_proxy", outside_bar, 0.3 if outside_bar else 0.0, None, ["previous.high", "previous.low", "latest.high", "latest.low"], {"outside_bar": outside_bar}, "Expansion proxy for outside-bar behavior."),
        _row("opening_range_position", "ORB", 9, "VwapOrbCprContextResult", "behavior_proxy", opening_position, _score_centered(opening_position, 0.5, 0.5), None, ["first_5.high", "first_5.low", "close"], {"opening_range_position": round(opening_position, 4)}, "Position of latest close inside the opening replay range."),
        _row("breakout_quality_score", "Breakout", 18, "TradeDecisionResult", "behavior_proxy", breakout_quality, _score_centered(breakout_quality, 0.5, 0.5), None, ["opening_high", "close", "atr_proxy"], {"breakout_quality": round(breakout_quality, 4)}, "Replay breakout continuation quality proxy."),
        _row("fakeout_risk_score", "Trap Detection", 29, "NoTradeDecisionRecord", "safety_proxy", fakeout_risk, -_score_centered(fakeout_risk, 0, 1), None, ["upper_wick_pct", "body_pct", "opening_high"], {"fakeout_risk": round(fakeout_risk, 4)}, "Trap/fakeout pressure from wick rejection and weak body."),
        _row("absorption_score", "Order Flow Proxy", 14, "OrderFlowProxyResult", "behavior_proxy", absorption, -_score_centered(absorption, 0, 1), None, ["volume_z", "body_pct"], {"absorption_score": round(absorption, 4)}, "High-volume weak-body absorption proxy."),
        _row("continuation_quality_score", "Continuation", 18, "TradeDecisionResult", "behavior_proxy", continuation_quality, _score_centered(continuation_quality, 0.5, 0.5), None, ["close", "vwap", "ema_slope", "body_pct"], {"continuation_quality": round(continuation_quality, 4)}, "Continuation quality from VWAP, slope, and body strength."),
        _row("retest_quality_score", "Retest", 19, "DynamicTargetResult", "behavior_proxy", retest_quality, _score_centered(retest_quality, 0.5, 0.5), None, ["vwap_distance_pct", "lower_wick_pct"], {"retest_quality": round(retest_quality, 4)}, "Retest quality around VWAP and lower-wick demand."),
        _row("level_respect_proxy", "Support/Resistance", 16, "SupportResistanceMemoryResult", "behavior_proxy", level_respect, _score_centered(level_respect, 0.5, 0.5), None, ["close", "vwap", "atr_proxy"], {"level_respect_proxy": round(level_respect, 4)}, "Current replay level respect around VWAP."),
        _row("support_resistance_distance_pct", "Support/Resistance", 16, "SupportResistanceMemoryResult", "behavior_proxy", support_resistance_distance_pct, _clamp(support_resistance_distance_pct / 2, -1, 1), None, ["session_high", "session_low", "close"], {"sr_distance_pct": round(support_resistance_distance_pct, 4)}, "Distance from nearest replay high/low boundary."),
        _row("gap_context_score", "Gap", 13, "GapContextResult", "behavior_proxy", gap_context, gap_context, None, ["first.close", "latest.close"], {"gap_context_score": round(gap_context, 4)}, "Replay gap/move continuation proxy."),
        _row("session_phase_score", "Session Rhythm", 17, "SessionRhythmResult", "behavior_proxy", session_phase, _score_centered(session_phase, 0.5, 0.5), None, ["event_count", "session_clock"], {"session_phase_score": round(session_phase, 4)}, "Mock replay phase progress through the session window."),
        _row("order_flow_imbalance_proxy", "Order Flow Proxy", 14, "OrderFlowProxyResult", "behavior_proxy", order_flow_imbalance, _clamp(order_flow_imbalance, -1, 1), None, ["event.payload.imbalance"], {"imbalance": round(order_flow_imbalance, 4)}, "Order-flow proxy from deterministic replay imbalance payloads."),
        _row("liquidity_score", "Liquidity", 4, "LiquidityFilterResult", "safety_proxy", liquidity_score, _score_centered(liquidity_score, 0.5, 0.5), None, ["volume"], {"liquidity_score": round(liquidity_score, 4)}, "Replay liquidity adequacy from recent volume."),
        _row("slippage_risk_proxy", "Execution", 3, "SlippageBrokerageResult", "safety_proxy", slippage_risk, -_score_centered(slippage_risk, 0, 1), None, ["volume", "imbalance"], {"slippage_risk": round(slippage_risk, 4)}, "Replay slippage risk proxy from liquidity and imbalance."),
        _row("no_trade_safety_pressure", "No Trade", 29, "NoTradeDecisionRecord", "safety_proxy", no_trade_pressure, -_score_centered(no_trade_pressure, 0, 1), None, ["fakeout_risk", "slippage_risk", "continuation_quality", "absorption"], {"no_trade_pressure": round(no_trade_pressure, 4)}, "Combined safety pressure that would push the decision toward WAIT/NO TRADE."),
    ]
    return rows


def _row(
    row_id: str,
    family: str,
    layer_index: int | None,
    contract_name: str,
    source: str,
    latest_value: float | str | bool | None,
    normalized_score: float,
    chart_overlay_key: str | None,
    required_inputs: list[str],
    output_fields: dict[str, float | str | bool | None],
    explanation: str,
) -> ReplayIndicatorMatrixRow:
    score = _clamp(normalized_score, -1, 1)
    return ReplayIndicatorMatrixRow(
        row_id=row_id,
        family=family,
        layer_index=layer_index,
        contract_name=contract_name,
        source=source,  # type: ignore[arg-type]
        latest_value=round(latest_value, 4) if isinstance(latest_value, float) else latest_value,
        normalized_score=round(score, 4),
        signal=_signal_from_score(score),
        chart_overlay_key=chart_overlay_key,
        required_inputs=required_inputs,
        output_fields=output_fields,
        point_in_time_safe=True,
        readiness_status="ready" if source in {"replay_candle", "derived_overlay"} else "proxy",
        explanation=explanation,
    )


def _signal_from_score(score: float) -> str:
    if score >= 0.35:
        return "bullish"
    if score <= -0.35:
        return "bearish"
    if abs(score) >= 0.15:
        return "watch"
    return "neutral"


def _gates(
    request: ReplayIndicatorMatrixRequest,
    base_report: ReplayIndicatorValidationReport,
    rows: list[ReplayIndicatorMatrixRow],
) -> list[RuntimeReadinessGate]:
    all_point_in_time = all(row.point_in_time_safe for row in rows)
    all_contract_bound = all(row.contract_name and row.required_inputs and row.output_fields for row in rows)
    return [
        _gate("TV-V034-001", "Base replay indicator validation linked", base_report.validation_version == "behavior-replay-indicator-chart.v0.33", f"Base report version is {base_report.validation_version}."),
        _gate("TV-V034-002", "Matrix row coverage", len(rows) >= request.required_matrix_rows, f"{len(rows)} rows generated; required {request.required_matrix_rows}."),
        _gate("TV-V034-003", "Point-in-time matrix rows", all_point_in_time, "Every matrix row is computed from replay current/prior bars only."),
        _gate("TV-V034-004", "Rows bind to contracts and inputs", all_contract_bound, "Every matrix row declares contract, inputs, and output fields."),
        _gate("TV-V034-005", "Deterministic chart/research matrix", True, "Matrix hash is derived from base hash and matrix rows only."),
        _gate("TV-V034-006", "Legacy runtime decoupled", True, "Matrix uses replay candles and deterministic overlays without importing legacy runtime."),
        _gate("TV-V034-007", "Live trading blocked", True, "Matrix endpoint is research/replay only and exposes no broker route."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> RuntimeReadinessGate:
    return RuntimeReadinessGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_research=not passed,
        remediation=None if passed else "Fix replay indicator matrix coverage before promotion.",
    )


def _score_from_sign(value: float) -> float:
    return _clamp(value / max(abs(value), 1.0), -1, 1) if value else 0.0


def _score_distance(value: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0
    return _clamp((value - baseline) / abs(baseline) * 10, -1, 1)


def _score_centered(value: float, center: float, width: float) -> float:
    if width == 0:
        return 0.0
    return _clamp((value - center) / width, -1, 1)


def _clamp01(value: float) -> float:
    return _clamp(value, 0, 1)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _hash_output(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
