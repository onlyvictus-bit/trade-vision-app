from __future__ import annotations

import app.behavior.decision_spine.canonical_pta_marker_runtime as pta_runtime


H1 = "1" * 64


def _candles():
    return [
        {
            "event_time": f"2026-09-09T09:{15 + index:02d}:00+05:30",
            "open": 100.0 + index,
            "high": 101.0 + index,
            "low": 99.0 + index,
            "close": 100.5 + index,
            "volume": 1000 + index * 10,
        }
        for index in range(20)
    ]


def test_pta_marker_receipt_binds_snapshot_and_bounds_events(monkeypatch):
    def fake_runtime(candles, indicator_ids):
        outputs = {indicator_ids[0]: [{"time": str(index), "direction": "bullish"} for index in range(50)]}
        telemetry = [
            {
                "indicator_id": indicator_ids[0],
                "status": "computed",
                "event_count": 50,
                "used_for_probability": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
            }
        ]
        return outputs, telemetry, {"dependency_available": True}

    monkeypatch.setattr(pta_runtime, "compute_pta_marker_outputs_with_telemetry", fake_runtime)
    result = pta_runtime.build_canonical_pta_marker_evidence(
        candles=_candles(),
        indicator_ids=("pta_a",),
        source_snapshot_hash=H1,
        source_timeframe="5m",
    )
    assert result.source_snapshot_hash == H1
    assert result.observations[0].event_count == 50
    assert len(result.observations[0].bounded_events) == pta_runtime.MAX_EVENTS_PER_INDICATOR
    assert result.used_for_probability is False
    assert result.may_set_final_band is False
    assert result.may_execute is False


def test_pta_dependency_unavailable_degrades_without_neutral_default(monkeypatch):
    def fake_runtime(candles, indicator_ids):
        return {}, [
            {
                "indicator_id": indicator_ids[0],
                "status": "dependency_unavailable",
                "event_count": 0,
            }
        ], {"dependency_available": False}

    monkeypatch.setattr(pta_runtime, "compute_pta_marker_outputs_with_telemetry", fake_runtime)
    result = pta_runtime.build_canonical_pta_marker_evidence(
        candles=_candles(),
        indicator_ids=("pta_a",),
        source_snapshot_hash=H1,
        source_timeframe="5m",
    )
    assert result.availability == "DEGRADED"
    assert result.observations[0].reason_code == "DEPENDENCY_UNAVAILABLE"
    assert result.computed_count == 0
    assert result.trade_allowed is False
    assert result.order_routing_enabled is False
