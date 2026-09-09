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


def _episode():
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=1_000,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id="s1",
        session_phase="OPENING_RANGE",
        fact_families={"indicator": {"rsi": 62.0}},
        sources=(MemorySourceRef("price", H4, H5, 1_000),),
    )


def _label(episode):
    return build_delayed_label(
        episode=episode,
        label_policy_id="horizon-5m",
        label_policy_version="v1",
        label_available_after_ns=1_500,
        label_observed_at_ns=2_000,
        outcome_horizon_ns=500,
        future_price_source_hash=H6,
        future_snapshot_hash=H7,
        return_after_horizon=0.01,
        max_favorable_excursion=0.015,
        max_adverse_excursion=-0.004,
        outcome_class="CONTINUATION",
    )


def test_duplicate_label_and_quarantine_merge_is_order_independent_and_conservative():
    episode = _episode()
    label = _label(episode)
    labelled = MemoryRecord(episode=episode, label=label)
    quarantined = quarantine_record(
        MemoryRecord(episode=episode),
        reason="provider_schema_drift",
        quarantine_version="q.v1",
        quarantined_at_ns=2_100,
    )

    left_first = build_memory_corpus(records=(labelled, quarantined), cutoff_time_ns=2_500)
    right_first = build_memory_corpus(records=(quarantined, labelled), cutoff_time_ns=2_500)

    assert left_first.corpus_hash == right_first.corpus_hash
    assert left_first.labelled_count == right_first.labelled_count == 1
    assert left_first.quarantined_count == right_first.quarantined_count == 1
    assert left_first.independent_episode_count == right_first.independent_episode_count == 0

    merged = left_first.records[0]
    assert merged.label is not None
    assert merged.label.label_hash == label.label_hash
    assert merged.quarantined is True
    assert merged.quarantine_reason == "provider_schema_drift"
    assert merged.quarantine_version == "q.v1"
    assert merged.quarantined_at_ns == 2_100

    assert retrieve_pit_records(left_first, decision_time_ns=2_500) == ()
    visible_for_audit = retrieve_pit_records(
        left_first,
        decision_time_ns=2_500,
        include_quarantined=True,
    )
    assert len(visible_for_audit) == 1
    assert visible_for_audit[0].label is not None


def test_conflicting_duplicate_quarantine_metadata_fails_closed():
    episode = _episode()
    first = quarantine_record(
        MemoryRecord(episode=episode),
        reason="provider_schema_drift",
        quarantine_version="q.v1",
        quarantined_at_ns=2_100,
    )
    second = quarantine_record(
        MemoryRecord(episode=episode),
        reason="identity_mismatch",
        quarantine_version="q.v1",
        quarantined_at_ns=2_100,
    )

    with pytest.raises(MemoryCorpusError, match="CONFLICTING_QUARANTINE_STATE_FOR_EPISODE"):
        build_memory_corpus(records=(first, second), cutoff_time_ns=2_500)
    with pytest.raises(MemoryCorpusError, match="CONFLICTING_QUARANTINE_STATE_FOR_EPISODE"):
        build_memory_corpus(records=(second, first), cutoff_time_ns=2_500)


def test_duplicate_merge_never_moves_memory_availability_earlier():
    episode = _episode()
    label = _label(episode)
    later = MemoryRecord(
        episode=episode,
        label=label,
        memory_available_at_ns=2_300,
    )
    quarantined_earlier = quarantine_record(
        MemoryRecord(episode=episode),
        reason="provider_schema_drift",
        quarantine_version="q.v1",
        quarantined_at_ns=2_100,
    )

    with pytest.raises(MemoryCorpusError, match="CONFLICTING_DUPLICATE_STATE_FOR_EPISODE"):
        build_memory_corpus(records=(later, quarantined_earlier), cutoff_time_ns=2_500)
    with pytest.raises(MemoryCorpusError, match="CONFLICTING_DUPLICATE_STATE_FOR_EPISODE"):
        build_memory_corpus(records=(quarantined_earlier, later), cutoff_time_ns=2_500)
