from __future__ import annotations

import time

import pytest

from app.behavior.decision_spine.canonical_evidence_graph_v2 import (
    SpecialistEvidenceInputV2,
    build_canonical_evidence_graph_v2,
)
from app.behavior.decision_spine.canonical_indicator_contracts_v2 import build_canonical_indicator_contracts_v2
from app.behavior.decision_spine.evidence_graph import EvidenceAvailability, EpistemicType


SNAPSHOT = "a" * 64
OUT1 = "b" * 64
OUT2 = "c" * 64
OUT3 = "d" * 64


def _inputs():
    return (
        SpecialistEvidenceInputV2(
            claim_id="trend",
            statement="Price path has persistent bullish directional evidence.",
            source_engine="CANONICAL_CHART_STATE_V2",
            source_output_hash=OUT1,
            calculation_version="canonical-chart-state.v2",
            dependency_family="PRICE_PATH",
            correlation_group="TREND_PATH",
            confirmation_needed=("Subsequent closed bars should preserve directional efficiency.",),
            invalidation_conditions=("Persistent counter-direction path invalidates continuation evidence.",),
        ),
        SpecialistEvidenceInputV2(
            claim_id="trend-derived-ema",
            statement="EMA-derived trend state agrees with the price-path trend.",
            source_engine="CANONICAL_INDICATOR_CONTRACTS_V2",
            source_output_hash=OUT2,
            calculation_version="indicator-evidence.v1",
            dependency_family="PRICE_PATH",
            correlation_group="TREND_PATH",
            supporting_claim_ids=("trend",),
        ),
        SpecialistEvidenceInputV2(
            claim_id="rejection",
            statement="Recent morphology contains an opposing rejection signature.",
            source_engine="CANONICAL_CANDLE_MORPHOLOGY_V2",
            source_output_hash=OUT3,
            calculation_version="canonical-candle-morphology.v2",
            dependency_family="CANDLE_GEOMETRY",
            correlation_group="MORPHOLOGY",
            contradicting_claim_ids=("trend",),
            invalidation_conditions=("A decisive close through the rejection extreme invalidates this signature.",),
        ),
    )


def test_m311g_001_claims_are_d2_bound_traceable_and_zero_authority():
    result = build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=_inputs())
    assert result.source_snapshot_hash == SNAPSHOT
    assert all(c.source_snapshot_hash == SNAPSHOT for c in result.graph.claims)
    assert all(c.source_output_hash for c in result.graph.claims)
    assert result.research_only is True
    assert result.used_for_probability is False
    assert result.may_set_final_band is False
    assert result.may_execute is False
    assert result.trade_allowed is False
    assert result.order_routing_enabled is False
    assert result.live_trading_blocked is True


def test_m311g_002_correlated_derivatives_do_not_fake_independent_confluence():
    result = build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=_inputs())
    # Three raw claims, but trend + EMA trend share one dependency/correlation key.
    assert len(result.graph.claims) == 3
    assert result.independent_evidence_family_count == 2
    assert result.bounded_summary()["raw_claim_count_is_independent_count"] is False
    assert dict(result.correlation_cluster_sizes)["TREND_PATH"] == 2


def test_m311g_003_contradictions_are_preserved_not_averaged_away():
    result = build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=_inputs())
    rejection = result.graph.claim("rejection")
    assert rejection.contradicting_claim_ids == ("trend",)
    assert result.contradiction_link_count == 1
    assert rejection.invalidation_conditions


def test_m311g_004_missing_and_unavailable_are_not_neutral():
    unavailable = SpecialistEvidenceInputV2(
        claim_id="volume-confirmation",
        statement="Volume confirmation cannot be evaluated because volume is unavailable.",
        source_engine="CANONICAL_MARKET_STRUCTURE_V2",
        source_output_hash=OUT1,
        calculation_version="canonical-market-structure.v2",
        dependency_family="VOLUME_PARTICIPATION",
        correlation_group="VOLUME",
        availability=EvidenceAvailability.UNAVAILABLE,
        quality="SOURCE_UNAVAILABLE",
        confirmation_needed=("Valid D2-bound volume is required before this evidence can become available.",),
    )
    result = build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=(unavailable,))
    assert result.available_claim_count == 0
    assert result.unavailable_claim_count == 1
    assert result.missing_evidence_claim_ids == ("volume-confirmation",)
    assert result.independent_evidence_family_count == 0


def test_m311g_005_predictive_claim_requires_calibration_identity():
    predictive = SpecialistEvidenceInputV2(
        claim_id="uncalibrated-prediction",
        statement="Next bar will continue.",
        source_engine="TEST",
        source_output_hash=OUT1,
        calculation_version="test.v1",
        dependency_family="PRICE_PATH",
        correlation_group="TEST",
        claim_type=EpistemicType.PREDICTIVE,
    )
    with pytest.raises(ValueError, match="calibration_id"):
        build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=(predictive,))


def test_m311g_006_indicator_contract_dag_is_wired_without_94_vote_inflation():
    contracts = build_canonical_indicator_contracts_v2()
    result = build_canonical_evidence_graph_v2(
        source_snapshot_hash=SNAPSHOT,
        specialist_inputs=_inputs(),
        indicator_contracts=contracts,
    )
    contract_claim = result.graph.claim("indicator-contract-dag")
    assert "94 output contracts" in contract_claim.statement
    assert contract_claim.quality == "CONTRACT_ONLY"
    assert contract_claim.used_for_probability is False
    assert result.independent_evidence_family_count < len(result.graph.claims)


def test_m311g_007_unknown_links_and_cycles_fail_closed():
    bad = SpecialistEvidenceInputV2(
        claim_id="bad",
        statement="Bad dependency.",
        source_engine="TEST",
        source_output_hash=OUT1,
        calculation_version="test.v1",
        dependency_family="TEST",
        correlation_group="TEST",
        upstream_claim_ids=("missing",),
    )
    with pytest.raises(ValueError, match="unknown claim"):
        build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=(bad,))

    a = SpecialistEvidenceInputV2(
        claim_id="a", statement="A", source_engine="TEST", source_output_hash=OUT1,
        calculation_version="test.v1", dependency_family="TEST", correlation_group="TEST",
        upstream_claim_ids=("b",),
    )
    b = SpecialistEvidenceInputV2(
        claim_id="b", statement="B", source_engine="TEST", source_output_hash=OUT2,
        calculation_version="test.v1", dependency_family="TEST", correlation_group="TEST",
        upstream_claim_ids=("a",),
    )
    with pytest.raises(ValueError, match="cycle"):
        build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=(a, b))


def test_m311g_008_deterministic_replay_and_order_invariance():
    first = build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=_inputs())
    second = build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=reversed(_inputs()))
    assert first.graph.graph_hash == second.graph.graph_hash
    assert first.graph_hash == second.graph_hash


def test_m311g_009_snapshot_mismatch_cannot_be_hidden():
    # source hash is imposed centrally by the builder; malformed hashes fail at the base graph boundary.
    with pytest.raises(ValueError, match="SHA-256"):
        build_canonical_evidence_graph_v2(source_snapshot_hash="bad", specialist_inputs=_inputs())


def test_m311g_010_runtime_is_bounded():
    started = time.perf_counter()
    for _ in range(100):
        build_canonical_evidence_graph_v2(source_snapshot_hash=SNAPSHOT, specialist_inputs=_inputs())
    assert time.perf_counter() - started < 2.0
