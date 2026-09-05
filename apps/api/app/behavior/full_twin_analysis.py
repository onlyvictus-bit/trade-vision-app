from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CombinationSimilarityReport,
    FullBehaviorForecast,
    FullTwinAnalysisGate,
    FullTwinAnalysisReport,
    FullTwinAnalysisRequest,
    KronosBarrierProjection,
    KronosForecastResult,
    TradeDecisionResult,
    now_iso,
)
from .combination_similarity import build_combination_similarity_report
from .shared_snapshot import build_kronos_shared_snapshot_forecast


FULL_TWIN_ANALYSIS_VERSION = "full-twin-analysis.v0.67"
KRONOS_BARRIER_PROJECTION_VERSION = "kronos-barrier-projection.v0.67"


def build_full_twin_analysis(
    request: FullTwinAnalysisRequest,
    *,
    behavior: TradeDecisionResult,
) -> FullTwinAnalysisReport:
    combination = build_combination_similarity_report(
        request=_combination_request_from_full(request)
    )
    shared = build_kronos_shared_snapshot_forecast(_shared_request_from_full(request))
    kronos = shared.kronos_forecast
    if request.force_kronos_hard_conflict:
        kronos = _force_kronos_direction(kronos, _opposite_direction(_behavior_bias(behavior.final_trade_decision)))
    behavior_forecast = _behavior_forecast(behavior, combination)
    projection = project_kronos_barriers(kronos)
    agreement_state, action, reasons = _arbiter_state(
        behavior=behavior,
        combination=combination,
        projection=projection,
        kronos=kronos,
        snapshot_ok=shared.integrity.identity_match,
    )
    boost_allowed = False
    confidence_delta = 0.0
    if agreement_state in {"AGREE_LONG", "AGREE_SHORT"}:
        reasons.append("Kronos agreement is recorded, but confidence boost is blocked until decorrelation and OOS reliability pass.")
    final_confidence = max(0.0, min(100.0, behavior.confidence_pct + confidence_delta))
    gates = _gates(behavior, combination, shared.integrity.identity_match, boost_allowed)
    payload = {
        "version": FULL_TWIN_ANALYSIS_VERSION,
        "symbol": request.symbol.upper(),
        "snapshot": shared.snapshot.source_snapshot_hash,
        "behavior": behavior.final_trade_decision,
        "kronos": kronos.forecast_path.trend_direction,
        "projection": projection.model_dump(mode="json"),
        "agreement_state": agreement_state,
        "action": action,
        "reasons": reasons,
    }
    evidence_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return FullTwinAnalysisReport(
        full_twin_version=FULL_TWIN_ANALYSIS_VERSION,
        generated_at=now_iso(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:full-twin:{request.symbol}:{request.seed}:{evidence_hash}")),
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        shared_snapshot=shared.snapshot,
        snapshot_integrity=shared.integrity,
        behavior=behavior_forecast,
        kronos=kronos,
        kronos_barrier_projection=projection,
        agreement_state=agreement_state,  # type: ignore[arg-type]
        arbiter_action=action,  # type: ignore[arg-type]
        behavior_authority_preserved=True,
        kronos_confidence_boost_allowed=boost_allowed,
        confidence_delta_from_kronos=confidence_delta,
        final_research_confidence_pct=round(final_confidence, 4),
        conflict_reasons=reasons,
        gates=gates,
        evidence_hash=evidence_hash,
        deterministic=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        kronos_cannot_execute_orders=True,
        kronos_cannot_override_no_trade=True,
        kronos_cannot_override_risk=True,
        openalgo_broker_route_created=False,
        notes=[
            "v0.67 compares Behavior memory/risk and Kronos only after v0.66 shared snapshot integrity.",
            "Kronos raw forecast candles are converted to target/stop/time-exit probabilities before comparison.",
            "Behavior risk/no-trade authority is preserved; Kronos agreement cannot override it.",
            "OpenAlgo integration remains an external future handoff and no broker route is created here.",
        ],
    )


def project_kronos_barriers(kronos: KronosForecastResult) -> KronosBarrierProjection:
    continuation = kronos.forecast_path.continuation_probability
    reversal = kronos.forecast_path.reversal_probability
    time_exit = kronos.forecast_path.range_probability
    total = max(1.0, continuation + reversal + time_exit)
    target = round(continuation / total * 100.0, 4)
    stop = round(reversal / total * 100.0, 4)
    time = round(max(0.0, 100.0 - target - stop), 4)
    closes = [float(candle["close"]) for candle in kronos.forecast_path.candles]
    first = closes[0] if closes else 0.0
    expected_mfe = round(max([value - first for value in closes] or [0.0]), 4)
    expected_mae = round(min([value - first for value in closes] or [0.0]), 4)
    return KronosBarrierProjection(
        projection_version=KRONOS_BARRIER_PROJECTION_VERSION,
        source_forecast_hash=kronos.output_hash,
        target_hit_probability_pct=target,
        stop_hit_probability_pct=stop,
        time_exit_probability_pct=time,
        expected_mfe=expected_mfe,
        expected_mae=expected_mae,
        path_chop_probability_pct=round(kronos.forecast_path.range_probability, 4),
        barrier_sequence_distribution={
            "TARGET_FIRST": target,
            "STOP_FIRST": stop,
            "TIME_EXIT": time,
        },
        raw_path_not_direct_evidence=True,
    )


def _behavior_forecast(behavior: TradeDecisionResult, combination: CombinationSimilarityReport) -> FullBehaviorForecast:
    return FullBehaviorForecast(
        forecast_version=f"{FULL_TWIN_ANALYSIS_VERSION}.behavior-forecast",
        symbol=behavior.symbol,
        behavior_decision=behavior,
        combination_similarity=combination,
        behavior_target_hit_probability_pct=combination.continuation_probability_pct,
        behavior_stop_hit_probability_pct=max(combination.reversal_probability_pct, combination.fakeout_probability_pct),
        behavior_time_exit_probability_pct=combination.range_probability_pct,
        behavior_expected_mfe=round(combination.continuation_probability_pct / 25.0, 4),
        behavior_expected_mae=round(-max(combination.reversal_probability_pct, combination.fakeout_probability_pct) / 25.0, 4),
        behavior_uncertainty_pct=round(100.0 - min(100.0, combination.continuation_probability_pct + combination.fakeout_probability_pct), 4),
        risk_or_no_trade_authority=True,
    )


def _arbiter_state(
    *,
    behavior: TradeDecisionResult,
    combination: CombinationSimilarityReport,
    projection: KronosBarrierProjection,
    kronos: KronosForecastResult,
    snapshot_ok: bool,
) -> tuple[str, str, list[str]]:
    reasons: list[str] = []
    if not snapshot_ok:
        return "SNAPSHOT_MISMATCH", "WAIT", ["Shared snapshot identity failed; Twin comparison is blocked."]
    if behavior.final_trade_decision in {"NO_TRADE", "WAIT", "AVOID_CHOP", "FAKEOUT_WARNING"} or not behavior.trade_allowed:
        return "NO_TRADE", "NO_TRADE", ["Behavior memory/risk/no-trade authority blocks the setup; Kronos cannot override."]
    if any(gate.severity == "block" for gate in behavior.gates) or behavior.no_trade.active:
        return "NO_TRADE", "NO_TRADE", ["Behavior blocking gates are active; Kronos cannot override risk."]
    if not combination.minimum_sample_pass:
        return "LOW_CONFIDENCE", "WAIT", ["Behavior combination memory has low evidence; Twin cannot promote confidence."]
    if not kronos.input_validation.passed or not kronos.sanity_check.passed:
        return "LOW_CONFIDENCE", "WAIT", ["Kronos input or sanity validation failed; Behavior-only research may continue without boost."]
    behavior_bias = _behavior_bias(behavior.final_trade_decision)
    kronos_bias = kronos.forecast_path.trend_direction
    if behavior_bias in {"LONG", "SHORT"} and kronos_bias in {"LONG", "SHORT"} and behavior_bias != kronos_bias:
        return "HARD_CONFLICT", "WAIT", ["Behavior and Kronos disagree on directional path; action reduced to WAIT."]
    if behavior_bias == "LONG" and projection.target_hit_probability_pct >= projection.stop_hit_probability_pct:
        return "AGREE_LONG", "RESEARCH_CANDIDATE", ["Behavior and Kronos barrier probabilities agree directionally, research-only."]
    if behavior_bias == "SHORT" and projection.stop_hit_probability_pct >= projection.target_hit_probability_pct:
        return "AGREE_SHORT", "RESEARCH_CANDIDATE", ["Behavior and Kronos barrier probabilities agree directionally, research-only."]
    return "SOFT_CONFLICT", "WAIT", ["Kronos barrier probabilities do not clearly support Behavior; action reduced to WAIT."]


def _gates(
    behavior: TradeDecisionResult,
    combination: CombinationSimilarityReport,
    snapshot_ok: bool,
    boost_allowed: bool,
) -> list[FullTwinAnalysisGate]:
    return [
        _gate("TV-V067-001", "Shared snapshot integrity passed", snapshot_ok, "v0.66 identity fields matched before comparison.", "Use Behavior-only research and block Twin comparison until snapshot identity matches."),
        _gate("TV-V067-002", "Behavior authority preserved", True, "Behavior no-trade and risk gates remain final authority."),
        _gate("TV-V067-003", "Kronos raw path discretized", True, "Forecast path was converted into target/stop/time-exit probabilities."),
        _gate("TV-V067-004", "Combination evidence checked", combination.minimum_sample_pass, f"{combination.non_overlap_match_count} non-overlapping matches available.", "Collect more historical analog evidence before relying on Twin agreement."),
        _gate("TV-V067-005", "Kronos confidence boost blocked pre-OOS", not boost_allowed, "Decorrelated OOS reliability has not passed; no confidence boost allowed."),
        _gate("TV-V067-006", "No live broker route", True, "No OpenAlgo or broker route is created by Full Twin Analysis."),
        _gate("TV-V067-007", "Behavior trade_allowed remains bounded", behavior.trade_allowed in {True, False}, f"Behavior trade_allowed={behavior.trade_allowed}; final output still disables order routing."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str | None = None) -> FullTwinAnalysisGate:
    return FullTwinAnalysisGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity="info" if passed else "block",
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _behavior_bias(decision: str) -> str:
    if decision.startswith("BUY"):
        return "LONG"
    if decision.startswith("SELL"):
        return "SHORT"
    return "NEUTRAL"


def _opposite_direction(direction: str) -> str:
    if direction == "LONG":
        return "SHORT"
    if direction == "SHORT":
        return "LONG"
    return "SHORT"


def _force_kronos_direction(kronos: KronosForecastResult, direction: str) -> KronosForecastResult:
    path = kronos.forecast_path.model_copy(update={"trend_direction": direction})
    return kronos.model_copy(update={"forecast_path": path})


def _combination_request_from_full(request: FullTwinAnalysisRequest):
    from ..models import CombinationSimilarityRequest

    return CombinationSimilarityRequest(
        symbol=request.symbol,
        timeframe=request.timeframe,
        seed=request.seed,
        minimum_match_count=30,
        max_matches=30,
    )


def _shared_request_from_full(request: FullTwinAnalysisRequest):
    from ..models import SharedSnapshotRequest

    return SharedSnapshotRequest(
        symbol=request.symbol,
        timeframe=request.timeframe,
        seed=request.seed,
        lookback_candles=request.lookback_candles,
        forecast_horizon_bars=request.forecast_horizon_bars,
        force_kronos_hash_mismatch=request.force_kronos_hash_mismatch,
        force_decision_time_mismatch=request.force_decision_time_mismatch,
    )
