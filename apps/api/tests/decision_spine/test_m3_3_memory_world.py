from __future__ import annotations

from app.behavior.decision_spine.canonical_analog_memory import AnalogFeatureSpec, retrieve_analogs
from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.canonical_memory_world import analyze_memory_health, build_canonical_memory_world
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_delayed_label, build_memory_corpus, quarantine_record


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H6 = "6" * 64
H7 = "7" * 64


def _episode(decision: int, session: str, rsi: float, source_digit: str):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session,
        session_phase="OPENING_RANGE",
        fact_families={"indicator": {"rsi": rsi}, "price": {"trend": "UP"}},
        sources=(MemorySourceRef("price", source_digit * 64, str((int(source_digit) + 1) % 10) * 64, decision),),
    )


def _record(episode, outcome):
    label = build_delayed_label(
        episode=episode,
        label_policy_id="p",
        label_policy_version="v1",
        label_available_after_ns=episode.decision_time_ns + 10,
        label_observed_at_ns=episode.decision_time_ns + 10,
        outcome_horizon_ns=10,
        future_price_source_hash=H6,
        future_snapshot_hash=H7,
        return_after_horizon=0.0,
        max_favorable_excursion=0.01,
        max_adverse_excursion=-0.01,
        outcome_class=outcome,
    )
    return MemoryRecord(episode=episode, label=label)


def _analogs(query, corpus, minimum=1):
    return retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=query.decision_time_ns,
        feature_manifest_version="v1",
        feature_specs=(AnalogFeatureSpec("indicator.rsi", "NUMERIC", scale=100.0),),
        max_analogs=100,
        maximum_distance=1.0,
        minimum_independent_analogs=minimum,
    )


def test_distribution_shift_creates_drift_alert_without_inventing_edge_decay():
    records = []
    for idx in range(10):
        records.append(_record(_episode(100 + idx * 20, f"b{idx}", 50.0, str((idx % 7) + 1)), "CONTINUATION"))
    for idx in range(10):
        records.append(_record(_episode(1_000 + idx * 20, f"r{idx}", 50.0, str(((idx + 1) % 7) + 1)), "TRAP"))
    query = _episode(10_000, "query", 50.0, "9")
    corpus = build_memory_corpus(records=tuple(records), cutoff_time_ns=10_000)
    analogs = _analogs(query, corpus)
    health = analyze_memory_health(corpus=corpus, analogs=analogs, recent_episode_count=10, minimum_window_count=10)
    assert health.drift_state == "ALERT"
    assert health.outcome_distribution_divergence == 1.0
    assert health.decay_state == "UNKNOWN"
    assert "EDGE_DECAY_REQUIRES_POLICY_SPECIFIC_UTILITY_LABEL" in health.reason_codes


def test_insufficient_windows_keep_drift_unknown():
    query = _episode(10_000, "query", 50.0, "9")
    record = _record(_episode(100, "s1", 50.0, "2"), "CONTINUATION")
    corpus = build_memory_corpus(records=(record,), cutoff_time_ns=10_000)
    analogs = _analogs(query, corpus)
    health = analyze_memory_health(corpus=corpus, analogs=analogs)
    assert health.drift_state == "UNKNOWN"
    assert health.small_sample is True


def test_quarantine_state_is_explicit_and_preserved():
    query = _episode(10_000, "query", 50.0, "9")
    base = _record(_episode(100, "s1", 50.0, "2"), "CONTINUATION")
    quarantined = quarantine_record(base, reason="poison", quarantine_version="q1", quarantined_at_ns=200)
    corpus = build_memory_corpus(records=(quarantined,), cutoff_time_ns=10_000)
    analogs = _analogs(query, corpus)
    health = analyze_memory_health(corpus=corpus, analogs=analogs)
    assert health.quarantine_state == "ALERT"


def test_world_preserves_counts_provenance_and_zero_authority():
    query = _episode(10_000, "query", 50.0, "9")
    records = tuple(
        _record(_episode(100 + idx * 100, f"s{idx}", 50.0 + idx, str((idx % 7) + 1)), "CONTINUATION")
        for idx in range(6)
    )
    corpus = build_memory_corpus(records=records, cutoff_time_ns=10_000)
    analogs = _analogs(query, corpus, minimum=5)
    health = analyze_memory_health(corpus=corpus, analogs=analogs, minimum_window_count=2, recent_episode_count=3)
    world = build_canonical_memory_world(query_episode=query, corpus=corpus, analogs=analogs, health=health)
    assert world.corpus_hash == corpus.corpus_hash
    assert world.raw_record_count == corpus.raw_record_count
    assert world.independent_episode_count == corpus.independent_episode_count
    assert world.retrieved_episode_count == analogs.raw_nearest_neighbor_count
    assert world.independent_retrieved_episode_count == analogs.independent_analog_count
    assert world.may_propose is False
    assert world.may_veto is False
    assert world.may_downgrade is False
    assert world.may_set_final_band is False
    assert world.may_execute is False
    assert world.trade_allowed is False
    assert world.order_routing_enabled is False
    assert world.live_trading_blocked is True
    assert world.human_approval_required is True


def test_ood_dominates_memory_confidence():
    query = _episode(10_000, "query", 50.0, "9")
    record = _record(_episode(100, "s1", 50.0, "2"), "CONTINUATION")
    corpus = build_memory_corpus(records=(record,), cutoff_time_ns=10_000)
    analogs = _analogs(query, corpus, minimum=5)
    health = analyze_memory_health(corpus=corpus, analogs=analogs)
    world = build_canonical_memory_world(query_episode=query, corpus=corpus, analogs=analogs, health=health)
    assert world.ood is True
    assert world.confidence == "OOD"
    assert "MEMORY_OOD" in world.failure_risks


def test_later_corpus_records_do_not_leak_into_earlier_health_or_world_counts():
    old = _record(_episode(100, "old", 50.0, "2"), "CONTINUATION")
    future = _record(_episode(5_000, "future", 55.0, "3"), "TRAP")
    query = _episode(2_000, "query", 50.0, "9")
    corpus = build_memory_corpus(records=(old, future), cutoff_time_ns=10_000)

    analogs = _analogs(query, corpus)
    health = analyze_memory_health(corpus=corpus, analogs=analogs, minimum_window_count=2)
    world = build_canonical_memory_world(query_episode=query, corpus=corpus, analogs=analogs, health=health)

    assert corpus.episode_count == 2
    assert world.raw_record_count == old.episode.raw_record_count
    assert world.independent_episode_count == 1
    assert future.episode.episode_hash not in world.source_episode_hashes
    assert health.small_sample is True
    assert health.quarantine_state == "CLEAR"


def test_future_quarantine_does_not_leak_into_earlier_health_or_world_state():
    base = _record(_episode(100, "old", 50.0, "2"), "CONTINUATION")
    future_quarantined = quarantine_record(
        base,
        reason="provider_drift",
        quarantine_version="q1",
        quarantined_at_ns=3_000,
    )
    query = _episode(2_000, "query", 50.0, "9")
    corpus = build_memory_corpus(records=(future_quarantined,), cutoff_time_ns=10_000)

    analogs = _analogs(query, corpus)
    health = analyze_memory_health(corpus=corpus, analogs=analogs, minimum_window_count=1)
    world = build_canonical_memory_world(query_episode=query, corpus=corpus, analogs=analogs, health=health)

    assert corpus.quarantined_count == 1
    assert health.quarantine_state == "CLEAR"
    assert "MEMORY_QUARANTINE" not in world.failure_risks
    assert world.independent_episode_count == 1
    assert world.retrieved_episode_count == 1
