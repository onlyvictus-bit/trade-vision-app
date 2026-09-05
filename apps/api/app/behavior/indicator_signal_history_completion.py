from __future__ import annotations

from typing import Any

from ..models import (
    IndicatorSignalHistoryCompletePendingReport,
    IndicatorSignalHistoryCompletePendingRequest,
    IndicatorSignalHistoryRecord,
    IndicatorSignalHistorySaveRequest,
    IndicatorSignalOutcomeLabelRequest,
)
from ..storage import list_indicator_signal_history_records
from .indicator_reliability_memory import save_indicator_signal_history


INDICATOR_SIGNAL_HISTORY_COMPLETION_VERSION = "indicator-signal-history-completion.v1.85"


def complete_pending_indicator_signal_history(
    request: IndicatorSignalHistoryCompletePendingRequest,
) -> IndicatorSignalHistoryCompletePendingReport:
    records = list_indicator_signal_history_records(
        symbol=request.symbol.upper(),
        indicator_id=request.indicator_id,
        timeframe=request.timeframe,
        limit=request.limit,
    )
    pending = [
        record
        for record in records
        if record.label.label_status == "pending"
        and (request.history_id is None or record.history_id == request.history_id)
    ]
    completed: list[IndicatorSignalHistoryRecord] = []
    still_pending: list[IndicatorSignalHistoryRecord] = []
    skipped = 0
    for record in pending:
        future_bars = [bar for bar in request.post_signal_bars if bar.timestamp_ns > record.signal_time_ns]
        if not future_bars:
            still_pending.append(record)
            continue
        save_request = IndicatorSignalHistorySaveRequest(
            symbol=record.symbol,
            indicator_id=record.indicator_id,
            timeframe=record.timeframe,
            signal_direction=record.signal_direction,
            signal_time_ns=record.signal_time_ns,
            decision_time_ns=record.decision_time_ns,
            session_phase=record.session_phase,
            regime_id=record.regime_id,
            source_snapshot_id=record.source_snapshot_id,
            source_snapshot_hash=record.source_snapshot_hash,
            feature_manifest_version=record.feature_manifest_version,
            indicator_registry_version=record.indicator_registry_version,
            signal_value=record.signal_value,
            signal_strength=record.signal_strength,
            missing_mask=record.missing_mask,
            label_request=IndicatorSignalOutcomeLabelRequest(
                symbol=record.symbol,
                indicator_id=record.indicator_id,
                timeframe=record.timeframe,
                signal_direction=record.signal_direction,
                signal_time_ns=record.signal_time_ns,
                entry_price=request.entry_price,
                stop_price=request.stop_price,
                target_price=request.target_price,
                horizon_candles=record.label.horizon_candles,
                post_signal_bars=future_bars,
                has_lower_timeframe_sequence=request.has_lower_timeframe_sequence,
            ),
        )
        updated = save_indicator_signal_history(save_request)
        if updated.label.label_status == "complete":
            completed.append(updated)
        else:
            still_pending.append(updated)

    if request.history_id is not None and not pending:
        skipped = 1
    return IndicatorSignalHistoryCompletePendingReport(
        completion_version=INDICATOR_SIGNAL_HISTORY_COMPLETION_VERSION,
        symbol=request.symbol.upper(),
        indicator_id=request.indicator_id,
        timeframe=request.timeframe,
        scanned_pending_count=len(pending),
        completed_count=len(completed),
        still_pending_count=len(still_pending),
        skipped_count=skipped,
        completed_records=completed,
        still_pending_records=still_pending,
        gates=[
            _gate("IND-COMPLETE-001", "Only pending rows scanned", True, f"pending_scanned={len(pending)}"),
            _gate("IND-COMPLETE-002", "Future bars supplied by caller", bool(request.post_signal_bars), f"future_bar_count={len(request.post_signal_bars)}"),
            _gate("IND-COMPLETE-003", "Completed rows become reliability-countable only after horizon closes", all(record.counted_in_reliability for record in completed), f"completed={len(completed)}"),
            _gate("IND-COMPLETE-004", "Research-only safety preserved", True, "trade_allowed=false; order_routing_enabled=false; live_trading_blocked=true"),
        ],
        notes=[
            "v1.85 completes pending indicator history only from explicitly supplied future bars.",
            "Rows stay pending when the supplied future bars do not complete the stored horizon.",
            "Same-bar target/stop ambiguity is handled by the existing conservative stop-first labeler.",
        ],
    )


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"gate_id": gate_id, "name": name, "passed": passed, "evidence": evidence}
