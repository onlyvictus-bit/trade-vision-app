from __future__ import annotations

from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.canonical_reliability_memory import build_canonical_reliability_memory
from app.behavior.decision_spine.canonical_session_memory import build_canonical_session_memory
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_delayed_label, build_memory_corpus


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64


def _episode(*, decision: int, session_id: str, phase: str = "OPEN", regime: str = "TREND", dow: str = "Monday", calendar: str = "normal_day"):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session_id,
        session_phase=phase,
        fact_families={
            "regime": {"regime_id": regime},
            "session": {"day_of_week": dow, "calendar_class": calendar},
        },
        sources=(MemorySourceRef("price", H4, H5, decision),),
    )


def _record(episode, outcome="CONTINUATION"):
    label = build_delayed_label(
        episode=episode,
        label_policy_id="policy",
        label_policy_version="v1",
        label_available_after_ns=episode.decision_time_ns + 100,
        label_observed_at_ns=episode.decision_time_ns + 100,
        outcome_horizon_ns=100,
        future_price_source_hash=H4,
        future_snapshot_hash=H5,
        return_after_horizon=0.01,
        max_favorable_excursion=0.02,
        max_adverse_excursion=-0.005,
        outcome_class=outcome,
    )
    return MemoryRecord(episode=episode, label=label)


def test_reliability_memory_uses_real_independent_labels_only():
    query = _episode(decision=10_000, session_id="query")
    records = (
        _record(_episode(decision=1_000, session_id="s1"), "CONTINUATION"),
        _record(_episode(decision=2_000, session_id="s2"), "TRAP"),
        _record(_episode(decision=3_000, session_id="s3"), "CONTINUATION"),
    )
    corpus = build_memory_corpus(records=records, cutoff_time_ns=10_000)
    result = build_canonical_reliability_memory(
        query_episode=query,
        corpus=corpus,
        minimum_sample_size=2,
        recent_window=1,
    )
    assert result.independent_episode_count == 3
    assert result.minimum_sample_pass is True
    assert result.outcome_counts["CONTINUATION"] == 2
    assert result.used_for_probability is False
    assert result.may_set_final_band is False
    assert result.may_execute is False


def test_reliability_memory_never_invents_fixture_when_empty():
    query = _episode(decision=10_000, session_id="query")
    corpus = build_memory_corpus(records=(), cutoff_time_ns=10_000)
    result = build_canonical_reliability_memory(query_episode=query, corpus=corpus)
    assert result.independent_episode_count == 0
    assert result.availability == "UNAVAILABLE"
    assert "NO_PIT_VALID_LABELLED_MEMORY" in result.reason_codes
    assert result.posterior_outcome_distribution


def test_session_memory_conditions_on_canonical_session_identity():
    query = _episode(decision=10_000, session_id="query", phase="OPEN", dow="Monday")
    records = (
        _record(_episode(decision=1_000, session_id="s1", phase="OPEN", dow="Monday")),
        _record(_episode(decision=2_000, session_id="s2", phase="OPEN", dow="Tuesday"), "TRAP"),
        _record(_episode(decision=3_000, session_id="s3", phase="MIDDAY", dow="Monday"), "REVERSAL"),
    )
    corpus = build_memory_corpus(records=records, cutoff_time_ns=10_000)
    result = build_canonical_session_memory(query_episode=query, corpus=corpus, minimum_sample_size=1)
    assert result.independent_phase_episode_count == 2
    assert result.independent_day_episode_count == 1
    assert result.phase_outcome_distribution["CONTINUATION"] == 0.5
    assert result.phase_outcome_distribution["TRAP"] == 0.5
    assert result.trade_allowed is False
    assert result.order_routing_enabled is False
