from __future__ import annotations

import pytest

from app.behavior.decision_spine.evidence_graph import (
    EVIDENCE_GRAPH_VERSION,
    EpistemicType,
    EvidenceAvailability,
    build_evidence_graph,
    make_evidence_claim,
)


SNAPSHOT = "a" * 64
OUTPUT = "b" * 64


def _claim(claim_id: str, *, claim_type=EpistemicType.DERIVED, upstream=(), support=(), against=(), calibration_id=None):
    return make_evidence_claim(
        claim_id=claim_id,
        claim_type=claim_type,
        statement=f"claim {claim_id}",
        source_engine="M3_1_1_TEST",
        source_snapshot_hash=SNAPSHOT,
        source_output_hash=OUTPUT,
        calculation_version="test.v1",
        dependency_family="price",
        correlation_group="price:morphology",
        availability=EvidenceAvailability.AVAILABLE,
        quality="TEST",
        upstream_claim_ids=upstream,
        supporting_claim_ids=support,
        contradicting_claim_ids=against,
        calibration_id=calibration_id,
    )


def test_m311_graph_001_deterministic_zero_authority_graph():
    observed = make_evidence_claim(
        claim_id="bar.close",
        claim_type=EpistemicType.OBSERVED,
        statement="Latest closed-bar close is directly observed.",
        source_engine="D2_CLOSED_CANDLE_SNAPSHOT",
        source_snapshot_hash=SNAPSHOT,
        source_output_hash=OUTPUT,
        calculation_version="closed-candle-snapshot.v1.87",
        dependency_family="price",
        correlation_group="raw-price",
        quality="CANONICAL",
    )
    derived = make_evidence_claim(
        claim_id="bar.body_ratio",
        claim_type=EpistemicType.DERIVED,
        statement="Body ratio is deterministically derived from the closed bar.",
        source_engine="MARKET_PRIMITIVE_KERNEL_V2",
        source_snapshot_hash=SNAPSHOT,
        source_output_hash=OUTPUT,
        calculation_version="market-primitive-kernel.v2",
        dependency_family="price",
        correlation_group="price:morphology",
        quality="CANONICAL",
        upstream_claim_ids=("bar.close",),
    )
    first = build_evidence_graph(SNAPSHOT, [derived, observed])
    replay = build_evidence_graph(SNAPSHOT, [observed, derived])
    assert first.graph_version == EVIDENCE_GRAPH_VERSION
    assert first.graph_hash == replay.graph_hash
    assert first.used_for_probability is False
    assert first.may_set_final_band is False
    assert first.may_execute is False
    assert first.trade_allowed is False
    assert first.order_routing_enabled is False
    assert first.live_trading_blocked is True


def test_m311_graph_002_predictive_claim_requires_calibration_id():
    with pytest.raises(ValueError, match="calibration_id"):
        _claim("prediction", claim_type=EpistemicType.PREDICTIVE)

    claim = _claim(
        "prediction",
        claim_type=EpistemicType.PREDICTIVE,
        calibration_id="walk-forward-calibration-2026q3-v1",
    )
    assert claim.calibration_id == "walk-forward-calibration-2026q3-v1"


def test_m311_graph_003_nonpredictive_claim_cannot_smuggle_calibration_id():
    with pytest.raises(ValueError, match="reserved"):
        _claim("heuristic", calibration_id="fake-probability")


def test_m311_graph_004_rejects_cross_snapshot_claim():
    claim = make_evidence_claim(
        claim_id="x",
        claim_type=EpistemicType.DERIVED,
        statement="x",
        source_engine="TEST",
        source_snapshot_hash="c" * 64,
        source_output_hash=OUTPUT,
        calculation_version="v1",
        dependency_family="price",
        correlation_group="price",
        quality="TEST",
    )
    with pytest.raises(ValueError, match="snapshot hash"):
        build_evidence_graph(SNAPSHOT, [claim])


def test_m311_graph_005_rejects_unknown_upstream_reference():
    orphan = _claim("orphan", upstream=("missing",))
    with pytest.raises(ValueError, match="unknown claim"):
        build_evidence_graph(SNAPSHOT, [orphan])


def test_m311_graph_006_rejects_cycles():
    a = _claim("a", upstream=("b",))
    b = _claim("b", upstream=("a",))
    with pytest.raises(ValueError, match="cycle"):
        build_evidence_graph(SNAPSHOT, [a, b])


def test_m311_graph_007_rejects_duplicate_claim_ids():
    with pytest.raises(ValueError, match="duplicate"):
        build_evidence_graph(SNAPSHOT, [_claim("same"), _claim("same")])


def test_m311_graph_008_dependency_family_count_is_independent_of_indicator_count():
    claims = [
        make_evidence_claim(
            claim_id=f"ema-{period}",
            claim_type=EpistemicType.DERIVED,
            statement=f"EMA {period} fact",
            source_engine="INDICATOR_DAG",
            source_snapshot_hash=SNAPSHOT,
            source_output_hash=OUTPUT,
            calculation_version="indicator.v2",
            dependency_family="price-trend",
            correlation_group="ema-family",
            quality="CANONICAL",
        )
        for period in (9, 20, 50)
    ]
    graph = build_evidence_graph(SNAPSHOT, claims)
    assert len(graph.claims) == 3
    assert graph.independent_dependency_families == ("price-trend",)
    assert graph.correlation_groups == ("ema-family",)


def test_m311_graph_009_contradictions_are_preserved_not_resolved():
    bull = _claim("bull")
    bear = _claim("bear")
    contested = _claim("contested", support=("bull",), against=("bear",))
    graph = build_evidence_graph(SNAPSHOT, [bull, bear, contested])
    result = graph.claim("contested")
    assert result.supporting_claim_ids == ("bull",)
    assert result.contradicting_claim_ids == ("bear",)


def test_m311_graph_010_unavailable_claim_is_not_converted_to_neutral():
    unavailable = make_evidence_claim(
        claim_id="volume.participation",
        claim_type=EpistemicType.DERIVED,
        statement="Volume participation cannot be derived because volume is missing.",
        source_engine="MARKET_PRIMITIVE_KERNEL_V2",
        source_snapshot_hash=SNAPSHOT,
        source_output_hash=OUTPUT,
        calculation_version="market-primitive-kernel.v2",
        dependency_family="volume",
        correlation_group="volume-participation",
        availability=EvidenceAvailability.UNAVAILABLE,
        quality="MISSING_DEPENDENCY",
    )
    graph = build_evidence_graph(SNAPSHOT, [unavailable])
    assert graph.claim("volume.participation").availability is EvidenceAvailability.UNAVAILABLE
    assert "neutral" not in graph.claim("volume.participation").statement.lower()


def test_m311_graph_011_hypothesis_carries_confirmation_and_invalidation_without_probability():
    hypothesis = make_evidence_claim(
        claim_id="hyp.breakout-continuation",
        claim_type=EpistemicType.HYPOTHESIS,
        statement="Breakout continuation is a hypothesis, not a market fact.",
        source_engine="HYPOTHESIS_SHADOW",
        source_snapshot_hash=SNAPSHOT,
        source_output_hash=OUTPUT,
        calculation_version="hypothesis.v1",
        dependency_family="multi-evidence",
        correlation_group="breakout-hypothesis",
        quality="UNCALIBRATED",
        confirmation_needed=("ORH retest holds", "participation does not collapse"),
        invalidation_conditions=("close returns inside opening range",),
    )
    assert hypothesis.used_for_probability is False
    assert len(hypothesis.confirmation_needed) == 2
    assert len(hypothesis.invalidation_conditions) == 1


def test_m311_graph_012_summary_is_bounded_and_exposes_epistemic_accounting():
    graph = build_evidence_graph(SNAPSHOT, [_claim("a"), _claim("b", claim_type=EpistemicType.INFERRED)])
    summary = graph.bounded_summary()
    assert summary["claim_count"] == 2
    assert summary["type_counts"] == {"DERIVED": 1, "INFERRED": 1}
    assert summary["authority"]["may_set_final_band"] is False
    assert len(str(summary)) < 5000
