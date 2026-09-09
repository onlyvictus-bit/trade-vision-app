from __future__ import annotations

from app.behavior.decision_spine.authority_registry import (
    FINAL_BAND_AUTHORITY,
    all_engine_authorities,
    validate_authority_registry,
)
from app.behavior.decision_spine.stage2_integrity import (
    Availability,
    EvidenceObservation,
    SourceMode,
    build_stage2_integrity_report,
)

SNAPSHOT = "a" * 64
CURRENT_P1_ENGINE_ORDER = [
    "CHART_REASONING",
    "CANDLE_CONDITION",
    "LEVEL_CONTEXT",
    "SNAPSHOT_INDICATOR_RUNTIME",
    "MTF_CONFIRMATION",
    "PERSISTED_INDICATOR_MEMORY",
    "MARKET_STRUCTURE_LIQUIDITY",
    "EXECUTION_EVENT_OI_RISK",
    "FINAL_CONFLUENCE_ARBITER",
]


def _receipt(engine_id: str, *, status: str = "completed", summary=None, snapshot: str = SNAPSHOT):
    return {
        "engine_id": engine_id,
        "source_snapshot_hash": snapshot,
        "status": status,
        "identity_match": True,
        "used_for_probability": False,
        "output_summary": summary or {},
        "warnings": [],
    }


def test_ds_s2_001_registry_has_exactly_one_final_authority_and_no_execution():
    assert validate_authority_registry() == ()
    finalizers = [item.engine_id for item in all_engine_authorities() if item.may_set_final_band]
    assert finalizers == [FINAL_BAND_AUTHORITY]
    assert all(item.may_execute is False for item in all_engine_authorities())


def test_ds_s2_002_current_p1_engines_are_registered():
    registered = {item.engine_id for item in all_engine_authorities()}
    assert set(CURRENT_P1_ENGINE_ORDER).issubset(registered)


def test_ds_s2_003_same_snapshot_completed_receipts_pass():
    report = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=[_receipt("CHART_REASONING"), _receipt("CANDLE_CONDITION")],
    )
    assert report.status == "PASS"
    assert report.canonical_context_eligible is True
    assert report.paper_promotion_eligible is False
    assert report.trade_allowed is False
    assert report.order_routing_enabled is False
    assert report.live_trading_blocked is True


def test_ds_s2_004_snapshot_mismatch_blocks_context_entry():
    report = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=[_receipt("CHART_REASONING", snapshot="b" * 64)],
    )
    assert report.status == "BLOCK"
    assert report.canonical_context_eligible is False
    assert "SNAPSHOT_HASH_MISMATCH:CHART_REASONING" in report.hard_blockers


def test_ds_s2_005_unavailable_nested_evidence_degrades_and_never_looks_clean():
    report = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=[_receipt("EXECUTION_EVENT_OI_RISK", summary={
            "event_context_status": "unavailable",
            "options_context_status": "unavailable",
            "depth_context_status": "unavailable",
            "unavailable_reasons": ["event provider missing", "options provider missing"],
        })],
    )
    assert report.status == "DEGRADED"
    assert report.available_count == 0
    assert report.degraded_count == 1
    state = report.engine_states[0]
    assert state.unavailable_reasons
    assert any("event_context_status=unavailable" in item for item in state.unavailable_reasons)
    assert report.paper_promotion_eligible is False


def test_ds_s2_006_synthetic_fallback_is_explanation_only_not_probability_authority():
    safe = EvidenceObservation(
        engine_id="NINE_CANDLE_MEMORY",
        source_snapshot_hash=SNAPSHOT,
        source_mode=SourceMode.SYNTHETIC_FALLBACK,
        availability=Availability.DEGRADED,
        explanation_only=True,
        used_for_probability=False,
    )
    report = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT, evidence_observations=[safe])
    assert report.status == "DEGRADED"
    assert not any("NON_AUTHORITATIVE_SOURCE_USED_FOR_PROBABILITY" in item for item in report.hard_blockers)


def test_ds_s2_007_synthetic_fallback_probability_claim_is_hard_blocked():
    unsafe = EvidenceObservation(
        engine_id="NINE_CANDLE_MEMORY",
        source_snapshot_hash=SNAPSHOT,
        source_mode=SourceMode.SYNTHETIC_FALLBACK,
        used_for_probability=True,
        explanation_only=False,
    )
    report = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT, evidence_observations=[unsafe])
    assert report.status == "BLOCK"
    assert "NON_AUTHORITATIVE_SOURCE_USED_FOR_PROBABILITY:NINE_CANDLE_MEMORY" in report.hard_blockers


def test_ds_s2_008_neutral_substitution_for_missing_evidence_is_hard_blocked():
    observation = EvidenceObservation(
        engine_id="RELATIVE_STRENGTH",
        source_snapshot_hash=SNAPSHOT,
        availability=Availability.UNAVAILABLE,
        neutral_default_substituted=True,
        unavailable_reasons=("relative-strength provider not connected",),
    )
    report = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT, evidence_observations=[observation])
    assert report.status == "BLOCK"
    assert "UNAVAILABLE_EVIDENCE_REPLACED_WITH_NEUTRAL:RELATIVE_STRENGTH" in report.hard_blockers


def test_ds_s2_009_only_d6_may_claim_final_band():
    illegal = EvidenceObservation(engine_id="ORB_CORE", source_snapshot_hash=SNAPSHOT, final_band_claimed=True)
    blocked = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT, evidence_observations=[illegal])
    assert "UNAUTHORIZED_FINAL_BAND_CLAIM:ORB_CORE" in blocked.hard_blockers

    allowed = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=[_receipt("FINAL_CONFLUENCE_ARBITER", summary={"final_decision": "WAIT", "decision_band": "WAIT"})],
    )
    assert not any("UNAUTHORIZED_FINAL_BAND_CLAIM" in item for item in allowed.hard_blockers)


def test_ds_s2_010_unregistered_engine_is_fail_closed():
    report = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT, engine_receipts=[_receipt("MYSTERY_BUY_ENGINE")])
    assert report.status == "BLOCK"
    assert "UNREGISTERED_ENGINE:MYSTERY_BUY_ENGINE" in report.hard_blockers


def test_ds_s2_011_integrity_hash_is_deterministic_and_order_independent():
    first = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=[_receipt("CHART_REASONING"), _receipt("CANDLE_CONDITION")],
    )
    second = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=[_receipt("CANDLE_CONDITION"), _receipt("CHART_REASONING")],
    )
    assert first.output_hash == second.output_hash


def test_ds_s2_012_future_leakage_and_identity_mismatch_block():
    observations = [
        EvidenceObservation(engine_id="MTF_CONFIRMATION", source_snapshot_hash=SNAPSHOT, future_leakage_detected=True),
        EvidenceObservation(engine_id="LEVEL_CONTEXT", source_snapshot_hash=SNAPSHOT, identity_match=False),
    ]
    report = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT, evidence_observations=observations)
    assert report.status == "BLOCK"
    assert "FUTURE_LEAKAGE_DETECTED:MTF_CONFIRMATION" in report.hard_blockers
    assert "ENGINE_IDENTITY_MISMATCH:LEVEL_CONTEXT" in report.hard_blockers


def test_ds_s2_013_empty_stage2_evidence_fails_closed():
    report = build_stage2_integrity_report(canonical_snapshot_hash=SNAPSHOT)
    assert report.status == "BLOCK"
    assert report.canonical_context_eligible is False
    assert "NO_STAGE2_EVIDENCE" in report.hard_blockers


def test_ds_s2_014_malformed_canonical_snapshot_hash_fails_closed():
    report = build_stage2_integrity_report(
        canonical_snapshot_hash="not-a-snapshot-hash",
        engine_receipts=[_receipt("CHART_REASONING")],
    )
    assert report.status == "BLOCK"
    assert "INVALID_CANONICAL_SNAPSHOT_HASH" in report.hard_blockers

def test_ds_s2_015_explicit_skipped_migration_evidence_degrades_without_authority():
    observation = EvidenceObservation(
        engine_id="PTA_MARKER_RUNTIME",
        source_snapshot_hash=SNAPSHOT,
        availability=Availability.SKIPPED,
        source_mode=SourceMode.UNKNOWN,
        used_for_probability=False,
        final_band_claimed=False,
        unavailable_reasons=("not D2-native yet",),
    )
    report = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        evidence_observations=[observation],
    )
    assert report.status == "DEGRADED"
    assert report.canonical_context_eligible is True
    assert report.paper_promotion_eligible is False
    assert report.trade_allowed is False
    assert report.order_routing_enabled is False
    assert report.live_trading_blocked is True
