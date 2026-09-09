from __future__ import annotations

from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.canonical_nine_candle_memory import (
    CanonicalNineCandleError,
    build_canonical_nine_candle_memory,
    build_nine_candle_state,
)
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_delayed_label, build_memory_corpus


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64


def _bars(start=1_000, count=9):
    rows = []
    price = 100.0
    for index in range(count):
        close = price + 0.4
        rows.append(
            {
                "timestamp_ns": start + index * 100,
                "open": price,
                "high": close + 0.2,
                "low": price - 0.2,
                "close": close,
                "volume": 1000 + index * 25,
            }
        )
        price = close
    return rows


def _telemetry(snapshot_hash=H1):
    return [
        {
            "indicator_id": "si_rsi_div",
            "evidence": {
                "source_snapshot_hash": snapshot_hash,
                "status": "COMPUTED",
                "output_present": True,
                "family": "momentum",
                "correlation_group": "momentum-rsi",
                "direction": "bullish",
                "strength": 0.7,
                "value": 55.0,
                "evidence_hash": H4,
            },
        }
    ]


def _episode(decision, session, state):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session,
        session_phase="OPEN",
        fact_families={"nine_candle": state.as_fact()},
        sources=(MemorySourceRef("price", H4, H5, decision),),
    )


def _record(episode, outcome="CONTINUATION"):
    label = build_delayed_label(
        episode=episode,
        label_policy_id="9c",
        label_policy_version="v1",
        label_available_after_ns=episode.decision_time_ns + 100,
        label_observed_at_ns=episode.decision_time_ns + 100,
        outcome_horizon_ns=100,
        future_price_source_hash=H4,
        future_snapshot_hash=H5,
        return_after_horizon=0.01,
        max_favorable_excursion=0.02,
        max_adverse_excursion=-0.004,
        outcome_class=outcome,
    )
    return MemoryRecord(episode=episode, label=label)


def test_current_9c_uses_snapshot_native_closed_bars_and_indicator_provenance():
    state = build_nine_candle_state(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=10_000,
        source_snapshot_hash=H1,
        closed_bars=_bars(),
        indicator_telemetry=_telemetry(),
    )
    assert state.candle_count == 9
    assert state.indicator_facts["si_rsi_div"]["direction"] == "bullish"
    assert not state.missing_indicators


def test_wrong_indicator_snapshot_is_masked_not_reused():
    state = build_nine_candle_state(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=10_000,
        source_snapshot_hash=H1,
        closed_bars=_bars(),
        indicator_telemetry=_telemetry("9" * 64),
    )
    assert "si_rsi_div" in state.missing_indicators
    assert "si_rsi_div" not in state.indicator_facts


def test_9c_rejects_future_bar():
    bars = _bars(start=9_500)
    try:
        build_nine_candle_state(
            symbol="RELIANCE",
            timeframe="5m",
            decision_time_ns=10_000,
            source_snapshot_hash=H1,
            closed_bars=bars,
            indicator_telemetry=_telemetry(),
        )
    except CanonicalNineCandleError as exc:
        assert str(exc) == "FUTURE_OR_UNFINISHED_BAR_IN_9C"
    else:
        raise AssertionError("future bar must fail closed")


def test_canonical_9c_uses_only_persisted_labelled_history():
    historical_state = build_nine_candle_state(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=2_000,
        source_snapshot_hash=H1,
        closed_bars=_bars(start=100),
        indicator_telemetry=_telemetry(),
    )
    historical = _episode(2_000, "s1", historical_state)
    current_state = build_nine_candle_state(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=10_000,
        source_snapshot_hash=H1,
        closed_bars=_bars(start=5_000),
        indicator_telemetry=_telemetry(),
    )
    query = _episode(10_000, "query", current_state)
    corpus = build_memory_corpus(records=(_record(historical),), cutoff_time_ns=10_000)
    result = build_canonical_nine_candle_memory(
        query_episode=query,
        current_state=current_state,
        corpus=corpus,
        minimum_independent_matches=1,
        maximum_distance=1.0,
    )
    assert result.independent_match_count == 1
    assert result.matches[0].episode_hash == historical.episode_hash
    assert result.used_for_probability is False
    assert result.may_execute is False


def test_empty_9c_corpus_is_unavailable_not_mock_generated():
    current_state = build_nine_candle_state(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=10_000,
        source_snapshot_hash=H1,
        closed_bars=_bars(start=5_000),
        indicator_telemetry=_telemetry(),
    )
    query = _episode(10_000, "query", current_state)
    corpus = build_memory_corpus(records=(), cutoff_time_ns=10_000)
    result = build_canonical_nine_candle_memory(query_episode=query, current_state=current_state, corpus=corpus)
    assert result.availability == "UNAVAILABLE"
    assert "NO_COMPARABLE_PERSISTED_9C_HISTORY" in result.ood_reasons
    assert result.matches == ()
