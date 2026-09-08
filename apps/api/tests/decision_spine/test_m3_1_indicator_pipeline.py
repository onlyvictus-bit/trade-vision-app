from __future__ import annotations

import json

import pytest

from app.behavior import real_indicator_adapter as adapter
from app.behavior.real_indicator_adapter import (
    INDICATOR_EVIDENCE_VERSION,
    build_indicator_evidence_summary,
    clear_real_indicator_runtime_cache,
    compute_real_indicator_outputs_with_telemetry,
)


def _candles(count: int = 40, *, volume: float | None = 100_000.0):
    return [
        {
            "event_time": f"2026-09-08 09:{15 + i:02d}:00" if i < 45 else f"2026-09-08 10:{i - 45:02d}:00",
            "open": 100.0 + i * 0.1,
            "high": 100.2 + i * 0.1,
            "low": 99.9 + i * 0.1,
            "close": 100.1 + i * 0.1,
            "volume": volume,
        }
        for i in range(count)
    ]


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_real_indicator_runtime_cache()
    yield
    clear_real_indicator_runtime_cache()


def _patch_compute(monkeypatch, payload_by_id):
    from app.vendor.stock_app.shared.indicators import self_indc

    def fake_compute(df, keys, params=None):
        return {key: payload_by_id.get(key) for key in keys}

    monkeypatch.setattr(self_indc, "compute_selected", fake_compute)


def test_m31d_001_computed_evidence_is_d2_bound_and_zero_authority(monkeypatch):
    _patch_compute(monkeypatch, {"si_rsi_div": {"direction": "bull", "strength": 0.6, "value": 57.2}})
    outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(),
        ["si_rsi_div"],
        source_snapshot_hash="a" * 64,
        source_timeframe="5m",
    )
    assert "si_rsi_div" in outputs
    row = telemetry[0]
    evidence = row["evidence"]
    assert row["status"] == "computed"
    assert row["canonical_status"] == "COMPUTED"
    assert evidence["source_snapshot_hash"] == "a" * 64
    assert evidence["source_timeframe"] == "5m"
    assert evidence["direction"] == "bullish"
    assert evidence["strength"] == 0.6
    assert evidence["calculation_version"] == INDICATOR_EVIDENCE_VERSION
    assert evidence["used_for_probability"] is False
    assert evidence["may_set_final_band"] is False
    assert evidence["may_execute"] is False


def test_m31d_002_insufficient_warmup_is_not_neutral_zero(monkeypatch):
    _patch_compute(monkeypatch, {"si_cdl": []})
    outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(5), ["si_cdl"], source_snapshot_hash="b" * 64, source_timeframe="5m"
    )
    assert outputs == {}
    evidence = telemetry[0]["evidence"]
    assert telemetry[0]["status"] == "insufficient_warmup"
    assert evidence["status"] == "INSUFFICIENT_WARMUP"
    assert evidence["reason_code"] == "INSUFFICIENT_BARS"
    assert evidence["value"] is None
    assert evidence["strength"] is None
    assert evidence["direction"] == "unknown"


def test_m31d_003_no_signal_is_distinct_from_no_output(monkeypatch):
    _patch_compute(monkeypatch, {"si_cdl": [], "si_rsi_div": {}})
    _, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(40), ["si_cdl", "si_rsi_div"]
    )
    by_id = {row["indicator_id"]: row for row in telemetry}
    assert by_id["si_cdl"]["canonical_status"] == "NO_SIGNAL"
    assert by_id["si_cdl"]["evidence"]["reason_code"] == "NO_SIGNAL"
    assert by_id["si_rsi_div"]["canonical_status"] == "NO_OUTPUT"
    assert by_id["si_rsi_div"]["evidence"]["reason_code"] == "NO_OUTPUT"


def test_m31d_004_missing_volume_dependency_is_unavailable_not_zero(monkeypatch):
    _patch_compute(monkeypatch, {"si_vwap_conf": {"direction": "bull"}})
    outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(40, volume=None),
        ["si_vwap_conf"],
        source_snapshot_hash="f" * 64,
        source_timeframe="5m",
    )
    assert outputs == {}
    evidence = telemetry[0]["evidence"]
    assert telemetry[0]["status"] == "dependency_unavailable"
    assert evidence["status"] == "DEPENDENCY_UNAVAILABLE"
    assert evidence["reason_code"] == "DEPENDENCY_UNAVAILABLE"
    assert evidence["value"] is None


def test_m31d_005_calculation_error_is_explicit_and_not_output(monkeypatch):
    from app.vendor.stock_app.shared.indicators import self_indc

    def explode(df, keys, params=None):
        raise RuntimeError("forced-indicator-failure")

    monkeypatch.setattr(self_indc, "compute_selected", explode)
    outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"]
    )
    assert outputs == {}
    assert telemetry[0]["status"] == "error"
    assert telemetry[0]["canonical_status"] == "ERROR"
    assert telemetry[0]["evidence"]["reason_code"] == "CALCULATION_ERROR"
    assert "forced-indicator-failure" in telemetry[0]["error"]


def test_m31d_006_slow_runtime_is_blocked_not_usable(monkeypatch):
    _patch_compute(monkeypatch, {"si_rsi_div": {"direction": "bull"}})
    ticks = iter([100.0, 100.901])
    monkeypatch.setattr(adapter.time, "perf_counter", lambda: next(ticks))
    outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"]
    )
    assert outputs == {}
    assert telemetry[0]["status"] == "slow_blocked"
    assert telemetry[0]["canonical_status"] == "SLOW_BLOCKED"
    assert telemetry[0]["evidence"]["reason_code"] == "LATENCY_BLOCK"


def test_m31d_007_cache_replay_preserves_evidence_hash(monkeypatch):
    calls = {"count": 0}
    from app.vendor.stock_app.shared.indicators import self_indc

    def fake_compute(df, keys, params=None):
        calls["count"] += 1
        return {key: {"direction": "bull", "value": 1.0} for key in keys}

    monkeypatch.setattr(self_indc, "compute_selected", fake_compute)
    first_outputs, first = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], source_snapshot_hash="c" * 64, source_timeframe="5m"
    )
    second_outputs, second = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], source_snapshot_hash="c" * 64, source_timeframe="5m"
    )
    assert calls["count"] == 1
    assert first_outputs == second_outputs
    assert first[0]["cache_hit"] is False
    assert second[0]["cache_hit"] is True
    assert first[0]["evidence_hash"] == second[0]["evidence_hash"]
    assert second[0]["latency_ms"] == 0.0


def test_m31d_008_parameter_identity_changes_cache_and_evidence(monkeypatch):
    calls = {"count": 0}
    from app.vendor.stock_app.shared.indicators import self_indc

    def fake_compute(df, keys, params=None):
        calls["count"] += 1
        return {key: {"direction": "bull", "value": 1.0} for key in keys}

    monkeypatch.setattr(self_indc, "compute_selected", fake_compute)
    _, first = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], parameters_by_indicator={"si_rsi_div": {"length": 14}}
    )
    _, second = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], parameters_by_indicator={"si_rsi_div": {"length": 20}}
    )
    assert calls["count"] == 2
    assert first[0]["evidence"]["parameter_hash"] != second[0]["evidence"]["parameter_hash"]
    assert first[0]["evidence_hash"] != second[0]["evidence_hash"]


def test_m31d_009_one_dataframe_build_is_accounted_for_batch(monkeypatch):
    _patch_compute(
        monkeypatch,
        {
            "si_rsi_div": {"direction": "bull"},
            "si_macd_ta": {"direction": "bear"},
            "si_trend_sig": {"direction": "bull"},
        },
    )
    _, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div", "si_macd_ta", "si_trend_sig"]
    )
    assert len(telemetry) == 3
    assert all(
        row["runtime_audit"]["indicator_dataframe_build_count"] == 1
        for row in telemetry
    )
    summary = build_indicator_evidence_summary(telemetry)
    assert summary["operational"]["indicator_dataframe_build_count"] == 1


def test_m31d_010_family_and_correlation_metadata_prevent_vote_masquerade(monkeypatch):
    _patch_compute(
        monkeypatch,
        {
            "si_rsi_div": {"direction": "bull"},
            "si_rsi_ss": {"direction": "bull"},
            "si_trend_sig": {"direction": "bull"},
        },
    )
    _, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div", "si_rsi_ss", "si_trend_sig"]
    )
    by_id = {row["indicator_id"]: row["evidence"] for row in telemetry}
    assert by_id["si_rsi_div"]["correlation_group"] == "momentum-rsi"
    assert by_id["si_rsi_ss"]["correlation_group"] == "momentum-rsi"
    assert by_id["si_trend_sig"]["correlation_group"] == "trend-moving-average"
    summary = build_indicator_evidence_summary(telemetry)
    assert summary["correlation_group_counts"]["momentum-rsi"] == 2
    assert summary["correlation_group_counts"]["trend-moving-average"] == 1


def test_m31d_011_same_facts_same_canonical_summary_hash_across_cache_state(monkeypatch):
    _patch_compute(monkeypatch, {"si_rsi_div": {"direction": "bull", "value": 55.0}})
    _, cold = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], source_snapshot_hash="d" * 64, source_timeframe="5m"
    )
    _, warm = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], source_snapshot_hash="d" * 64, source_timeframe="5m"
    )
    cold_summary = build_indicator_evidence_summary(cold)
    warm_summary = build_indicator_evidence_summary(warm)
    assert cold_summary["canonical_evidence_hash"] == warm_summary["canonical_evidence_hash"]
    assert cold_summary["operational"]["cache_hit_count"] == 0
    assert warm_summary["operational"]["cache_hit_count"] == 1


def test_m31d_012_canonical_evidence_is_bounded(monkeypatch):
    huge_payload = {
        "direction": "bull",
        "strength": 0.7,
        "values": list(range(10_000)),
        "signals": [{"direction": "bull", "name": "x"}] * 1000,
    }
    _patch_compute(monkeypatch, {"si_rsi_div": huge_payload})
    _, telemetry = compute_real_indicator_outputs_with_telemetry(
        _candles(), ["si_rsi_div"], source_snapshot_hash="e" * 64, source_timeframe="5m"
    )
    evidence = telemetry[0]["evidence"]
    encoded = json.dumps(evidence, sort_keys=True)
    assert len(encoded.encode("utf-8")) < 4096
    assert "values" not in evidence
    assert "signals" not in evidence
