from __future__ import annotations

import pytest

from app.behavior.decision_spine.canonical_memory_intelligence import (
    CanonicalMemoryError,
    MemorySourceRef,
    freeze_memory_episode,
)


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64


def _source(source_id: str = "price") -> MemorySourceRef:
    return MemorySourceRef(
        source_id=source_id,
        source_snapshot_hash=H4,
        source_output_hash=H5,
        available_at_ns=1_000,
    )


def _episode(**overrides):
    kwargs = dict(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=2_000,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id="2026-09-09:NSE",
        session_phase="OPENING_RANGE",
        fact_families={
            "price_structure": {"trend": "UP", "swing_count": 4},
            "indicator": {"rsi": 63.2, "vwap_state": "ABOVE"},
        },
        sources=(_source(),),
        missing_facts=(),
        degraded_facts=(),
        contradictions=(),
        failure_risks=(),
        warnings=(),
    )
    kwargs.update(overrides)
    return freeze_memory_episode(**kwargs)


def test_episode_is_deterministic_and_order_independent():
    a = _episode(
        fact_families={
            "indicator": {"vwap_state": "ABOVE", "rsi": 63.2},
            "price_structure": {"swing_count": 4, "trend": "UP"},
        },
        sources=(
            MemorySourceRef("z", H4, H5, 1_000),
            MemorySourceRef("a", "6" * 64, "7" * 64, 1_100),
        ),
    )
    b = _episode(
        fact_families={
            "price_structure": {"trend": "UP", "swing_count": 4},
            "indicator": {"rsi": 63.2, "vwap_state": "ABOVE"},
        },
        sources=(
            MemorySourceRef("a", "6" * 64, "7" * 64, 1_100),
            MemorySourceRef("z", H4, H5, 1_000),
        ),
    )
    assert a.feature_hash == b.feature_hash
    assert a.episode_hash == b.episode_hash
    assert a.episode_id == b.episode_id


def test_correlated_facts_do_not_inflate_independent_episode_count():
    episode = _episode(
        fact_families={"indicator": {f"i{idx}": idx for idx in range(50)}}
    )
    assert episode.raw_record_count == 50
    assert episode.independent_episode_count == 1
    assert episode.independent_session_count == 1
    assert episode.independent_symbol_count == 1


def test_future_source_fails_closed():
    with pytest.raises(CanonicalMemoryError, match="FUTURE_SOURCE"):
        _episode(sources=(MemorySourceRef("future", H4, H5, 2_001),))


def test_synthetic_available_source_fails_closed():
    with pytest.raises(CanonicalMemoryError, match="SYNTHETIC_SOURCE_NOT_CANONICAL"):
        _episode(sources=(MemorySourceRef("synthetic", H4, H5, 1_000, synthetic=True),))


def test_identity_mismatch_fails_closed():
    with pytest.raises(CanonicalMemoryError, match="SOURCE_IDENTITY_MISMATCH"):
        _episode(sources=(MemorySourceRef("wrong", H4, H5, 1_000, identity_match=False),))


def test_duplicate_source_id_is_rejected():
    with pytest.raises(CanonicalMemoryError, match="DUPLICATE_SOURCE_ID"):
        _episode(sources=(_source("same"), _source("same")))


def test_missing_or_contradictory_evidence_degrades_not_neutralizes():
    episode = _episode(
        missing_facts=("sector.relative_strength",),
        contradictions=("price_up_but_sector_down",),
    )
    assert episode.availability == "DEGRADED"
    assert episode.missing_facts == ("sector.relative_strength",)
    assert episode.contradictions == ("price_up_but_sector_down",)


def test_zero_authority_is_explicit():
    episode = _episode()
    assert episode.used_for_probability is False
    assert episode.may_propose is False
    assert episode.may_veto is False
    assert episode.may_downgrade is False
    assert episode.may_set_final_band is False
    assert episode.may_execute is False
    assert episode.trade_allowed is False
    assert episode.order_routing_enabled is False
    assert episode.live_trading_blocked is True
    assert episode.human_approval_required is True


def test_nonfinite_fact_is_rejected():
    with pytest.raises(CanonicalMemoryError, match="NON_FINITE_FACT"):
        _episode(fact_families={"indicator": {"bad": float("nan")}})


def test_unavailable_when_no_sources_or_no_facts():
    assert _episode(sources=()).availability == "UNAVAILABLE"
    assert _episode(fact_families={}).availability == "UNAVAILABLE"
