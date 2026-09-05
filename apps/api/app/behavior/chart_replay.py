from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorChartReplayReport,
    BehaviorChartReplayRequest,
    ChartOverlaySummary,
    ChartViewport,
    MarketEvent,
    ReplayIndicatorValidationRequest,
    RuntimeReadinessGate,
    SelectedCandleEvidence,
)
from .replay_indicator_validation import build_replay_indicator_validation_report


CHART_VERSION = "behavior-chart-replay-workbench.v0.41"


def build_chart_replay_report(
    request: BehaviorChartReplayRequest,
    events: list[MarketEvent],
) -> BehaviorChartReplayReport:
    base = build_replay_indicator_validation_report(
        ReplayIndicatorValidationRequest(
            symbol=request.symbol,
            scenario_id=request.scenario_id,
            seed=request.seed,
            event_count=request.event_count,
            timeframe=request.timeframe,
        ),
        events,
    )
    selected_idx = _selected_index(request.selected_sequence_number, len(base.chart_points))
    selected_point = base.chart_points[selected_idx]
    selected_bar = base.candle_series.bars[selected_idx]
    viewport = _viewport(base.chart_points)
    overlays = _overlay_summaries(base.chart_points)
    selected_evidence = _selected_evidence(selected_bar.sequence_number, selected_point)
    output_hash = _hash_output(
        {
            "chart_version": CHART_VERSION,
            "base_output_hash": base.output_hash,
            "selected_sequence_number": selected_bar.sequence_number,
            "viewport": viewport.model_dump(mode="json"),
            "overlays": [overlay.model_dump(mode="json") for overlay in overlays],
            "selected": selected_evidence.model_dump(mode="json"),
        }
    )
    gates = _gates(base, overlays)
    return BehaviorChartReplayReport(
        chart_version=CHART_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:{CHART_VERSION}:{base.run_id}:{selected_bar.sequence_number}")),
        base_validation_version=base.validation_version,
        symbol=base.symbol,
        scenario_id=base.scenario_id,
        seed=base.seed,
        timeframe=request.timeframe,
        event_count=base.event_count,
        candle_count=base.candle_count,
        chart_point_count=base.chart_point_count,
        selected_sequence_number=selected_bar.sequence_number,
        viewport=viewport,
        chart_points=base.chart_points,
        overlays=overlays,
        selected_candle=selected_evidence,
        input_event_chain_hash=base.input_event_chain_hash,
        base_output_hash=base.output_hash,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=base.no_future_leakage,
        runtime_dependency_on_legacy_stock_app=False,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.41 is a chart workbench only; it visualizes replay/import-ready candles and indicator overlays.",
            "Selected-candle evidence is derived from the candle and current/prior indicator values only.",
            "This endpoint cannot place orders, approve trades, or connect to a broker.",
        ],
    )


def _selected_index(selected_sequence_number: int | None, point_count: int) -> int:
    if selected_sequence_number is None:
        return point_count - 1
    return max(0, min(point_count - 1, selected_sequence_number - 1))


def _viewport(points) -> ChartViewport:
    lows = [point.low for point in points]
    highs = [point.high for point in points]
    min_price = min(lows)
    max_price = max(highs)
    span = max(0.01, max_price - min_price)
    padding = span * 0.08
    return ChartViewport(
        min_price=round(max(0.01, min_price - padding), 4),
        max_price=round(max_price + padding, 4),
        min_timestamp_ns=points[0].timestamp_ns,
        max_timestamp_ns=points[-1].timestamp_ns,
        candle_count=len(points),
        price_padding_pct=8.0,
    )


def _overlay_summaries(points) -> list[ChartOverlaySummary]:
    labels = {
        "sma_3": ("SMA 3", "Short rolling mean for replay trend context."),
        "ema_5": ("EMA 5", "Fast moving average used by the replay momentum proxy."),
        "vwap": ("VWAP", "Volume-weighted intraday fair-value anchor."),
        "rsi_5": ("RSI 5", "Compact momentum oscillator for selected-candle evidence."),
        "macd_fast_slow": ("MACD Fast-Slow", "Fast minus slow EMA momentum spread."),
        "volume_z": ("Volume Z", "Local participation anomaly score."),
    }
    summaries: list[ChartOverlaySummary] = []
    for key, (label, purpose) in labels.items():
        values = [point.indicator_overlay.get(key) for point in points if point.indicator_overlay.get(key) is not None]
        summaries.append(
            ChartOverlaySummary(
                overlay_key=key,
                label=label,
                visible=key in {"ema_5", "vwap", "sma_3"},
                latest_value=round(values[-1], 4) if values else None,
                min_value=round(min(values), 4) if values else None,
                max_value=round(max(values), 4) if values else None,
                point_count=len(values),
                purpose=purpose,
            )
        )
    return summaries


def _selected_evidence(sequence_number: int, point) -> SelectedCandleEvidence:
    candle_range = max(0.0001, point.high - point.low)
    body = abs(point.close - point.open)
    upper_wick = point.high - max(point.open, point.close)
    lower_wick = min(point.open, point.close) - point.low
    clv = ((point.close - point.low) / candle_range) * 2 - 1
    direction = "bullish" if point.close > point.open else "bearish" if point.close < point.open else "neutral"
    evidence_rows = [
        f"Close {point.close:.2f} vs open {point.open:.2f} => {direction} candle.",
        f"Body uses {body / candle_range:.2%} of candle range.",
        f"Close location value is {clv:.2f}; positive means close is near high.",
    ]
    if "close_above_vwap" in point.markers:
        evidence_rows.append("Price is above VWAP on the selected candle.")
    if "close_below_vwap" in point.markers:
        evidence_rows.append("Price is below VWAP on the selected candle.")
    if "volume_expansion" in point.markers:
        evidence_rows.append("Volume expansion marker is active.")
    if "replay_absorption_proxy" in point.markers:
        evidence_rows.append("High volume with weak body creates an absorption proxy warning.")
    return SelectedCandleEvidence(
        sequence_number=sequence_number,
        timestamp_ns=point.timestamp_ns,
        candle_direction=direction,
        body_pct=round(body / candle_range, 4),
        upper_wick_pct=round(max(0.0, upper_wick) / candle_range, 4),
        lower_wick_pct=round(max(0.0, lower_wick) / candle_range, 4),
        close_location_value=round(clv, 4),
        marker_tags=point.markers,
        overlay_values=point.indicator_overlay,
        evidence_rows=evidence_rows,
        reason="Selected candle evidence explains the current chart point without using future candles.",
    )


def _gates(base, overlays: list[ChartOverlaySummary]) -> list[RuntimeReadinessGate]:
    return [
        _gate("TV-V041-001", "Base replay chart validation available", base.chart_point_count == base.candle_count, f"{base.chart_point_count} chart points from {base.candle_count} candles."),
        _gate("TV-V041-002", "Viewport bounded", base.chart_point_count > 0, "Price and time viewport created for the chart surface."),
        _gate("TV-V041-003", "Overlay summaries available", len(overlays) >= 6, f"{len(overlays)} overlay summaries generated."),
        _gate("TV-V041-004", "Selected candle evidence available", True, "Selected candle has body, wick, CLV, marker, and overlay evidence."),
        _gate("TV-V041-005", "Point-in-time chart evidence", base.no_future_leakage, "Chart evidence reuses v0.33 current/prior candle indicator calculations."),
        _gate("TV-V041-006", "Live trading blocked", True, "Chart workbench exposes no order route and keeps live trading blocked."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> RuntimeReadinessGate:
    return RuntimeReadinessGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "fail",
        evidence=evidence,
        blocks_research=not passed,
        remediation=None if passed else "Fix chart replay data before using the workbench.",
    )


def _hash_output(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
