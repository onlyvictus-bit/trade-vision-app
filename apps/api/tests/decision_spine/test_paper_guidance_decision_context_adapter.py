from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.behavior.decision_spine.decision_context import (
    CANONICAL_EVIDENCE_FIELDS,
    DecisionContextError,
    IntegrityState,
)
from app.behavior.decision_spine.paper_guidance_decision_context_adapter import (
    CANONICAL_FIELD_BINDINGS,
    build_canonical_stage2_observations,
    build_paper_guidance_decision_context,
    decision_context_audit_summary,
)
from app.behavior.decision_spine.stage2_integrity import (
    Availability,
    EvidenceObservation,
    SourceMode,
    build_stage2_integrity_report,
)


SNAPSHOT = "a" * 64
DECISION_TIME_NS = 1_786_000_000_000_000_000


def _snapshot(hash_value: str = SNAPSHOT):
    return SimpleNamespace(
        symbol="RELIANCE",
        timeframe="5m",
        decision_time_ns=DECISION_TIME_NS,
        snapshot_hash=hash_value,
    )


def _quality(score: float = 0.99):
    return SimpleNamespace(data_quality_score=score)


def _pit(passed: bool = True):
    return SimpleNamespace(passed=passed)


def _receipt(engine_id: str, *, summary=None, output_hash: str | None = None, status="completed"):
    return SimpleNamespace(
        engine_id=engine_id,
        source_snapshot_hash=SNAPSHOT,
        output_hash=output_hash or (engine_id.lower().encode().hex() + "0" * 64)[:64],
        status=status,
        identity_match=True,
        output_summary=summary or {"value": engine_id},
        warnings=[],
        used_for_probability=False,
        engine_version=f"{engine_id.lower()}.v1",
    )


def _active_receipts():
    return [
        _receipt("CHART_REASONING"),
        _receipt("CANDLE_CONDITION"),
        _receipt("LEVEL_CONTEXT"),
        _receipt("SNAPSHOT_INDICATOR_RUNTIME", output_hash="1" * 64),
        _receipt("MTF_CONFIRMATION"),
        _receipt("PERSISTED_INDICATOR_MEMORY"),
        _receipt("MARKET_STRUCTURE_LIQUIDITY"),
        _receipt("EXECUTION_EVENT_OI_RISK"),
    ]


def _stage2(receipts=None):
    receipts = receipts or _active_receipts()
    observations = build_canonical_stage2_observations(
        snapshot_hash=SNAPSHOT,
        active_engine_ids=[item.engine_id for item in receipts],
    )
    return build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=receipts,
        evidence_observations=observations,
    )


def _context(receipts=None, stage2=None):
    receipts = receipts or _active_receipts()
    return build_paper_guidance_decision_context(
        snapshot=_snapshot(),
        data_quality=_quality(),
        point_in_time=_pit(),
        receipts=receipts,
        stage2_integrity=stage2 or _stage2(receipts),
    )


def test_m2_adapter_001_binding_table_exactly_covers_canonical_fields():
    assert tuple(item.field_name for item in CANONICAL_FIELD_BINDINGS) == CANONICAL_EVIDENCE_FIELDS
    assert len(CANONICAL_FIELD_BINDINGS) == 22


def test_m2_adapter_002_inactive_inventory_is_unique_and_explicit():
    observations = build_canonical_stage2_observations(
        snapshot_hash=SNAPSHOT,
        active_engine_ids=[item.engine_id for item in _active_receipts()],
    )
    ids = [item.engine_id for item in observations]
    assert len(ids) == len(set(ids))
    assert "SECTOR_CONTEXT" in ids
    assert "DERIVATIVES" in ids
    assert "CANDLE_ANATOMY" in ids
    assert "ORB_CORE" in ids
    assert all(item.unavailable_reasons for item in observations)
    assert all(item.used_for_probability is False for item in observations)


def test_m2_adapter_003_active_engine_is_not_duplicated_by_inactive_inventory():
    observations = build_canonical_stage2_observations(
        snapshot_hash=SNAPSHOT,
        active_engine_ids=["LEVEL_CONTEXT", "DERIVATIVES"],
    )
    ids = {item.engine_id for item in observations}
    assert "LEVEL_CONTEXT" not in ids
    assert "DERIVATIVES" not in ids


def test_m2_adapter_004_same_inputs_produce_same_context_hash():
    first = _context()
    second = _context()
    assert first.context_hash == second.context_hash
    assert first.as_dict() == second.as_dict()


def test_m2_adapter_005_receipt_output_hash_is_preserved_in_evidence_provenance():
    context = _context()
    assert context.indicators.source_output_hash == "1" * 64
    assert any("indicators:SNAPSHOT_INDICATOR_RUNTIME:" + "1" * 64 == item for item in context.provenance.source_output_hashes)


def test_m2_adapter_006_missing_specialists_remain_explicit_not_neutral():
    context = _context()
    assert context.sector_context.status is Availability.UNAVAILABLE
    assert context.sector_context.source_mode is SourceMode.UNKNOWN
    assert dict(context.sector_context.payload) == {}
    assert context.sector_context.reasons
    assert context.derivatives.status is Availability.UNAVAILABLE
    assert context.orb_variants.status is Availability.SKIPPED
    assert context.afre_scenarios.status is Availability.SKIPPED


def test_m2_adapter_007_unknown_freshness_and_quarantine_are_not_fabricated_passes():
    context = _context()
    assert context.input_integrity.pit_status is IntegrityState.PASS
    assert context.input_integrity.freshness is IntegrityState.UNKNOWN
    assert context.input_integrity.quarantine_status is IntegrityState.UNKNOWN
    joined = " ".join(context.input_integrity.reasons).lower()
    assert "freshness" in joined
    assert "quarantine" in joined


def test_m2_adapter_008_stage2_must_contain_every_canonical_source():
    receipts = _active_receipts()
    incomplete = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=receipts,
        evidence_observations=[
            EvidenceObservation(
                engine_id="ORB_CORE",
                source_snapshot_hash=SNAPSHOT,
                availability=Availability.SKIPPED,
                source_mode=SourceMode.UNKNOWN,
                unavailable_reasons=("fixture skipped",),
            )
        ],
    )
    with pytest.raises(DecisionContextError, match="absent from Stage2 integrity"):
        _context(receipts=receipts, stage2=incomplete)


def test_m2_adapter_009_stage2_block_cannot_construct_context():
    receipts = _active_receipts()
    complete_inventory = list(
        build_canonical_stage2_observations(
            snapshot_hash=SNAPSHOT,
            active_engine_ids=[item.engine_id for item in receipts],
        )
    )
    complete_inventory = [
        EvidenceObservation(
            engine_id=item.engine_id,
            source_snapshot_hash="b" * 64,
            availability=item.availability,
            source_mode=item.source_mode,
            identity_match=item.identity_match,
            used_for_probability=item.used_for_probability,
            neutral_default_substituted=item.neutral_default_substituted,
            final_band_claimed=item.final_band_claimed,
            future_leakage_detected=item.future_leakage_detected,
            explanation_only=item.explanation_only,
            unavailable_reasons=("wrong snapshot",),
            notes=item.notes,
        )
        if item.engine_id == "SECTOR_CONTEXT"
        else item
        for item in complete_inventory
    ]
    blocked = build_stage2_integrity_report(
        canonical_snapshot_hash=SNAPSHOT,
        engine_receipts=receipts,
        evidence_observations=complete_inventory,
    )
    assert blocked.canonical_context_eligible is False
    with pytest.raises(DecisionContextError, match="not eligible"):
        _context(receipts=receipts, stage2=blocked)


def test_m2_adapter_010_adapter_never_grants_downstream_authority():
    context = _context()
    assert context.paper_promotion_eligible is False
    assert context.trade_allowed is False
    assert context.order_routing_enabled is False
    assert context.live_trading_blocked is True
    assert "final_band" not in context.as_dict()
    assert "final_decision" not in context.as_dict()


def test_m2_adapter_011_audit_summary_is_compact_and_deterministic():
    context = _context()
    first = decision_context_audit_summary(context)
    second = decision_context_audit_summary(context)
    assert first == second
    assert first["context_hash"] == context.context_hash
    assert first["snapshot_hash"] == SNAPSHOT
    assert first["stage2_integrity_hash"] == context.provenance.stage2_integrity_hash
    assert first["evidence"]["field_count"] == 22
    assert sum(
        first["evidence"][key]
        for key in (
            "available_count",
            "degraded_count",
            "unavailable_count",
            "skipped_count",
            "error_count",
        )
    ) == 22


def test_m2_adapter_012_changed_receipt_payload_changes_context_hash():
    first_receipts = _active_receipts()
    second_receipts = _active_receipts()
    second_receipts[3] = _receipt(
        "SNAPSHOT_INDICATOR_RUNTIME",
        summary={"value": "changed"},
        output_hash="2" * 64,
    )
    first = _context(receipts=first_receipts)
    second = _context(receipts=second_receipts)
    assert first.context_hash != second.context_hash


def test_m2_adapter_013_non_passing_pit_fails_closed():
    receipts = _active_receipts()
    with pytest.raises(DecisionContextError, match="PIT status must PASS"):
        build_paper_guidance_decision_context(
            snapshot=_snapshot(),
            data_quality=_quality(),
            point_in_time=_pit(False),
            receipts=receipts,
            stage2_integrity=_stage2(receipts),
        )
