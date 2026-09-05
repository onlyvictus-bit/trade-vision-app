from __future__ import annotations

import random

from ..models import BehaviorValidationFoldResult, BehaviorValidationRequest, BehaviorValidationResult


VALIDATION_VERSION = "behavior-validation.v0.24"


def run_behavior_validation(request: BehaviorValidationRequest) -> BehaviorValidationResult:
    rng = random.Random(f"{request.symbol}:{request.timeframe}:{request.seed}:{request.validation_type}")
    folds = [
        _fold_result(request, fold_index=idx + 1, rng=rng)
        for idx in range(request.folds if request.validation_type == "walk_forward" else 1)
    ]
    total_trades = sum(fold.trade_count for fold in folds)
    aggregate_win_rate = _weighted_average([(fold.win_rate_pct, fold.trade_count) for fold in folds])
    aggregate_expectancy = _weighted_average([(fold.expectancy_r, fold.trade_count) for fold in folds])
    aggregate_pf = _weighted_average([(fold.profit_factor, fold.trade_count) for fold in folds])
    aggregate_dd = max((fold.max_drawdown_pct for fold in folds), default=0.0)
    no_leakage = all(fold.leakage_pass for fold in folds)
    sample_pass = all(fold.minimum_sample_pass for fold in folds)
    promotion_blockers = _promotion_blockers(no_leakage, sample_pass, aggregate_pf, aggregate_expectancy, aggregate_dd)
    return BehaviorValidationResult(
        validation_version=VALIDATION_VERSION,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        validation_type=request.validation_type,
        folds=folds,
        aggregate_win_rate_pct=round(aggregate_win_rate, 4),
        aggregate_profit_factor=round(aggregate_pf, 4),
        aggregate_expectancy_r=round(aggregate_expectancy, 4),
        aggregate_max_drawdown_pct=round(aggregate_dd, 4),
        total_trades=total_trades,
        no_future_leakage=no_leakage,
        deterministic=True,
        live_trading_blocked=True,
        promotion_allowed=not promotion_blockers,
        promotion_blockers=promotion_blockers,
        notes=[
            "Validation uses deterministic mock folds and explicit non-overlapping train/test windows.",
            "Promotion remains blocked unless leakage, sample, profit factor, expectancy, and drawdown gates pass.",
            "This validation layer is research-only and cannot enable live routing.",
        ],
    )


def _fold_result(request: BehaviorValidationRequest, *, fold_index: int, rng: random.Random) -> BehaviorValidationFoldResult:
    stride = request.test_days
    train_start = (fold_index - 1) * stride
    train_end = train_start + request.train_days - 1
    test_start = train_end + 1
    test_end = test_start + request.test_days - 1
    if request.validation_type == "out_of_sample":
        train_start = 0
        train_end = request.train_days - 1
        test_start = request.train_days
        test_end = request.train_days + request.test_days - 1
    train_samples = request.train_days * 6 + rng.randint(0, 12)
    test_samples = request.test_days * 4 + rng.randint(0, 8)
    leakage_pass = train_end < test_start
    sample_pass = train_samples >= request.minimum_train_samples and test_samples >= request.minimum_test_samples
    win_rate = 43.0 + rng.random() * 18.0
    expectancy = -0.05 + rng.random() * 0.42
    profit_factor = 0.85 + rng.random() * 0.85
    drawdown = 4.0 + rng.random() * 9.5
    average_r = expectancy + rng.uniform(-0.04, 0.04)
    median_r = average_r + rng.uniform(-0.05, 0.05)
    notes = ["Train/test windows are non-overlapping." if leakage_pass else "Leakage risk: train/test windows overlap."]
    if not sample_pass:
        notes.append("Minimum sample guard blocks promotion.")
    if profit_factor < 1.15:
        notes.append("Profit factor is too weak for promotion.")
    if expectancy <= 0.0:
        notes.append("Expectancy is not positive.")
    return BehaviorValidationFoldResult(
        fold_index=fold_index,
        train_start_day=train_start,
        train_end_day=train_end,
        test_start_day=test_start,
        test_end_day=test_end,
        train_samples=train_samples,
        test_samples=test_samples,
        leakage_pass=leakage_pass,
        minimum_sample_pass=sample_pass,
        win_rate_pct=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        expectancy_r=round(expectancy, 4),
        max_drawdown_pct=round(drawdown, 4),
        average_r=round(average_r, 4),
        median_r=round(median_r, 4),
        trade_count=test_samples,
        notes=notes,
    )


def _weighted_average(values: list[tuple[float, int]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in values) / total_weight


def _promotion_blockers(
    no_leakage: bool,
    sample_pass: bool,
    profit_factor: float,
    expectancy: float,
    drawdown: float,
) -> list[str]:
    blockers: list[str] = []
    if not no_leakage:
        blockers.append("Leakage check failed.")
    if not sample_pass:
        blockers.append("Minimum train/test sample guard failed.")
    if profit_factor < 1.15:
        blockers.append("Aggregate profit factor is below 1.15.")
    if expectancy <= 0.0:
        blockers.append("Aggregate expectancy is not positive.")
    if drawdown > 12.0:
        blockers.append("Aggregate drawdown exceeds 12%.")
    return blockers
