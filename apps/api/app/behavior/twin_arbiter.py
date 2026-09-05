from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    KillSwitchState,
    BotHandoffVerificationReport,
    BotHandoffVerificationRequest,
    KronosForecastResult,
    SignalIntentBundle,
    SystemMode,
    TradeDecisionResult,
    TwinConflictRecord,
    TwinEngineComparison,
    TwinMachineDashboard,
    TwinReliabilityReport,
    TwinTournamentRequest,
    TwinTournamentResult,
    now_iso,
)


TWIN_VERSION = "twin-machine-arbiter.v0.47"


def build_twin_engine_comparison(
    *,
    symbol: str,
    behavior: TradeDecisionResult,
    kronos: KronosForecastResult | None,
) -> TwinEngineComparison:
    kronos_available = kronos is not None and kronos.input_validation.passed and kronos.sanity_check.passed
    kronos_direction = kronos.forecast_path.trend_direction if kronos else "UNKNOWN"
    behavior_bias = _behavior_bias(behavior.final_trade_decision)
    conflict_reasons: list[str] = []
    if behavior.final_trade_decision in {"NO_TRADE", "WAIT", "AVOID_CHOP", "FAKEOUT_WARNING"}:
        conflict_reasons.append("Behavior engine is not permitting a trade-like candidate.")
    risk_blocked = any(gate.severity == "block" for gate in behavior.gates) or bool(behavior.no_trade.blocking_gates)
    if risk_blocked:
        conflict_reasons.append("Behavior risk/no-trade gates block the setup.")
    if not kronos_available:
        conflict_reasons.append("Kronos is unavailable, invalid, expired, or sanity-blocked.")
    if kronos and kronos.uncertainty.discarded_for_high_uncertainty:
        conflict_reasons.append("Kronos uncertainty is too wide to trust.")
    hard_conflict = (
        kronos_available
        and behavior_bias in {"LONG", "SHORT"}
        and kronos_direction in {"LONG", "SHORT"}
        and behavior_bias != kronos_direction
    )
    if hard_conflict:
        conflict_reasons.append("Behavior and Kronos disagree on direction.")
    if behavior_bias == "LONG" and kronos_direction == "LONG" and not conflict_reasons:
        agreement_state = "AGREE_LONG"
        action = "RESEARCH_CANDIDATE"
    elif behavior_bias == "SHORT" and kronos_direction == "SHORT" and not conflict_reasons:
        agreement_state = "AGREE_SHORT"
        action = "RESEARCH_CANDIDATE"
    elif hard_conflict:
        agreement_state = "HARD_CONFLICT"
        action = "WAIT"
    elif not kronos_available:
        agreement_state = "LOW_CONFIDENCE"
        action = "WAIT"
    elif behavior.final_trade_decision in {"NO_TRADE", "AVOID_CHOP", "FAKEOUT_WARNING"} or risk_blocked:
        agreement_state = "NO_TRADE"
        action = "NO_TRADE"
    else:
        agreement_state = "SOFT_CONFLICT"
        action = "WAIT"
    agreement_score = _agreement_score(agreement_state, behavior, kronos)
    payload = {
        "symbol": symbol.upper(),
        "behavior": behavior.final_trade_decision,
        "kronos": kronos_direction,
        "agreement_state": agreement_state,
        "action": action,
        "agreement_score": agreement_score,
        "conflict_reasons": conflict_reasons,
        "kronos_hash": kronos.output_hash if kronos else None,
    }
    evidence_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return TwinEngineComparison(
        twin_version=TWIN_VERSION,
        generated_at=now_iso(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:twin:{symbol}:{evidence_hash}")),
        symbol=symbol.upper(),
        behavior_decision=behavior.final_trade_decision,
        behavior_trade_allowed=behavior.trade_allowed,
        behavior_risk_blocked=risk_blocked,
        kronos_available=kronos_available,
        kronos_direction=kronos_direction,  # type: ignore[arg-type]
        kronos_confidence=kronos.forecast_confidence if kronos else 0.0,
        agreement_state=agreement_state,  # type: ignore[arg-type]
        arbiter_action=action,  # type: ignore[arg-type]
        agreement_score=agreement_score,
        conflict_reasons=conflict_reasons or ["No directional conflict found, but output remains research-only."],
        evidence_hash=evidence_hash,
        twin_agreement_hash=hashlib.sha256(f"{evidence_hash}:twin-agreement".encode("utf-8")).hexdigest(),
        kronos=kronos,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        kronos_cannot_execute_orders=True,
        kronos_cannot_override_no_trade=True,
        kronos_cannot_override_risk=True,
        notes=[
            "Twin Arbiter compares Behavior memory/risk with Kronos forecast prior.",
            "A conflict reduces action to WAIT or NO_TRADE.",
            "The arbiter does not execute orders and does not bypass OpenAlgo gates.",
        ],
    )


def build_twin_conflicts(symbol: str, comparison: TwinEngineComparison) -> list[TwinConflictRecord]:
    if comparison.agreement_state not in {"HARD_CONFLICT", "SOFT_CONFLICT", "LOW_CONFIDENCE", "NO_TRADE"}:
        return []
    return [
        TwinConflictRecord(
            conflict_id=str(uuid5(NAMESPACE_URL, f"tradevision:twin-conflict:{symbol}:{comparison.evidence_hash}")),
            symbol=symbol.upper(),
            agreement_state=comparison.agreement_state,
            behavior_decision=comparison.behavior_decision,
            kronos_direction=comparison.kronos_direction,
            conflict_reasons=comparison.conflict_reasons,
            evidence_hash=comparison.evidence_hash,
            created_at=now_iso(),
        )
    ]


def build_twin_reliability(symbol: str, sample_count: int = 0) -> TwinReliabilityReport:
    minimum = sample_count >= 30
    return TwinReliabilityReport(
        reliability_version=f"{TWIN_VERSION}.reliability",
        symbol=symbol.upper(),
        sample_count=sample_count,
        behavior_only_accuracy=0.0,
        kronos_only_accuracy=0.0,
        twin_arbiter_accuracy=0.0,
        fakeout_avoidance=0.0,
        no_trade_quality=0.0,
        calibration_error=1.0,
        minimum_sample_pass=minimum,
        notes=[
            "Reliability remains low-evidence until replay tournament and Indian market fixtures create enough samples.",
            "Do not use Kronos or Twin reliability for bot decisions before minimum sample passes.",
        ],
    )


def build_twin_tournament(request: TwinTournamentRequest, comparisons: list[TwinEngineComparison]) -> TwinTournamentResult:
    behavior_score = 0.0
    kronos_score = sum(item.kronos_confidence for item in comparisons) / len(comparisons) if comparisons else 0.0
    twin_score = sum(item.agreement_score for item in comparisons) / len(comparisons) if comparisons else 0.0
    payload = {
        "symbol": request.symbol.upper(),
        "seed": request.seed,
        "scenario_count": request.scenario_count,
        "behavior_score": behavior_score,
        "kronos_score": kronos_score,
        "twin_score": twin_score,
    }
    evidence_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    leaderboard = sorted(
        [
            {"engine": "Behavior", "score": round(behavior_score, 4)},
            {"engine": "Kronos", "score": round(kronos_score, 4)},
            {"engine": "Twin", "score": round(twin_score, 4)},
        ],
        key=lambda item: float(item["score"]),
        reverse=True,
    )
    return TwinTournamentResult(
        tournament_version=f"{TWIN_VERSION}.tournament",
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:twin-tournament:{request.symbol}:{request.seed}:{evidence_hash}")),
        symbol=request.symbol.upper(),
        scenario_count=request.scenario_count,
        deterministic=True,
        behavior_score=round(behavior_score, 4),
        kronos_score=round(kronos_score, 4),
        twin_score=round(twin_score, 4),
        leaderboard=leaderboard,
        promotion_allowed=False,
        evidence_hash=evidence_hash,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "Tournament is deterministic mock evidence only.",
            "Promotion requires replay/OOS/paper evidence and cannot happen from this report alone.",
        ],
    )


def build_signal_intent_preview(
    *,
    comparison: TwinEngineComparison,
    mode: SystemMode,
    kill_switch: KillSwitchState,
    valid_until: str,
) -> SignalIntentBundle:
    side = "LONG" if comparison.agreement_state == "AGREE_LONG" else "SHORT" if comparison.agreement_state == "AGREE_SHORT" else "NO_TRADE"
    intent_payload = {
        "symbol": comparison.symbol,
        "side": side,
        "evidence_hash": comparison.evidence_hash,
        "twin_agreement_hash": comparison.twin_agreement_hash,
        "valid_until": valid_until,
    }
    canonical = json.dumps(intent_payload, sort_keys=True)
    intent_id = str(uuid5(NAMESPACE_URL, f"tradevision:signal-intent:{canonical}"))
    duplicate_key = hashlib.sha256(f"{comparison.symbol}:{side}:{comparison.evidence_hash}:{comparison.twin_agreement_hash}".encode("utf-8")).hexdigest()
    signature_payload = {
        **intent_payload,
        "intent_id": intent_id,
        "duplicate_key": duplicate_key,
        "mode": mode.mode,
        "kill_switch_state": kill_switch.state,
        "export_allowed": False,
    }
    intent_signature = hashlib.sha256(json.dumps(signature_payload, sort_keys=True).encode("utf-8")).hexdigest()
    expired = _is_expired(valid_until)
    mode_permission = _mode_permission(mode.mode)
    permission_matrix = [
        {"gate": "mode_allows_preview", "passed": mode_permission in {"mock_preview_only", "simulation_preview_only", "replay_preview_only"}, "evidence": f"mode={mode.mode}; permission={mode_permission}"},
        {"gate": "kill_switch_rechecked", "passed": kill_switch.state == "armed", "evidence": f"kill_switch={kill_switch.state}"},
        {"gate": "human_veto_required", "passed": True, "evidence": "external executor must require human approval before paper/live use"},
        {"gate": "expiry_enforced", "passed": not expired, "evidence": f"valid_until={valid_until}"},
        {"gate": "duplicate_key_generated", "passed": len(duplicate_key) == 64, "evidence": duplicate_key[:16]},
        {"gate": "broker_order_created", "passed": False, "evidence": "Trade Vision generated an intent preview only"},
    ]
    return SignalIntentBundle(
        intent_version="openalgo-signal-intent.preview.v0.48",
        intent_id=intent_id,
        intent_signature=intent_signature,
        duplicate_key=duplicate_key,
        duplicate_intent_blocked=False,
        symbol=comparison.symbol,
        timeframe="5m",
        side=side,  # type: ignore[arg-type]
        entry_zone="preview_only_no_order",
        stop_loss=None,
        target=None,
        risk_reward=0.0,
        position_size_suggestion=0,
        valid_until=valid_until,
        expired=expired,
        expiry_enforced=True,
        behavior_decision=comparison.behavior_decision,
        kronos_decision=comparison.kronos_direction,
        twin_decision=comparison.arbiter_action,
        twin_agreement_hash=comparison.twin_agreement_hash,
        evidence_hash=comparison.evidence_hash,
        kill_switch_state=kill_switch.state,
        kill_switch_rechecked=True,
        human_veto_required=True,
        human_veto_active=False,
        mode=mode.mode,
        mode_permission=mode_permission,  # type: ignore[arg-type]
        permission_matrix=permission_matrix,
        replay_snapshot_id=comparison.kronos.input_snapshot_id if comparison.kronos else None,
        model_version=comparison.kronos.model_version if comparison.kronos else "kronos_unavailable",
        rule_version=comparison.twin_version,
        data_version="point_in_time_mock",
        feature_version="behavior_kronos_twin_mock",
        export_status="expired" if expired else "preview_only",
        export_allowed=False,
        broker_credentials_present=False,
        broker_order_created=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "This is a signed OpenAlgo intent draft only; no broker order is created.",
            "OpenAlgo must re-check risk, expiry, kill switch, duplicate orders, and account state externally.",
        ],
    )


def _is_expired(valid_until: str) -> bool:
    try:
        normalized = valid_until.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized) <= datetime.now(timezone.utc)
    except ValueError:
        return True


def _mode_permission(mode: str) -> str:
    if mode == "MOCK":
        return "mock_preview_only"
    if mode == "SIMULATION":
        return "simulation_preview_only"
    if mode == "REPLAY":
        return "replay_preview_only"
    if mode == "PAPER":
        return "paper_blocked"
    return "live_blocked"


def build_twin_machine_dashboard(
    *,
    symbol: str,
    comparison: TwinEngineComparison,
    conflicts: list[TwinConflictRecord],
    reliability: TwinReliabilityReport,
    tournament: TwinTournamentResult,
    intent_preview: SignalIntentBundle,
) -> TwinMachineDashboard:
    kronos = comparison.kronos
    forecast_path_points = kronos.forecast_path.candles if kronos else []
    forecast_fan = {
        "lower": kronos.uncertainty.lower_path if kronos else [],
        "median": kronos.uncertainty.median_path if kronos else [],
        "upper": kronos.uncertainty.upper_path if kronos else [],
    }
    ghost_path_summary = {
        "direction": comparison.kronos_direction,
        "expected_return_pct": kronos.forecast_path.expected_return_pct if kronos else 0.0,
        "expected_move_atr": kronos.forecast_path.expected_move_atr if kronos else 0.0,
        "uncertainty_score": kronos.uncertainty.uncertainty_score if kronos else 1.0,
        "discarded_for_uncertainty": kronos.uncertainty.discarded_for_high_uncertainty if kronos else True,
    }
    safety_gate_matrix = [
        {"gate": "Behavior trade allowed", "passed": comparison.behavior_trade_allowed, "effect": "must remain false before OpenAlgo paper/live integration"},
        {"gate": "Behavior risk blocked", "passed": not comparison.behavior_risk_blocked, "effect": "risk block forces NO_TRADE"},
        {"gate": "Kronos available", "passed": comparison.kronos_available, "effect": "unavailable Kronos cannot boost confidence"},
        {"gate": "Kronos cannot execute", "passed": comparison.kronos_cannot_execute_orders, "effect": "forecast is research-only"},
        {"gate": "Order routing disabled", "passed": not comparison.order_routing_enabled, "effect": "Trade Vision creates no broker order"},
        {"gate": "OpenAlgo preview only", "passed": not intent_preview.broker_order_created, "effect": "intent export is not execution"},
    ]
    conflict_explorer = [
        {
            "source": "Twin Arbiter",
            "state": comparison.agreement_state,
            "reason": reason,
        }
        for reason in comparison.conflict_reasons
    ]
    action = "NO_TRADE" if comparison.arbiter_action == "NO_TRADE" else "WAIT" if comparison.arbiter_action == "WAIT" else "REPLAY_REVIEW_ONLY"
    payload = {
        "symbol": symbol.upper(),
        "comparison_hash": comparison.evidence_hash,
        "intent_id": intent_preview.intent_id,
        "tournament": tournament.evidence_hash,
        "action": action,
    }
    dashboard_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return TwinMachineDashboard(
        dashboard_version=f"{TWIN_VERSION}.dashboard",
        generated_at=now_iso(),
        symbol=symbol.upper(),
        comparison=comparison,
        conflicts=conflicts,
        reliability=reliability,
        tournament=tournament,
        openalgo_intent_preview=intent_preview,
        forecast_path_points=forecast_path_points,
        forecast_fan=forecast_fan,
        ghost_path_summary=ghost_path_summary,
        safety_gate_matrix=safety_gate_matrix,
        reliability_leaderboard=tournament.leaderboard,
        conflict_explorer=conflict_explorer,
        recommended_workspace_action=action,  # type: ignore[arg-type]
        dashboard_hash=dashboard_hash,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "v0.47 Twin Machine dashboard is a side-by-side research cockpit.",
            "It compares Behavior DNA authority with Kronos forecast prior.",
            "OpenAlgo content is preview-only; no broker order is created.",
        ],
    )


def verify_bot_handoff_intent(
    request: BotHandoffVerificationRequest,
    *,
    verified_at: str | None = None,
) -> BotHandoffVerificationReport:
    intent = request.intent
    signature_valid = _verify_intent_signature(intent)
    duplicate_detected = intent.duplicate_key in set(request.seen_duplicate_keys) or intent.duplicate_intent_blocked
    expired = intent.expired or _is_expired(intent.valid_until)
    rejection_reasons: list[str] = []
    if not signature_valid:
        rejection_reasons.append("Intent signature is invalid.")
    if duplicate_detected:
        rejection_reasons.append("Duplicate intent key detected.")
    if expired:
        rejection_reasons.append("Intent is expired.")
    if intent.mode_permission not in {"mock_preview_only", "simulation_preview_only", "replay_preview_only"}:
        rejection_reasons.append(f"Mode permission blocks handoff: {intent.mode_permission}.")
    if intent.kill_switch_state != "armed" or not intent.kill_switch_rechecked:
        rejection_reasons.append("Kill switch is not armed or was not rechecked.")
    if not intent.human_veto_required:
        rejection_reasons.append("Human veto requirement is missing.")
    if not request.external_human_approval_present:
        rejection_reasons.append("External human approval is missing.")
    if not request.external_risk_check_passed:
        rejection_reasons.append("External risk check is missing or failed.")
    if not request.external_account_state_checked:
        rejection_reasons.append("External account state was not checked.")
    if intent.broker_credentials_present:
        rejection_reasons.append("Intent unexpectedly reports broker credentials inside Trade Vision.")
    if intent.broker_order_created:
        rejection_reasons.append("Intent unexpectedly reports broker order creation.")
    if intent.trade_allowed or intent.order_routing_enabled or not intent.live_trading_blocked:
        rejection_reasons.append("Intent safety flags are not locked.")
    if intent.export_allowed:
        rejection_reasons.append("Intent export_allowed must remain false inside Trade Vision.")
    gate_results = [
        {"gate": "signature_valid", "passed": signature_valid, "evidence": intent.intent_signature[:16]},
        {"gate": "duplicate_not_seen", "passed": not duplicate_detected, "evidence": intent.duplicate_key[:16]},
        {"gate": "not_expired", "passed": not expired, "evidence": intent.valid_until},
        {"gate": "mode_permission_preview_only", "passed": intent.mode_permission in {"mock_preview_only", "simulation_preview_only", "replay_preview_only"}, "evidence": intent.mode_permission},
        {"gate": "kill_switch_armed", "passed": intent.kill_switch_state == "armed" and intent.kill_switch_rechecked, "evidence": intent.kill_switch_state},
        {"gate": "human_veto_required", "passed": intent.human_veto_required, "evidence": str(intent.human_veto_required)},
        {"gate": "external_human_approval_present", "passed": request.external_human_approval_present, "evidence": str(request.external_human_approval_present)},
        {"gate": "external_risk_check_passed", "passed": request.external_risk_check_passed, "evidence": str(request.external_risk_check_passed)},
        {"gate": "external_account_state_checked", "passed": request.external_account_state_checked, "evidence": str(request.external_account_state_checked)},
        {"gate": "no_broker_credentials_inside_trade_vision", "passed": not intent.broker_credentials_present, "evidence": str(intent.broker_credentials_present)},
        {"gate": "no_broker_order_created", "passed": not intent.broker_order_created, "evidence": str(intent.broker_order_created)},
        {"gate": "trade_vision_safety_flags_locked", "passed": not intent.trade_allowed and not intent.order_routing_enabled and intent.live_trading_blocked, "evidence": f"trade={intent.trade_allowed};routing={intent.order_routing_enabled};live_blocked={intent.live_trading_blocked}"},
    ]
    payload = {
        "intent_id": intent.intent_id,
        "signature_valid": signature_valid,
        "duplicate_detected": duplicate_detected,
        "expired": expired,
        "target_executor": request.target_executor,
        "rejection_reasons": rejection_reasons,
    }
    verification_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return BotHandoffVerificationReport(
        verifier_version="openalgo-bot-handoff-verifier.v0.49",
        verified_at=verified_at or now_iso(),
        intent_id=intent.intent_id,
        symbol=intent.symbol,
        target_executor=request.target_executor,
        accepted_for_external_review=not rejection_reasons,
        rejected=bool(rejection_reasons),
        rejection_reasons=rejection_reasons,
        gate_results=gate_results,
        signature_valid=signature_valid,
        duplicate_detected=duplicate_detected,
        expired=expired,
        mode_permission=intent.mode_permission,
        kill_switch_rechecked=intent.kill_switch_rechecked,
        human_veto_required=intent.human_veto_required,
        external_human_approval_present=request.external_human_approval_present,
        external_risk_check_passed=request.external_risk_check_passed,
        external_account_state_checked=request.external_account_state_checked,
        broker_credentials_present=intent.broker_credentials_present,
        broker_order_created=intent.broker_order_created,
        export_allowed=intent.export_allowed,
        verification_hash=verification_hash,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "v0.49 verifies an intent draft for external OpenAlgo/trading-bot review only.",
            "Accepted for external review does not mean executable inside Trade Vision.",
            "A broker-connected executor must still perform its own account, order, and exchange checks.",
        ],
    )


def _verify_intent_signature(intent: SignalIntentBundle) -> bool:
    signature_payload = {
        "symbol": intent.symbol,
        "side": intent.side,
        "evidence_hash": intent.evidence_hash,
        "twin_agreement_hash": intent.twin_agreement_hash,
        "valid_until": intent.valid_until,
        "intent_id": intent.intent_id,
        "duplicate_key": intent.duplicate_key,
        "mode": intent.mode,
        "kill_switch_state": intent.kill_switch_state,
        "export_allowed": intent.export_allowed,
    }
    expected = hashlib.sha256(json.dumps(signature_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return expected == intent.intent_signature


def _behavior_bias(decision: str) -> str:
    if decision.startswith("BUY"):
        return "LONG"
    if decision.startswith("SELL"):
        return "SHORT"
    return "WAIT"


def _agreement_score(state: str, behavior: TradeDecisionResult, kronos: KronosForecastResult | None) -> float:
    if state in {"AGREE_LONG", "AGREE_SHORT"}:
        return round(min(1.0, behavior.confidence_pct / 100.0 * 0.55 + (kronos.forecast_confidence if kronos else 0.0) * 0.45), 4)
    if state == "SOFT_CONFLICT":
        return 0.35
    if state == "HARD_CONFLICT":
        return 0.05
    return 0.0
