from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timedelta, timezone

import pytest

from app.orb.candidate_intake import (
    AvailabilityState,
    CandidateState,
    InstrumentType,
    OrbCandidateReasonV1,
    OrbCandidateReferencePriceV1,
    OrbCandidateSourceFactV1,
    OrbHistoricalReconstructionPolicyV1,
    ReferenceType,
    TruthState,
    UniverseScope,
    build_candidate_intake,
    canonical_json_bytes,
    manual_candidate_intake,
    project_eligible_symbols,
    trendforge_candidate_intakes,
)


T0 = datetime(2026, 9, 13, 3, 30, tzinfo=timezone.utc)
SHA_A = "a" * 64
SHA_B = "b" * 64


def _policy(selector_version: str = "selector.v1") -> OrbHistoricalReconstructionPolicyV1:
    return OrbHistoricalReconstructionPolicyV1(
        policy_id="policy",
        policy_version="v1",
        selector_version=selector_version,
        selection_cutoff_rule="available by cutoff",
        universe_rule="replay same selector",
    )


def _fact(
    fact_id: str = "f1",
    *,
    availability: AvailabilityState = AvailabilityState.AVAILABLE,
    value=1.0,
    available_at: datetime = T0,
    required: bool = False,
) -> OrbCandidateSourceFactV1:
    return OrbCandidateSourceFactV1(
        fact_id=fact_id,
        name=fact_id,
        availability=availability,
        value=value if availability is AvailabilityState.AVAILABLE else None,
        units="score" if availability is AvailabilityState.AVAILABLE else None,
        source_id="source" if availability is AvailabilityState.AVAILABLE else None,
        source_hash=SHA_A if availability is AvailabilityState.AVAILABLE else None,
        observed_at=T0 if availability is AvailabilityState.AVAILABLE else None,
        available_at=available_at if availability is AvailabilityState.AVAILABLE else None,
        required_for_selection=required,
    )


def _reason(*, requires_reference: bool = False) -> OrbCandidateReasonV1:
    return OrbCandidateReasonV1(
        reason_id="r1",
        reason_code="RESEARCH_REASON",
        truth=TruthState.TRUE,
        requires_reference_price=requires_reference,
        evidence_fact_ids=("f1",),
    )


def _build(**overrides):
    params = dict(
        symbol="reliance",
        instrument_type=InstrumentType.NSE_EQUITY,
        source_adapter="TEST",
        source_record_id="record-1",
        selection_rule_version="selector.v1",
        selection_cutoff=T0,
        universe_scope=UniverseScope.ONLINE_SELECTED,
        reasons=[_reason()],
        source_facts=[_fact()],
        reconstruction_policy=_policy(),
        reference_price_identity=None,
    )
    params.update(overrides)
    return build_candidate_intake(**params)


def test_candidate_is_research_only_and_has_zero_direction_or_execution_authority() -> None:
    candidate = _build()
    names = {item.name for item in fields(candidate)}
    assert candidate.state is CandidateState.ELIGIBLE_FOR_STUDY
    assert candidate.research_only is True
    assert candidate.trade_allowed is False
    assert candidate.order_routing_enabled is False
    assert candidate.live_trading_blocked is True
    assert candidate.may_set_final_band is False
    assert candidate.may_execute is False
    assert names.isdisjoint({"direction", "entry", "stop", "target", "probability", "final_band"})


def test_manual_adapter_preserves_legacy_symbol_projection_without_direction_semantics() -> None:
    first = manual_candidate_intake(" reliance ", selected_at=T0)
    duplicate = manual_candidate_intake("RELIANCE", selected_at=T0 + timedelta(seconds=1))
    second = manual_candidate_intake("TCS", selected_at=T0)
    assert first.symbol == "RELIANCE"
    assert first.reasons[0].reason_code == "MANUAL_RESEARCH_CANDIDATE"
    assert project_eligible_symbols([first, duplicate, second]) == ["RELIANCE", "TCS"]


def test_candidate_hash_is_deterministic_under_fact_and_reason_reordering() -> None:
    f1 = _fact("f1")
    f2 = _fact("f2")
    r1 = OrbCandidateReasonV1(reason_id="r1", reason_code="A", truth=TruthState.TRUE, evidence_fact_ids=("f1",))
    r2 = OrbCandidateReasonV1(reason_id="r2", reason_code="B", truth=TruthState.FALSE, evidence_fact_ids=("f2",))
    a = _build(source_facts=[f1, f2], reasons=[r1, r2])
    b = _build(source_facts=[f2, f1], reasons=[r2, r1])
    assert a.candidate_id == b.candidate_id
    assert a.candidate_hash == b.candidate_hash
    assert canonical_json_bytes(a) == canonical_json_bytes(b)


def test_conflicting_duplicate_source_fact_fails_closed() -> None:
    with pytest.raises(ValueError, match="conflicting duplicate source fact"):
        _build(source_facts=[_fact("f1", value=1.0), _fact("f1", value=2.0)])


def test_optional_missing_fact_remains_missing_and_never_becomes_numeric_zero() -> None:
    missing = _fact("optional", availability=AvailabilityState.MISSING)
    candidate = _build(source_facts=[_fact("f1"), missing])
    row = next(item for item in candidate.source_facts if item.fact_id == "optional")
    assert row.availability is AvailabilityState.MISSING
    assert row.value is None
    assert candidate.state is CandidateState.ELIGIBLE_FOR_STUDY


def test_non_available_fact_cannot_carry_a_fabricated_value() -> None:
    with pytest.raises(ValueError, match="non-AVAILABLE fact"):
        OrbCandidateSourceFactV1(
            fact_id="bad",
            name="bad",
            availability=AvailabilityState.UNAVAILABLE,
            value=0.0,
        )


def test_required_missing_fact_blocks_study_without_becoming_false_or_safe() -> None:
    unavailable = _fact("required", availability=AvailabilityState.UNAVAILABLE, required=True)
    candidate = _build(source_facts=[_fact("f1"), unavailable])
    assert candidate.state is CandidateState.UNAVAILABLE_REQUIRED_FACT
    assert "REQUIRED_FACT_UNAVAILABLE:required" in candidate.rejection_reasons


def test_fact_available_after_selection_cutoff_is_quarantined_as_future_leakage() -> None:
    future = _fact("f1", available_at=T0 + timedelta(seconds=1), required=True)
    candidate = _build(source_facts=[future])
    assert candidate.state is CandidateState.QUARANTINED
    assert "FUTURE_FACT:f1" in candidate.rejection_reasons


def test_reference_dependent_reason_requires_exact_reference_identity() -> None:
    candidate = _build(reasons=[_reason(requires_reference=True)])
    assert candidate.state is CandidateState.UNAVAILABLE_REQUIRED_FACT
    assert "REFERENCE_PRICE_REQUIRED:r1" in candidate.rejection_reasons


def test_reference_identity_is_pit_bound_and_future_reference_is_quarantined() -> None:
    reference = OrbCandidateReferencePriceV1(
        reference_type=ReferenceType.CLOSE,
        reference_session_id="NSE:2026-09-12",
        price_basis="unadjusted official close",
        value=1500.25,
        units="INR",
        source_id="official-close",
        source_hash=SHA_B,
        observed_at=T0,
        available_at=T0 + timedelta(seconds=1),
    )
    candidate = _build(reasons=[_reason(requires_reference=True)], reference_price_identity=reference)
    assert candidate.state is CandidateState.QUARANTINED
    assert "FUTURE_REFERENCE_PRICE" in candidate.rejection_reasons


def test_historical_reconstructed_scope_requires_same_selector_version() -> None:
    candidate = _build(
        universe_scope=UniverseScope.HISTORICAL_RECONSTRUCTED_SELECTION,
        reconstruction_policy=_policy(selector_version="different.v2"),
    )
    assert candidate.state is CandidateState.REJECTED
    assert "HISTORICAL_SELECTOR_VERSION_MISMATCH" in candidate.rejection_reasons


def _trendforge_intake(*, state: str = "READY", received_at: datetime = T0) -> dict:
    evidence_at = received_at - timedelta(seconds=5)
    return {
        "intakeId": "trendforge-intake:packet-1",
        "intakeState": "ACCEPTED_RESEARCH_ONLY",
        "evidenceAsOf": evidence_at.isoformat(),
        "receivedAt": received_at.isoformat(),
        "payloadSha256": SHA_A,
        "packet": {
            "evidenceAsOf": evidence_at.isoformat(),
            "payloadSha256": SHA_A,
            "evidence": {
                "candidates": [
                    {
                        "recordId": 17,
                        "symbol": "RELIANCE",
                        "state": state,
                        "createdAt": evidence_at.isoformat(),
                        "payload": {"symbol": "RELIANCE", "state": state, "statusGroup": "ready"},
                    }
                ]
            },
        },
    }


def test_trendforge_adapter_preserves_validated_packet_provenance_and_no_reference_fabrication() -> None:
    rows = trendforge_candidate_intakes(_trendforge_intake())
    assert len(rows) == 1
    candidate = rows[0]
    assert candidate.symbol == "RELIANCE"
    assert candidate.state is CandidateState.ELIGIBLE_FOR_STUDY
    assert candidate.source_adapter == "TRENDFORGE_VALIDATED_INTAKE"
    assert candidate.reference_price_identity is None
    fact = candidate.source_facts[0]
    assert fact.source_hash == SHA_A
    assert fact.value == "READY"
    assert fact.quality == "VALIDATED_BRIDGE_RECEIPT"


def test_trendforge_adapter_accepts_priority_radar_but_not_non_selected_state() -> None:
    assert len(trendforge_candidate_intakes(_trendforge_intake(state="PRIORITY_RADAR"))) == 1
    assert trendforge_candidate_intakes(_trendforge_intake(state="WAIT_DATA_WEAK")) == []


def test_stale_or_rejected_trendforge_receipt_cannot_become_candidate() -> None:
    intake = _trendforge_intake()
    intake["intakeState"] = "WAIT_STALE_TRENDFORGE_EVIDENCE"
    assert trendforge_candidate_intakes(intake) == []


def test_trendforge_candidate_created_after_receipt_fails_closed_before_candidate_materialization() -> None:
    intake = _trendforge_intake()
    intake["packet"]["evidence"]["candidates"][0]["createdAt"] = (T0 + timedelta(seconds=2)).isoformat()
    with pytest.raises(ValueError, match="observed_at cannot be after available_at"):
        trendforge_candidate_intakes(intake)


def test_reference_price_rejects_zero_nan_and_bad_hash() -> None:
    base = dict(
        reference_type=ReferenceType.CLOSE,
        reference_session_id="NSE:2026-09-12",
        price_basis="close",
        units="INR",
        source_id="src",
        source_hash=SHA_B,
        observed_at=T0,
        available_at=T0,
    )
    with pytest.raises(ValueError, match="finite and positive"):
        OrbCandidateReferencePriceV1(value=0.0, **base)
    with pytest.raises(ValueError, match="finite and positive"):
        OrbCandidateReferencePriceV1(value=float("nan"), **base)
    with pytest.raises(ValueError, match="SHA-256"):
        OrbCandidateReferencePriceV1(value=1.0, **{**base, "source_hash": "bad"})
