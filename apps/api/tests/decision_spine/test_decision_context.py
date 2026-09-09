from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.behavior.decision_spine.decision_context import (
    CANONICAL_EVIDENCE_FIELDS,
    DecisionContextError,
    DecisionIdentity,
    EvidenceBlock,
    InputIntegrity,
    IntegrityState,
    build_decision_context,
    unavailable_evidence,
)
from app.behavior.decision_spine.stage2_integrity import (
    Availability,
    EvidenceObservation,
    SourceMode,
    build_stage2_integrity_report,
)


SNAPSHOT = "a" * 64
DECISION_TIME = datetime(2026, 9, 8, 9, 45, tzinfo=timezone.utc)

ENGINE_BY_FIELD = {
    "price_structure": "MARKET_STRUCTURE_LIQUIDITY",
    "candle_anatomy": "CANDLE_ANATOMY",
    "levels": "LEVEL_CONTEXT",
    "indicators": "SNAPSHOT_INDICATOR_RUNTIME",
    "market_regime": "MARKET_REGIME",
    "session_context": "SESSION_MEMORY",
    "index_context": "INDEX_CONTEXT",
    "sector_context": "SECTOR_CONTEXT",
    "relative_strength": "RELATIVE_STRENGTH",
    "memory": "PERSISTED_INDICATOR_MEMORY",
    "historical_analogs": "ANALOG_MEMORY",
    "hypotheses": "HYPOTHESIS_ENGINE",
    "strategy_candidates": "ORB_CORE",
    "orb_variants": "ORB_CORE",
    "afre_scenarios": "AFRE",
    "derivatives": "DERIVATIVES",
    "events": "EXECUTION_EVENT_OI_RISK",
    "failure_scenarios": "FAILURE_DETECTOR",
    "execution_quality": "EXECUTION_EVENT_OI_RISK",
    "portfolio_risk": "BEHAVIOR_RISK",
    "proof_status": "AFRE",
    "paper_authority": "BEHAVIOR_DECISION",
}


def _identity(snapshot: str = SNAPSHOT) -> DecisionIdentity:
    return DecisionIdentity(
        symbol="reliance",
        timeframe="5m",
        decision_time=DECISION_TIME,
        snapshot_hash=snapshot,
        universe_watermark="NSE:2026-09-08",
    )


def _input_integrity(**overrides) -> InputIntegrity:
    values = {
        "data_quality": 0.99,
        "pit_status": IntegrityState.PASS,
        "freshness": IntegrityState.PASS,
        "quarantine_status": IntegrityState.PASS,
        "reasons": (),
    }
    values.update(overrides)
    return InputIntegrity(**values)


def _stage2(snapshot: str = SNAPSHOT, overrides=None, omit=()):
    overrides = overrides or {}
    observations = []
    for engine_id in sorted(set(ENGINE_BY_FIELD.values()) - set(omit)):
        availability, source_mode = overrides.get(
            engine_id,
            (Availability.AVAILABLE, SourceMode.VERIFIED_SNAPSHOT),
        )
        reasons = ()
        if availability in {Availability.DEGRADED, Availability.UNAVAILABLE, Availability.SKIPPED, Availability.ERROR}:
            reasons = (f"fixture:{engine_id}:{availability.value}",)
        observations.append(
            EvidenceObservation(
                engine_id=engine_id,
                source_snapshot_hash=snapshot,
                availability=availability,
                source_mode=source_mode,
                unavailable_reasons=reasons,
            )
        )
    return build_stage2_integrity_report(
        canonical_snapshot_hash=snapshot,
        evidence_observations=observations,
    )


def _block(field: str, **overrides) -> EvidenceBlock:
    values = {
        "source_engine": ENGINE_BY_FIELD[field],
        "source_snapshot_hash": SNAPSHOT,
        "source_output_hash": "c" * 64,
        "status": Availability.AVAILABLE,
        "payload": {"field": field, "value": 1},
        "observed_at": DECISION_TIME - timedelta(minutes=1),
        "source_mode": SourceMode.VERIFIED_SNAPSHOT,
        "evidence_version": "v1",
        "capability_source": f"fixture:{field}",
    }
    values.update(overrides)
    return EvidenceBlock(**values)


def _evidence(**replacements) -> dict[str, EvidenceBlock]:
    result = {field: _block(field) for field in CANONICAL_EVIDENCE_FIELDS}
    result.update(replacements)
    return result


def _build(evidence=None, **kwargs):
    return build_decision_context(
        identity=kwargs.pop("identity", _identity()),
        input_integrity=kwargs.pop("input_integrity", _input_integrity()),
        stage2_integrity=kwargs.pop("stage2_integrity", _stage2()),
        evidence=evidence or _evidence(),
        **kwargs,
    )


def test_m2_001_builds_immutable_safety_first_context():
    context = _build()
    assert context.identity.symbol == "RELIANCE"
    assert context.identity.snapshot_hash == SNAPSHOT
    assert len(context.context_hash) == 64
    assert context.paper_promotion_eligible is False
    assert context.trade_allowed is False
    assert context.order_routing_enabled is False
    assert context.live_trading_blocked is True


def test_m2_002_same_inputs_produce_same_hash():
    first = _build()
    second = _build()
    assert first.context_hash == second.context_hash
    assert first.as_dict() == second.as_dict()


def test_m2_003_payload_mapping_order_does_not_change_hash():
    first = _evidence(indicators=_block("indicators", payload={"a": 1, "b": 2}))
    second = _evidence(indicators=_block("indicators", payload={"b": 2, "a": 1}))
    assert _build(first).context_hash == _build(second).context_hash


def test_m2_004_material_evidence_change_changes_hash():
    first = _build()
    changed = _evidence(indicators=_block("indicators", payload={"field": "indicators", "value": 2}))
    assert first.context_hash != _build(changed).context_hash


def test_m2_005_every_canonical_evidence_block_is_required():
    evidence = _evidence()
    del evidence["sector_context"]
    with pytest.raises(DecisionContextError, match="missing explicit evidence blocks: sector_context"):
        _build(evidence)


def test_m2_006_unknown_evidence_block_is_rejected():
    evidence = _evidence()
    evidence["mystery"] = _block("indicators")
    with pytest.raises(DecisionContextError, match="unknown evidence blocks: mystery"):
        _build(evidence)


def test_m2_007_stage2_snapshot_must_match_identity():
    with pytest.raises(DecisionContextError, match="Stage2IntegrityReport snapshot hash"):
        _build(stage2_integrity=_stage2("b" * 64))


def test_m2_008_each_evidence_block_must_use_same_d2_snapshot():
    evidence = _evidence(indicators=_block("indicators", source_snapshot_hash="b" * 64))
    with pytest.raises(DecisionContextError, match="indicators: snapshot hash mismatch"):
        _build(evidence)


def test_m2_009_future_evidence_is_rejected():
    evidence = _evidence(indicators=_block("indicators", observed_at=DECISION_TIME + timedelta(seconds=1)))
    with pytest.raises(DecisionContextError, match="future evidence detected"):
        _build(evidence)


def test_m2_010_unregistered_engine_is_rejected():
    evidence = _evidence(indicators=_block("indicators", source_engine="NOT_A_REAL_ENGINE"))
    with pytest.raises(DecisionContextError, match="unregistered source engine"):
        _build(evidence)


def test_m2_011_unavailable_is_explicit_and_not_neutral():
    stage2 = _stage2(
        overrides={"RELATIVE_STRENGTH": (Availability.UNAVAILABLE, SourceMode.UNKNOWN)}
    )
    evidence = _evidence(
        relative_strength=unavailable_evidence(
            source_engine="RELATIVE_STRENGTH",
            snapshot_hash=SNAPSHOT,
            reason="index comparison feed not loaded",
        )
    )
    context = _build(evidence, stage2_integrity=stage2)
    assert context.relative_strength.status is Availability.UNAVAILABLE
    assert dict(context.relative_strength.payload) == {}
    assert context.relative_strength.used_for_probability is False


def test_m2_012_unavailable_without_reason_is_invalid():
    with pytest.raises(DecisionContextError, match="requires an explicit reason"):
        EvidenceBlock(
            source_engine="RELATIVE_STRENGTH",
            source_snapshot_hash=SNAPSHOT,
            status=Availability.UNAVAILABLE,
            payload={},
            source_mode=SourceMode.UNKNOWN,
        )


def test_m2_013_degraded_without_reason_is_invalid():
    with pytest.raises(DecisionContextError, match="requires an explicit reason"):
        _block("indicators", status=Availability.DEGRADED)


def test_m2_014_neutral_substitution_is_hard_rejected():
    evidence = _evidence(
        relative_strength=_block(
            "relative_strength",
            payload={"score": 0.5},
            neutral_default_substituted=True,
        )
    )
    with pytest.raises(DecisionContextError, match="replaced with a neutral default"):
        _build(evidence)


def test_m2_015_synthetic_probability_authority_is_rejected():
    stage2 = _stage2(
        overrides={"SNAPSHOT_INDICATOR_RUNTIME": (Availability.AVAILABLE, SourceMode.SYNTHETIC_FALLBACK)}
    )
    evidence = _evidence(
        indicators=_block(
            "indicators",
            source_mode=SourceMode.SYNTHETIC_FALLBACK,
            used_for_probability=True,
        )
    )
    with pytest.raises(DecisionContextError, match="cannot be probability evidence"):
        _build(evidence, stage2_integrity=stage2)


def test_m2_016_synthetic_explanation_only_is_allowed_but_not_promoted():
    stage2 = _stage2(
        overrides={"SNAPSHOT_INDICATOR_RUNTIME": (Availability.AVAILABLE, SourceMode.SYNTHETIC_FALLBACK)}
    )
    evidence = _evidence(
        indicators=_block(
            "indicators",
            source_mode=SourceMode.SYNTHETIC_FALLBACK,
            used_for_probability=False,
            warnings=("synthetic fallback explanation only",),
        )
    )
    context = _build(evidence, stage2_integrity=stage2)
    assert context.indicators.source_mode is SourceMode.SYNTHETIC_FALLBACK
    assert context.paper_promotion_eligible is False


@pytest.mark.parametrize(
    ("flag", "message"),
    [
        ("claims_proof_authority", "cannot grant proof authority"),
        ("claims_paper_authority", "cannot grant paper authority"),
        ("claims_trade_authority", "cannot grant trade authority"),
        ("final_band_claimed", "cannot claim a final band"),
    ],
)
def test_m2_017_context_evidence_cannot_claim_downstream_authority(flag, message):
    evidence = _evidence(indicators=_block("indicators", **{flag: True}))
    with pytest.raises(DecisionContextError, match=message):
        _build(evidence)


def test_m2_018_stage2_hard_block_prevents_context_construction():
    blocked = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        evidence_observations=[
            EvidenceObservation(
                engine_id="CHART_REASONING",
                source_snapshot_hash="b" * 64,
                availability=Availability.AVAILABLE,
            )
        ],
    )
    with pytest.raises(DecisionContextError, match="not eligible"):
        _build(stage2_integrity=blocked)


def test_m2_019_pit_must_pass():
    with pytest.raises(DecisionContextError, match="PIT status must PASS"):
        _build(
            input_integrity=_input_integrity(
                pit_status=IntegrityState.UNKNOWN,
                reasons=("PIT unknown",),
            )
        )


def test_m2_020_freshness_block_prevents_context_construction():
    with pytest.raises(DecisionContextError, match="blocked freshness"):
        _build(
            input_integrity=_input_integrity(
                freshness=IntegrityState.BLOCK,
                reasons=("market data is stale",),
            )
        )


def test_m2_021_quarantine_block_prevents_context_construction():
    with pytest.raises(DecisionContextError, match="quarantined input"):
        _build(
            input_integrity=_input_integrity(
                quarantine_status=IntegrityState.BLOCK,
                reasons=("input is quarantined",),
            )
        )


def test_m2_022_non_pass_input_integrity_requires_reason():
    with pytest.raises(DecisionContextError, match="requires an explicit reason"):
        _input_integrity(freshness=IntegrityState.UNKNOWN)


def test_m2_023_payload_is_recursively_immutable():
    context = _build(
        _evidence(indicators=_block("indicators", payload={"nested": {"value": [1, 2]}}))
    )
    with pytest.raises(TypeError):
        context.indicators.payload["new"] = 1
    with pytest.raises(TypeError):
        context.indicators.payload["nested"]["value"] = (3,)


def test_m2_024_provenance_is_deterministic_and_contains_receipt_fingerprints():
    context = _build()
    assert context.provenance.stage2_integrity_hash == _stage2().output_hash
    assert tuple(sorted(context.provenance.engines_run)) == context.provenance.engines_run
    assert "SNAPSHOT_INDICATOR_RUNTIME" in context.provenance.engines_run
    assert len(context.provenance.evidence_versions) == len(CANONICAL_EVIDENCE_FIELDS)
    assert len(context.provenance.capability_sources) == len(CANONICAL_EVIDENCE_FIELDS)
    assert context.provenance.source_output_hashes


def test_m2_025_context_does_not_contain_a_final_decision():
    payload = _build().as_dict()
    assert "final_decision" not in payload
    assert "final_band" not in payload
    assert payload["trade_allowed"] is False
    assert payload["order_routing_enabled"] is False


def test_m2_026_exact_stage2_membership_is_required():
    stage2 = _stage2(omit=("SECTOR_CONTEXT",))
    with pytest.raises(DecisionContextError, match="absent from the exact Stage2IntegrityReport"):
        _build(stage2_integrity=stage2)


def test_m2_027_degraded_stage2_cannot_be_upgraded_to_available():
    stage2 = _stage2(
        overrides={"RELATIVE_STRENGTH": (Availability.DEGRADED, SourceMode.VERIFIED_SNAPSHOT)}
    )
    with pytest.raises(DecisionContextError, match="upgrades Stage2 status DEGRADED"):
        _build(stage2_integrity=stage2)


def test_m2_028_unavailable_stage2_cannot_be_upgraded_to_available():
    stage2 = _stage2(
        overrides={"RELATIVE_STRENGTH": (Availability.UNAVAILABLE, SourceMode.UNKNOWN)}
    )
    with pytest.raises(DecisionContextError, match="upgrades Stage2 status UNAVAILABLE"):
        _build(stage2_integrity=stage2)


def test_m2_029_source_mode_must_match_exact_stage2_provenance():
    stage2 = _stage2(
        overrides={"RELATIVE_STRENGTH": (Availability.AVAILABLE, SourceMode.REAL)}
    )
    with pytest.raises(DecisionContextError, match="source_mode VERIFIED_SNAPSHOT does not match"):
        _build(stage2_integrity=stage2)


def test_m2_030_available_stage2_may_be_safely_downgraded():
    evidence = _evidence(
        relative_strength=_block(
            "relative_strength",
            status=Availability.DEGRADED,
            reasons=("partial comparison universe",),
        )
    )
    context = _build(evidence)
    assert context.relative_strength.status is Availability.DEGRADED


def test_m2_031_source_output_hash_must_be_sha256_when_present():
    with pytest.raises(DecisionContextError, match="source_output_hash must be SHA-256"):
        _block("indicators", source_output_hash="bad")
