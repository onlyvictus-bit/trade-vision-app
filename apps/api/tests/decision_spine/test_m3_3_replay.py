from __future__ import annotations

from app.behavior.decision_spine.canonical_analog_memory import AnalogFeatureSpec, retrieve_analogs
from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_delayed_label, build_memory_corpus


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64


def _episode(decision: int, session: str, value: float):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session,
        session_phase="OPEN",
        fact_families={"feature": {"x": value}},
        sources=(MemorySourceRef("source", H4, H5, decision),),
    )


def _record(episode, observed_at: int):
    label = build_delayed_label(
        episode=episode,
        label_policy_id="replay",
        label_policy_version="v1",
        label_available_after_ns=episode.decision_time_ns + 100,
        label_observed_at_ns=observed_at,
        outcome_horizon_ns=100,
        future_price_source_hash=H4,
        future_snapshot_hash=H5,
        return_after_horizon=0.01,
        max_favorable_excursion=0.02,
        max_adverse_excursion=-0.003,
        outcome_class="CONTINUATION",
    )
    return MemoryRecord(episode=episode, label=label)


def test_old_decision_replays_old_corpus_even_after_new_record_exists():
    old = _record(_episode(1_000, "s1", 1.0), 1_100)
    future = _record(_episode(5_000, "s2", 1.1), 5_100)
    old_view = build_memory_corpus(records=(future, old), cutoff_time_ns=2_000)
    replay_view = build_memory_corpus(records=(old, future), cutoff_time_ns=2_000)
    later_view = build_memory_corpus(records=(old, future), cutoff_time_ns=6_000)
    assert old_view.corpus_hash == replay_view.corpus_hash
    assert old_view.episode_hashes == replay_view.episode_hashes
    assert future.episode.episode_hash not in old_view.episode_hashes
    assert future.episode.episode_hash in later_view.episode_hashes
    assert old_view.corpus_hash != later_view.corpus_hash


def test_analog_output_is_order_independent_under_restart():
    query = _episode(10_000, "query", 1.05)
    records = (
        _record(_episode(1_000, "s1", 1.0), 1_100),
        _record(_episode(3_000, "s2", 1.2), 3_100),
    )
    specs = (AnalogFeatureSpec("feature.x", "NUMERIC", scale=1.0),)
    first_corpus = build_memory_corpus(records=records, cutoff_time_ns=10_000)
    second_corpus = build_memory_corpus(records=tuple(reversed(records)), cutoff_time_ns=10_000)
    first = retrieve_analogs(
        query_episode=query,
        corpus=first_corpus,
        decision_time_ns=10_000,
        feature_manifest_version="replay.v1",
        feature_specs=specs,
        maximum_distance=1.0,
        minimum_independent_analogs=1,
    )
    second = retrieve_analogs(
        query_episode=query,
        corpus=second_corpus,
        decision_time_ns=10_000,
        feature_manifest_version="replay.v1",
        feature_specs=specs,
        maximum_distance=1.0,
        minimum_independent_analogs=1,
    )
    assert first_corpus.corpus_hash == second_corpus.corpus_hash
    assert first.output_hash == second.output_hash
    assert [match.episode_hash for match in first.matches] == [match.episode_hash for match in second.matches]
