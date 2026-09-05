from __future__ import annotations

import hashlib
import json
import random

from ..models import (
    EngineValidationSummary,
    FamilyWeightStabilityRecord,
    WalkForwardFoldResult,
    WalkForwardValidationGate,
    WalkForwardValidationReport,
    WalkForwardValidationRequest,
    now_iso,
)


VALIDATION_VERSION = "walk-forward-validation.v0.68"
OBJECTIVE = "analog_retrieval_precision_at_10_plus_expected_calibration_error"
BASE_TIMESTAMP_NS = 1_704_067_200_000_000_000
MONTH_NS = 30 * 24 * 60 * 60 * 1_000_000_000
ENGINE_FIELDS = {
    "behavior": ("behavior_precision_at_10", "behavior_ece", "behavior_profit_factor"),
    "kronos": ("kronos_precision_at_10", "kronos_ece", "kronos_profit_factor"),
    "twin": ("twin_precision_at_10", "twin_ece", "twin_profit_factor"),
}
FAMILY_BASE_WEIGHTS = {
    "candle_structure": 0.18,
    "indicator_similarity": 0.16,
    "session_rhythm": 0.14,
    "level_context": 0.15,
    "stock_dna_memory": 0.17,
    "risk_safety": 0.20,
}


def build_walk_forward_validation_report(request: WalkForwardValidationRequest) -> WalkForwardValidationReport:
    normalized_symbol = request.symbol.upper()
    rng = random.Random(
        "v0.68:"
        f"{normalized_symbol}:{','.join(request.timeframes)}:{request.seed}:"
        f"{request.fold_count}:{request.minimum_calibration_outcomes}"
    )
    folds = [
        _build_fold(request, timeframe=timeframe, fold_index=fold_index, rng=rng)
        for timeframe in request.timeframes
        for fold_index in range(1, request.fold_count + 1)
    ]
    summaries = [_engine_summary(engine, folds, request) for engine in ("behavior", "kronos", "twin")]
    stability = _family_weight_stability(request, rng)
    all_oos = all(fold.out_of_sample_only and fold.no_future_leakage for fold in folds)
    weight_passed = all(item.stable for item in stability)
    calibration_passed = all(summary.calibration_passed for summary in summaries)
    recalibration_required = any(
        summary.mean_ece > request.recent_ece_recalibration_trigger for summary in summaries
    )
    gates = _gates(request, folds, summaries, weight_passed, calibration_passed, recalibration_required)
    report_seed = {
        "version": VALIDATION_VERSION,
        "symbol": normalized_symbol,
        "timeframes": request.timeframes,
        "folds": [fold.model_dump(mode="json") for fold in folds],
        "summaries": [summary.model_dump(mode="json") for summary in summaries],
        "stability": [item.model_dump(mode="json") for item in stability],
        "gates": [gate.model_dump(mode="json") for gate in gates],
    }
    evidence_hash = hashlib.sha256(json.dumps(report_seed, sort_keys=True).encode("utf-8")).hexdigest()
    return WalkForwardValidationReport(
        validation_version=VALIDATION_VERSION,
        generated_at=now_iso(),
        run_id=f"wf-v068-{_safe_id(normalized_symbol)}-{request.seed}-{request.fold_count}f",
        symbol=normalized_symbol,
        timeframes=request.timeframes,
        method="walk_forward_optimization",
        fold_count=request.fold_count,
        train_size=f"{request.train_months} months",
        test_size=f"{request.test_months} months",
        step_size=f"{request.step_months} month",
        objective=OBJECTIVE,
        minimum_calibration_outcomes=request.minimum_calibration_outcomes,
        expected_calibration_error_threshold=request.expected_calibration_error_threshold,
        recent_ece_recalibration_trigger=request.recent_ece_recalibration_trigger,
        folds=folds,
        engine_summaries=summaries,
        family_weight_stability=stability,
        all_folds_out_of_sample=all_oos,
        weight_stability_passed=weight_passed,
        calibration_passed=calibration_passed,
        recalibration_required=recalibration_required,
        promotion_allowed=False,
        deterministic=True,
        research_only=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.68 validates Behavior-only, Kronos-only, and Twin performance separately.",
            "Every fold is deterministic and out-of-sample; train windows end before test windows begin.",
            "Promotion remains blocked because this is a research-only mock/replay validation layer.",
        ],
        evidence_hash=evidence_hash,
    )


def _build_fold(
    request: WalkForwardValidationRequest,
    *,
    timeframe: str,
    fold_index: int,
    rng: random.Random,
) -> WalkForwardFoldResult:
    train_start = BASE_TIMESTAMP_NS + (fold_index - 1) * request.step_months * MONTH_NS
    train_end = train_start + request.train_months * MONTH_NS - 1
    test_start = train_end + 1
    test_end = test_start + request.test_months * MONTH_NS - 1
    tf_factor = _timeframe_factor(timeframe)
    sample_count = max(12, int(90 * request.test_months * tf_factor) + rng.randint(0, 24))
    behavior_precision = 0.52 + rng.random() * 0.08
    kronos_precision = 0.49 + rng.random() * 0.08
    twin_precision = max(behavior_precision, kronos_precision) + rng.random() * 0.04
    behavior_ece = 0.038 + rng.random() * 0.026
    kronos_ece = 0.045 + rng.random() * 0.035
    twin_ece = min(behavior_ece, kronos_ece) - rng.random() * 0.006
    return WalkForwardFoldResult(
        fold_id=f"{_safe_id(timeframe)}-fold-{fold_index:02d}",
        fold_index=fold_index,
        timeframe=timeframe,  # type: ignore[arg-type]
        train_start_ns=train_start,
        train_end_ns=train_end,
        test_start_ns=test_start,
        test_end_ns=test_end,
        train_size_label=f"{request.train_months}m",
        test_size_label=f"{request.test_months}m",
        sample_count=sample_count,
        behavior_precision_at_10=round(behavior_precision, 4),
        kronos_precision_at_10=round(kronos_precision, 4),
        twin_precision_at_10=round(min(0.75, twin_precision), 4),
        behavior_ece=round(behavior_ece, 4),
        kronos_ece=round(kronos_ece, 4),
        twin_ece=round(max(0.0, twin_ece), 4),
        behavior_profit_factor=round(1.02 + rng.random() * 0.22, 4),
        kronos_profit_factor=round(0.96 + rng.random() * 0.20, 4),
        twin_profit_factor=round(1.08 + rng.random() * 0.26, 4),
        out_of_sample_only=train_end < test_start,
        no_future_leakage=train_end < test_start,
    )


def _engine_summary(
    engine: str,
    folds: list[WalkForwardFoldResult],
    request: WalkForwardValidationRequest,
) -> EngineValidationSummary:
    precision_field, ece_field, pf_field = ENGINE_FIELDS[engine]
    sample_count = sum(fold.sample_count for fold in folds)
    mean_precision = _weighted_average([(getattr(fold, precision_field), fold.sample_count) for fold in folds])
    mean_ece = _weighted_average([(getattr(fold, ece_field), fold.sample_count) for fold in folds])
    mean_pf = _weighted_average([(getattr(fold, pf_field), fold.sample_count) for fold in folds])
    calibration_passed = (
        sample_count >= request.minimum_calibration_outcomes
        and mean_ece <= request.expected_calibration_error_threshold
    )
    reliability_grade = "acceptable_mock" if calibration_passed else "watch"
    if engine == "kronos":
        reliability_grade = "research_only" if not calibration_passed else "watch"
    notes = [
        f"{engine} evaluated on {sample_count} out-of-sample observations.",
        "Calibration pass does not permit trading; it only permits research comparison.",
    ]
    if sample_count < request.minimum_calibration_outcomes:
        notes.append("Minimum calibration outcome guard blocks strong probabilities.")
    if mean_ece > request.expected_calibration_error_threshold:
        notes.append("Expected calibration error exceeds the mock promotion threshold.")
    return EngineValidationSummary(
        engine=engine,  # type: ignore[arg-type]
        mean_precision_at_10=round(mean_precision, 4),
        mean_ece=round(mean_ece, 4),
        mean_profit_factor=round(mean_pf, 4),
        oos_sample_count=sample_count,
        calibration_passed=calibration_passed,
        promotion_allowed=False,
        reliability_grade=reliability_grade,  # type: ignore[arg-type]
        notes=notes,
    )


def _family_weight_stability(
    request: WalkForwardValidationRequest,
    rng: random.Random,
) -> list[FamilyWeightStabilityRecord]:
    records: list[FamilyWeightStabilityRecord] = []
    for family, weight in FAMILY_BASE_WEIGHTS.items():
        std = 0.018 + rng.random() * 0.028
        relative_variance = std / max(weight, 0.0001)
        stable = std <= request.weight_stability_threshold and relative_variance <= request.max_relative_weight_variance
        records.append(
            FamilyWeightStabilityRecord(
                family=family,
                mean_weight=round(weight, 4),
                cross_fold_std=round(std, 4),
                relative_variance=round(relative_variance, 4),
                stable=stable,
            )
        )
    return records


def _gates(
    request: WalkForwardValidationRequest,
    folds: list[WalkForwardFoldResult],
    summaries: list[EngineValidationSummary],
    weight_passed: bool,
    calibration_passed: bool,
    recalibration_required: bool,
) -> list[WalkForwardValidationGate]:
    all_oos = all(fold.out_of_sample_only and fold.no_future_leakage for fold in folds)
    enough_outcomes = all(summary.oos_sample_count >= request.minimum_calibration_outcomes for summary in summaries)
    separate_engines = {summary.engine for summary in summaries} == {"behavior", "kronos", "twin"}
    return [
        _gate("TV-V068-001", "Minimum five folds", request.fold_count >= 5, f"fold_count={request.fold_count}", "Use at least five walk-forward folds."),
        _gate("TV-V068-002", "Out-of-sample fold separation", all_oos, "All train_end_ns values are before test_start_ns.", "Rebuild folds with non-overlapping windows."),
        _gate("TV-V068-003", "Minimum calibration outcomes", enough_outcomes, f"minimum_calibration_outcomes={request.minimum_calibration_outcomes}", "Collect more labeled outcomes before trusting probabilities."),
        _gate("TV-V068-004", "Engine metrics are separate", separate_engines, "Behavior, Kronos, and Twin summaries are independently published.", "Publish separate engine summaries."),
        _gate("TV-V068-005", "Calibration ECE checked", calibration_passed, f"threshold={request.expected_calibration_error_threshold}", "Recalibrate confidence before promotion."),
        _gate("TV-V068-006", "Family weight stability", weight_passed, f"std_threshold={request.weight_stability_threshold}", "Freeze or reduce unstable family weights."),
        _gate("TV-V068-007", "Recent ECE recalibration trigger", not recalibration_required, f"trigger={request.recent_ece_recalibration_trigger}", "Force recalibration when recent ECE breaches trigger."),
        _gate("TV-V068-008", "Research-only promotion block", True, "promotion_allowed=false, trade_allowed=false, live_trading_blocked=true", "Keep validation research-only until later release gates pass."),
    ]


def _gate(
    gate_id: str,
    name: str,
    passed: bool,
    evidence: str,
    remediation: str,
) -> WalkForwardValidationGate:
    return WalkForwardValidationGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        severity="info" if passed else "block",
        evidence=evidence,
        remediation=remediation,
    )


def _weighted_average(values: list[tuple[float, int]]) -> float:
    total = sum(weight for _, weight in values)
    if total <= 0:
        return 0.0
    return sum(value * weight for value, weight in values) / total


def _timeframe_factor(timeframe: str) -> float:
    return {
        "1m": 1.5,
        "3m": 1.2,
        "5m": 1.0,
        "15m": 0.75,
        "30m": 0.60,
        "1H": 0.45,
        "4H": 0.32,
        "daily": 0.22,
        "weekly": 0.10,
    }.get(timeframe, 1.0)


def _safe_id(value: str) -> str:
    return value.lower().replace(" ", "-").replace("_", "-").replace("/", "-")
