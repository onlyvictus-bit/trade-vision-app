from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorAcpHardeningResult,
    BehaviorDriftResult,
    BehaviorOODResult,
    BehaviorSafetyReport,
    GoldenReplayFixture,
    GoldenReplayVerificationResult,
    MarketEvent,
    MemoryQuarantineRecord,
    MemoryQuarantineRequest,
    MemoryRebuildPlan,
    RealityGapCheckResult,
    now_iso,
)


OPERATIONAL_SAFETY_VERSION = "behavior-operational-safety.v0.26"


def build_safety_report(
    *,
    symbol: str,
    drift: BehaviorDriftResult,
    ood: BehaviorOODResult,
    reality_gap: RealityGapCheckResult,
    acp: BehaviorAcpHardeningResult,
) -> BehaviorSafetyReport:
    normalized = symbol.upper()
    created_at = now_iso()
    promotion_allowed = drift.promotion_allowed and ood.promotion_allowed and reality_gap.promotion_allowed and acp.promotion_allowed
    payload = {
        "report_version": OPERATIONAL_SAFETY_VERSION,
        "symbol": normalized,
        "created_at": created_at,
        "drift": drift.model_dump(mode="json"),
        "ood": ood.model_dump(mode="json"),
        "reality_gap": reality_gap.model_dump(mode="json"),
        "acp": acp.model_dump(mode="json"),
        "promotion_allowed": promotion_allowed,
        "memory_quarantine_required": drift.memory_quarantine_required,
        "confidence_blocked": ood.confidence_blocked,
        "reality_gap_alert": reality_gap.alert,
    }
    report_hash = _canonical_hash(payload)
    report_id = f"safety-{normalized}-{report_hash[:18]}"
    return BehaviorSafetyReport(
        **payload,
        report_id=report_id,
        report_hash=report_hash,
        immutable=True,
        notes=[
            "Safety report is immutable and hash-addressed for audit replay.",
            "Promotion requires drift, OOD, reality-gap, and ACP gates to agree.",
        ],
    )


def build_memory_quarantine(
    request: MemoryQuarantineRequest,
    *,
    available_memory_ids: list[str],
    source_report: BehaviorSafetyReport | None = None,
) -> MemoryQuarantineRecord:
    normalized = request.symbol.upper()
    created_at = now_iso()
    affected = request.affected_memory_ids or available_memory_ids
    source_report_id = request.source_report_id or (source_report.report_id if source_report else None)
    reason = request.reason
    if source_report and source_report.memory_quarantine_required:
        reason = f"{reason}; drift_status={source_report.drift.drift_status}; drift_score={source_report.drift.drift_score}"
    quarantine_id = str(uuid5(NAMESPACE_URL, f"tradevision:quarantine:{normalized}:{source_report_id}:{reason}:{','.join(affected)}"))
    return MemoryQuarantineRecord(
        quarantine_version=OPERATIONAL_SAFETY_VERSION,
        quarantine_id=quarantine_id,
        symbol=normalized,
        created_at=created_at,
        status="active",
        reason=reason,
        source_report_id=source_report_id,
        actor_id=request.actor_id,
        affected_memory_ids=affected,
        confidence_blocked=True,
        memory_promotion_blocked=True,
        read_policy="read_allowed_for_audit_only",
        release_requires=[
            "point-in-time data rebuild completed",
            "golden replay fixture verification passed",
            "drift status returns stable",
            "OOD status returns normal",
            "reality-gap alert cleared",
            "manual risk review approved",
        ],
        notes=[
            "Quarantined memory cannot raise confidence or promote trades.",
            "Reads remain available only for audit and explanation of why confidence is blocked.",
        ],
    )


def build_memory_rebuild_plan(
    *,
    symbol: str,
    quarantines: list[MemoryQuarantineRecord],
) -> MemoryRebuildPlan:
    normalized = symbol.upper()
    active = [item for item in quarantines if item.status in {"active", "rebuild_pending"}]
    quarantine_id = active[0].quarantine_id if active else None
    plan_id = str(uuid5(NAMESPACE_URL, f"tradevision:rebuild-plan:{normalized}:{quarantine_id or 'clear'}"))
    return MemoryRebuildPlan(
        rebuild_version=OPERATIONAL_SAFETY_VERSION,
        plan_id=plan_id,
        symbol=normalized,
        quarantine_id=quarantine_id,
        created_at=now_iso(),
        allowed_to_rebuild=bool(active),
        required_inputs=[
            "immutable point-in-time OHLCV snapshots",
            "corporate action adjusted symbol history",
            "validated outcome labels",
            "golden replay fixture pass report",
            "latest drift/OOD/reality-gap safety report",
        ],
        rebuild_steps=[
            "freeze current quarantined memory for audit only",
            "recompute candle anatomy and context features from point-in-time snapshots",
            "relabel outcomes without future leakage",
            "rebuild similar-day clusters with minimum evidence guard",
            "run walk-forward and out-of-sample validation",
            "run drift, OOD, reality-gap, and ACP hardening checks",
            "release memory only after manual risk review",
        ],
        promotion_gates=[
            "minimum sample size >= 30",
            "golden replay deterministic verification passed",
            "drift_status == stable",
            "ood_status == normal",
            "reality_gap.alert == false",
            "ACP promotion_allowed == true",
            "no live broker route exists",
        ],
        estimated_safe_status="shadow_only" if active else "mock_ready",
        notes=[
            "Rebuild plan is a controlled workflow, not an automatic online-learning update.",
            "Memory release remains blocked until validation and human risk approval pass.",
        ],
    )


def build_golden_replay_fixture(*, symbol: str, scenario_id: str, seed: int, events: list[MarketEvent]) -> GoldenReplayFixture:
    if not events:
        raise ValueError("Golden replay fixture requires at least one event.")
    normalized = symbol.upper()
    chain_hash = event_chain_hash(events)
    fixture_id = f"golden-{_safe_id(normalized)}-{_safe_id(scenario_id)}-{seed}"
    return GoldenReplayFixture(
        fixture_version=OPERATIONAL_SAFETY_VERSION,
        fixture_id=fixture_id,
        symbol=normalized,
        scenario_id=scenario_id,
        seed=seed,
        expected_event_count=len(events),
        expected_first_event_id=events[0].event_id,
        expected_last_event_id=events[-1].event_id,
        expected_chain_hash=chain_hash,
        safety_assertions=[
            "same seed and scenario must produce identical event IDs",
            "same seed and scenario must produce identical watermark chain hash",
            "fixture verification cannot enable live trading",
            "fixture failure blocks promotion",
        ],
    )


def verify_golden_replay_fixture(fixture: GoldenReplayFixture, events: list[MarketEvent]) -> GoldenReplayVerificationResult:
    actual_chain_hash = event_chain_hash(events)
    first_id = events[0].event_id if events else None
    last_id = events[-1].event_id if events else None
    issues: list[str] = []
    if len(events) != fixture.expected_event_count:
        issues.append("Event count does not match fixture.")
    if first_id != fixture.expected_first_event_id:
        issues.append("First event ID does not match fixture.")
    if last_id != fixture.expected_last_event_id:
        issues.append("Last event ID does not match fixture.")
    if actual_chain_hash != fixture.expected_chain_hash:
        issues.append("Watermark chain hash does not match fixture.")
    return GoldenReplayVerificationResult(
        verification_version=OPERATIONAL_SAFETY_VERSION,
        fixture=fixture,
        actual_event_count=len(events),
        actual_first_event_id=first_id,
        actual_last_event_id=last_id,
        actual_chain_hash=actual_chain_hash,
        deterministic=not issues,
        passed=not issues,
        issues=issues,
        live_trading_blocked=True,
    )


def event_chain_hash(events: list[MarketEvent]) -> str:
    payload = [
        {
            "event_id": event.event_id,
            "parent_event_id": event.parent_event_id,
            "sequence_number": event.sequence_number,
            "virtual_timestamp_ns": event.virtual_timestamp_ns,
            "watermark": event.watermark,
        }
        for event in events
    ]
    return _canonical_hash(payload)


def _canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")
