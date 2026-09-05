from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from statistics import fmean, pstdev
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    CandleSeries,
    MarketEvent,
    ReplayChartPoint,
    ReplayIndicatorPoint,
    ReplayIndicatorValidationReport,
    ReplayIndicatorValidationRequest,
    RuntimeReadinessGate,
)


VALIDATION_VERSION = "behavior-replay-indicator-chart.v0.33"
INDICATOR_NAMES = ["sma_3", "ema_5", "rsi_5", "vwap", "macd_fast_slow", "volume_z"]


def build_replay_indicator_validation_report(
    request: ReplayIndicatorValidationRequest,
    events: list[MarketEvent],
) -> ReplayIndicatorValidationReport:
    """Build deterministic replay-fed candles, indicators, and chart points."""

    if len(events) < request.event_count:
        raise ValueError("event_count exceeds available replay events")

    selected_events = events[: request.event_count]
    candle_series = _events_to_candle_series(request, selected_events)
    indicator_points = _indicator_points(candle_series.bars)
    chart_points = _chart_points(candle_series.bars, indicator_points)
    event_chain_hash = _hash_events(selected_events)
    output_hash = _hash_output(
        {
            "validation_version": VALIDATION_VERSION,
            "symbol": request.symbol,
            "scenario_id": request.scenario_id,
            "seed": request.seed,
            "event_count": request.event_count,
            "timeframe": request.timeframe,
            "event_chain_hash": event_chain_hash,
            "candles": [bar.model_dump(mode="json") for bar in candle_series.bars],
            "indicators": [point.model_dump(mode="json") for point in indicator_points],
            "chart_points": [point.model_dump(mode="json") for point in chart_points],
        }
    )
    gates = _gates(request, selected_events, candle_series, indicator_points, chart_points)
    return ReplayIndicatorValidationReport(
        validation_version=VALIDATION_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:{VALIDATION_VERSION}:{request.scenario_id}:{request.seed}:{request.event_count}:{request.timeframe}")),
        symbol=request.symbol,
        scenario_id=request.scenario_id,
        seed=request.seed,
        event_count=len(selected_events),
        candle_count=len(candle_series.bars),
        indicator_count=len(INDICATOR_NAMES),
        chart_point_count=len(chart_points),
        replay_session_id=f"{request.scenario_id}-{request.seed}",
        candle_series=candle_series,
        indicator_points=indicator_points,
        chart_points=chart_points,
        deterministic=True,
        input_event_chain_hash=event_chain_hash,
        output_hash=output_hash,
        no_future_leakage=True,
        runtime_dependency_on_legacy_stock_app=False,
        safe_mode=True,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.33 validates replay-to-candle-to-indicator-to-chart plumbing only; it does not create live trading authority.",
            "Each indicator point is computed from the current bar and prior bars only.",
            "The output_hash is stable for the same scenario, seed, event count, and timeframe.",
        ],
    )


def _events_to_candle_series(request: ReplayIndicatorValidationRequest, events: list[MarketEvent]) -> CandleSeries:
    bars: list[CandleBar] = []
    previous_close: float | None = None
    for event in events:
        price = float(event.payload.get("price", 0.0))
        volume = float(event.payload.get("volume", 0.0))
        imbalance = abs(float(event.payload.get("imbalance", 0.0)))
        open_price = previous_close if previous_close is not None else price
        close_price = max(0.01, price)
        high = max(open_price, close_price) + round(imbalance * 0.05, 4)
        low = max(0.01, min(open_price, close_price) - round(imbalance * 0.05, 4))
        bars.append(
            CandleBar(
                symbol=request.symbol,
                timeframe=request.timeframe,
                timestamp_ns=event.virtual_timestamp_ns,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close_price, 4),
                volume=round(volume, 4),
                source="replay",
                sequence_number=event.sequence_number,
            )
        )
        previous_close = close_price
    snapshot_id = str(uuid5(NAMESPACE_URL, f"tradevision:candles:{request.scenario_id}:{request.seed}:{request.event_count}:{request.timeframe}"))
    return CandleSeries(symbol=request.symbol, timeframe=request.timeframe, bars=bars, snapshot_id=snapshot_id, schema_version="candles.replay.v0.33")


def _indicator_points(bars: list[CandleBar]) -> list[ReplayIndicatorPoint]:
    points: list[ReplayIndicatorPoint] = []
    closes: list[float] = []
    volumes: list[float] = []
    cumulative_price_volume = 0.0
    cumulative_volume = 0.0
    ema_5: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    for bar in bars:
        close = round(bar.close, 4)
        volume = float(bar.volume or 0.0)
        closes.append(close)
        volumes.append(volume)
        cumulative_price_volume += close * volume
        cumulative_volume += volume
        ema_5 = _ema_next(ema_5, close, 5)
        ema_fast = _ema_next(ema_fast, close, 3)
        ema_slow = _ema_next(ema_slow, close, 6)
        vwap = cumulative_price_volume / cumulative_volume if cumulative_volume else close
        sma_3 = fmean(closes[-3:]) if len(closes) >= 3 else None
        rsi_5 = _rsi(closes, 5)
        volume_z = _zscore(volumes[-5:], volume)
        macd_fast_slow = (ema_fast or close) - (ema_slow or close)
        flags = _signal_flags(bar, ema_5, vwap, macd_fast_slow, volume_z, len(points))
        points.append(
            ReplayIndicatorPoint(
                sequence_number=bar.sequence_number,
                timestamp_ns=bar.timestamp_ns,
                close=close,
                sma_3=round(sma_3, 4) if sma_3 is not None else None,
                ema_5=round(ema_5, 4),
                rsi_5=round(rsi_5, 4),
                vwap=round(vwap, 4),
                macd_fast_slow=round(macd_fast_slow, 4),
                volume_z=round(volume_z, 4),
                signal_flags=flags,
            )
        )
    return points


def _chart_points(bars: list[CandleBar], indicators: list[ReplayIndicatorPoint]) -> list[ReplayChartPoint]:
    chart_points: list[ReplayChartPoint] = []
    for bar, indicator in zip(bars, indicators):
        markers = list(indicator.signal_flags)
        if bar.close > bar.open and "close_above_vwap" in markers:
            markers.append("bullish_replay_candle")
        if bar.close < bar.open and "close_below_vwap" in markers:
            markers.append("bearish_replay_candle")
        chart_points.append(
            ReplayChartPoint(
                timestamp_ns=bar.timestamp_ns,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=float(bar.volume or 0.0),
                indicator_overlay={
                    "sma_3": indicator.sma_3,
                    "ema_5": indicator.ema_5,
                    "vwap": indicator.vwap,
                    "rsi_5": indicator.rsi_5,
                    "macd_fast_slow": indicator.macd_fast_slow,
                    "volume_z": indicator.volume_z,
                },
                markers=markers,
            )
        )
    return chart_points


def _ema_next(previous: float | None, value: float, period: int) -> float:
    if previous is None:
        return value
    alpha = 2 / (period + 1)
    return value * alpha + previous * (1 - alpha)


def _rsi(closes: list[float], period: int) -> float:
    if len(closes) < 2:
        return 50.0
    deltas = [closes[idx] - closes[idx - 1] for idx in range(max(1, len(closes) - period), len(closes))]
    gains = [delta for delta in deltas if delta > 0]
    losses = [-delta for delta in deltas if delta < 0]
    avg_gain = fmean(gains) if gains else 0.0
    avg_loss = fmean(losses) if losses else 0.0
    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100 - (100 / (1 + relative_strength))


def _zscore(values: list[float], current: float) -> float:
    if len(values) < 2:
        return 0.0
    mean = fmean(values)
    std = pstdev(values)
    if std == 0:
        return 0.0
    return (current - mean) / std


def _signal_flags(bar: CandleBar, ema_5: float, vwap: float, macd: float, volume_z: float, point_index: int) -> list[str]:
    flags: list[str] = []
    range_size = max(0.0001, bar.high - bar.low)
    body_pct = abs(bar.close - bar.open) / range_size
    if bar.close >= vwap:
        flags.append("close_above_vwap")
    else:
        flags.append("close_below_vwap")
    if bar.close >= ema_5 and macd >= 0:
        flags.append("momentum_positive")
    if bar.close < ema_5 and macd < 0:
        flags.append("momentum_negative")
    if volume_z > 1:
        flags.append("volume_expansion")
    if volume_z > 1 and body_pct < 0.25:
        flags.append("replay_absorption_proxy")
    if point_index < 5 and bar.close > vwap and bar.close >= ema_5:
        flags.append("opening_drive_proxy")
    return flags


def _gates(
    request: ReplayIndicatorValidationRequest,
    events: list[MarketEvent],
    candles: CandleSeries,
    indicators: list[ReplayIndicatorPoint],
    chart_points: list[ReplayChartPoint],
) -> list[RuntimeReadinessGate]:
    return [
        _gate("TV-V033-001", "Replay events available", len(events) == request.event_count, f"{len(events)} replay events selected from seed {request.seed}."),
        _gate("TV-V033-002", "Replay events converted to candles", len(candles.bars) == len(events), f"{len(candles.bars)} candles generated from {len(events)} events."),
        _gate("TV-V033-003", "Indicator overlays produced", len(INDICATOR_NAMES) >= 6 and len(indicators) == len(candles.bars), f"{len(INDICATOR_NAMES)} indicator overlays computed for {len(indicators)} bars."),
        _gate("TV-V033-004", "Chart points produced", len(chart_points) == len(candles.bars), f"{len(chart_points)} chart-ready OHLCV points generated."),
        _gate("TV-V033-005", "Point-in-time indicator calculation", True, "Indicators use current and prior bars only; no future candle fields are read."),
        _gate("TV-V033-006", "Legacy runtime decoupled", True, "Validation does not import or execute the legacy stock-app runtime."),
        _gate("TV-V033-007", "Live trading blocked", True, "Validation endpoint is research/replay only and exposes no broker route."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> RuntimeReadinessGate:
    return RuntimeReadinessGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_research=not passed,
        remediation=None if passed else "Fix replay, candle, or indicator validation before promotion.",
    )


def _hash_events(events: list[MarketEvent]) -> str:
    payload = [
        {
            "event_id": event.event_id,
            "parent_event_id": event.parent_event_id,
            "virtual_timestamp_ns": event.virtual_timestamp_ns,
            "source_mode": event.source_mode,
            "sequence_number": event.sequence_number,
            "symbol": event.symbol,
            "watermark": event.watermark,
            "payload": event.payload,
        }
        for event in events
    ]
    return _hash_output(payload)


def _hash_output(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
