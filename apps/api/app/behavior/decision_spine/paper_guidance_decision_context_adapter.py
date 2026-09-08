from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .decision_context import (
    CANONICAL_EVIDENCE_FIELDS,
    DecisionContext,
    DecisionContextError,
    DecisionIdentity,
    EvidenceBlock,
    InputIntegrity,
    IntegrityState,
    build_decision_context,
)
from .stage2_integrity import (
    Availability,
    EngineIntegrityState,
    EvidenceObservation,
    SourceMode,
    Stage2IntegrityReport,
)


PAPER_GUIDANCE_CONTEXT_ADAPTER_VERSION = "paper-guidance-decision-context-adapter.v1"


@dataclass(frozen=True, slots=True)
class CanonicalFieldBinding:
    field_name: str
    source_engine: str
    inactive_status: Availability
    inactive_reason: str


# This table is intentionally conservative. Registering or implementing an
# engine elsewhere in the repository does not make it canonical evidence in the
# Paper Guidance route. M3 will migrate specialists one by one.
CANONICAL_FIELD_BINDINGS: tuple[CanonicalFieldBinding, ...] = (
    CanonicalFieldBinding("price_structure", "MARKET_STRUCTURE_LIQUIDITY", Availability.UNAVAILABLE, "Market-structure receipt is not available in this Paper Guidance run."),
    CanonicalFieldBinding("candle_anatomy", "CANDLE_ANATOMY", Availability.UNAVAILABLE, "Candle Anatomy is not yet D2-native in the canonical Paper Guidance route."),
    CanonicalFieldBinding("levels", "LEVEL_CONTEXT", Availability.UNAVAILABLE, "Level Context receipt is not available in this Paper Guidance run."),
    CanonicalFieldBinding("indicators", "SNAPSHOT_INDICATOR_RUNTIME", Availability.UNAVAILABLE, "Snapshot indicator receipt is not available in this Paper Guidance run."),
    CanonicalFieldBinding("market_regime", "MARKET_REGIME", Availability.UNAVAILABLE, "Canonical Market Regime specialist migration is deferred to M3."),
    CanonicalFieldBinding("session_context", "SESSION_MEMORY", Availability.UNAVAILABLE, "Canonical Session Memory migration is deferred to M3."),
    CanonicalFieldBinding("index_context", "INDEX_CONTEXT", Availability.UNAVAILABLE, "Canonical Index Context migration is deferred to M3."),
    CanonicalFieldBinding("sector_context", "SECTOR_CONTEXT", Availability.UNAVAILABLE, "Canonical Sector Context migration is deferred to M3."),
    CanonicalFieldBinding("relative_strength", "RELATIVE_STRENGTH", Availability.UNAVAILABLE, "Canonical Relative Strength migration is deferred to M3."),
    CanonicalFieldBinding("memory", "PERSISTED_INDICATOR_MEMORY", Availability.UNAVAILABLE, "Persisted indicator memory receipt is not available in this Paper Guidance run."),
    CanonicalFieldBinding("historical_analogs", "ANALOG_MEMORY", Availability.UNAVAILABLE, "Canonical historical analog memory migration is deferred to M3."),
    CanonicalFieldBinding("hypotheses", "HYPOTHESIS_ENGINE", Availability.UNAVAILABLE, "Canonical Hypothesis Engine migration is deferred to M3."),
    CanonicalFieldBinding("strategy_candidates", "ORB_CORE", Availability.SKIPPED, "ORB strategy candidates are intentionally not activated in M2."),
    CanonicalFieldBinding("orb_variants", "ORB_CORE", Availability.SKIPPED, "ORB variants are intentionally not activated in M2."),
    CanonicalFieldBinding("afre_scenarios", "AFRE", Availability.SKIPPED, "AFRE scenarios are intentionally not activated in M2."),
    CanonicalFieldBinding("derivatives", "DERIVATIVES", Availability.UNAVAILABLE, "Canonical derivatives evidence is not yet wired into Paper Guidance."),
    CanonicalFieldBinding("events", "EXECUTION_EVENT_OI_RISK", Availability.UNAVAILABLE, "Execution/Event/OI receipt is not available in this Paper Guidance run."),
    CanonicalFieldBinding("failure_scenarios", "FAILURE_DETECTOR", Availability.UNAVAILABLE, "Canonical failure-scenario migration is deferred to M3."),
    CanonicalFieldBinding("execution_quality", "EXECUTION_EVENT_OI_RISK", Availability.UNAVAILABLE, "Execution/Event/OI receipt is not available in this Paper Guidance run."),
    CanonicalFieldBinding("portfolio_risk", "BEHAVIOR_RISK", Availability.UNAVAILABLE, "Canonical portfolio-risk migration is deferred to M3."),
    CanonicalFieldBinding("proof_status", "AFRE", Availability.SKIPPED, "No canonical proof authority is activated in M2; AFRE cannot grant proof authority."),
    CanonicalFieldBinding("paper_authority", "BEHAVIOR_DECISION", Availability.UNAVAILABLE, "No canonical paper-authority specialist is activated in M2."),
)

_BINDING_BY_FIELD = {item.field_name: item for item in CANONICAL_FIELD_BINDINGS}
if tuple(_BINDING_BY_FIELD) != CANONICAL_EVIDENCE_FIELDS:
    raise RuntimeError("M2 canonical field binding table must exactly match CANONICAL_EVIDENCE_FIELDS")


def build_canonical_stage2_observations(
    *,
    snapshot_hash: str,
    active_engine_ids: Sequence[str],
) -> tuple[EvidenceObservation, ...]:
    """Return explicit Stage2 observations for canonical engines that did not run.

    This function performs no I/O and no market calculation. It only completes
    the causal inventory so missing evidence cannot be silently interpreted as
    neutral or safe.
    """

    active = {str(item).strip().upper() for item in active_engine_ids if str(item).strip()}
    observations: dict[str, EvidenceObservation] = {}
    for binding in CANONICAL_FIELD_BINDINGS:
        engine_id = binding.source_engine
        if engine_id in active or engine_id in observations:
            continue
        observations[engine_id] = EvidenceObservation(
            engine_id=engine_id,
            source_snapshot_hash=snapshot_hash,
            availability=binding.inactive_status,
            source_mode=SourceMode.UNKNOWN,
            identity_match=True,
            used_for_probability=False,
            neutral_default_substituted=False,
            final_band_claimed=False,
            future_leakage_detected=False,
            explanation_only=True,
            unavailable_reasons=(binding.inactive_reason,),
            notes=("M2 explicit canonical inventory; repository presence does not imply runtime availability.",),
        )
    return tuple(observations[key] for key in sorted(observations))


def build_paper_guidance_decision_context(
    *,
    snapshot: Any,
    data_quality: Any,
    point_in_time: Any,
    receipts: Sequence[Any],
    stage2_integrity: Stage2IntegrityReport,
) -> DecisionContext:
    """Assemble the canonical M2 world-state from already-computed evidence.

    Strictly no fetching, persistence reads, specialist execution, indicator
    calculation, probability calculation, ORB/AFRE execution, AI calls, or D6
    arbitration are permitted here.
    """

    snapshot_hash = str(_get(snapshot, "snapshot_hash", "")).lower()
    decision_time_ns = int(_get(snapshot, "decision_time_ns", 0))
    if decision_time_ns <= 0:
        raise DecisionContextError("Paper Guidance snapshot must provide decision_time_ns")

    identity = DecisionIdentity(
        symbol=str(_get(snapshot, "symbol", "")),
        timeframe=str(_get(snapshot, "timeframe", "")),
        decision_time=datetime.fromtimestamp(decision_time_ns / 1_000_000_000, tz=timezone.utc),
        snapshot_hash=snapshot_hash,
        # Paper Guidance currently has no canonical universe watermark contract.
        # Empty means unknown, not a fabricated PASS.
        universe_watermark="",
    )

    input_reasons: list[str] = []
    pit_passed = bool(_get(point_in_time, "passed", False))
    pit_status = IntegrityState.PASS if pit_passed else IntegrityState.BLOCK
    if not pit_passed:
        input_reasons.append("Point-in-time guard did not pass for the canonical D2 snapshot.")

    # PIT correctness and data freshness are different claims. Until a dedicated
    # D2-native freshness assessor is wired, freshness must remain UNKNOWN.
    freshness = IntegrityState.UNKNOWN
    input_reasons.append("No canonical D2-native freshness assessor is wired in this Paper Guidance path.")

    # D1 currently does not expose a canonical quarantine verdict for this path.
    quarantine_status = IntegrityState.UNKNOWN
    input_reasons.append("No canonical D1/D2 quarantine assessor is wired in this Paper Guidance path.")

    input_integrity = InputIntegrity(
        data_quality=float(_get(data_quality, "data_quality_score", 0.0)),
        pit_status=pit_status,
        freshness=freshness,
        quarantine_status=quarantine_status,
        reasons=tuple(input_reasons),
    )

    receipt_by_engine = _receipt_index(receipts)
    stage2_by_engine = _stage2_index(stage2_integrity)
    evidence: dict[str, EvidenceBlock] = {}

    for field_name in CANONICAL_EVIDENCE_FIELDS:
        binding = _BINDING_BY_FIELD[field_name]
        state = stage2_by_engine.get(binding.source_engine)
        if state is None:
            raise DecisionContextError(
                f"{field_name}: canonical source {binding.source_engine} is absent from Stage2 integrity"
            )
        receipt = receipt_by_engine.get(binding.source_engine)
        evidence[field_name] = _evidence_from_state(
            field_name=field_name,
            binding=binding,
            state=state,
            receipt=receipt,
            snapshot_hash=snapshot_hash,
        )

    return build_decision_context(
        identity=identity,
        input_integrity=input_integrity,
        stage2_integrity=stage2_integrity,
        evidence=evidence,
        blockers=(),
        warnings=stage2_integrity.warnings,
    )


def decision_context_audit_summary(context: DecisionContext) -> dict[str, Any]:
    statuses = [getattr(context, name).status for name in CANONICAL_EVIDENCE_FIELDS]
    return {
        "adapter_version": PAPER_GUIDANCE_CONTEXT_ADAPTER_VERSION,
        "context_version": context.context_version,
        "context_hash": context.context_hash,
        "snapshot_hash": context.identity.snapshot_hash,
        "stage2_integrity_hash": context.provenance.stage2_integrity_hash,
        "integrity": {
            "data_quality": context.input_integrity.data_quality,
            "pit_status": context.input_integrity.pit_status.value,
            "freshness": context.input_integrity.freshness.value,
            "quarantine_status": context.input_integrity.quarantine_status.value,
            "reasons": list(context.input_integrity.reasons),
        },
        "evidence": {
            "available_count": sum(item is Availability.AVAILABLE for item in statuses),
            "degraded_count": sum(item is Availability.DEGRADED for item in statuses),
            "unavailable_count": sum(item is Availability.UNAVAILABLE for item in statuses),
            "skipped_count": sum(item is Availability.SKIPPED for item in statuses),
            "error_count": sum(item is Availability.ERROR for item in statuses),
            "field_count": len(statuses),
        },
        "safety": {
            "paper_promotion_eligible": context.paper_promotion_eligible,
            "trade_allowed": context.trade_allowed,
            "order_routing_enabled": context.order_routing_enabled,
            "live_trading_blocked": context.live_trading_blocked,
        },
    }


def _evidence_from_state(
    *,
    field_name: str,
    binding: CanonicalFieldBinding,
    state: EngineIntegrityState,
    receipt: Any | None,
    snapshot_hash: str,
) -> EvidenceBlock:
    if receipt is None:
        reasons = _state_reasons(state, binding.inactive_reason)
        return EvidenceBlock(
            source_engine=binding.source_engine,
            source_snapshot_hash=snapshot_hash,
            status=state.availability,
            payload={},
            observed_at=None,
            source_mode=state.source_mode,
            evidence_version="m2-explicit-inactive.v1",
            capability_source=f"canonical-inventory:{binding.source_engine}",
            source_output_hash=None,
            reasons=reasons,
            warnings=state.warnings,
            used_for_probability=False,
        )

    receipt_snapshot = str(_get(receipt, "source_snapshot_hash", "")).lower()
    if receipt_snapshot != snapshot_hash:
        raise DecisionContextError(f"{field_name}: receipt snapshot hash mismatch")
    receipt_hash = str(_get(receipt, "output_hash", ""))
    summary = _get(receipt, "output_summary", {})
    if not isinstance(summary, Mapping):
        raise DecisionContextError(f"{field_name}: receipt output_summary must be a mapping")
    reasons = _state_reasons(state, f"Stage2 classified {binding.source_engine} as {state.availability.value}.")
    return EvidenceBlock(
        source_engine=binding.source_engine,
        source_snapshot_hash=snapshot_hash,
        status=state.availability,
        payload=dict(summary),
        observed_at=None,
        source_mode=state.source_mode,
        evidence_version=str(_get(receipt, "engine_version", "v1")),
        capability_source=f"paper-guidance-receipt:{binding.source_engine}",
        source_output_hash=receipt_hash,
        reasons=reasons if state.availability is not Availability.AVAILABLE else (),
        warnings=tuple(str(item) for item in (_get(receipt, "warnings", ()) or ())),
        used_for_probability=bool(_get(receipt, "used_for_probability", False)),
    )


def _state_reasons(state: EngineIntegrityState, fallback: str) -> tuple[str, ...]:
    reasons = tuple(str(item) for item in state.unavailable_reasons if str(item))
    if reasons:
        return tuple(sorted(set(reasons)))
    warning_reasons = tuple(str(item) for item in state.warnings if str(item))
    if warning_reasons:
        return tuple(sorted(set(warning_reasons)))
    return (fallback,)


def _receipt_index(receipts: Sequence[Any]) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for receipt in receipts:
        engine_id = str(_get(receipt, "engine_id", "")).strip().upper()
        if not engine_id:
            raise DecisionContextError("Paper Guidance receipt has no engine_id")
        if engine_id in index:
            raise DecisionContextError(f"duplicate Paper Guidance receipt: {engine_id}")
        index[engine_id] = receipt
    return index


def _stage2_index(stage2_integrity: Stage2IntegrityReport) -> dict[str, EngineIntegrityState]:
    index: dict[str, EngineIntegrityState] = {}
    for state in stage2_integrity.engine_states:
        engine_id = state.engine_id.strip().upper()
        if engine_id in index:
            raise DecisionContextError(f"duplicate Stage2 engine state: {engine_id}")
        index[engine_id] = state
    return index


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)
