from __future__ import annotations

import json

import pytest

from app.behavior.decision_spine.canonical_context_intelligence import ContextSourceObservation
from app.behavior.decision_spine.canonical_market_context import (
    MAX_MARKET_CONTEXT_BYTES,
    BenchmarkMapping,
    CanonicalMarketContextError,
    PriceBasisLineage,
    ProviderFreshnessPolicy,
    build_benchmark_observation,
    build_benchmark_registry,
    build_canonical_index_sector_context,
)


DECISION = 1_800_000_000_000_000_000
D2_HASH = "a" * 64


def _mapping(*, start: int = DECISION - 1_000, end: int | None = None, sector: str = "NIFTY IT") -> BenchmarkMapping:
    return BenchmarkMapping(
        stock_symbol="INFY",
        sector_symbol=sector,
        broad_index_symbol="NIFTY 50",
        effective_from_ns=start,
        effective_to_ns=end,
        mapping_source="fixture:nse-classification",
        mapping_version="fixture-map.v1",
        lineage_hash="1" * 64,
    )


def _source(role: str, symbol: str, hash_char: str, *, close_age: int = 300, availability: str = "AVAILABLE") -> ContextSourceObservation:
    return ContextSourceObservation(
        source_id=f"{role}:{symbol}:5m",
        source_kind=role,  # type: ignore[arg-type]
        symbol_or_universe=symbol,
        provider_id="fixture-provider",
        provider_contract_version="fixture-provider.v1",
        source_snapshot_hash=hash_char * 64,
        source_timeframe="5m",
        source_bar_close_time_ns=DECISION - close_age,
        available_at_ns=DECISION - close_age + 10,
        d2_decision_time_ns=DECISION,
        sequence_or_watermark=f"{role}-42",
        freshness_state="FRESH",
        clock_skew_state="ALIGNED",
        availability=availability,  # type: ignore[arg-type]
    )


def _policy(role: str, *, max_age: int = 1_000) -> ProviderFreshnessPolicy:
    return ProviderFreshnessPolicy(
        provider_id="fixture-provider",
        provider_contract_version="fixture-provider.v1",
        source_kind=role,  # type: ignore[arg-type]
        timeframe="5m",
        max_source_age_ns=max_age,
        max_availability_lag_ns=100,
        max_clock_skew_ns=10,
    )


def _basis(basis: str = "RAW") -> PriceBasisLineage:
    return PriceBasisLineage(
        basis=basis,  # type: ignore[arg-type]
        adjustment_policy_id="fixture-price-policy",
        adjustment_policy_version="fixture-price-policy.v1",
        corporate_action_source_id=None,
        corporate_action_snapshot_hash=None,
    )


def _observations(*, sector_basis: str = "RAW"):
    index = build_benchmark_observation(
        role="INDEX",
        source=_source("INDEX", "NIFTY 50", "b"),
        policy=_policy("INDEX"),
        price_basis=_basis(),
    )
    sector = build_benchmark_observation(
        role="SECTOR",
        source=_source("SECTOR", "NIFTY IT", "c"),
        policy=_policy("SECTOR"),
        price_basis=_basis(sector_basis),
    )
    return index, sector


def test_m32c_001_registry_resolves_effective_mapping_at_decision_time():
    registry = build_benchmark_registry([_mapping()])
    resolved = registry.resolve(stock_symbol="infy", decision_time_ns=DECISION)
    assert resolved.sector_symbol == "NIFTY IT"
    assert resolved.broad_index_symbol == "NIFTY 50"


def test_m32c_002_registry_rejects_overlapping_mapping_history():
    with pytest.raises(CanonicalMarketContextError, match="BENCHMARK_MAPPING_OVERLAP"):
        build_benchmark_registry([
            _mapping(start=DECISION - 2_000, end=DECISION + 500),
            _mapping(start=DECISION - 1_000, sector="NIFTY TECH"),
        ])


def test_m32c_003_registry_missing_mapping_is_explicit_not_defaulted():
    registry = build_benchmark_registry([_mapping()])
    with pytest.raises(CanonicalMarketContextError, match="BENCHMARK_MAPPING_MISSING"):
        registry.resolve(stock_symbol="RELIANCE", decision_time_ns=DECISION)


def test_m32c_004_provider_policy_degrades_stale_source_without_neutralizing_it():
    observation = build_benchmark_observation(
        role="INDEX",
        source=_source("INDEX", "NIFTY 50", "b", close_age=2_000),
        policy=_policy("INDEX", max_age=1_000),
        price_basis=_basis(),
    )
    assert observation.source.availability == "DEGRADED"
    assert "SOURCE_STALE_BY_POLICY" in observation.source.reason_codes


def test_m32c_005_provider_policy_rejects_wrong_provider_contract():
    source = _source("INDEX", "NIFTY 50", "b")
    wrong = ProviderFreshnessPolicy(
        provider_id="other-provider",
        provider_contract_version="fixture-provider.v1",
        source_kind="INDEX",
        timeframe="5m",
        max_source_age_ns=1_000,
        max_availability_lag_ns=100,
        max_clock_skew_ns=10,
    )
    with pytest.raises(CanonicalMarketContextError, match="FRESHNESS_POLICY_PROVIDER_MISMATCH"):
        build_benchmark_observation(role="INDEX", source=source, policy=wrong, price_basis=_basis())


def test_m32c_006_adjusted_price_basis_requires_corporate_action_lineage():
    with pytest.raises(CanonicalMarketContextError, match="ADJUSTED_BASIS_LINEAGE_UNPROVEN"):
        build_benchmark_observation(
            role="INDEX",
            source=_source("INDEX", "NIFTY 50", "b"),
            policy=_policy("INDEX"),
            price_basis=_basis("SPLIT_ADJUSTED"),
        )


def test_m32c_007_independent_index_sector_context_is_deterministic_and_zero_authority():
    registry = build_benchmark_registry([_mapping()])
    index, sector = _observations()
    first = build_canonical_index_sector_context(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        stock_symbol="INFY",
        registry=registry,
        index=index,
        sector=sector,
    )
    second = build_canonical_index_sector_context(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        stock_symbol="infy",
        registry=registry,
        index=index,
        sector=sector,
    )
    assert first.output_hash == second.output_hash
    assert first.availability == "AVAILABLE"
    assert first.relation == "ALIGNED"
    assert first.index is not None and first.sector is not None
    assert first.index.source.source_snapshot_hash != first.sector.source.source_snapshot_hash
    payload = first.as_dict()
    assert payload["used_for_probability"] is False
    assert payload["may_propose"] is False
    assert payload["may_veto"] is False
    assert payload["may_downgrade"] is False
    assert payload["may_set_final_band"] is False
    assert payload["may_execute"] is False
    assert payload["trade_allowed"] is False
    assert payload["order_routing_enabled"] is False
    assert payload["live_trading_blocked"] is True
    assert len(json.dumps(payload, sort_keys=True).encode("utf-8")) < MAX_MARKET_CONTEXT_BYTES


def test_m32c_008_wrong_sector_identity_fails_closed():
    registry = build_benchmark_registry([_mapping()])
    index, _ = _observations()
    wrong_sector = build_benchmark_observation(
        role="SECTOR",
        source=_source("SECTOR", "NIFTY BANK", "c"),
        policy=_policy("SECTOR"),
        price_basis=_basis(),
    )
    with pytest.raises(CanonicalMarketContextError, match="SECTOR_BENCHMARK_IDENTITY_MISMATCH"):
        build_canonical_index_sector_context(
            d2_snapshot_hash=D2_HASH,
            decision_time_ns=DECISION,
            stock_symbol="INFY",
            registry=registry,
            index=index,
            sector=wrong_sector,
        )


def test_m32c_009_missing_sector_remains_partial_not_neutral():
    registry = build_benchmark_registry([_mapping()])
    index, _ = _observations()
    result = build_canonical_index_sector_context(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        stock_symbol="INFY",
        registry=registry,
        index=index,
        sector=None,
    )
    assert result.availability == "DEGRADED"
    assert result.relation == "PARTIAL"
    assert "SECTOR_OBSERVATION_MISSING" in result.reason_codes
    assert result.sector is None


def test_m32c_010_incompatible_price_bases_preserve_contradiction():
    registry = build_benchmark_registry([_mapping()])
    index = build_benchmark_observation(
        role="INDEX",
        source=_source("INDEX", "NIFTY 50", "b"),
        policy=_policy("INDEX"),
        price_basis=_basis("RAW"),
    )
    adjusted = PriceBasisLineage(
        basis="SPLIT_ADJUSTED",
        adjustment_policy_id="fixture-price-policy",
        adjustment_policy_version="fixture-price-policy.v1",
        corporate_action_source_id="fixture-ca",
        corporate_action_snapshot_hash="d" * 64,
    )
    sector = build_benchmark_observation(
        role="SECTOR",
        source=_source("SECTOR", "NIFTY IT", "c"),
        policy=_policy("SECTOR"),
        price_basis=adjusted,
    )
    result = build_canonical_index_sector_context(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        stock_symbol="INFY",
        registry=registry,
        index=index,
        sector=sector,
    )
    assert result.availability == "DEGRADED"
    assert result.relation == "CONTRADICTORY"
    assert "INDEX_SECTOR_PRICE_BASIS_MISMATCH" in result.contradictions


def test_m32c_011_index_sector_snapshot_hash_collision_is_visible_contradiction():
    registry = build_benchmark_registry([_mapping()])
    index = build_benchmark_observation(
        role="INDEX", source=_source("INDEX", "NIFTY 50", "b"), policy=_policy("INDEX"), price_basis=_basis()
    )
    sector = build_benchmark_observation(
        role="SECTOR", source=_source("SECTOR", "NIFTY IT", "b"), policy=_policy("SECTOR"), price_basis=_basis()
    )
    result = build_canonical_index_sector_context(
        d2_snapshot_hash=D2_HASH,
        decision_time_ns=DECISION,
        stock_symbol="INFY",
        registry=registry,
        index=index,
        sector=sector,
    )
    assert result.relation == "CONTRADICTORY"
    assert "INDEX_SECTOR_SOURCE_HASH_COLLISION" in result.contradictions


def test_m32c_012_mapping_transition_uses_half_open_effective_interval():
    old = _mapping(start=DECISION - 2_000, end=DECISION, sector="NIFTY IT")
    new = BenchmarkMapping(
        stock_symbol="INFY",
        sector_symbol="NIFTY TECH",
        broad_index_symbol="NIFTY 50",
        effective_from_ns=DECISION,
        effective_to_ns=None,
        mapping_source="fixture:nse-classification",
        mapping_version="fixture-map.v2",
        lineage_hash="2" * 64,
    )
    registry = build_benchmark_registry([new, old])
    assert registry.resolve(stock_symbol="INFY", decision_time_ns=DECISION - 1).sector_symbol == "NIFTY IT"
    assert registry.resolve(stock_symbol="INFY", decision_time_ns=DECISION).sector_symbol == "NIFTY TECH"
