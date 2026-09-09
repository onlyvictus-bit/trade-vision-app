from __future__ import annotations

import json
import time

import pytest

from app.behavior.decision_spine.canonical_context_intelligence import ContextSourceObservation
from app.behavior.decision_spine.canonical_market_context import BenchmarkMapping, PriceBasisLineage
from app.behavior.decision_spine.canonical_relative_strength import (
    MAX_RELATIVE_STRENGTH_BYTES,
    CanonicalRelativeStrengthError,
    RelativeStrengthWindow,
    build_canonical_relative_strength,
    build_return_observation,
)

D = 1_800_000_000_000_000_000
H = "a" * 64
WINDOW = RelativeStrengthWindow("15m", D - 900_000_000_000, D)
RAW = PriceBasisLineage("RAW", "raw", "raw.v1", None, None)
MAPPING = BenchmarkMapping("ABC", "NIFTY IT", "NIFTY 50", D - 10_000_000_000_000, None, "fixture", "map.v1", "f" * 64)


def src(role, symbol, h):
    return ContextSourceObservation(
        source_id=f"{role}:{symbol}", source_kind=role, symbol_or_universe=symbol,
        provider_id="p", provider_contract_version="p.v1", source_snapshot_hash=h,
        source_timeframe="5m", source_bar_close_time_ns=D, available_at_ns=D,
        d2_decision_time_ns=D, freshness_state="FRESH", clock_skew_state="ALIGNED",
    )


def obs(role, symbol, start, end, h, basis=RAW, window=WINDOW):
    return build_return_observation(role=role, source=src(role, symbol, h), window=window,
                                    start_price=str(start), end_price=str(end), price_basis=basis,
                                    series_hash=h)


def build(stock_end, sector_end=None, index_end=None, *, sector_basis=RAW, index_basis=RAW):
    return build_canonical_relative_strength(
        d2_snapshot_hash=H, decision_time_ns=D, stock_symbol="ABC", mapping=MAPPING,
        stock=obs("STOCK", "ABC", 100, stock_end, "b" * 64),
        sector=obs("SECTOR", "NIFTY IT", 100, sector_end, "c" * 64, sector_basis) if sector_end is not None else None,
        index=obs("INDEX", "NIFTY 50", 100, index_end, "d" * 64, index_basis) if index_end is not None else None,
    )


def test_leadership():
    r = build(102, 100.5, 100.2)
    assert r.state == "STOCK_LEADER"
    assert r.stock_vs_sector == "0.015"
    assert r.stock_vs_index == "0.018"


def test_green_but_relative_laggard():
    r = build(100.5, 102, 101.5)
    assert r.state == "STOCK_LAGGARD"
    assert r.stock_return == "0.005"


def test_negative_absolute_but_relative_outperformer():
    r = build(99.5, 97.5, 98)
    assert r.state == "STOCK_LEADER"
    assert r.stock_return == "-0.005"
    assert float(r.stock_vs_sector) > 0


def test_stock_up_sector_down_index_up_preserves_conflict():
    r = build(101, 99, 100.5)
    assert r.state == "CONFLICTING"
    assert "STOCK_UP_SECTOR_DOWN_INDEX_UP" in r.contradictions


def test_missing_sector_is_not_neutral():
    r = build(101, None, 100.5)
    assert r.stock_vs_sector is None
    assert "SECTOR_RETURN_UNAVAILABLE" in r.missing_facts
    assert r.availability == "DEGRADED"


def test_missing_both_benchmarks_is_unavailable():
    r = build(101)
    assert r.availability == "UNAVAILABLE"
    assert r.state == "INSUFFICIENT_EVIDENCE"


def test_future_window_rejected():
    w = RelativeStrengthWindow("future", D - 1, D + 1)
    with pytest.raises(CanonicalRelativeStrengthError, match="FUTURE_WINDOW"):
        obs("STOCK", "ABC", 100, 101, "b" * 64, window=w)


def test_stale_source_rejected():
    s = src("INDEX", "NIFTY 50", "d" * 64)
    s = ContextSourceObservation(**{**s.as_dict(), "freshness_state": "STALE"})
    with pytest.raises(CanonicalRelativeStrengthError, match="SOURCE_NOT_FRESH_ALIGNED"):
        build_return_observation(role="INDEX", source=s, window=WINDOW, start_price="100", end_price="101", price_basis=RAW, series_hash="d" * 64)


def test_wrong_benchmark_rejected():
    with pytest.raises(CanonicalRelativeStrengthError, match="SECTOR_BENCHMARK_MISMATCH"):
        build_canonical_relative_strength(d2_snapshot_hash=H, decision_time_ns=D, stock_symbol="ABC", mapping=MAPPING,
            stock=obs("STOCK", "ABC", 100, 101, "b" * 64), sector=obs("SECTOR", "WRONG", 100, 101, "c" * 64), index=None)


def test_price_basis_mismatch_degrades_without_fake_relative_value():
    split = PriceBasisLineage("SPLIT_ADJUSTED", "split", "split.v1", "ca", "e" * 64)
    r = build(101, 102, 100.5, sector_basis=split)
    assert r.stock_vs_sector is None
    assert "PRICE_BASIS_MISMATCH" in r.reason_codes
    assert r.availability == "DEGRADED"


def test_mapping_effective_identity_is_bound():
    r = build(101, 100, 100)
    assert r.benchmark_mapping_hash == "f" * 64


def test_source_order_cannot_change_role_relationships_and_replay_is_deterministic():
    a = build(102, 100.5, 100.2)
    b = build(102, 100.5, 100.2)
    assert a.output_hash == b.output_hash
    assert a.as_dict() == b.as_dict()


def test_duplicate_role_rejected():
    stock = obs("STOCK", "ABC", 100, 101, "b" * 64)
    duplicate_stock = obs("STOCK", "ABC", 100, 102, "c" * 64)
    with pytest.raises(CanonicalRelativeStrengthError, match="DUPLICATE_OBSERVATION_ROLE"):
        build_canonical_relative_strength(d2_snapshot_hash=H, decision_time_ns=D, stock_symbol="ABC", mapping=MAPPING,
            stock=stock, sector=duplicate_stock, index=None)  # type: ignore[arg-type]


def test_bounded_zero_authority_receipt():
    r = build(102, 100.5, 100.2)
    p = r.as_dict()
    assert len(json.dumps(p, sort_keys=True).encode()) < MAX_RELATIVE_STRENGTH_BYTES
    assert p["used_for_probability"] is False
    assert p["may_propose"] is False and p["may_veto"] is False and p["may_downgrade"] is False
    assert p["may_set_final_band"] is False and p["may_execute"] is False
    assert p["trade_allowed"] is False and p["order_routing_enabled"] is False
    assert p["live_trading_blocked"] is True and p["human_approval_required"] is True


def test_performance_anti_pathology():
    started = time.perf_counter()
    for _ in range(300):
        build(102, 100.5, 100.2)
    assert (time.perf_counter() - started) < 2.0
