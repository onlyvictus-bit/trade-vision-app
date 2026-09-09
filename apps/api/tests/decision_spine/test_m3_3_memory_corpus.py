from __future__ import annotations

import pytest

from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.memory_corpus import (
    MemoryCorpusError,
    MemoryRecord,
    build_delayed_label,
    build_memory_corpus,
    quarantine_record,
    retrieve_pit_records,
)


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64
H6 = "6" * 64
H7 = "7" * 64


def _episode(*, decision_time_ns: int = 1_000, symbol: str = "RELIANCE", session_id: str = "s1"):
    return freeze_memory_episode(
        symbol=symbol,
        timeframe="5m",
        decision_time_ns=decision_time_ns,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session_id,
        session_phase="OPENING_RANGE",
        fact_families={"indicator": {"rsi": 62.0}},
        sources=(MemorySourceRef("price", H4, H5, decision_time_ns),),
    )


def _label(episode, *, observed: int = 2_000):
    return build_delayed_label(
        episode=episode,
        label_policy_id="horizon-5m",
        label_policy_version="v1",
        label_available_after_ns=1_500,
        label_observed_at_ns=observed,
        outcome_horizon_ns=500,
        future_price_source_hash=H6,
        future_snapshot_hash=H7,
        return_after_horizon=0.01,
        max_favorable_excursion=0.015,
        max_adverse_excursion=-0.004,
        outcome_class="CONTINUATION",
    )


def test_label_cannot_exist_before_horizon():
    episode = _episode()
    with pytest.raises(MemoryCorpusError, match="LABEL_AVAILABLE_BEFORE_HORIZON"):
        build_delayed_label(
            episode=episode,
            label_policy_id="x",
            label_policy_version="v1",
            label_available_after_ns=1_499,
            label_observed_at_ns=1_600,
            outcome_horizon_ns=500,
            future_price_source_hash=H6,
            future_snapshot_hash=H7,
            return_after_horizon=0.0,
            max_favorable_excursion=0.0,
            max_adverse_excursion=0.0,
            outcome_class="NO_EDGE",
        )


def test_label_observation_before_availability_fails_closed():
    episode = _episode()
    with pytest.raises(MemoryCorpusError, match="LABEL_OBSERVED_BEFORE_AVAILABLE"):
        build_delayed_label(
            episode=episode,
            label_policy_id="x",
            label_policy_version="v1",
            label_available_after_ns=1_500,
            label_observed_at_ns=1_499,
            outcome_horizon_ns=500,
            future_price_source_hash=H6,
            future_snapshot_hash=H7,
            return_after_horizon=0.0,
            max_favorable_excursion=0.0,
            max_adverse_excursion=0.0,
            outcome_class="NO_EDGE",
        )


def test_unfinished_future_candle_and_synthetic_label_are_rejected():
    episode = _episode()
    common = dict(
        episode=episode,
        label_policy_id="x",
        label_policy_version="v1",
        label_available_after_ns=1_500,
        label_observed_at_ns=1_600,
        outcome_horizon_ns=500,
        future_price_source_hash=H6,
        future_snapshot_hash=H7,
        return_after_horizon=0.0,
        max_favorable_excursion=0.0,
        max_adverse_excursion=0.0,
        outcome_class="NO_EDGE",
    )
    with pytest.raises(MemoryCorpusError, match="FUTURE_CANDLE_UNFINISHED"):
        build_delayed_label(**common, future_candle_finished=False)
    with pytest.raises(MemoryCorpusError, match="SYNTHETIC_LABEL_NOT_CANONICAL"):
        build_delayed_label(**common, synthetic=True)


def test_corpus_uses_memory_available_at_not_episode_start():
    episode = _episode()
    record = MemoryRecord(episode=episode, label=_label(episode))
    early = build_memory_corpus(records=(record,), cutoff_time_ns=1_900)
    late = build_memory_corpus(records=(record,), cutoff_time_ns=2_000)
    assert early.episode_count == 0
    assert late.episode_count == 1
    assert late.labelled_count == 1


def test_duplicate_episode_does_not_create_fake_independence():
    episode = _episode()
    label = _label(episode)
    corpus = build_memory_corpus(
        records=(MemoryRecord(episode=episode), MemoryRecord(episode=episode, label=label)),
        cutoff_time_ns=2_500,
    )
    assert corpus.episode_count == 1
    assert corpus.independent_episode_count == 1
    assert corpus.labelled_count == 1


def test_conflicting_labels_for_same_episode_fail_closed():
    episode = _episode()
    a = _label(episode, observed=2_000)
    b = build_delayed_label(
        episode=episode,
        label_policy_id="horizon-5m",
        label_policy_version="v1",
        label_available_after_ns=1_500,
        label_observed_at_ns=2_000,
        outcome_horizon_ns=500,
        future_price_source_hash=H6,
        future_snapshot_hash=H7,
        return_after_horizon=-0.01,
        max_favorable_excursion=0.002,
        max_adverse_excursion=-0.02,
        outcome_class="TRAP",
    )
    with pytest.raises(MemoryCorpusError, match="CONFLICTING_LABELS_FOR_EPISODE"):
        build_memory_corpus(
            records=(MemoryRecord(episode=episode, label=a), MemoryRecord(episode=episode, label=b)),
            cutoff_time_ns=2_500,
        )


def test_quarantine_preserves_record_but_removes_it_from_independent_count():
    episode = _episode()
    quarantined = quarantine_record(
        MemoryRecord(episode=episode, label=_label(episode)),
        reason="provider_schema_drift",
        quarantine_version="q.v1",
        quarantined_at_ns=2_100,
    )
    corpus = build_memory_corpus(records=(quarantined,), cutoff_time_ns=2_500)
    assert corpus.episode_count == 1
    assert corpus.quarantined_count == 1
    assert corpus.independent_episode_count == 0
    assert retrieve_pit_records(corpus, decision_time_ns=2_500) == ()
    assert len(retrieve_pit_records(corpus, decision_time_ns=2_500, include_quarantined=True)) == 1


def test_independence_counts_episode_session_and_symbol_separately():
    e1 = _episode(decision_time_ns=1_000, symbol="RELIANCE", session_id="s1")
    e2 = _episode(decision_time_ns=1_100, symbol="RELIANCE", session_id="s1")
    e3 = _episode(decision_time_ns=1_200, symbol="TCS", session_id="s2")
    corpus = build_memory_corpus(
        records=(MemoryRecord(e1), MemoryRecord(e2), MemoryRecord(e3)),
        cutoff_time_ns=2_500,
    )
    assert corpus.independent_episode_count == 3
    assert corpus.independent_session_count == 2
    assert corpus.independent_symbol_count == 2


def test_corpus_hash_is_order_independent():
    e1 = _episode(decision_time_ns=1_000, session_id="s1")
    e2 = _episode(decision_time_ns=1_100, session_id="s2")
    a = build_memory_corpus(records=(MemoryRecord(e1), MemoryRecord(e2)), cutoff_time_ns=2_500)
    b = build_memory_corpus(records=(MemoryRecord(e2), MemoryRecord(e1)), cutoff_time_ns=2_500)
    assert a.corpus_hash == b.corpus_hash


def test_query_after_corpus_cutoff_is_rejected():
    episode = _episode()
    corpus = build_memory_corpus(records=(MemoryRecord(episode),), cutoff_time_ns=2_000)
    with pytest.raises(MemoryCorpusError, match="QUERY_AFTER_CORPUS_CUTOFF"):
        retrieve_pit_records(corpus, decision_time_ns=2_001)
