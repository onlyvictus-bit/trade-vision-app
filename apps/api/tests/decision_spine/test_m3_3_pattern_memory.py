from __future__ import annotations

from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.canonical_pattern_memory import (
    CanonicalPatternMemoryError,
    build_canonical_pattern_memory,
    build_day_shape_v2,
)
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_delayed_label, build_memory_corpus


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
MIN = 60 * 1_000_000_000


def _bars(start=1_000, count=40, step=5 * MIN):
    rows = []
    price = 100.0
    for index in range(count):
        close = price + 0.2 + index * 0.01
        rows.append(
            {
                "timestamp_ns": start + index * step,
                "open": price,
                "high": close + 0.3,
                "low": price - 0.2,
                "close": close,
                "volume": 1000 + index * 10,
            }
        )
        price = close
    return rows


def _episode(decision: int, session: str, pattern_fact):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session,
        session_phase="OPEN",
        fact_families={"pattern": pattern_fact},
        sources=(MemorySourceRef("price", H4, H5, decision),),
    )


def _record(episode):
    label = build_delayed_label(
        episode=episode,
        label_policy_id="p",
        label_policy_version="v1",
        label_available_after_ns=episode.decision_time_ns + 100,
        label_observed_at_ns=episode.decision_time_ns + 100,
        outcome_horizon_ns=100,
        future_price_source_hash=H4,
        future_snapshot_hash=H5,
        return_after_horizon=0.01,
        max_favorable_excursion=0.02,
        max_adverse_excursion=-0.005,
        outcome_class="CONTINUATION",
    )
    return MemoryRecord(episode=episode, label=label)


def test_day_shape_uses_close_time_and_preserves_missing_gap():
    session_open = 1_000
    decision = session_open + 20 * MIN
    shape = build_day_shape_v2(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        session_open_ns=session_open,
        timeframe_duration_ns=5 * MIN,
        source_snapshot_hash=H1,
        bars=_bars(start=session_open, count=8),
        previous_close=None,
    )
    assert shape.vector[0] is None
    assert shape.missing_mask[0] is True
    assert shape.closed_bar_count == 4
    assert shape.first15_bar_count == 3


def test_pattern_memory_retrieves_persisted_day_shapes_only():
    session_open = 1_000
    hist_shape = build_day_shape_v2(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=session_open + 35 * MIN,
        session_open_ns=session_open,
        timeframe_duration_ns=5 * MIN,
        source_snapshot_hash=H1,
        bars=_bars(start=session_open, count=7),
        previous_close=99.5,
    )
    historical = _episode(hist_shape.decision_time_ns, "s1", hist_shape.as_fact())
    query_shape = build_day_shape_v2(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=session_open + 50 * MIN,
        session_open_ns=session_open,
        timeframe_duration_ns=5 * MIN,
        source_snapshot_hash=H1,
        bars=_bars(start=session_open, count=10),
        previous_close=99.5,
    )
    query = _episode(query_shape.decision_time_ns, "query", query_shape.as_fact())
    corpus = build_memory_corpus(records=(_record(historical),), cutoff_time_ns=query.decision_time_ns)
    result = build_canonical_pattern_memory(
        query_episode=query,
        current_shape=query_shape,
        corpus=corpus,
        max_matches=5,
        minimum_overlap_features=4,
        ood_distance_threshold=1.0,
    )
    assert result.independent_match_count == 1
    assert result.matches[0].episode_hash == historical.episode_hash
    assert result.may_set_final_band is False


def test_pattern_memory_rejects_wrong_snapshot_identity():
    session_open = 1_000
    shape = build_day_shape_v2(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=session_open + 35 * MIN,
        session_open_ns=session_open,
        timeframe_duration_ns=5 * MIN,
        source_snapshot_hash=H1,
        bars=_bars(start=session_open, count=7),
        previous_close=99.5,
    )
    query = freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=shape.decision_time_ns,
        d2_snapshot_hash="9" * 64,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id="query",
        session_phase="OPEN",
        fact_families={"pattern": shape.as_fact()},
        sources=(MemorySourceRef("price", H4, H5, shape.decision_time_ns),),
    )
    corpus = build_memory_corpus(records=(), cutoff_time_ns=shape.decision_time_ns)
    try:
        build_canonical_pattern_memory(query_episode=query, current_shape=shape, corpus=corpus)
    except CanonicalPatternMemoryError as exc:
        assert str(exc) == "CURRENT_SHAPE_SNAPSHOT_MISMATCH"
    else:
        raise AssertionError("wrong snapshot identity must fail closed")
