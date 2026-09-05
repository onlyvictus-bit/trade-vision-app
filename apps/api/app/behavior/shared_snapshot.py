from __future__ import annotations

import hashlib
import json
import random
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    CandleSeries,
    KronosForecastRequest,
    KronosSharedSnapshotForecastReport,
    KronosSnapshotReceipt,
    SharedAnalysisSnapshot,
    SharedSnapshotRequest,
    TwinSnapshotIntegrity,
    now_iso,
)
from .kronos_proxy import KRONOS_VERSION, build_kronos_forecast_with_optional_service
from .point_in_time_guard import timeframe_duration_ns


SHARED_SNAPSHOT_VERSION = "shared-analysis-snapshot.v0.66"
KRONOS_SNAPSHOT_RECEIPT_VERSION = "kronos-snapshot-receipt.v0.66"
TWIN_SNAPSHOT_INTEGRITY_VERSION = "twin-snapshot-integrity.v0.66"


def build_shared_snapshot(request: SharedSnapshotRequest | None = None) -> tuple[SharedAnalysisSnapshot, CandleSeries]:
    payload = request or SharedSnapshotRequest()
    series = payload.series or _synthetic_series(payload.symbol, payload.timeframe, payload.seed, payload.lookback_candles)
    bars = sorted(series.bars, key=lambda bar: bar.timestamp_ns)[-payload.lookback_candles :]
    duration_ns = timeframe_duration_ns(payload.timeframe)
    decision_time_ns = payload.decision_time_ns or (bars[-1].timestamp_ns + duration_ns)
    closed_bars = [
        bar
        for bar in bars
        if bar.timestamp_ns + duration_ns <= decision_time_ns
    ]
    if not closed_bars:
        raise ValueError("Shared snapshot requires at least one fully closed candle")
    last_bar_timestamp_ns = closed_bars[-1].timestamp_ns
    normalized_series = CandleSeries(
        symbol=series.symbol.upper(),
        timeframe=series.timeframe,
        bars=closed_bars,
        snapshot_id=series.snapshot_id,
        schema_version=series.schema_version,
    )
    source_hash = canonical_snapshot_hash(normalized_series)
    snapshot_id = str(uuid5(NAMESPACE_URL, f"tradevision:shared-snapshot:{normalized_series.symbol}:{normalized_series.timeframe}:{decision_time_ns}:{source_hash}"))
    snapshot = SharedAnalysisSnapshot(
        snapshot_id=snapshot_id,
        symbol=normalized_series.symbol,
        timeframe=normalized_series.timeframe,
        decision_time_ns=decision_time_ns,
        last_bar_timestamp_ns=last_bar_timestamp_ns,
        closed_ohlcv_bars=closed_bars,
        source_snapshot_hash=source_hash,
        corporate_action_version=payload.corporate_action_version,
        calendar_version=payload.calendar_version,
        immutable=True,
        point_in_time_safe=True,
    )
    series_for_engines = normalized_series.model_copy(update={"snapshot_id": snapshot.snapshot_id})
    return snapshot, series_for_engines


def build_kronos_shared_snapshot_forecast(request: SharedSnapshotRequest | None = None) -> KronosSharedSnapshotForecastReport:
    payload = request or SharedSnapshotRequest()
    snapshot, series = build_shared_snapshot(payload)
    kronos_request = KronosForecastRequest(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        seed=payload.seed,
        lookback_candles=len(snapshot.closed_ohlcv_bars),
        forecast_horizon_bars=payload.forecast_horizon_bars,
        decision_time_ns=snapshot.decision_time_ns + (1 if payload.force_decision_time_mismatch else 0),
        series=series,
        replay_snapshot_id=snapshot.snapshot_id,
        model_name=payload.model_name,
    )
    forecast = build_kronos_forecast_with_optional_service(kronos_request, series)
    receipt_hash = forecast.input_snapshot_hash
    if payload.force_kronos_hash_mismatch:
        receipt_hash = "forced-mismatch-" + receipt_hash[:48]
    receipt = KronosSnapshotReceipt(
        receipt_version=KRONOS_SNAPSHOT_RECEIPT_VERSION,
        snapshot_id=snapshot.snapshot_id,
        source_snapshot_hash=snapshot.source_snapshot_hash,
        kronos_input_snapshot_id=forecast.input_snapshot_id,
        kronos_input_snapshot_hash=receipt_hash,
        decision_time_ns=forecast.input_validation.decision_time_ns,
        last_bar_timestamp_ns=series.bars[-1].timestamp_ns if series.bars else None,
        forecast_run_id=forecast.run_id,
        identity_echo_complete=bool(forecast.input_snapshot_id and forecast.input_snapshot_hash and forecast.input_validation.decision_time_ns),
        kronos_cannot_execute_orders=True,
        kronos_cannot_override_no_trade=True,
        kronos_cannot_override_risk=True,
    )
    integrity = verify_twin_snapshot_integrity(snapshot, receipt)
    return KronosSharedSnapshotForecastReport(
        report_version=f"{SHARED_SNAPSHOT_VERSION}.kronos-forecast",
        generated_at=now_iso(),
        snapshot=snapshot,
        kronos_forecast=forecast.model_copy(update={"input_snapshot_hash": receipt_hash}),
        receipt=receipt,
        integrity=integrity,
        behavior_can_continue_without_kronos=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "v0.66 forces Trade Vision and Kronos to consume the same immutable OHLCV snapshot.",
            "Twin comparison fails closed when snapshot_id, source_snapshot_hash, decision_time_ns, or last_bar_timestamp_ns differ.",
            "Behavior analysis may continue without a Kronos confidence boost when Kronos identity fails.",
        ],
    )


def verify_twin_snapshot_integrity(snapshot: SharedAnalysisSnapshot, receipt: KronosSnapshotReceipt) -> TwinSnapshotIntegrity:
    mismatches: list[str] = []
    if receipt.kronos_input_snapshot_id != snapshot.snapshot_id:
        mismatches.append("snapshot_id")
    if receipt.kronos_input_snapshot_hash != snapshot.source_snapshot_hash:
        mismatches.append("source_snapshot_hash")
    if receipt.decision_time_ns != snapshot.decision_time_ns:
        mismatches.append("decision_time_ns")
    if receipt.last_bar_timestamp_ns != snapshot.last_bar_timestamp_ns:
        mismatches.append("last_bar_timestamp_ns")
    identity_match = not mismatches and receipt.identity_echo_complete
    return TwinSnapshotIntegrity(
        integrity_version=TWIN_SNAPSHOT_INTEGRITY_VERSION,
        generated_at=now_iso(),
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        snapshot_id=snapshot.snapshot_id,
        source_snapshot_hash=snapshot.source_snapshot_hash,
        decision_time_ns=snapshot.decision_time_ns,
        last_bar_timestamp_ns=snapshot.last_bar_timestamp_ns,
        kronos_receipt=receipt,
        identity_match=identity_match,
        mismatch_fields=mismatches,
        fail_closed=not identity_match,
        twin_comparison_allowed=identity_match,
        arbiter_action="RESEARCH_COMPARE_ALLOWED" if identity_match else "WAIT",
        reason="Shared snapshot identity matched; research comparison may proceed." if identity_match else f"Snapshot identity mismatch: {', '.join(mismatches)}. Twin must fail closed.",
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "This integrity report is required before Twin may compare Behavior and Kronos.",
            "A pass does not permit trading; it only permits research comparison.",
        ],
    )


def canonical_snapshot_hash(series: CandleSeries) -> str:
    sorted_bars = sorted(series.bars, key=lambda bar: bar.timestamp_ns)
    payload = {
        "symbol": series.symbol,
        "timeframe": series.timeframe,
        "bars": [bar.model_dump(mode="json") for bar in sorted_bars],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _synthetic_series(symbol: str, timeframe: str, seed: int, bars: int) -> CandleSeries:
    rng = random.Random(f"shared-snapshot:{symbol}:{timeframe}:{seed}")
    interval = _timeframe_ns(timeframe) or 300_000_000_000
    base = 1_714_724_800_000_000_000
    price = 100.0 + rng.uniform(-0.8, 0.8)
    candle_bars: list[CandleBar] = []
    for idx in range(bars):
        open_price = price
        close = max(1.0, open_price + rng.uniform(-0.28, 0.34))
        high = max(open_price, close) + rng.uniform(0.05, 0.42)
        low = min(open_price, close) - rng.uniform(0.05, 0.42)
        candle_bars.append(
            CandleBar(
                symbol=symbol.upper(),
                timeframe=timeframe,  # type: ignore[arg-type]
                timestamp_ns=base + idx * interval,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=1_200 + idx * 13,
                source="mock",
                sequence_number=idx + 1,
            )
        )
        price = close
    return CandleSeries(
        symbol=symbol.upper(),
        timeframe=timeframe,  # type: ignore[arg-type]
        bars=candle_bars,
        snapshot_id=f"shared-snapshot-seed-{seed}",
        schema_version=f"candles.shared.{KRONOS_VERSION}.v1",
    )


def _timeframe_ns(timeframe: str) -> int | None:
    return {
        "1m": 60_000_000_000,
        "3m": 180_000_000_000,
        "5m": 300_000_000_000,
        "15m": 900_000_000_000,
        "30m": 1_800_000_000_000,
        "1H": 3_600_000_000_000,
        "4H": 14_400_000_000_000,
        "daily": 86_400_000_000_000,
        "1D": 86_400_000_000_000,
        "weekly": 604_800_000_000_000,
        "1W": 604_800_000_000_000,
    }.get(timeframe)
