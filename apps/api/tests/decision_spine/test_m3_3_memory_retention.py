from __future__ import annotations

import pytest

from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_memory_corpus, quarantine_record
from app.behavior.decision_spine.memory_retention import (
    MemoryRetentionError,
    RetentionPolicy,
    apply_retention_policy,
)


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64


def _episode(decision: int, session: str, digit: str):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session,
        session_phase="OPENING_RANGE",
        fact_families={"price": {"trend": "UP"}},
        sources=(MemorySourceRef("price", digit * 64, str((int(digit) + 1) % 10) * 64, decision),),
    )


def test_max_age_retires_old_records_with_tombstones():
    old = MemoryRecord(_episode(100, "old", "1"), memory_available_at_ns=100)
    new = MemoryRecord(_episode(900, "new", "2"), memory_available_at_ns=900)
    corpus = build_memory_corpus(records=(new, old), cutoff_time_ns=1_000)
    view = apply_retention_policy(
        corpus=corpus,
        policy=RetentionPolicy(
            policy_id="age",
            policy_version="v1",
            maximum_age_ns=500,
            retain_unlabelled=False,
        ),
        evaluated_at_ns=1_000,
    )
    assert old.episode.episode_hash in view.retired_episode_hashes
    assert new.episode.episode_hash in view.retained_episode_hashes
    assert view.tombstones[0].reason == "MAXIMUM_AGE"
    assert len(view.tombstones[0].tombstone_hash) == 64


def test_size_limit_is_deterministic_and_keeps_newest():
    records = tuple(MemoryRecord(_episode(100 + i * 100, f"s{i}", str(i + 1))) for i in range(5))
    corpus = build_memory_corpus(records=tuple(reversed(records)), cutoff_time_ns=1_000)
    policy = RetentionPolicy(
        policy_id="size",
        policy_version="v1",
        maximum_corpus_size=2,
        retain_unlabelled=False,
    )
    a = apply_retention_policy(corpus=corpus, policy=policy, evaluated_at_ns=1_000)
    b = apply_retention_policy(corpus=corpus, policy=policy, evaluated_at_ns=1_000)
    assert a.output_hash == b.output_hash
    assert a.retained_episode_count == 2
    assert set(a.retained_episode_hashes) == {records[-1].episode.episode_hash, records[-2].episode.episode_hash}


def test_minimum_independent_floor_prevents_over_pruning():
    records = tuple(MemoryRecord(_episode(100 + i * 100, f"s{i}", str(i + 1))) for i in range(4))
    corpus = build_memory_corpus(records=records, cutoff_time_ns=1_000)
    view = apply_retention_policy(
        corpus=corpus,
        policy=RetentionPolicy(
            policy_id="floor",
            policy_version="v1",
            maximum_age_ns=50,
            minimum_independent_episodes=3,
            retain_unlabelled=False,
        ),
        evaluated_at_ns=1_000,
    )
    assert view.retained_independent_episode_count == 3
    assert view.retired_episode_count == 1


def test_quarantined_records_are_retained_when_policy_requires_audit():
    base = MemoryRecord(_episode(100, "s1", "1"))
    quarantined = quarantine_record(
        base,
        reason="provider_drift",
        quarantine_version="q1",
        quarantined_at_ns=200,
    )
    corpus = build_memory_corpus(records=(quarantined,), cutoff_time_ns=1_000)
    view = apply_retention_policy(
        corpus=corpus,
        policy=RetentionPolicy(
            policy_id="audit",
            policy_version="v1",
            maximum_age_ns=100,
            retain_quarantined=True,
            retain_unlabelled=False,
        ),
        evaluated_at_ns=1_000,
    )
    assert view.retained_episode_count == 1
    assert view.retired_episode_count == 0


def test_unlabelled_records_can_be_preserved_until_labeling_completes():
    record = MemoryRecord(_episode(100, "s1", "1"))
    corpus = build_memory_corpus(records=(record,), cutoff_time_ns=1_000)
    view = apply_retention_policy(
        corpus=corpus,
        policy=RetentionPolicy(
            policy_id="pending",
            policy_version="v1",
            maximum_age_ns=100,
            retain_unlabelled=True,
        ),
        evaluated_at_ns=1_000,
    )
    assert view.retained_episode_count == 1


def test_invalid_size_below_independent_floor_is_rejected():
    corpus = build_memory_corpus(records=(), cutoff_time_ns=1_000)
    with pytest.raises(MemoryRetentionError, match="SIZE_LIMIT_BELOW_MINIMUM"):
        apply_retention_policy(
            corpus=corpus,
            policy=RetentionPolicy(
                policy_id="bad",
                policy_version="v1",
                maximum_corpus_size=2,
                minimum_independent_episodes=3,
            ),
            evaluated_at_ns=1_000,
        )


def test_future_episode_cannot_enter_earlier_retention_view():
    old = MemoryRecord(_episode(100, "old", "1"), memory_available_at_ns=100)
    future = MemoryRecord(_episode(900, "future", "2"), memory_available_at_ns=900)
    corpus = build_memory_corpus(records=(old, future), cutoff_time_ns=1_000)
    view = apply_retention_policy(
        corpus=corpus,
        policy=RetentionPolicy(
            policy_id="pit-size",
            policy_version="v1",
            maximum_corpus_size=10,
            retain_unlabelled=False,
        ),
        evaluated_at_ns=500,
    )
    assert corpus.episode_count == 2
    assert view.original_episode_count == 1
    assert future.episode.episode_hash not in view.retained_episode_hashes
    assert future.episode.episode_hash not in view.retired_episode_hashes
    assert old.episode.episode_hash in view.retained_episode_hashes


def test_future_quarantine_cannot_change_earlier_retention_decision():
    base = MemoryRecord(_episode(100, "old", "1"), memory_available_at_ns=100)
    future_quarantined = quarantine_record(
        base,
        reason="provider_drift",
        quarantine_version="q1",
        quarantined_at_ns=800,
    )
    corpus = build_memory_corpus(records=(future_quarantined,), cutoff_time_ns=1_000)
    view = apply_retention_policy(
        corpus=corpus,
        policy=RetentionPolicy(
            policy_id="pit-quarantine",
            policy_version="v1",
            maximum_age_ns=100,
            retain_quarantined=True,
            retain_unlabelled=False,
        ),
        evaluated_at_ns=500,
    )
    assert corpus.quarantined_count == 1
    assert view.original_episode_count == 1
    assert view.retained_episode_count == 0
    assert view.retired_episode_count == 1
    assert base.episode.episode_hash in view.retired_episode_hashes
    assert view.tombstones[0].reason == "MAXIMUM_AGE"
