from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
from time import perf_counter
from zoneinfo import ZoneInfo

import pytest

from app.behavior.decision_spine.canonical_level_graph_v2 import (
    CANONICAL_LEVEL_GRAPH_V2_VERSION,
    CanonicalLevelGraphV2Error,
    build_canonical_level_graph_v2,
)
from app.behavior.decision_spine.canonical_level_intelligence import build_canonical_level_intelligence
from app.behavior.decision_spine.market_primitive_kernel_v2 import build_market_primitive_kernel_v2
from app.behavior.decision_spine.snapshot_feature_kernel import build_snapshot_feature_kernel
from app.behavior.point_in_time_guard import timeframe_duration_ns
from app.models import CandleBar, CandleSeries, ClosedCandleSnapshot, VwapOrbCprContextRequest

IST = ZoneInfo("Asia/Kolkata")
PREVIOUS_DAY = date(2026, 9, 4)
CURRENT_DAY = date(2026, 9, 7)


def _ns(day: date, hour: int = 9, minute: int = 15) -> int:
    return int(datetime.combine(day, time(hour, minute), tzinfo=IST).timestamp() * 1_000_000_000)


def _rows(day: date, *, count: int, seq: int, base: float, missing: int | None = None):
    duration = timeframe_duration_ns("5m")
    out = []
    for i in range(count):
        op = base + i * 0.08
        close = op + (0.05 if i % 3 else -0.02)
        out.append(CandleBar(symbol="RELIANCE", timeframe="5m", timestamp_ns=_ns(day)+i*duration,
            open=op, high=max(op, close)+0.18, low=min(op, close)-0.16, close=close,
            volume=None if i == missing else 100_000+i*250, source="user_csv", sequence_number=seq+i))
    return out


def _snapshot(*, missing_current: int | None = None, hash_override: str | None = None):
    previous = _rows(PREVIOUS_DAY, count=75, seq=1, base=80.0)
    current = _rows(CURRENT_DAY, count=18, seq=76, base=100.0, missing=missing_current)
    rows = previous + current
    duration = timeframe_duration_ns("5m")
    end = rows[-1].timestamp_ns + duration
    digest = hashlib.sha256(json.dumps([x.model_dump(mode="json") for x in rows], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ClosedCandleSnapshot(snapshot_version="closed-candle-snapshot.v1.87", snapshot_id="e-test",
        snapshot_hash=hash_override or digest, symbol="RELIANCE", timeframe="5m", decision_time_ns=end,
        decision_time=datetime.fromtimestamp(end/1_000_000_000, tz=timezone.utc).isoformat(), timezone_offset_minutes=330,
        bar_count=len(rows), first_bar_timestamp_ns=rows[0].timestamp_ns, last_bar_timestamp_ns=rows[-1].timestamp_ns,
        last_bar_close_time_ns=end, closed_ohlcv_bars=rows, source_schema_version="candles.v1", immutable=True,
        closed_candle_only=True, point_in_time_safe=True)


def _build(snapshot=None, **kwargs):
    s = snapshot or _snapshot()
    observed = build_snapshot_feature_kernel(s)
    primitive = build_market_primitive_kernel_v2(observed)
    series = CandleSeries(symbol=s.symbol, timeframe=s.timeframe, bars=s.closed_ohlcv_bars,
                          snapshot_id=s.snapshot_id, schema_version=s.source_schema_version)
    levels = build_canonical_level_intelligence(VwapOrbCprContextRequest(series=series, decision_time_ns=s.decision_time_ns),
                                                feature_kernel=observed)
    graph = build_canonical_level_graph_v2(levels, primitive, observed, **kwargs)
    return graph, levels, primitive, observed


def test_e001_zero_authority_and_versioned_provenance():
    g, levels, primitive, _ = _build()
    assert g.calculation_version == CANONICAL_LEVEL_GRAPH_V2_VERSION
    assert g.source_level_hash == levels.provenance.canonical_level_hash
    assert g.source_primitive_hash == primitive.primitive_hash
    assert not g.used_for_probability and not g.may_set_final_band and not g.may_execute
    assert not g.trade_allowed and not g.order_routing_enabled and g.live_trading_blocked and g.human_approval_required


def test_e002_consumes_locked_canonical_level_sources_without_recreating_them():
    g, levels, *_ = _build()
    by_source = {n.source: n for n in g.nodes}
    assert by_source["SESSION_VWAP"].price == pytest.approx(levels.session_vwap.value)
    assert by_source["OR15_HIGH"].price == pytest.approx(levels.opening_range(15).high)
    assert by_source["PDH"].price == pytest.approx(levels.previous_session.high)
    assert by_source["CPR_PIVOT"].price == pytest.approx(levels.cpr.pivot)


def test_e003_dynamic_vwap_does_not_fabricate_historical_interaction_counts():
    g, *_ = _build()
    node = next(n for n in g.nodes if n.source == "SESSION_VWAP")
    assert node.dynamic is True
    assert node.touch_count is None and node.break_count is None and node.reclaim_count is None and node.role_flip is None


def test_e004_tick_and_spread_are_never_invented():
    g, *_ = _build()
    assert g.tick_size is None and g.spread is None
    assert all(n.distance_ticks is None for n in g.nodes)
    assert g.receipt_summary()["tolerance"]["invented_tick_or_spread"] is False


def test_e005_supplied_tick_size_enables_tick_distance_without_changing_level_price():
    base, *_ = _build()
    ticked, *_ = _build(tick_size=0.05)
    assert ticked.tick_size == 0.05
    assert all(n.distance_ticks is not None for n in ticked.nodes)
    assert {n.source: n.price for n in base.nodes} == {n.source: n.price for n in ticked.nodes}


def test_e006_clusters_count_independent_families_not_raw_nodes():
    g, *_ = _build()
    assert g.clusters
    for cluster in g.clusters:
        assert cluster.independent_family_count == len(set(cluster.source_families))
        assert cluster.independent_family_count <= cluster.raw_node_count


def test_e007_directional_semantics_are_symmetric_evidence_not_trade_blocks():
    g, *_ = _build()
    for node in g.nodes:
        assert node.directional_support in {"LONG", "SHORT", "CONFLICTED_AT_LEVEL"}
        assert node.directional_conflict in {"LONG", "SHORT", "CONFLICTED_AT_LEVEL"}
        if node.directional_support == "LONG": assert node.directional_conflict == "SHORT"
        if node.directional_support == "SHORT": assert node.directional_conflict == "LONG"


def test_e008_missing_volume_propagates_unavailable_vwap_not_zero_level():
    g, *_ = _build(_snapshot(missing_current=17))
    assert "VWAP" in g.unavailable_sources
    assert all(not n.source.startswith("VWAP") and n.source != "SESSION_VWAP" for n in g.nodes)


def test_e009_replay_is_deterministic_and_hash_is_causal():
    s = _snapshot()
    a, *_ = _build(s)
    b, *_ = _build(s)
    assert a == b and a.graph_hash == b.graph_hash


def test_e010_causal_mismatch_is_rejected():
    g, levels, primitive, observed = _build()
    other = build_snapshot_feature_kernel(_snapshot(hash_override="f"*64))
    with pytest.raises(CanonicalLevelGraphV2Error, match="snapshot hash mismatch|feature hash mismatch"):
        build_canonical_level_graph_v2(levels, primitive, other)


def test_e011_invalid_microstructure_inputs_fail_closed():
    with pytest.raises(CanonicalLevelGraphV2Error): _build(tick_size=0.0)
    with pytest.raises(CanonicalLevelGraphV2Error): _build(spread=-0.01)


def test_e012_receipt_is_bounded_and_contains_no_probability_or_execution_claim():
    g, *_ = _build()
    text = str(g.receipt_summary()).lower()
    assert "probability" not in text
    assert "may_set_final_band': true" not in text
    assert "may_execute': true" not in text
    assert len(text) < 12000


def test_e013_runtime_is_bounded():
    g, levels, primitive, observed = _build()
    started = perf_counter()
    for _ in range(100):
        result = build_canonical_level_graph_v2(levels, primitive, observed)
        assert result.nodes
    assert perf_counter() - started < 2.0
