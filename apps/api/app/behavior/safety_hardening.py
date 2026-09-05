from __future__ import annotations

from ..models import (
    BehaviorAcpCheckRecord,
    BehaviorAcpHardeningResult,
    BehaviorDriftRequest,
    BehaviorDriftResult,
    BehaviorOODRequest,
    BehaviorOODResult,
    OODFeatureCheck,
    OODFeatureResult,
    RealityGapCheckRequest,
    RealityGapCheckResult,
)


SAFETY_HARDENING_VERSION = "behavior-safety-hardening.v0.25"


def default_drift_request(symbol: str) -> BehaviorDriftRequest:
    return BehaviorDriftRequest(
        symbol=symbol.upper(),
        feature_name="open_drive_vwap_support_memory",
        baseline_mean=0.42,
        baseline_std=0.18,
        live_mean=0.46,
        live_std=0.20,
        baseline_sample_count=180,
        live_sample_count=64,
    )


def high_drift_request(symbol: str) -> BehaviorDriftRequest:
    return BehaviorDriftRequest(
        symbol=symbol.upper(),
        feature_name="open_drive_vwap_support_memory",
        baseline_mean=0.35,
        baseline_std=0.12,
        live_mean=0.82,
        live_std=0.42,
        baseline_sample_count=180,
        live_sample_count=64,
    )


def evaluate_behavior_drift(request: BehaviorDriftRequest) -> BehaviorDriftResult:
    mean_shift_z = abs(request.live_mean - request.baseline_mean) / max(request.baseline_std, 1e-9)
    volatility_shift_ratio = abs(request.live_std - request.baseline_std) / max(request.baseline_std, 1e-9)
    population_stability_index = _bounded(
        (mean_shift_z / 4.0) * 0.65 + (volatility_shift_ratio / 3.0) * 0.35
    )
    low_sample_penalty = 0.12 if min(request.baseline_sample_count, request.live_sample_count) < 30 else 0.0
    drift_score = _bounded(population_stability_index + low_sample_penalty)

    if drift_score >= request.quarantine_threshold:
        status = "quarantine"
    elif drift_score >= request.watch_threshold:
        status = "watch"
    else:
        status = "stable"

    blockers: list[str] = []
    if status == "quarantine":
        blockers.append("Memory quarantine required because live distribution no longer matches replay baseline.")
    if min(request.baseline_sample_count, request.live_sample_count) < 30:
        blockers.append("Minimum sample guard failed for drift measurement.")

    confidence_multiplier = 1.0
    if status == "watch":
        confidence_multiplier = 0.65
    if status == "quarantine":
        confidence_multiplier = 0.0

    return BehaviorDriftResult(
        safety_version=SAFETY_HARDENING_VERSION,
        symbol=request.symbol.upper(),
        feature_name=request.feature_name,
        baseline_sample_count=request.baseline_sample_count,
        live_sample_count=request.live_sample_count,
        mean_shift_z=round(mean_shift_z, 6),
        volatility_shift_ratio=round(volatility_shift_ratio, 6),
        population_stability_index=round(population_stability_index, 6),
        drift_score=round(drift_score, 6),
        drift_status=status,
        memory_quarantine_required=status == "quarantine",
        confidence_multiplier=confidence_multiplier,
        promotion_allowed=not blockers,
        promotion_blockers=blockers,
        notes=[
            "Drift is measured against a fixed replay baseline, not a rolling baseline alone.",
            "Quarantine blocks memory promotion and sets confidence multiplier to zero.",
        ],
    )


def default_ood_request(symbol: str) -> BehaviorOODRequest:
    return BehaviorOODRequest(
        symbol=symbol.upper(),
        features=[
            OODFeatureCheck(feature_name="volume_z", current_value=1.8, expected_min=-2.5, expected_max=2.5, hard_min=-5.0, hard_max=5.0),
            OODFeatureCheck(feature_name="candle_range_atr", current_value=1.15, expected_min=0.2, expected_max=2.2, hard_min=0.0, hard_max=5.0),
            OODFeatureCheck(feature_name="gap_pct", current_value=0.35, expected_min=-1.5, expected_max=1.5, hard_min=-6.0, hard_max=6.0),
            OODFeatureCheck(feature_name="slippage_risk_pct", current_value=0.08, expected_min=0.0, expected_max=0.35, hard_min=0.0, hard_max=1.25),
        ],
    )


def high_ood_request(symbol: str) -> BehaviorOODRequest:
    return BehaviorOODRequest(
        symbol=symbol.upper(),
        features=[
            OODFeatureCheck(feature_name="volume_z", current_value=8.2, expected_min=-2.5, expected_max=2.5, hard_min=-5.0, hard_max=5.0),
            OODFeatureCheck(feature_name="candle_range_atr", current_value=5.8, expected_min=0.2, expected_max=2.2, hard_min=0.0, hard_max=5.0),
            OODFeatureCheck(feature_name="gap_pct", current_value=7.4, expected_min=-1.5, expected_max=1.5, hard_min=-6.0, hard_max=6.0),
            OODFeatureCheck(feature_name="slippage_risk_pct", current_value=2.1, expected_min=0.0, expected_max=0.35, hard_min=0.0, hard_max=1.25),
        ],
    )


def evaluate_behavior_ood(request: BehaviorOODRequest) -> BehaviorOODResult:
    feature_results = [_evaluate_feature_ood(feature) for feature in request.features]
    max_distance = max((feature.distance_score for feature in feature_results), default=0.0)
    avg_distance = sum(feature.distance_score for feature in feature_results) / max(len(feature_results), 1)
    hard_outlier = any(feature.status == "hard_outlier" for feature in feature_results)
    ood_score = _bounded(max(max_distance * 0.7, avg_distance))

    if hard_outlier or ood_score >= request.block_threshold:
        status = "block"
    elif ood_score >= request.watch_threshold:
        status = "watch"
    else:
        status = "normal"

    blockers: list[str] = []
    if status == "block":
        blockers.append("OOD confidence block active because one or more features are outside safe replay envelope.")

    return BehaviorOODResult(
        safety_version=SAFETY_HARDENING_VERSION,
        symbol=request.symbol.upper(),
        ood_score=round(ood_score, 6),
        max_feature_distance=round(max_distance, 6),
        ood_status=status,
        confidence_blocked=status == "block",
        trade_blocked=status == "block",
        feature_results=feature_results,
        promotion_allowed=not blockers,
        promotion_blockers=blockers,
        notes=[
            "OOD guard blocks confidence before narrative or decision layers can promote a trade.",
            "Hard outliers block even when average score looks acceptable.",
        ],
    )


def _evaluate_feature_ood(feature: OODFeatureCheck) -> OODFeatureResult:
    if feature.expected_min > feature.expected_max:
        raise ValueError(f"Invalid expected range for {feature.feature_name}.")
    if feature.hard_min > feature.hard_max:
        raise ValueError(f"Invalid hard range for {feature.feature_name}.")

    value = feature.current_value
    if value < feature.hard_min or value > feature.hard_max:
        return OODFeatureResult(
            **feature.model_dump(),
            distance_score=1.0,
            status="hard_outlier",
            reason="Current value is outside the hard safety envelope.",
        )
    if feature.expected_min <= value <= feature.expected_max:
        return OODFeatureResult(
            **feature.model_dump(),
            distance_score=0.0,
            status="inside",
            reason="Current value is inside the expected replay envelope.",
        )

    if value < feature.expected_min:
        denominator = max(feature.expected_min - feature.hard_min, 1e-9)
        distance = (feature.expected_min - value) / denominator
        reason = "Current value is below expected replay range."
    else:
        denominator = max(feature.hard_max - feature.expected_max, 1e-9)
        distance = (value - feature.expected_max) / denominator
        reason = "Current value is above expected replay range."

    return OODFeatureResult(
        **feature.model_dump(),
        distance_score=round(_bounded(distance), 6),
        status="soft_outlier",
        reason=reason,
    )


def default_reality_gap_request(symbol: str) -> RealityGapCheckRequest:
    return RealityGapCheckRequest(symbol=symbol.upper())


def high_reality_gap_request(symbol: str) -> RealityGapCheckRequest:
    return RealityGapCheckRequest(
        symbol=symbol.upper(),
        replay_slippage_pct=0.08,
        observed_slippage_pct=0.72,
        replay_fill_rate_pct=96.0,
        observed_fill_rate_pct=61.0,
        replay_latency_ms=120,
        observed_latency_ms=940,
        replay_pnl_r=0.35,
        observed_pnl_r=-0.65,
    )


def evaluate_reality_gap(request: RealityGapCheckRequest) -> RealityGapCheckResult:
    slippage_drift = abs(request.observed_slippage_pct - request.replay_slippage_pct)
    fill_rate_drift = abs(request.observed_fill_rate_pct - request.replay_fill_rate_pct)
    latency_drift = abs(request.observed_latency_ms - request.replay_latency_ms)
    pnl_drift = abs(request.observed_pnl_r - request.replay_pnl_r)

    components = [
        slippage_drift / max(request.max_slippage_drift_pct, 1e-9),
        fill_rate_drift / max(request.max_fill_rate_drift_pct, 1e-9),
        latency_drift / max(request.max_latency_drift_ms, 1),
        pnl_drift / max(request.max_pnl_drift_r, 1e-9),
    ]
    score = _bounded(max(components) / 2.0)

    blockers: list[str] = []
    if slippage_drift > request.max_slippage_drift_pct:
        blockers.append("Replay/live slippage divergence exceeds threshold.")
    if fill_rate_drift > request.max_fill_rate_drift_pct:
        blockers.append("Replay/live fill-rate divergence exceeds threshold.")
    if latency_drift > request.max_latency_drift_ms:
        blockers.append("Replay/live latency divergence exceeds threshold.")
    if pnl_drift > request.max_pnl_drift_r:
        blockers.append("Replay/live PnL distribution divergence exceeds threshold.")

    severity = "normal"
    if blockers:
        severity = "critical" if score >= 0.7 else "watch"

    return RealityGapCheckResult(
        safety_version=SAFETY_HARDENING_VERSION,
        symbol=request.symbol.upper(),
        slippage_drift_pct=round(slippage_drift, 6),
        fill_rate_drift_pct=round(fill_rate_drift, 6),
        latency_drift_ms=latency_drift,
        pnl_drift_r=round(pnl_drift, 6),
        reality_gap_score=round(score, 6),
        alert=bool(blockers),
        severity=severity,  # type: ignore[arg-type]
        promotion_allowed=not blockers,
        promotion_blockers=blockers,
        notes=[
            "Reality-gap checks compare replay assumptions against simulated or observed execution facts.",
            "Any active alert blocks promotion to paper/live modes.",
        ],
    )


def build_acp_hardening_status(
    *,
    drift: BehaviorDriftResult,
    ood: BehaviorOODResult,
    reality_gap: RealityGapCheckResult,
) -> BehaviorAcpHardeningResult:
    checks = [
        BehaviorAcpCheckRecord(
            check_id="ACP-20",
            purpose="Live drift vs backtest drift remains monitored.",
            status="fail" if drift.memory_quarantine_required else "pass",
            evidence=f"drift_status={drift.drift_status}; drift_score={drift.drift_score}",
            blocks_promotion=drift.memory_quarantine_required,
        ),
        BehaviorAcpCheckRecord(
            check_id="ACP-46",
            purpose="Replay-to-live divergence remains below configured thresholds.",
            status="fail" if reality_gap.alert else "pass",
            evidence=f"severity={reality_gap.severity}; score={reality_gap.reality_gap_score}",
            blocks_promotion=reality_gap.alert,
        ),
        BehaviorAcpCheckRecord(
            check_id="TV-BI-050",
            purpose="Drift demotes stale memory and quarantines unsafe memory.",
            status="fail" if drift.memory_quarantine_required else "pass",
            evidence=f"confidence_multiplier={drift.confidence_multiplier}",
            blocks_promotion=drift.memory_quarantine_required,
        ),
        BehaviorAcpCheckRecord(
            check_id="TV-BI-051",
            purpose="OOD blocks confidence when feature values leave replay envelope.",
            status="fail" if ood.confidence_blocked else "pass",
            evidence=f"ood_status={ood.ood_status}; ood_score={ood.ood_score}",
            blocks_promotion=ood.confidence_blocked,
        ),
        BehaviorAcpCheckRecord(
            check_id="TV-BI-052",
            purpose="Reality-gap alerts block promotion when replay assumptions diverge.",
            status="fail" if reality_gap.alert else "pass",
            evidence=f"promotion_allowed={reality_gap.promotion_allowed}",
            blocks_promotion=reality_gap.alert,
        ),
    ]
    blockers = [f"{check.check_id}: {check.purpose}" for check in checks if check.blocks_promotion]
    return BehaviorAcpHardeningResult(
        safety_version=SAFETY_HARDENING_VERSION,
        checks=checks,
        pass_count=sum(1 for check in checks if check.status == "pass"),
        fail_count=sum(1 for check in checks if check.status == "fail"),
        promotion_allowed=not blockers,
        promotion_blockers=blockers,
        live_trading_blocked=True,
        notes=[
            "ACP hardening is promotion gating only; it cannot enable live orders.",
            "Failing checks force WAIT/BLOCK semantics in later promotion flows.",
        ],
    )


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))
