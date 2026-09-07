from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorDataQualityResult,
    CandleBar,
    CandleSeries,
    ChartReasoningRequest,
    ClosedCandleSnapshot,
    ConditionClassifierRequest,
    ExecutionEventOiRiskRequest,
    FinalConfluenceArbiterRequest,
    HTFConfirmationRequest,
    KillSwitchState,
    MarketStructureLiquidityRequest,
    PaperGuidanceEngineReceipt,
    PaperGuidanceEvidenceVote,
    PaperGuidanceMtfEvidence,
    PaperGuidanceRequest,
    PaperGuidanceSafetyCheck,
    PaperGuidanceSafetyGate,
    PaperTradeGuidance,
    PointInTimeGuardRequest,
    PointInTimeGuardResult,
    SystemMode,
    SystemModeValue,
    VwapOrbCprContextRequest,
)
from ..storage import list_indicator_signal_history_records
from .chart_reasoning_volatility import build_chart_reasoning_report
from .condition_classifier import classify_conditions
from .context_engines import analyze_htf_confirmation, analyze_level_context
from .data_quality import scan_data_quality
from .execution_event_oi_risk import build_execution_event_oi_risk_report
from .final_confluence_arbiter import build_final_confluence_arbiter_report
from .market_structure_liquidity import build_market_structure_liquidity_report
from .paper_guidance_config import PaperGuidanceConfig, load_paper_guidance_config
from .point_in_time_guard import run_point_in_time_guard, timeframe_duration_ns
from .real_indicator_adapter import (
    REAL_RUNTIME_PROMOTED_INDICATORS,
    compute_real_indicator_outputs_with_telemetry,
)


PAPER_GUIDANCE_VERSION = "paper-trade-guidance.v1.87"
PAPER_GUIDANCE_GATE_VERSION = "paper-guidance-safety-gate.v1.87"
PAPER_GUIDANCE_SNAPSHOT_VERSION = "closed-candle-snapshot.v1.87"
PAPER_GUIDANCE_P1_VERSION = "paper-trade-guidance.v1.88"
PAPER_GUIDANCE_RECEIPT_VERSION = "paper-guidance-engine-receipt.v1.88"
# v1.99.2: bounded recent window for snapshot indicator computation (9C needs
# last-9 + warmup; slowest promoted lookback ~300 bars). Keeps every promoted
# indicator inside the latency warn band on any snapshot size.
SNAPSHOT_INDICATOR_WINDOW_BARS = 400


def run_paper_guidance_p1(
    request: PaperGuidanceRequest,
    *,
    mode: SystemMode,
    kill_switch: KillSwitchState,
    config: PaperGuidanceConfig | None = None,
) -> PaperTradeGuidance:
    """Run snapshot-native research guidance through the hardened D6 arbiter."""

    settings = config or load_paper_guidance_config()
    base = run_paper_guidance_p0(
        request,
        mode=mode,
        kill_switch=kill_switch,
        config=settings,
    )
    if not base.safety_gate.passed or base.snapshot is None or base.snapshot_hash is None:
        return base

    snapshot = base.snapshot
    series = _series_from_snapshot(snapshot)
    receipts: list[PaperGuidanceEngineReceipt] = []
    warnings = list(base.warnings)
    engines_run = ["D1_SAFETY_GATE", "D2_CLOSED_CANDLE_SNAPSHOT"]
    engines_skipped: list[str] = []

    chart, chart_receipt = _run_engine(
        "CHART_REASONING",
        "D3A_SETUP",
        snapshot,
        lambda: build_chart_reasoning_report(ChartReasoningRequest(series=series)),
        lambda value: {
            "trend_health": value.trend_health,
            "chop_risk": value.chop_risk,
            "volatility_regime": value.volatility_regime,
            "trend_persistence_score": value.trend_persistence_score,
        },
    )
    receipts.append(chart_receipt)
    _record_engine_state(chart_receipt, engines_run, engines_skipped, warnings)

    condition, condition_receipt = _run_engine(
        "CANDLE_CONDITION",
        "D3A_SETUP",
        snapshot,
        lambda: classify_conditions(ConditionClassifierRequest(series=series)),
        lambda value: {
            "market_state": value.market_state,
            "signal_bias": value.final_signal_bias,
            "blocks_trade": value.blocks_trade,
        },
    )
    receipts.append(condition_receipt)
    _record_engine_state(condition_receipt, engines_run, engines_skipped, warnings)

    levels, levels_receipt = _run_engine(
        "LEVEL_CONTEXT",
        "D3A_SETUP",
        snapshot,
        lambda: analyze_level_context(
            VwapOrbCprContextRequest(
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
    _record_engine_state(levels_receipt, engines_run, engines_skipped, warnings)

    indicator_summary, indicator_receipt = _snapshot_indicator_evidence(request, snapshot)
    receipts.append(indicator_receipt)
    _record_engine_state(indicator_receipt, engines_run, engines_skipped, warnings)

    mtf_evidence = _build_mtf_evidence(request, snapshot)
    mtf_receipt = _receipt(
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
    _record_engine_state(mtf_receipt, engines_run, engines_skipped, warnings)

    memory_summary, memory_receipt = _build_persisted_memory_evidence(
        request,
        snapshot,
        indicator_summary["indicator_ids"],
        settings.minimum_evidence_count,
    )
    receipts.append(memory_receipt)
    _record_engine_state(memory_receipt, engines_run, engines_skipped, warnings)

    structure, structure_receipt = _run_engine(
        "MARKET_STRUCTURE_LIQUIDITY",
        "D4_STRUCTURE",
        snapshot,
        lambda: build_market_structure_liquidity_report(
            MarketStructureLiquidityRequest(series=series)
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
    _record_engine_state(structure_receipt, engines_run, engines_skipped, warnings)

    execution_risk, execution_receipt = _run_engine(
        "EXECUTION_EVENT_OI_RISK",
        "D4_STRUCTURE",
        snapshot,
        lambda: build_execution_event_oi_risk_report(
            ExecutionEventOiRiskRequest(series=series)
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
    _record_engine_state(execution_receipt, engines_run, engines_skipped, warnings)

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
    arbiter_request = FinalConfluenceArbiterRequest(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        direction=request.direction,
        data_quality_pass=not base.data_quality.blocks_trade,
        liquidity_grade=getattr(execution_risk, "liquidity_grade", "UNKNOWN"),
        market_regime_score=_market_regime_score(chart, request.direction),
        relative_strength_score=0.5,
        structure_score=_structure_score(condition, levels, structure, request.direction),
        volume_auction_score=_volume_auction_score(structure, request.direction),
        indicator_signal_score=0.0,
        external_ai_score=0.0,
        trap_score=float(getattr(structure, "trap_score", 0.0)),
        event_risk_score=float(getattr(execution_risk, "event_risk_score", 0.0)),
        daily_resistance_conflict=_daily_resistance_conflict(levels, request.direction),
        weak_sector=False,
        post_entry_thesis_status="not_entered",
        evidence_count=authoritative_count,
        minimum_evidence_count=settings.minimum_evidence_count,
        low_evidence_flag=low_evidence,
        required_mtf_complete=required_mtf_complete,
        entry_plan_authority_present=False,
        no_future_leakage=True,
    )
    arbiter = build_final_confluence_arbiter_report(arbiter_request)
    arbiter_receipt = _receipt(
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
    _record_engine_state(arbiter_receipt, engines_run, engines_skipped, warnings)
    _run_d6_shadow(arbiter_request, arbiter, execution_risk, snapshot, series, request)

    final_band = _paper_band_from_arbiter(arbiter.final_decision)
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
            + _hash_payload([receipt.output_hash for receipt in receipts]),
        )
    )
    return PaperTradeGuidance(
        guidance_version=PAPER_GUIDANCE_P1_VERSION,
        guidance_id=guidance_id,
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        decision_time=snapshot.decision_time,
        snapshot_hash=snapshot.snapshot_hash,
        snapshot=snapshot,
        final_band=final_band,
        confidence_cap=round(confidence_cap, 4),
        next_action="DO_NOTHING",
        blockers=_unique(blockers),
        warnings=_unique(warnings),
        reason_for=_unique(reason_for),
        reason_against=_unique(reason_against),
        entry_plan=None,
        evidence_votes=[
            PaperGuidanceEvidenceVote(
                engine_id=vote.evidence_layer,
                vote=_paper_vote(vote.direction),
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
        engines_run=_unique(engines_run),
        engines_skipped=_unique(engines_skipped),
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
        },
        data_quality=base.data_quality,
        point_in_time=base.point_in_time,
        safety_gate=base.safety_gate,
        low_evidence_flag=low_evidence,
        historical_match_count=authoritative_count,
        minimum_evidence_count=settings.minimum_evidence_count,
    )


def run_paper_guidance_p0(
    request: PaperGuidanceRequest,
    *,
    mode: SystemMode,
    kill_switch: KillSwitchState,
    config: PaperGuidanceConfig | None = None,
) -> PaperTradeGuidance:
    settings = config or load_paper_guidance_config()
    decision_time_ns = _decision_time_ns(request)
    quality = scan_data_quality(request.series).model_copy(
        update={"checked_at": _iso_from_ns(decision_time_ns)}
    )
    point_in_time = run_point_in_time_guard(
        PointInTimeGuardRequest(
            series=request.series,
            decision_time_ns=decision_time_ns,
            source_timeframe=request.timeframe,
        )
    )
    safety_gate = build_d1_safety_gate(
        request,
        mode=mode,
        kill_switch=kill_switch,
        quality=quality,
        point_in_time=point_in_time,
        decision_time_ns=decision_time_ns,
        config=settings,
    )
    low_evidence = request.historical_match_count < settings.minimum_evidence_count

    if not safety_gate.passed:
        return _blocked_guidance(
            request,
            safety_gate=safety_gate,
            quality=quality,
            point_in_time=point_in_time,
            decision_time_ns=decision_time_ns,
            config=settings,
            low_evidence=low_evidence,
        )

    snapshot = freeze_d2_closed_candle_snapshot(
        request,
        decision_time_ns=decision_time_ns,
    )
    confidence_cap = settings.p0_confidence_cap
    warnings = list(safety_gate.warnings)
    reason_against = [
        "v1.87 P0 has no D3 setup, D3b memory, D4 structure, D5 Kronos, or D6 arbiter authority.",
        "Paper entry remains blocked until the later spine milestones are implemented and verified.",
    ]
    if low_evidence:
        confidence_cap = min(confidence_cap, settings.low_evidence_confidence_cap)
        warnings.append(
            f"Low evidence: {request.historical_match_count} matches are below the required "
            f"{settings.minimum_evidence_count}."
        )
        reason_against.append("Low evidence cannot be promoted to ENTER_PAPER.")
    if request.include_kronos:
        warnings.append("Kronos was requested but is intentionally skipped in v1.87 P0.")
    if request.include_orb_playbook:
        warnings.append("ORB playbook lookup was requested but is intentionally skipped in v1.87 P0.")

    guidance_id = str(
        uuid5(
            NAMESPACE_URL,
            f"tradevision:paper-guidance:{snapshot.snapshot_hash}:{request.historical_match_count}",
        )
    )
    return PaperTradeGuidance(
        guidance_version=PAPER_GUIDANCE_VERSION,
        guidance_id=guidance_id,
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        decision_time=snapshot.decision_time,
        snapshot_hash=snapshot.snapshot_hash,
        snapshot=snapshot,
        final_band="WATCH",
        confidence_cap=round(confidence_cap, 4),
        next_action="DO_NOTHING",
        blockers=[
            "ENTER_PAPER is unavailable in v1.87 P0 because downstream decision and human-approval stages are not active."
        ],
        warnings=_unique(warnings),
        reason_for=[
            "D1 safety gate passed.",
            f"D2 froze {snapshot.bar_count} fully closed {snapshot.timeframe} candles.",
            "The snapshot hash binds every downstream research consumer to the same immutable candle set.",
        ],
        reason_against=reason_against,
        entry_plan=None,
        evidence_votes=[],
        engines_run=["D1_SAFETY_GATE", "D2_CLOSED_CANDLE_SNAPSHOT"],
        engines_skipped=_p0_skipped_engines(),
        memory_summary={
            "historical_match_count": request.historical_match_count,
            "minimum_evidence_count": settings.minimum_evidence_count,
            "minimum_evidence_pass": not low_evidence,
            "low_evidence_flag": low_evidence,
        },
        risk_summary={
            "system_mode": mode.mode.value,
            "kill_switch_state": kill_switch.state,
            "data_quality_score": quality.data_quality_score,
            "point_in_time_passed": point_in_time.passed,
            "paper_entry_authority": False,
        },
        data_quality=quality,
        point_in_time=point_in_time,
        safety_gate=safety_gate,
        low_evidence_flag=low_evidence,
        historical_match_count=request.historical_match_count,
        minimum_evidence_count=settings.minimum_evidence_count,
    )


def build_d1_safety_gate(
    request: PaperGuidanceRequest,
    *,
    mode: SystemMode,
    kill_switch: KillSwitchState,
    quality: BehaviorDataQualityResult,
    point_in_time: PointInTimeGuardResult,
    decision_time_ns: int,
    config: PaperGuidanceConfig,
) -> PaperGuidanceSafetyGate:
    bars = request.series.bars
    finite_values = _all_values_finite(bars)
    checks = [
        _check(
            "PG-D1-001",
            "Research-only system mode",
            mode.mode != SystemModeValue.LIVE and not mode.allows_live_orders,
            "block",
            f"mode={mode.mode.value}; allows_live_orders={mode.allows_live_orders}",
        ),
        _check(
            "PG-D1-002",
            "Kill switch is armed",
            kill_switch.state == "armed" and not kill_switch.blocks_order_paths,
            "block",
            f"state={kill_switch.state}; blocks_order_paths={kill_switch.blocks_order_paths}",
        ),
        _check(
            "PG-D1-003",
            "Symbol identity matches candle series",
            request.symbol.upper() == request.series.symbol.upper(),
            "block",
            f"request={request.symbol.upper()}; series={request.series.symbol.upper()}",
        ),
        _check(
            "PG-D1-004",
            "Timeframe identity matches candle series",
            request.timeframe == request.series.timeframe,
            "block",
            f"request={request.timeframe}; series={request.series.timeframe}",
        ),
        _check(
            "PG-D1-005",
            "Input bar count is bounded",
            0 < len(bars) <= config.maximum_input_bars,
            "block",
            f"bars={len(bars)}; maximum={config.maximum_input_bars}",
        ),
        _check(
            "PG-D1-006",
            "OHLCV values are finite",
            finite_values,
            "block",
            "All OHLCV values are finite." if finite_values else "NaN or infinity was found in OHLCV.",
        ),
        _check(
            "PG-D1-007",
            "Data quality meets threshold",
            not quality.blocks_trade and quality.data_quality_score >= config.minimum_data_quality_score,
            "block",
            f"score={quality.data_quality_score:.4f}; threshold={config.minimum_data_quality_score:.4f}; "
            f"blocks_trade={quality.blocks_trade}",
        ),
        _check(
            "PG-D1-008",
            "All supplied candles are closed and point-in-time safe",
            point_in_time.passed,
            "block",
            f"allowed={point_in_time.allowed_bars}; blocked={point_in_time.blocked_bars}; "
            f"future={point_in_time.future_bar_blocked}; incomplete={point_in_time.incomplete_candle_blocked}",
        ),
        _check(
            "PG-D1-009",
            "Broker credentials and routing are unavailable",
            not mode.allows_broker_credentials,
            "block",
            f"allows_broker_credentials={mode.allows_broker_credentials}; order_routing_enabled=false",
        ),
    ]
    blockers = [check.name for check in checks if check.severity == "block" and not check.passed]
    warnings = [issue.message for issue in quality.issues if issue.severity == "warning"]
    passed = not blockers
    return PaperGuidanceSafetyGate(
        gate_version=PAPER_GUIDANCE_GATE_VERSION,
        decision_time_ns=decision_time_ns,
        mode=mode.mode,
        kill_switch_state=kill_switch.state,
        passed=passed,
        stop_pipeline=not passed,
        checks=checks,
        blockers=blockers,
        warnings=_unique(warnings),
    )


def freeze_d2_closed_candle_snapshot(
    request: PaperGuidanceRequest,
    *,
    decision_time_ns: int,
) -> ClosedCandleSnapshot:
    duration_ns = timeframe_duration_ns(request.timeframe)
    closed_bars = [
        bar
        for bar in request.series.bars
        if bar.timestamp_ns + duration_ns <= decision_time_ns
    ]
    if not closed_bars:
        raise ValueError("D2 requires at least one fully closed candle")

    payload = {
        "snapshot_version": PAPER_GUIDANCE_SNAPSHOT_VERSION,
        "symbol": request.symbol.upper(),
        "timeframe": request.timeframe,
        "decision_time_ns": decision_time_ns,
        "timezone_offset_minutes": request.timezone_offset_minutes,
        "source_schema_version": request.series.schema_version,
        "closed_ohlcv_bars": [
            bar.model_dump(mode="json")
            for bar in closed_bars
        ],
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    snapshot_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    snapshot_id = str(uuid5(NAMESPACE_URL, f"tradevision:paper-snapshot:{snapshot_hash}"))
    last_bar = closed_bars[-1]
    return ClosedCandleSnapshot(
        snapshot_version=PAPER_GUIDANCE_SNAPSHOT_VERSION,
        snapshot_id=snapshot_id,
        snapshot_hash=snapshot_hash,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        decision_time_ns=decision_time_ns,
        decision_time=_iso_from_ns(decision_time_ns),
        timezone_offset_minutes=request.timezone_offset_minutes,
        bar_count=len(closed_bars),
        first_bar_timestamp_ns=closed_bars[0].timestamp_ns,
        last_bar_timestamp_ns=last_bar.timestamp_ns,
        last_bar_close_time_ns=last_bar.timestamp_ns + duration_ns,
        closed_ohlcv_bars=closed_bars,
        source_schema_version=request.series.schema_version,
    )


def _blocked_guidance(
    request: PaperGuidanceRequest,
    *,
    safety_gate: PaperGuidanceSafetyGate,
    quality: BehaviorDataQualityResult,
    point_in_time: PointInTimeGuardResult,
    decision_time_ns: int,
    config: PaperGuidanceConfig,
    low_evidence: bool,
) -> PaperTradeGuidance:
    identity = ":".join(
        [
            request.symbol.upper(),
            request.timeframe,
            str(decision_time_ns),
            str(len(request.series.bars)),
            ",".join(safety_gate.blockers),
        ]
    )
    guidance_id = str(uuid5(NAMESPACE_URL, f"tradevision:blocked-paper-guidance:{identity}"))
    return PaperTradeGuidance(
        guidance_version=PAPER_GUIDANCE_VERSION,
        guidance_id=guidance_id,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        decision_time=_iso_from_ns(decision_time_ns),
        snapshot_hash=None,
        snapshot=None,
        final_band="WAIT",
        confidence_cap=0.0,
        next_action="DO_NOTHING",
        blockers=safety_gate.blockers,
        warnings=safety_gate.warnings,
        reason_for=[],
        reason_against=[
            "D1 safety gate failed, so D2 did not freeze data or mint a snapshot hash.",
            *[check.evidence for check in safety_gate.checks if not check.passed],
        ],
        entry_plan=None,
        evidence_votes=[],
        engines_run=["D1_SAFETY_GATE"],
        engines_skipped=["D2_CLOSED_CANDLE_SNAPSHOT", *_p0_skipped_engines()],
        memory_summary={
            "historical_match_count": request.historical_match_count,
            "minimum_evidence_count": config.minimum_evidence_count,
            "minimum_evidence_pass": not low_evidence,
            "low_evidence_flag": low_evidence,
        },
        risk_summary={
            "system_mode": safety_gate.mode.value,
            "kill_switch_state": safety_gate.kill_switch_state,
            "data_quality_score": quality.data_quality_score,
            "point_in_time_passed": point_in_time.passed,
            "paper_entry_authority": False,
        },
        data_quality=quality,
        point_in_time=point_in_time,
        safety_gate=safety_gate,
        low_evidence_flag=low_evidence,
        historical_match_count=request.historical_match_count,
        minimum_evidence_count=config.minimum_evidence_count,
    )


def _decision_time_ns(request: PaperGuidanceRequest) -> int:
    if request.decision_time_ns is not None:
        return request.decision_time_ns
    if not request.series.bars:
        return 0
    duration_ns = timeframe_duration_ns(request.timeframe)
    return max(bar.timestamp_ns + duration_ns for bar in request.series.bars)


def _all_values_finite(bars: list[CandleBar]) -> bool:
    for bar in bars:
        values = [bar.open, bar.high, bar.low, bar.close]
        if bar.volume is not None:
            values.append(bar.volume)
        if not all(math.isfinite(value) for value in values):
            return False
    return True


def _check(
    check_id: str,
    name: str,
    passed: bool,
    severity: str,
    evidence: str,
) -> PaperGuidanceSafetyCheck:
    return PaperGuidanceSafetyCheck(
        check_id=check_id,
        name=name,
        passed=passed,
        severity=severity,  # type: ignore[arg-type]
        evidence=evidence,
    )


def _iso_from_ns(timestamp_ns: int) -> str:
    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc).isoformat()


def _iso_to_ns(value: str) -> int:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp() * 1_000_000_000)
    except (TypeError, ValueError, OverflowError):
        return 2**63 - 1


def _p0_skipped_engines() -> list[str]:
    return [
        "D3A_SETUP:not_implemented_in_v1.87",
        "D3B_MEMORY:not_implemented_in_v1.87",
        "D4_STRUCTURE:not_implemented_in_v1.87",
        "D5_KRONOS:not_enabled_in_v1.87",
        "D6_ARBITER:not_implemented_in_v1.87",
        "D7_JARVIS_CARD:not_implemented_in_v1.87",
        "D8_HUMAN_TO_PAPER:not_implemented_in_v1.87",
    ]


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _series_from_snapshot(snapshot: ClosedCandleSnapshot) -> CandleSeries:
    return CandleSeries(
        symbol=snapshot.symbol,
        timeframe=snapshot.timeframe,
        bars=snapshot.closed_ohlcv_bars,
        snapshot_id=snapshot.snapshot_id,
        schema_version=snapshot.source_schema_version,
    )


def _run_engine(engine_id, stage, snapshot, runner, summarizer):
    try:
        result = runner()
        summary = summarizer(result)
        return result, _receipt(
            engine_id=engine_id,
            stage=stage,
            engine_version=_engine_version(result),
            snapshot=snapshot,
            status="completed",
            output_summary=summary,
        )
    except Exception as exc:
        warning = f"{engine_id} degraded safely: {type(exc).__name__}: {exc}"
        return None, _receipt(
            engine_id=engine_id,
            stage=stage,
            engine_version="unavailable",
            snapshot=snapshot,
            status="degraded",
            output_summary={"available": False},
            warnings=[warning],
        )


def _snapshot_indicator_evidence(
    request: PaperGuidanceRequest,
    snapshot: ClosedCandleSnapshot,
) -> tuple[dict, PaperGuidanceEngineReceipt]:
    # v1.99.2: compute on a bounded recent window. The 9C evidence needs only
    # the last 9 values plus warmup (slowest promoted indicator lookback ~300
    # bars); computing over the full snapshot history blew the 800 ms latency
    # guard on every indicator (2-6 s at 5000 bars) and degraded the receipt.
    selected = sorted(
        set(request.indicator_ids)
        if request.indicator_ids
        else REAL_RUNTIME_PROMOTED_INDICATORS
    )
    unsupported = [item for item in selected if item not in REAL_RUNTIME_PROMOTED_INDICATORS]
    runnable = [item for item in selected if item in REAL_RUNTIME_PROMOTED_INDICATORS]
    window_bars = SNAPSHOT_INDICATOR_WINDOW_BARS
    snapshot_bars = snapshot.closed_ohlcv_bars
    compute_bars = snapshot_bars[-window_bars:]
    candles = [
        {
            "event_time": _iso_from_ns(bar.timestamp_ns),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume or 0.0,
        }
        for bar in compute_bars
    ]
    warnings = (
        [f"Indicators are not promoted for real snapshot runtime: {', '.join(unsupported)}."]
        if unsupported
        else []
    )
    try:
        outputs, telemetry = compute_real_indicator_outputs_with_telemetry(candles, runnable)
        degraded = [
            str(item["indicator_id"])
            for item in telemetry
            if item.get("status") not in {"computed", "slow_warn"}
        ]
        if degraded:
            warnings.append(
                f"Indicators without usable snapshot output: {', '.join(degraded)}."
            )
        summary = {
            "indicator_ids": selected,
            "promoted_indicator_ids": runnable,
            "computed_count": len(outputs),
            "telemetry": telemetry,
            "source_timeframe": snapshot.timeframe,
            "source_bar_count": snapshot.bar_count,
            "compute_window_bars": len(compute_bars),
            "used_for_final_vote": False,
        }
        status = "completed" if not degraded and not unsupported else "degraded"
    except Exception as exc:
        summary = {
            "indicator_ids": selected,
            "promoted_indicator_ids": runnable,
            "computed_count": 0,
            "telemetry": [],
            "source_timeframe": snapshot.timeframe,
            "source_bar_count": snapshot.bar_count,
            "used_for_final_vote": False,
        }
        status = "degraded"
        warnings.append(f"Snapshot indicator runtime degraded safely: {type(exc).__name__}: {exc}")
    return summary, _receipt(
        engine_id="SNAPSHOT_INDICATOR_RUNTIME",
        stage="D3A_SETUP",
        engine_version="real-indicator-adapter-cache.v1",
        snapshot=snapshot,
        status=status,
        output_summary=summary,
        warnings=warnings,
    )


def _build_mtf_evidence(
    request: PaperGuidanceRequest,
    primary_snapshot: ClosedCandleSnapshot,
) -> PaperGuidanceMtfEvidence:
    snapshots: dict[str, ClosedCandleSnapshot] = {}
    reasons: list[str] = []
    for series in sorted(request.higher_timeframe_series, key=lambda item: item.timeframe):
        if series.symbol.upper() != primary_snapshot.symbol:
            reasons.append(
                f"{series.timeframe} was excluded because symbol {series.symbol.upper()} "
                f"does not match {primary_snapshot.symbol}."
            )
            continue
        try:
            mtf_request = PaperGuidanceRequest(
                symbol=primary_snapshot.symbol,
                timeframe=series.timeframe,
                series=series,
                decision_time_ns=primary_snapshot.decision_time_ns,
                direction=request.direction,
            )
            snapshot = freeze_d2_closed_candle_snapshot(
                mtf_request,
                decision_time_ns=primary_snapshot.decision_time_ns,
            )
            snapshots[series.timeframe] = snapshot
        except Exception as exc:
            reasons.append(
                f"{series.timeframe} was unavailable after closed-candle filtering: "
                f"{type(exc).__name__}: {exc}"
            )

    supplied = sorted({series.timeframe for series in request.higher_timeframe_series})
    usable = sorted(snapshots)
    missing = sorted(set(request.required_higher_timeframes) - set(usable))
    confirmation = analyze_htf_confirmation(
        HTFConfirmationRequest(
            symbol=primary_snapshot.symbol,
            decision_time_ns=primary_snapshot.decision_time_ns,
            direction=request.direction,
            higher_timeframe_series=[
                _series_from_snapshot(snapshots[timeframe])
                for timeframe in usable
            ],
        )
    )
    reasons.extend(confirmation.reasons)
    if missing:
        reasons.append(
            f"Required higher-timeframe evidence is missing: {', '.join(missing)}."
        )
    indicator_runtime: dict[str, dict] = {}
    selected = sorted(
        set(request.indicator_ids)
        if request.indicator_ids
        else REAL_RUNTIME_PROMOTED_INDICATORS
    )
    runnable = [
        indicator_id
        for indicator_id in selected
        if indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS
    ]
    for timeframe in usable:
        mtf_snapshot = snapshots[timeframe]
        candles = [
            {
                "event_time": _iso_from_ns(bar.timestamp_ns),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume or 0.0,
            }
            for bar in mtf_snapshot.closed_ohlcv_bars
        ]
        try:
            outputs, telemetry = compute_real_indicator_outputs_with_telemetry(
                candles,
                runnable,
            )
            indicator_runtime[timeframe] = {
                "source_snapshot_hash": mtf_snapshot.snapshot_hash,
                "source_bar_count": mtf_snapshot.bar_count,
                "indicator_ids": runnable,
                "computed_count": len(outputs),
                "telemetry": telemetry,
                "used_for_final_vote": False,
            }
        except Exception as exc:
            indicator_runtime[timeframe] = {
                "source_snapshot_hash": mtf_snapshot.snapshot_hash,
                "source_bar_count": mtf_snapshot.bar_count,
                "indicator_ids": runnable,
                "computed_count": 0,
                "telemetry": [],
                "used_for_final_vote": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            reasons.append(
                f"{timeframe} indicator runtime degraded safely: {type(exc).__name__}: {exc}"
            )
    return PaperGuidanceMtfEvidence(
        required_timeframes=request.required_higher_timeframes,
        supplied_timeframes=supplied,
        usable_timeframes=usable,
        missing_required_timeframes=missing,
        snapshot_hashes={
            timeframe: snapshots[timeframe].snapshot_hash
            for timeframe in usable
        },
        indicator_runtime_by_timeframe=indicator_runtime,
        confirmed=confirmation.confirmed,
        blocks_promotion=bool(missing) or confirmation.blocks_trade,
        reasons=_unique(reasons),
    )


def _build_persisted_memory_evidence(
    request: PaperGuidanceRequest,
    snapshot: ClosedCandleSnapshot,
    indicator_ids: list[str],
    minimum_evidence_count: int,
) -> tuple[dict, PaperGuidanceEngineReceipt]:
    records = []
    cutoff = _iso_from_ns(snapshot.decision_time_ns)
    for indicator_id in indicator_ids:
        records.extend(
            list_indicator_signal_history_records(
                symbol=snapshot.symbol,
                indicator_id=indicator_id,
                timeframe=snapshot.timeframe,
                limit=500,
                counted_only=True,
                available_by_decision_time_ns=snapshot.decision_time_ns,
                created_at_or_before=cutoff,
            )
        )
    complete = {
        record.history_id: record
        for record in records
        if record.label.label_status == "complete"
        and record.counted_in_reliability
        and record.no_future_leakage
        and not record.missing_mask
        and record.decision_time_ns <= snapshot.decision_time_ns
        and record.signal_time_ns <= snapshot.decision_time_ns
        and _iso_to_ns(record.created_at) <= snapshot.decision_time_ns
    }
    count = len(complete)
    low_evidence = count < minimum_evidence_count
    ignored_caller_count = request.historical_match_count
    summary = {
        "historical_match_count": count,
        "minimum_evidence_count": minimum_evidence_count,
        "minimum_evidence_pass": not low_evidence,
        "low_evidence_flag": low_evidence,
        "history_source": "persistent",
        "fixture_fallback_used": False,
        "indicator_count": len(indicator_ids),
        "caller_historical_match_count": ignored_caller_count,
        "caller_count_used_for_authority": False,
        "decision_time_cutoff": cutoff,
    }
    warnings = []
    if low_evidence:
        warnings.append(
            f"Only {count} completed persisted records were available; "
            f"{minimum_evidence_count} are required."
        )
    if ignored_caller_count:
        warnings.append(
            f"Caller historical_match_count={ignored_caller_count} was ignored for decision authority."
        )
    return summary, _receipt(
        engine_id="PERSISTED_INDICATOR_MEMORY",
        stage="D3B_MEMORY",
        engine_version="indicator-signal-history-store.v1.83",
        snapshot=snapshot,
        status="completed" if not low_evidence else "degraded",
        output_summary=summary,
        warnings=warnings,
    )


def _receipt(
    *,
    engine_id: str,
    stage: str,
    engine_version: str,
    snapshot: ClosedCandleSnapshot,
    status: str,
    output_summary: dict,
    warnings: list[str] | None = None,
) -> PaperGuidanceEngineReceipt:
    identity = {
        "engine_id": engine_id,
        "engine_version": engine_version,
        "source_snapshot_hash": snapshot.snapshot_hash,
        "output_summary": output_summary,
    }
    return PaperGuidanceEngineReceipt(
        receipt_version=PAPER_GUIDANCE_RECEIPT_VERSION,
        engine_id=engine_id,
        stage=stage,  # type: ignore[arg-type]
        engine_version=engine_version,
        source_snapshot_hash=snapshot.snapshot_hash,
        output_hash=_hash_payload(identity),
        status=status,  # type: ignore[arg-type]
        identity_match=True,
        output_summary=output_summary,
        warnings=warnings or [],
    )


def _record_engine_state(receipt, engines_run, engines_skipped, warnings):
    if receipt.status == "skipped":
        engines_skipped.append(f"{receipt.engine_id}:skipped")
    else:
        engines_run.append(receipt.engine_id)
    warnings.extend(receipt.warnings)


def _engine_version(value) -> str:
    for key in (
        "reasoning_version",
        "classifier_version",
        "context_version",
        "structure_version",
        "risk_version",
        "arbiter_version",
    ):
        version = getattr(value, key, None)
        if version:
            return str(version)
    return "unknown"


def _hash_payload(value) -> str:
    canonical = json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_safe(value):
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _market_regime_score(chart, direction: str) -> float:
    if chart is None:
        return 0.0
    score = float(chart.trend_persistence_score) * 2.0 - 1.0
    if direction == "short":
        score *= -1.0
    if chart.chop_risk == "high":
        score = min(score, -0.35)
    return max(-1.0, min(1.0, score))


def _structure_score(condition, levels, structure, direction: str) -> float:
    parts: list[float] = []
    if condition is not None:
        bias = condition.final_signal_bias
        score = 0.65 if bias == direction else -0.65 if bias in {"long", "short"} else -0.15
        if condition.blocks_trade:
            score = min(score, -0.55)
        parts.append(score)
    if levels is not None:
        score = levels.level_respect_score * 2.0 - 1.0
        if levels.blocks_trade:
            score = min(score, -0.55)
        parts.append(score)
    if structure is not None:
        score = 0.25
        if structure.vsa_downgrade_active:
            score -= 0.55
        score -= structure.trap_score * 0.65
        parts.append(score)
    if not parts:
        return 0.0
    return max(-1.0, min(1.0, sum(parts) / len(parts)))


def _volume_auction_score(structure, direction: str) -> float:
    if structure is None:
        return 0.0
    score = 0.2
    if structure.vsa_downgrade_active:
        score -= 0.65
    if structure.value_area_position == "above_value":
        score += 0.25 if direction == "long" else -0.25
    elif structure.value_area_position == "below_value":
        score += 0.25 if direction == "short" else -0.25
    return max(-1.0, min(1.0, score))


def _daily_resistance_conflict(levels, direction: str) -> bool:
    if levels is None or direction != "long":
        return False
    return any(
        flag in {"rejecting_pdh", "failed_orb_breakout"}
        for flag in levels.support_resistance_flags
    )


def _paper_vote(direction: str) -> str:
    if direction == "long":
        return "FOR"
    if direction in {"short", "block"}:
        return "AGAINST"
    return "NEUTRAL"


def _paper_band_from_arbiter(final_decision: str) -> str:
    if final_decision == "PAPER-CANDIDATE":
        return "WATCH"
    if final_decision == "SHORT PAPER-CANDIDATE":
        return "WATCH"
    if final_decision in {"WAIT", "WATCH", "AVOID"}:
        return final_decision
    return "WAIT"


def _run_d6_shadow(arbiter_request, arbiter, execution_risk, snapshot, series, request) -> None:
    """M2-D: run the D6 shadow comparator once per P1 run. Output-neutral by design.

    Returns None always; the divergence record goes to a bounded sidecar JSONL file
    (never into guidance, receipts, warnings, or hashes). Flag off (default) returns
    before importing anything or touching the filesystem.
    """
    import os

    if os.getenv("TRADEVISION_D6_SHADOW", "off").strip().lower() != "on":
        return
    from .d6_shadow_adapter import compare, risks_from_spine

    bars = list(getattr(series, "bars", []) or [])
    if not bars:
        return
    try:
        from .point_in_time_guard import timeframe_duration_ns

        duration_ns = timeframe_duration_ns(snapshot.timeframe)
        last_open_ns = int(bars[-1].timestamp_ns)
        # relative_strength arrives 0..1 in the arbiter request; the arbiter's own
        # vote uses (x*2-1), so the adapter receives the identical transform.
        layer_scores = {layer: float(getattr(arbiter_request, field, 0.0) or 0.0)
                        for layer, field in
                        (("market_regime", "market_regime_score"), ("structure_levels", "structure_score"),
                         ("volume_auction", "volume_auction_score"), ("indicators", "indicator_signal_score"))}
        layer_scores["relative_strength"] = float(getattr(arbiter_request, "relative_strength_score", 0.5) or 0.0) * 2.0 - 1.0
        record = compare(
            symbol=snapshot.symbol, timeframe=snapshot.timeframe, direction=arbiter_request.direction,
            layer_scores=layer_scores,
            risks=risks_from_spine(
                trap_score=float(getattr(arbiter_request, "trap_score", 0.0) or 0.0),
                event_risk_score=float(getattr(arbiter_request, "event_risk_score", 0.0) or 0.0),
                data_quality_pass=bool(getattr(arbiter_request, "data_quality_pass", False)),
                liquidity_grade=str(getattr(arbiter_request, "liquidity_grade", "UNKNOWN")),
                execution_slippage_risk=float(getattr(execution_risk, "slippage_risk", 0.0) or 0.0)),
            snapshot_id=snapshot.snapshot_hash, session_id=str(getattr(snapshot, "session_id", snapshot.symbol)),
            bar_open_ns=last_open_ns, bar_close_ns=last_open_ns + int(duration_ns),
            decision_ns=int(snapshot.decision_time_ns),
            entry=None, stop=None, target=None, entry_plan_authority_present=False,
            evidence_count=int(getattr(arbiter_request, "evidence_count", 0) or 0),
            minimum_evidence_count=int(getattr(arbiter_request, "minimum_evidence_count", 30) or 30),
            short_logic_enabled=bool(getattr(arbiter_request, "short_logic_enabled", False)),
            data_quality_pass=bool(getattr(arbiter_request, "data_quality_pass", False)),
            arbiter_band=str(getattr(arbiter, "final_decision", "WAIT")))
    except Exception:
        return  # Shadow must never break guidance; unrecordable divergence is dropped.
    if record is None:
        return
    path = os.getenv("TRADEVISION_D6_SHADOW_LOG", "data/d6_shadow_divergence.jsonl")
    try:
        lines: list[str] = []
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                lines = handle.read().splitlines()
        lines.append(json.dumps({"adapter_version": record.adapter_version, "input_hash": record.input_hash,
                                 "arbiter_band": record.arbiter_band, "d6_status": record.d6_status,
                                 "d6_side": record.d6_side, "d6_permission": record.d6_permission,
                                 "causes": list(record.causes)}, sort_keys=True))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines[-500:]) + "\n")
    except OSError:
        pass
