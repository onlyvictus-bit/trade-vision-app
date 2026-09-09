from __future__ import annotations

from app.behavior.decision_spine.canonical_analog_memory import AnalogFeatureSpec, retrieve_analogs
from app.behavior.decision_spine.canonical_memory_intelligence import MemorySourceRef, freeze_memory_episode
from app.behavior.decision_spine.memory_corpus import MemoryRecord, build_delayed_label, build_memory_corpus


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H6 = "6" * 64
H7 = "7" * 64


def _episode(*, decision: int, session: str, rsi: float, trend: str, source_digit: str):
    return freeze_memory_episode(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=decision,
        d2_snapshot_hash=H1,
        price_world_hash=H2,
        context_world_hash=H3,
        session_id=session,
        session_phase="OPENING_RANGE",
        fact_families={"indicator": {"rsi": rsi}, "price": {"trend": trend}},
        sources=(MemorySourceRef("price", source_digit * 64, (str((int(source_digit) + 1) % 10)) * 64, decision),),
    )


def _record(episode, outcome="CONTINUATION"):
    label = build_delayed_label(
        episode=episode,
        label_policy_id="p",
        label_policy_version="v1",
        label_available_after_ns=episode.decision_time_ns + 100,
        label_observed_at_ns=episode.decision_time_ns + 100,
        outcome_horizon_ns=100,
        future_price_source_hash=H6,
        future_snapshot_hash=H7,
        return_after_horizon=0.01,
        max_favorable_excursion=0.02,
        max_adverse_excursion=-0.003,
        outcome_class=outcome,
    )
    return MemoryRecord(episode=episode, label=label)


def _specs():
    return (
        AnalogFeatureSpec("indicator.rsi", "NUMERIC", scale=20.0),
        AnalogFeatureSpec("price.trend", "CATEGORICAL"),
    )


def test_retrieval_is_deterministic_and_pit_safe():
    query = _episode(decision=10_000, session="q", rsi=60.0, trend="UP", source_digit="1")
    a = _record(_episode(decision=1_000, session="s1", rsi=61.0, trend="UP", source_digit="2"))
    b = _record(_episode(decision=2_000, session="s2", rsi=40.0, trend="DOWN", source_digit="3"), "TRAP")
    corpus = build_memory_corpus(records=(b, a), cutoff_time_ns=10_000)
    one = retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=10_000,
        feature_manifest_version="v1",
        feature_specs=_specs(),
        max_analogs=10,
        minimum_independent_analogs=1,
    )
    two = retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=10_000,
        feature_manifest_version="v1",
        feature_specs=tuple(reversed(_specs())),
        max_analogs=10,
        minimum_independent_analogs=1,
    )
    assert one.output_hash == two.output_hash
    assert one.matches[0].episode_hash == a.episode.episode_hash
    assert one.matches[0].distance < one.matches[-1].distance


def test_same_session_analogs_do_not_inflate_independent_count():
    query = _episode(decision=10_000, session="q", rsi=60.0, trend="UP", source_digit="1")
    a = _record(_episode(decision=1_000, session="same", rsi=60.0, trend="UP", source_digit="2"))
    b = _record(_episode(decision=2_000, session="same", rsi=60.5, trend="UP", source_digit="3"))
    corpus = build_memory_corpus(records=(a, b), cutoff_time_ns=10_000)
    result = retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=10_000,
        feature_manifest_version="v1",
        feature_specs=_specs(),
        minimum_independent_analogs=1,
    )
    assert result.raw_nearest_neighbor_count == 2
    assert result.independent_analog_count == 1
    assert any("SAME_SESSION" in blocker for match in result.matches for blocker in match.independence_blockers)


def test_overlapping_outcome_horizons_do_not_inflate_independence():
    query = _episode(decision=10_000, session="q", rsi=60.0, trend="UP", source_digit="1")
    a = _record(_episode(decision=1_000, session="s1", rsi=60.0, trend="UP", source_digit="2"))
    b = _record(_episode(decision=1_050, session="s2", rsi=60.1, trend="UP", source_digit="3"))
    corpus = build_memory_corpus(records=(a, b), cutoff_time_ns=10_000)
    result = retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=10_000,
        feature_manifest_version="v1",
        feature_specs=_specs(),
        minimum_independent_analogs=1,
    )
    assert result.independent_analog_count == 1
    assert any("OVERLAPPING_OUTCOME_HORIZON" in blocker for match in result.matches for blocker in match.independence_blockers)


def test_insufficient_independent_analogs_marks_ood():
    query = _episode(decision=10_000, session="q", rsi=60.0, trend="UP", source_digit="1")
    a = _record(_episode(decision=1_000, session="s1", rsi=60.0, trend="UP", source_digit="2"))
    corpus = build_memory_corpus(records=(a,), cutoff_time_ns=10_000)
    result = retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=10_000,
        feature_manifest_version="v1",
        feature_specs=_specs(),
        minimum_independent_analogs=5,
    )
    assert result.ood is True
    assert "INSUFFICIENT_INDEPENDENT_ANALOGS:1<5" in result.ood_reasons


def test_zero_authority_is_explicit():
    query = _episode(decision=10_000, session="q", rsi=60.0, trend="UP", source_digit="1")
    a = _record(_episode(decision=1_000, session="s1", rsi=60.0, trend="UP", source_digit="2"))
    corpus = build_memory_corpus(records=(a,), cutoff_time_ns=10_000)
    result = retrieve_analogs(
        query_episode=query,
        corpus=corpus,
        decision_time_ns=10_000,
        feature_manifest_version="v1",
        feature_specs=_specs(),
        minimum_independent_analogs=1,
    )
    assert result.used_for_probability is False
    assert result.may_set_final_band is False
    assert result.may_execute is False
    assert result.trade_allowed is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True
    assert result.human_approval_required is True
