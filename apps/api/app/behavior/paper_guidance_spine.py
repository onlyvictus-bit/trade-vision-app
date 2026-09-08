from __future__ import annotations

"""M2 Paper Guidance orchestration.

The pre-M2 implementation is preserved byte-for-byte in
``paper_guidance_spine_legacy.py``. Public helpers/constants remain re-exported
from that module. Only ``run_paper_guidance_p1`` is overridden here so M2 can
insert canonical Stage2 inventory + DecisionContext construction before the
existing D6 request without rewriting the validated D1/D2 and specialist code.
"""

from uuid import NAMESPACE_URL, uuid5

from . import paper_guidance_spine_legacy as _legacy
from .paper_guidance_spine_legacy import *  # noqa: F401,F403
from .decision_spine.decision_context import DecisionContextError
from .decision_spine.paper_guidance_decision_context_adapter import (
    build_canonical_stage2_observations,
    build_paper_guidance_decision_context,
    decision_context_audit_summary,
)
from .decision_spine.stage2_integrity import build_stage2_integrity_report


def __getattr__(name: str):
    """Delegate private legacy helpers for compatibility during M2 migration."""

    return getattr(_legacy, name)


def run_paper_guidance_p1(
    request,
    *,
    mode,
    kill_switch,
    config=None,
):
    """Run Paper Guidance with M2 canonical context before the unchanged D6.

    The M2 layer performs orchestration/integrity work only. It does not run new
    market calculations, fetch data, grant paper authority, or alter D6 inputs.
    """

    settings = config or _legacy.load_paper_guidance_config()
    base = _legacy.run_paper_guidance_p0(
        request,
        mode=mode,
        kill_switch=kill_switch,
        config=settings,
    )
    if not base.safety_gate.passed or base.snapshot is None or base.snapshot_hash is None:
        return base

    snapshot = base.snapshot
    series = _legacy._series_from_snapshot(snapshot)
    receipts = []
    warnings = list(base.warnings)
    engines_run = ["D1_SAFETY_GATE", "D2_CLOSED_CANDLE_SNAPSHOT"]
    engines_skipped = []

    chart, chart_receipt = _legacy._run_engine(
        "CHART_REASONING",
        "D3A_SETUP",
        snapshot,
        lambda: _legacy.build_chart_reasoning_report(_legacy.ChartReasoningRequest(series=series)),
        lambda value: {
            "trend_health": value.trend_health,
            "chop_risk": value.chop_risk,
            "volatility_regime": value.volatility_regime,
            "trend_persistence_score": value.trend_persistence_score,
        },
    )
    receipts.append(chart_receipt)
    _legacy._record_engine_state(chart_receipt, engines_run, engines_skipped, warnings)

    condition, condition_receipt = _legacy._run_engine(
        "CANDLE_CONDITION",
        "D3A_SETUP",
        snapshot,
        lambda: _legacy.classify_conditions(_legacy.ConditionClassifierRequest(series=series)),
        lambda value: {
            "market_state": value.market_state,
            "signal_bias": value.final_signal_bias,
            "blocks_trade": value.blocks_trade,
        },
    )
    receipts.append(condition_receipt)
    _legacy._record_engine_state(condition_receipt, engines_run, engines_skipped, warnings)

    levels, levels_receipt = _legacy._run_engine(
        "LEVEL_CONTEXT",
        "D3A_SETUP",
        snapshot,
        lambda: _legacy.analyze_level_context(
            _legacy.VwapOrbCprContextRequest(
                series=series,
                decision_time_ns=snapshot.decision_time_ns,
            )
        ),
        lambda value: {
            "vwap_state": value.vwap_state,
            "opening_range_state": value.opening_range_state,
            "level_respect_score": value.level_respect_score,
            "blocks_trade": value.blocks_trade,
        },
    )
    receipts.append(levels_receipt)
    _legacy._record_engine_state(levels_receipt, engines_run, engines_skipped, warnings)

    indicator_summary, indicator_receipt = _legacy._snapshot_indicator_evidence(request, snapshot)
    receipts.append(indicator_receipt)
    _legacy._record_engine_state(indicator_receipt, engines_run, engines_skipped, warnings)

    mtf_evidence = _legacy._build_mtf_evidence(request, snapshot)
    mtf_receipt = _legacy._receipt(
        engine_id="MTF_CONFIRMATION",
        stage="D3B_MEMORY",
        engine_version="behavior-context.v0.16",
        snapshot=snapshot,
        status="completed" if not mtf_evidence.missing_required_timeframes else "degraded",
        output_summary=mtf_evidence.model_dump(mode="json"),
        warnings=[
            f"Missing required higher timeframes: {', '.join(mtf_evidence.missing_required_timeframes)}."
        ]
        if mtf_evidence.missing_required_timeframes
        else [],
    )
    receipts.append(mtf_receipt)
    _legacy._record_engine_state(mtf_receipt, engines_run, engines_skipped, warnings)

    memory_summary, memory_receipt = _legacy._build_persisted_memory_evidence(
        request,
        snapshot,
        indicator_summary["indicator_ids"],
        settings.minimum_evidence_count,
    )
    receipts.append(memory_receipt)
    _legacy._record_engine_state(memory_receipt, engines_run, engines_skipped, warnings)

    structure, structure_receipt = _legacy._run_engine(
        "MARKET_STRUCTURE_LIQUIDITY",
        "D4_STRUCTURE",
        snapshot,
        lambda: _legacy.build_market_structure_liquidity_report(
            _legacy.MarketStructureLiquidityRequest(series=series)
        ),
        lambda value: {
            "auction_state": value.auction_state,
            "profile_shape": value.profile_shape,
            "value_area_position": value.value_area_position,
            "trap_score": value.trap_score,
            "vsa_downgrade_active": value.vsa_downgrade_active,
            "confidence_cap": value.confidence_cap,
        },
    )
    receipts.append(structure_receipt)
    _legacy._record_engine_state(structure_receipt, engines_run, engines_skipped, warnings)

    execution_risk, execution_receipt = _legacy._run_engine(
        "EXECUTION_EVENT_OI_RISK",
        "D4_STRUCTURE",
        snapshot,
        lambda: _legacy.build_execution_event_oi_risk_report(
            _legacy.ExecutionEventOiRiskRequest(series=series)
        ),
        lambda value: {
            "liquidity_grade": value.liquidity_grade,
            "fill_probability": value.fill_probability,
            "slippage_risk": value.slippage_risk,
            "event_risk_score": value.event_risk_score,
            "event_context_status": value.event_context_status,
            "options_context_status": value.options_context_status,
            "depth_context_status": value.depth_context_status,
            "unavailable_reasons": value.unavailable_reasons,
            "confidence_cap": value.confidence_cap,
        },
    )
    receipts.append(execution_receipt)
    _legacy._record_engine_state(execution_receipt, engines_run, engines_skipped, warnings)

    if request.include_kronos:
        warnings.append("Kronos remains intentionally skipped in v1.88; it cannot boost guidance.")
    if request.include_orb_playbook:
        warnings.append("ORB remains intentionally skipped in v1.88; its primary setup role begins in v1.89.")
    engines_skipped.extend(
        [
            "D5_KRONOS:not_enabled_in_v1.88",
            "D3A_ORB:not_enabled_until_v1.89",
            "D7_JARVIS_CARD:not_enabled_until_v1.92",
            "D8_HUMAN_TO_PAPER:not_enabled_until_v1.93",
        ]
    )

    authoritative_count = int(memory_summary["historical_match_count"])
    low_evidence = authoritative_count < settings.minimum_evidence_count
    required_mtf_complete = not mtf_evidence.missing_required_timeframes

    # M2: complete the canonical inventory *before* the Stage2 report. Engines
    # that are implemented elsewhere but not D2-native here are explicit
    # UNAVAILABLE/SKIPPED facts; they are never silently neutralized.
    stage2_observations = build_canonical_stage2_observations(
        snapshot_hash=snapshot.snapshot_hash,
        active_engine_ids=[receipt.engine_id for receipt in receipts],
    )
    stage2_integrity = build_stage2_integrity_report(
        canonical_snapshot_hash=snapshot.snapshot_hash,
        engine_receipts=receipts,
        evidence_observations=stage2_observations,
    )
    if not stage2_integrity.canonical_context_eligible:
        return _stage2_blocked_guidance(
            base=base,
            snapshot=snapshot,
            settings=settings,
            stage2_integrity=stage2_integrity,
            receipts=receipts,
            mtf_evidence=mtf_evidence,
            memory_summary=memory_summary,
            authoritative_count=authoritative_count,
            low_evidence=low_evidence,
            engines_run=engines_run,
            engines_skipped=engines_skipped,
            warnings=warnings,
        )

    try:
        decision_context = build_paper_guidance_decision_context(
            snapshot=snapshot,
            data_quality=base.data_quality,
            point_in_time=base.point_in_time,
            receipts=receipts,
            stage2_integrity=stage2_integrity,
        )
    except DecisionContextError as exc:
        return _context_blocked_guidance(
            base=base,
            snapshot=snapshot,
            settings=settings,
            stage2_integrity=stage2_integrity,
            context_error=exc,
            receipts=receipts,
            mtf_evidence=mtf_evidence,
            memory_summary=memory_summary,
            authoritative_count=authoritative_count,
            low_evidence=low_evidence,
            engines_run=engines_run,
            engines_skipped=engines_skipped,
            warnings=warnings,
        )
    context_audit = decision_context_audit_summary(decision_context)

    # D6 inputs below are intentionally byte-for-byte equivalent in meaning to
    # the pre-M2 route. M2 records truthful context but does not alter scoring.
    arbiter_request = _legacy.FinalConfluenceArbiterRequest(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        direction=request.direction,
        data_quality_pass=not base.data_quality.blocks_trade,
        liquidity_grade=getattr(execution_risk, "liquidity_grade", "UNKNOWN"),
        market_regime_score=_legacy._market_regime_score(chart, request.direction),
        relative_strength_score=0.5,
        structure_score=_legacy._structure_score(condition, levels, structure, request.direction),
        volume_auction_score=_legacy._volume_auction_score(structure, request.direction),
        indicator_signal_score=0.0,
        external_ai_score=0.0,
        trap_score=float(getattr(structure, "trap_score", 0.0)),
        event_risk_score=float(getattr(execution_risk, "event_risk_score", 0.0)),
        daily_resistance_conflict=_legacy._daily_resistance_conflict(levels, request.direction),
        weak_sector=False,
        post_entry_thesis_status="not_entered",
        evidence_count=authoritative_count,
        minimum_evidence_count=settings.minimum_evidence_count,
        low_evidence_flag=low_evidence,
        required_mtf_complete=required_mtf_complete,
        entry_plan_authority_present=False,
        no_future_leakage=True,
    )
    arbiter = _legacy.build_final_confluence_arbiter_report(arbiter_request)
    arbiter_receipt = _legacy._receipt(
        engine_id="FINAL_CONFLUENCE_ARBITER",
        stage="D6_ARBITER",
        engine_version=arbiter.arbiter_version,
        snapshot=snapshot,
        status="completed",
        output_summary={
            "decision_band": arbiter.decision_band,
            "final_decision": arbiter.final_decision,
            "confluence_score": arbiter.confluence_score,
            "dominant_blocker": arbiter.dominant_blocker,
        },
    )
    receipts.append(arbiter_receipt)
    _legacy._record_engine_state(arbiter_receipt, engines_run, engines_skipped, warnings)

    final_band = _legacy._paper_band_from_arbiter(arbiter.final_decision)
    confidence_cap = min(
        settings.p0_confidence_cap,
        arbiter.confidence_interval[1],
        settings.low_evidence_confidence_cap if low_evidence else 1.0,
    )
    blockers = list(base.blockers)
    if low_evidence:
        blockers.append(
            f"Only {authoritative_count} completed persisted records were available; "
            f"{settings.minimum_evidence_count} are required."
        )
    if not required_mtf_complete:
        blockers.append(
            f"Required higher-timeframe evidence is missing: {', '.join(mtf_evidence.missing_required_timeframes)}."
        )
    blockers.append("A verified ORB entry/stop/target plan is not available until v1.92.")
    reason_for = [
        "D1 safety and D2 immutable snapshot checks passed.",
        *arbiter.human_reason_tree,
    ]
    reason_against = [
        *[receipt_warning for receipt in receipts for receipt_warning in receipt.warnings],
        "v1.88 has no entry-plan authority, so the final result cannot exceed WATCH.",
    ]
    guidance_id = str(
        uuid5(
            NAMESPACE_URL,
            "tradevision:paper-guidance:v1.88:"
            + snapshot.snapshot_hash
            + ":"
            + _legacy._hash_payload([receipt.output_hash for receipt in receipts]),
        )
    )
    return _legacy.PaperTradeGuidance(
        guidance_version=_legacy.PAPER_GUIDANCE_P1_VERSION,
        guidance_id=guidance_id,
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        decision_time=snapshot.decision_time,
        snapshot_hash=snapshot.snapshot_hash,
        snapshot=snapshot,
        final_band=final_band,
        confidence_cap=round(confidence_cap, 4),
        next_action="DO_NOTHING",
        blockers=_legacy._unique(blockers),
        warnings=_legacy._unique(warnings),
        reason_for=_legacy._unique(reason_for),
        reason_against=_legacy._unique(reason_against),
        entry_plan=None,
        evidence_votes=[
            _legacy.PaperGuidanceEvidenceVote(
                engine_id=vote.evidence_layer,
                vote=_legacy._paper_vote(vote.direction),
                weight=min(1.0, abs(vote.weighted_score) / 7.0),
                lag_penalty=0.0 if vote.evidence_layer != "indicators" else 0.5,
                note=vote.reason,
            )
            for vote in arbiter.evidence_votes
        ],
        engine_receipts=receipts,
        mtf_evidence=mtf_evidence,
        arbiter_summary={
            "arbiter_version": arbiter.arbiter_version,
            "decision_band": arbiter.decision_band,
            "final_decision": arbiter.final_decision,
            "confluence_score": arbiter.confluence_score,
            "dominant_blocker": arbiter.dominant_blocker,
            "gates": [gate.model_dump(mode="json") for gate in arbiter.gates],
        },
        engines_run=_legacy._unique(engines_run),
        engines_skipped=_legacy._unique(engines_skipped),
        memory_summary=memory_summary,
        risk_summary={
            "system_mode": mode.mode.value,
            "kill_switch_state": kill_switch.state,
            "data_quality_score": base.data_quality.data_quality_score,
            "point_in_time_passed": base.point_in_time.passed,
            "liquidity_grade": getattr(execution_risk, "liquidity_grade", "UNKNOWN"),
            "event_context_status": getattr(execution_risk, "event_context_status", "unavailable"),
            "options_context_status": getattr(execution_risk, "options_context_status", "unavailable"),
            "paper_entry_authority": False,
            "stage2_integrity": stage2_integrity.as_dict(),
            "decision_context": context_audit,
        },
        data_quality=base.data_quality,
        point_in_time=base.point_in_time,
        safety_gate=base.safety_gate,
        low_evidence_flag=low_evidence,
        historical_match_count=authoritative_count,
        minimum_evidence_count=settings.minimum_evidence_count,
    )


def _stage2_blocked_guidance(
    *,
    base,
    snapshot,
    settings,
    stage2_integrity,
    receipts,
    mtf_evidence,
    memory_summary,
    authoritative_count,
    low_evidence,
    engines_run,
    engines_skipped,
    warnings,
):
    stage2_blockers = [f"Stage-2 integrity: {item}" for item in stage2_integrity.hard_blockers]
    blocked_guidance_id = str(
        uuid5(
            NAMESPACE_URL,
            "tradevision:paper-guidance:stage2-block:"
            + snapshot.snapshot_hash
            + ":"
            + stage2_integrity.output_hash,
        )
    )
    return base.model_copy(
        update={
            "guidance_version": _legacy.PAPER_GUIDANCE_P1_VERSION,
            "guidance_id": blocked_guidance_id,
            "final_band": "WAIT",
            "confidence_cap": min(base.confidence_cap, settings.p0_confidence_cap),
            "next_action": "DO_NOTHING",
            "blockers": _legacy._unique(list(base.blockers) + stage2_blockers),
            "warnings": _legacy._unique(warnings + list(stage2_integrity.warnings)),
            "reason_for": _legacy._unique(list(base.reason_for) + ["D1 safety and D2 immutable snapshot checks passed."]),
            "reason_against": _legacy._unique(
                list(base.reason_against)
                + ["Stage-2 evidence integrity blocked canonical evidence before D6 arbitration."]
            ),
            "entry_plan": None,
            "evidence_votes": [],
            "engine_receipts": receipts,
            "mtf_evidence": mtf_evidence,
            "arbiter_summary": {
                "arbiter_run": False,
                "blocked_before_d6": True,
                "stage2_integrity_hash": stage2_integrity.output_hash,
            },
            "engines_run": _legacy._unique(engines_run),
            "engines_skipped": _legacy._unique(engines_skipped + ["D6_ARBITER:stage2_integrity_block"]),
            "memory_summary": memory_summary,
            "risk_summary": {
                **base.risk_summary,
                "paper_entry_authority": False,
                "stage2_integrity": stage2_integrity.as_dict(),
                "decision_context": None,
            },
            "low_evidence_flag": low_evidence,
            "historical_match_count": authoritative_count,
            "minimum_evidence_count": settings.minimum_evidence_count,
        }
    )


def _context_blocked_guidance(
    *,
    base,
    snapshot,
    settings,
    stage2_integrity,
    context_error,
    receipts,
    mtf_evidence,
    memory_summary,
    authoritative_count,
    low_evidence,
    engines_run,
    engines_skipped,
    warnings,
):
    reason = f"DecisionContext integrity: {type(context_error).__name__}: {context_error}"
    blocked_guidance_id = str(
        uuid5(
            NAMESPACE_URL,
            "tradevision:paper-guidance:m2-context-block:"
            + snapshot.snapshot_hash
            + ":"
            + stage2_integrity.output_hash
            + ":"
            + _legacy._hash_payload(reason),
        )
    )
    return base.model_copy(
        update={
            "guidance_version": _legacy.PAPER_GUIDANCE_P1_VERSION,
            "guidance_id": blocked_guidance_id,
            "final_band": "WAIT",
            "confidence_cap": min(base.confidence_cap, settings.p0_confidence_cap),
            "next_action": "DO_NOTHING",
            "blockers": _legacy._unique(list(base.blockers) + [reason]),
            "warnings": _legacy._unique(warnings + list(stage2_integrity.warnings)),
            "reason_for": _legacy._unique(list(base.reason_for) + ["D1 safety, D2 snapshot, and Stage2 integrity checks passed."]),
            "reason_against": _legacy._unique(
                list(base.reason_against)
                + ["Canonical DecisionContext construction failed closed before D6 arbitration."]
            ),
            "entry_plan": None,
            "evidence_votes": [],
            "engine_receipts": receipts,
            "mtf_evidence": mtf_evidence,
            "arbiter_summary": {
                "arbiter_run": False,
                "blocked_before_d6": True,
                "stage2_integrity_hash": stage2_integrity.output_hash,
                "decision_context_error": reason,
            },
            "engines_run": _legacy._unique(engines_run),
            "engines_skipped": _legacy._unique(engines_skipped + ["D6_ARBITER:decision_context_block"]),
            "memory_summary": memory_summary,
            "risk_summary": {
                **base.risk_summary,
                "paper_entry_authority": False,
                "stage2_integrity": stage2_integrity.as_dict(),
                "decision_context": None,
            },
            "low_evidence_flag": low_evidence,
            "historical_match_count": authoritative_count,
            "minimum_evidence_count": settings.minimum_evidence_count,
        }
    )
