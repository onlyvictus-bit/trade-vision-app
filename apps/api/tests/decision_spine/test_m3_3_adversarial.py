from __future__ import annotations

import pytest

from app.behavior.decision_spine.canonical_memory_intelligence import (
    CanonicalMemoryError,
    MemorySourceRef,
    freeze_memory_episode,
)
from app.behavior.decision_spine.memory_corpus import (
    MemoryCorpusError,
    MemoryRecord,
    build_delayed_label,
    build_memory_corpus,
)


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64


def _episode(decision=1_000, *, source=None):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=f"s-{decision}",
        session_phase="OPEN",
        fact_families={"price": {"trend": "UP"}},
        sources=(source or MemorySourceRef("price", H4, H5, decision),),
    )


def test_future_source_cannot_enter_memory_episode():
    with pytest.raises(CanonicalMemoryError, match="FUTURE_SOURCE"):
        _episode(source=MemorySourceRef("price", H4, H5, 2_000))


def test_synthetic_available_source_cannot_masquerade_as_canonical():
    with pytest.raises(CanonicalMemoryError, match="SYNTHETIC_SOURCE_NOT_CANONICAL"):
        _episode(source=MemorySourceRef("price", H4, H5, 1_000, synthetic=True))


def test_label_cannot_become_available_before_outcome_horizon():
    episode = _episode()
    with pytest.raises(MemoryCorpusError, match="LABEL_AVAILABLE_BEFORE_HORIZON"):
        build_delayed_label(
            episode=episode,
            label_policy_id="p",
            label_policy_version="v1",
            label_available_after_ns=1_050,
            label_observed_at_ns=1_050,
            outcome_horizon_ns=100,
            future_price_source_hash=H4,
            future_snapshot_hash=H5,
            return_after_horizon=0.0,
            max_favorable_excursion=0.0,
            max_adverse_excursion=0.0,
            outcome_class="NO_EDGE",
        )


def test_synthetic_label_is_rejected():
    episode = _episode()
    with pytest.raises(MemoryCorpusError, match="SYNTHETIC_LABEL_NOT_CANONICAL"):
        build_delayed_label(
            episode=episode,
            label_policy_id="p",
            label_policy_version="v1",
            label_available_after_ns=1_100,
            label_observed_at_ns=1_100,
            outcome_horizon_ns=100,
            future_price_source_hash=H4,
            future_snapshot_hash=H5,
            return_after_horizon=0.0,
            max_favorable_excursion=0.0,
            max_adverse_excursion=0.0,
            outcome_class="NO_EDGE",
            synthetic=True,
        )


def test_conflicting_labels_for_same_episode_fail_closed():
    episode = _episode()
    common = dict(
        episode=episode,
        label_policy_id="p",
        label_policy_version="v1",
        label_available_after_ns=1_100,
        outcome_horizon_ns=100,
        future_price_source_hash=H4,
        future_snapshot_hash=H5,
        return_after_horizon=0.0,
        max_favorable_excursion=0.0,
        max_adverse_excursion=0.0,
    )
    one = build_delayed_label(label_observed_at_ns=1_100, outcome_class="CONTINUATION", **common)
    two = build_delayed_label(label_observed_at_ns=1_101, outcome_class="TRAP", **common)
    with pytest.raises(MemoryCorpusError, match="CONFLICTING_LABELS_FOR_EPISODE"):
        build_memory_corpus(
            records=(MemoryRecord(episode=episode, label=one), MemoryRecord(episode=episode, label=two)),
            cutoff_time_ns=2_000,
        )
