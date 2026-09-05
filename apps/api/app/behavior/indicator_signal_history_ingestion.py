from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models import (
    IndicatorSignalHistoryIngestCurrentReport,
    IndicatorSignalHistoryIngestCurrentRequest,
    IndicatorSignalHistorySaveRequest,
    IndicatorSignalOutcomeLabelRequest,
)
from .indicator_reliability_memory import save_indicator_signal_history
from .nine_candle_hybrid import build_evidence_packet


INDICATOR_SIGNAL_HISTORY_INGEST_VERSION = "indicator-signal-history-ingestion.v1.84"


def ingest_current_indicator_signal_history(
    request: IndicatorSignalHistoryIngestCurrentRequest,
) -> IndicatorSignalHistoryIngestCurrentReport:
    packet = build_evidence_packet(request.symbol, request.timeframe, use_real_indicators=request.use_real_indicators)
    last_candle = packet.last_9_candles[-1]
    signal_time_ns = _iso_to_ns(str(last_candle["event_time"]))
    decision_time_ns = _iso_to_ns(packet.decision_time)
    close = float(last_candle["close"])
    saved = []
    skipped_missing = 0
    skipped_neutral = 0
    eligible = 0
    for sequence in packet.indicator_sequences:
        if len(saved) >= request.max_records:
            break
        if not sequence.last_9_signals or not sequence.last_9_values:
            skipped_missing += 1
            continue
        current_signal = str(sequence.last_9_signals[-1])
        current_value = sequence.last_9_values[-1]
        current_missing = bool(sequence.value_missing_mask[-1]) if sequence.value_missing_mask else current_value is None
        if current_missing or current_signal == "missing":
            skipped_missing += 1
            continue
        if current_signal == "neutral" and not request.include_neutral:
            skipped_neutral += 1
            continue
        if current_signal not in {"bullish", "bearish", "neutral"}:
            skipped_neutral += 1
            continue
        eligible += 1
        save_request = IndicatorSignalHistorySaveRequest(
            symbol=packet.symbol,
            indicator_id=sequence.indicator_id,
            timeframe=request.timeframe,
            signal_direction=current_signal,  # type: ignore[arg-type]
            signal_time_ns=signal_time_ns,
            decision_time_ns=decision_time_ns,
            session_phase=packet.session_phase,
            regime_id=packet.regime_id,
            source_snapshot_id=packet.source_snapshot_id,
            source_snapshot_hash=packet.evidence_packet_hash,
            feature_manifest_version=packet.feature_manifest_version,
            indicator_registry_version=packet.source_registry_version,
            signal_value=float(current_value) if current_value is not None else None,
            signal_strength=_signal_strength(current_value),
            missing_mask=False,
            label_request=_pending_label_request(packet.symbol, sequence.indicator_id, request.timeframe, current_signal, signal_time_ns, close, request.horizon_candles),
        )
        saved.append(save_indicator_signal_history(save_request))

    pending = [record for record in saved if record.label.label_status == "pending"]
    counted = [record for record in saved if record.counted_in_reliability]
    return IndicatorSignalHistoryIngestCurrentReport(
        ingest_version=INDICATOR_SIGNAL_HISTORY_INGEST_VERSION,
        symbol=packet.symbol,
        timeframe=request.timeframe,
        source_snapshot_id=packet.source_snapshot_id,
        source_snapshot_hash=packet.evidence_packet_hash,
        feature_manifest_version=packet.feature_manifest_version,
        indicator_registry_version=packet.source_registry_version,
        use_real_indicators=request.use_real_indicators,
        requested_indicator_count=min(len(packet.indicator_sequences), request.max_records),
        eligible_signal_count=eligible,
        saved_record_count=len(saved),
        pending_record_count=len(pending),
        counted_record_count=len(counted),
        skipped_missing_count=skipped_missing,
        skipped_neutral_count=skipped_neutral,
        saved_records=saved,
        gates=[
            _gate("IND-INGEST-001", "Closed-candle packet used", packet.closed_candle_only, "Ingestion consumed the current 9C evidence packet."),
            _gate("IND-INGEST-002", "No completed label without future horizon", len(counted) == 0, "Current ingestion writes pending labels only."),
            _gate("IND-INGEST-003", "Research-only safety preserved", True, "trade_allowed=false; order_routing_enabled=false; live_trading_blocked=true"),
        ],
        notes=[
            "v1.84 ingests current closed-candle indicator signals into persistent history as pending rows.",
            "Pending rows are audit/history evidence only and are excluded from reliability counts until a future horizon is completed.",
            "This endpoint is idempotent for the same symbol, timeframe, indicator, signal time, and horizon.",
        ],
    )


def _pending_label_request(
    symbol: str,
    indicator_id: str,
    timeframe: str,
    signal_direction: str,
    signal_time_ns: int,
    close: float,
    horizon_candles: int,
) -> IndicatorSignalOutcomeLabelRequest:
    if signal_direction == "bearish":
        stop = close * 1.01
        target = close * 0.98
    else:
        stop = close * 0.99
        target = close * 1.02
    return IndicatorSignalOutcomeLabelRequest(
        symbol=symbol,
        indicator_id=indicator_id,
        timeframe=timeframe,  # type: ignore[arg-type]
        signal_direction=signal_direction,  # type: ignore[arg-type]
        signal_time_ns=signal_time_ns,
        entry_price=round(close, 4),
        stop_price=round(stop, 4),
        target_price=round(target, 4),
        horizon_candles=horizon_candles,  # type: ignore[arg-type]
        post_signal_bars=[],
    )


def _signal_strength(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(min(abs(float(value)), 1.0), 6)


def _iso_to_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": passed, "evidence": evidence}
