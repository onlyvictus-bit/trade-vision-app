from __future__ import annotations

import time

import pytest

from app.behavior.indicator_registry import build_indicator_registry_report
from app.behavior.decision_spine.canonical_indicator_contracts_v2 import (
    CanonicalIndicatorContractsV2Error,
    DependencyEdgeV2,
    build_canonical_indicator_contracts_v2,
    validate_indicator_dependency_dag,
)


def test_m311f_001_exact_94_registry_is_single_contract_truth():
    registry = build_indicator_registry_report()
    contracts = build_canonical_indicator_contracts_v2()
    assert registry.total_output_groups == 94
    assert contracts.registered_output_count == 94
    assert {n.indicator_id for n in contracts.nodes} == {e.indicator_id for e in registry.entries}
    by_id = {e.indicator_id: e for e in registry.entries}
    for node in contracts.nodes:
        source = by_id[node.indicator_id]
        assert node.formula_hash == source.formula_hash
        assert node.implementation_version == source.implementation_version
        assert node.warmup_bars == source.warmup_bars_exact
        assert node.lookback_bars == source.lookback_bars
        assert node.confirmation_delay_bars == source.confirmation_delay_bars
        assert node.closed_bar_only == source.closed_bar_only
        assert node.point_in_time_safe == source.point_in_time_safe
        assert node.uses_future_pivots == source.uses_future_pivots


def test_m311f_002_pta_is_visible_but_noncanonical_and_never_d6_eligible():
    contracts = build_canonical_indicator_contracts_v2()
    assert contracts.noncanonical_pta_indicator_ids
    for indicator_id in contracts.noncanonical_pta_indicator_ids:
        node = contracts.node(indicator_id)
        assert node.registry_source == "pta_signal_markers"
        assert node.canonicalized is False
        assert node.d6_eligible is False
        assert node.used_for_probability is False
        assert node.may_set_final_band is False
        assert node.may_execute is False


def test_m311f_003_shared_indicator_derivatives_are_not_independent_votes():
    contracts = build_canonical_indicator_contracts_v2()
    macd_like = [n for n in contracts.nodes if "macd" in n.indicator_id.lower()]
    assert macd_like
    for node in macd_like:
        assert "DERIVED:EMA" in node.dependency_ancestry
        assert "MOVING_AVERAGE_TREND" in node.correlation_families
    rsi_like = [n for n in contracts.nodes if "rsi" in n.indicator_id.lower()]
    assert rsi_like
    for node in rsi_like:
        assert "DERIVED:RSI" in node.dependency_ancestry
        assert "MOMENTUM_OSCILLATOR" in node.correlation_families
    assert len(contracts.independent_family_keys) < contracts.registered_output_count


def test_m311f_004_volume_dependency_is_explicit_not_assumed_neutral():
    contracts = build_canonical_indicator_contracts_v2()
    volume_nodes = [n for n in contracts.nodes if "volume" in n.input_columns]
    assert volume_nodes
    for node in volume_nodes:
        assert "RAW:VOLUME" in node.dependency_roots
        assert "DERIVED:VOLUME_FLOW" in node.dependency_ancestry or "DERIVED:VWAP" in node.dependency_ancestry


def test_m311f_005_future_pivot_contract_preserves_confirmation_delay():
    contracts = build_canonical_indicator_contracts_v2()
    future = [n for n in contracts.nodes if n.uses_future_pivots]
    assert future
    assert all(n.confirmation_delay_bars > 0 for n in future)


def test_m311f_006_cycle_is_rejected():
    with pytest.raises(CanonicalIndicatorContractsV2Error, match="cycle"):
        validate_indicator_dependency_dag(
            (
                DependencyEdgeV2("A", "B", "UPSTREAM"),
                DependencyEdgeV2("B", "C", "UPSTREAM"),
                DependencyEdgeV2("C", "A", "UPSTREAM"),
            )
        )


def test_m311f_007_replay_hash_is_deterministic():
    first = build_canonical_indicator_contracts_v2()
    second = build_canonical_indicator_contracts_v2()
    assert first == second
    assert first.dag_hash == second.dag_hash
    assert len(first.dag_hash) == 64


def test_m311f_008_zero_authority_and_no_fake_probability():
    contracts = build_canonical_indicator_contracts_v2()
    summary = contracts.bounded_summary()
    assert contracts.research_only is True
    assert contracts.used_for_probability is False
    assert contracts.may_set_final_band is False
    assert contracts.may_execute is False
    assert contracts.trade_allowed is False
    assert contracts.order_routing_enabled is False
    assert contracts.live_trading_blocked is True
    assert contracts.human_approval_required is True
    assert summary["raw_indicator_count_is_independent_count"] is False
    assert summary["authority"]["used_for_probability"] is False


def test_m311f_009_build_runtime_is_bounded():
    started = time.perf_counter()
    for _ in range(25):
        build_canonical_indicator_contracts_v2()
    assert time.perf_counter() - started < 2.0
