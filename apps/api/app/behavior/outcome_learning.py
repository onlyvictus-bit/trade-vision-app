from __future__ import annotations

from collections import Counter, defaultdict
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    BehaviorMemoryRecord,
    CandleBar,
    FailureLibraryResult,
    FailurePatternRecord,
    LearningTrustRecord,
    LearningTrustResult,
    OutcomeLabelRequest,
    OutcomeLabelResult,
    OutcomeLabelValue,
    now_iso,
)


OUTCOME_LEARNING_VERSION = "behavior-outcome-learning.v0.19"
SUCCESS_OUTCOMES = {"TARGET_HIT", "PARTIAL_WIN", "RETEST_SUCCESS"}
FAILURE_OUTCOMES = {"SL_HIT", "FAKE_BREAKOUT", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"}
MINIMUM_SAMPLE_SIZE = 30


def label_trade_outcome(request: OutcomeLabelRequest) -> OutcomeLabelResult:
    bars = _post_entry_bars(request)
    run_id = request.run_id or _run_id(request)
    if not bars:
        return OutcomeLabelResult(
            outcome_version=OUTCOME_LEARNING_VERSION,
            run_id=run_id,
            symbol=request.series.symbol.upper(),
            timeframe=request.series.timeframe,
            direction=request.direction,
            pattern_id=request.pattern_id,
            outcome_label="TIME_EXIT",
            bars_to_target=None,
            bars_to_sl=None,
            max_profit_before_sl=0.0,
            max_loss_before_target=0.0,
            mfe=0.0,
            mae=0.0,
            target_hit_timestamp_ns=None,
            sl_hit_timestamp_ns=None,
            fakeout_detected=False,
            reason="No bars available after entry; labeled TIME_EXIT for safety.",
            audit_fields=_audit_fields(request, 0),
        )

    r_value = max(abs(request.entry_price - request.stop_loss), 0.0001)
    bars = bars[: request.max_holding_bars]
    target_index, target_time = _first_target_hit(request, bars)
    sl_index, sl_time = _first_sl_hit(request, bars)
    mfe, mae = _mfe_mae(request, bars)
    max_profit_before_sl = _max_profit_before_index(request, bars, sl_index)
    max_loss_before_target = _max_loss_before_index(request, bars, target_index)
    fakeout = _fakeout_detected(request, bars, r_value)
    outcome = _choose_outcome_label(request, bars, target_index, sl_index, mfe, mae, r_value, fakeout)
    return OutcomeLabelResult(
        outcome_version=OUTCOME_LEARNING_VERSION,
        run_id=run_id,
        symbol=request.series.symbol.upper(),
        timeframe=request.series.timeframe,
        direction=request.direction,
        pattern_id=request.pattern_id,
        outcome_label=outcome,
        bars_to_target=target_index + 1 if target_index is not None else None,
        bars_to_sl=sl_index + 1 if sl_index is not None else None,
        max_profit_before_sl=round(max_profit_before_sl, 4),
        max_loss_before_target=round(max_loss_before_target, 4),
        mfe=round(mfe, 4),
        mae=round(mae, 4),
        target_hit_timestamp_ns=target_time,
        sl_hit_timestamp_ns=sl_time,
        fakeout_detected=fakeout,
        reason=_outcome_reason(outcome, target_index, sl_index, fakeout),
        audit_fields=_audit_fields(request, len(bars)),
    )


def build_failure_library(symbol: str, memory: list[BehaviorMemoryRecord], outcomes: list[OutcomeLabelResult]) -> FailureLibraryResult:
    normalized = symbol.upper()
    failures: list[FailurePatternRecord] = []
    for outcome in outcomes:
        if outcome.outcome_label in FAILURE_OUTCOMES:
            failures.append(_failure_from_outcome(outcome))
    for record in memory:
        if record.outcome_label in FAILURE_OUTCOMES:
            failures.append(_failure_from_memory(record))
    counts = Counter(failure.failure_reason for failure in failures)
    most_common = counts.most_common(1)[0][0] if counts else None
    lessons = _no_trade_lessons(failures)
    return FailureLibraryResult(
        library_version=OUTCOME_LEARNING_VERSION,
        symbol=normalized,
        failures=failures,
        most_common_failure=most_common,
        no_trade_lessons=lessons,
    )


def build_learning_trust(symbol: str, memory: list[BehaviorMemoryRecord], outcomes: list[OutcomeLabelResult]) -> LearningTrustResult:
    normalized = symbol.upper()
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in memory:
        grouped[record.pattern_id].append(record.outcome_label)
    for outcome in outcomes:
        grouped[outcome.pattern_id].append(outcome.outcome_label)

    records: list[LearningTrustRecord] = []
    for pattern_id, labels in sorted(grouped.items()):
        sample_count = len(labels)
        successes = sum(1 for label in labels if label in SUCCESS_OUTCOMES)
        actual = (successes / sample_count) * 100.0 if sample_count else 0.0
        predicted = _mock_predicted_probability(pattern_id)
        error = abs(predicted - actual)
        evidence = _evidence_quality(sample_count)
        evidence_factor = 1.0 if evidence == "STRONG" else 0.75 if evidence == "MEDIUM" else 0.45
        trust_score = max(0.0, min(1.0, (1.0 - (error / 100.0)) * evidence_factor))
        notes = [f"{pattern_id} samples: {sample_count}.", f"Calibration error: {round(error, 2)}%."]
        if sample_count < MINIMUM_SAMPLE_SIZE:
            notes.append("Minimum evidence guard blocks strong trust claims.")
        records.append(
            LearningTrustRecord(
                trust_id=str(uuid5(NAMESPACE_URL, f"tradevision:trust:{normalized}:{pattern_id}")),
                symbol=normalized,
                pattern_id=pattern_id,
                sample_count=sample_count,
                predicted_probability_pct=round(predicted, 4),
                actual_success_rate_pct=round(actual, 4),
                calibration_error_pct=round(error, 4),
                trust_score=round(trust_score, 4),
                evidence_quality=evidence,
                notes=notes,
            )
        )

    aggregate = sum(record.trust_score for record in records) / len(records) if records else 0.0
    minimum_pass = sum(record.sample_count for record in records) >= MINIMUM_SAMPLE_SIZE
    status = "LOW_EVIDENCE" if not minimum_pass else "CALIBRATING" if aggregate < 0.72 else "CALIBRATED"
    return LearningTrustResult(
        trust_version=OUTCOME_LEARNING_VERSION,
        symbol=normalized,
        records=records,
        aggregate_trust_score=round(aggregate, 4),
        calibration_status=status,  # type: ignore[arg-type]
        minimum_sample_pass=minimum_pass,
        notes=[
            f"Total trust samples: {sum(record.sample_count for record in records)}.",
            "Trust is based on actual outcome labels versus predicted continuation probability.",
            "Low evidence blocks promotion even when individual patterns look strong.",
        ],
    )


def _post_entry_bars(request: OutcomeLabelRequest) -> list[CandleBar]:
    bars = sorted(request.series.bars, key=lambda item: item.timestamp_ns)
    if request.entry_timestamp_ns is None:
        return bars
    return [bar for bar in bars if bar.timestamp_ns >= request.entry_timestamp_ns]


def _first_target_hit(request: OutcomeLabelRequest, bars: list[CandleBar]) -> tuple[int | None, int | None]:
    for idx, bar in enumerate(bars):
        if request.direction == "long" and bar.high >= request.target:
            return idx, bar.timestamp_ns
        if request.direction == "short" and bar.low <= request.target:
            return idx, bar.timestamp_ns
    return None, None


def _first_sl_hit(request: OutcomeLabelRequest, bars: list[CandleBar]) -> tuple[int | None, int | None]:
    for idx, bar in enumerate(bars):
        if request.direction == "long" and bar.low <= request.stop_loss:
            return idx, bar.timestamp_ns
        if request.direction == "short" and bar.high >= request.stop_loss:
            return idx, bar.timestamp_ns
    return None, None


def _mfe_mae(request: OutcomeLabelRequest, bars: list[CandleBar]) -> tuple[float, float]:
    if request.direction == "long":
        mfe = max(bar.high - request.entry_price for bar in bars)
        mae = max(request.entry_price - bar.low for bar in bars)
    else:
        mfe = max(request.entry_price - bar.low for bar in bars)
        mae = max(bar.high - request.entry_price for bar in bars)
    return max(mfe, 0.0), max(mae, 0.0)


def _max_profit_before_index(request: OutcomeLabelRequest, bars: list[CandleBar], stop_index: int | None) -> float:
    sample = bars if stop_index is None else bars[: stop_index + 1]
    return _mfe_mae(request, sample)[0] if sample else 0.0


def _max_loss_before_index(request: OutcomeLabelRequest, bars: list[CandleBar], target_index: int | None) -> float:
    sample = bars if target_index is None else bars[: target_index + 1]
    return _mfe_mae(request, sample)[1] if sample else 0.0


def _fakeout_detected(request: OutcomeLabelRequest, bars: list[CandleBar], r_value: float) -> bool:
    early = bars[: min(3, len(bars))]
    if not early:
        return False
    mfe, mae = _mfe_mae(request, early)
    return mfe < 0.55 * r_value and mae >= 0.75 * r_value


def _choose_outcome_label(
    request: OutcomeLabelRequest,
    bars: list[CandleBar],
    target_index: int | None,
    sl_index: int | None,
    mfe: float,
    mae: float,
    r_value: float,
    fakeout: bool,
) -> OutcomeLabelValue:
    if target_index is not None and sl_index is not None:
        return "SL_HIT" if sl_index <= target_index else "TARGET_HIT"
    if sl_index is not None:
        return "FAKE_BREAKOUT" if fakeout else "SL_HIT"
    if target_index is not None:
        return "TARGET_HIT"
    if fakeout:
        return "FAKE_BREAKOUT"
    if mfe >= r_value and _final_profit(request, bars[-1]) > 0:
        return "PARTIAL_WIN"
    if abs(_final_profit(request, bars[-1])) <= 0.15 * r_value:
        return "BREAKEVEN"
    if mfe < 0.35 * r_value and mae < 0.45 * r_value:
        return "CHOP_NO_FOLLOWTHROUGH"
    return "TIME_EXIT"


def _final_profit(request: OutcomeLabelRequest, bar: CandleBar) -> float:
    if request.direction == "long":
        return bar.close - request.entry_price
    return request.entry_price - bar.close


def _outcome_reason(outcome: str, target_index: int | None, sl_index: int | None, fakeout: bool) -> str:
    if outcome == "TARGET_HIT":
        return f"Target was reached before stop loss in {target_index + 1 if target_index is not None else 'unknown'} bars."
    if outcome == "SL_HIT":
        return f"Stop loss was reached before target in {sl_index + 1 if sl_index is not None else 'unknown'} bars."
    if outcome == "FAKE_BREAKOUT":
        return "Early adverse move with weak favorable excursion produced fakeout label." if fakeout else "Failed breakout behavior was detected."
    if outcome == "PARTIAL_WIN":
        return "Trade achieved at least 1R favorable excursion but did not hit final target."
    if outcome == "BREAKEVEN":
        return "Trade ended near entry without target or stop."
    if outcome == "CHOP_NO_FOLLOWTHROUGH":
        return "Trade produced neither meaningful favorable nor adverse excursion."
    return "Maximum holding window expired before target or stop."


def _failure_from_outcome(outcome: OutcomeLabelResult) -> FailurePatternRecord:
    return FailurePatternRecord(
        failure_id=str(uuid5(NAMESPACE_URL, f"tradevision:failure:{outcome.run_id}:{outcome.pattern_id}:{outcome.outcome_label}")),
        symbol=outcome.symbol,
        pattern_id=outcome.pattern_id,
        outcome_label=outcome.outcome_label,
        failure_reason=_failure_reason(outcome.outcome_label),
        contributing_factors=_failure_factors(outcome),
        severity="high" if outcome.outcome_label in {"SL_HIT", "FAKE_BREAKOUT"} else "medium",
        created_at=now_iso(),
    )


def _failure_from_memory(record: BehaviorMemoryRecord) -> FailurePatternRecord:
    label = record.outcome_label if record.outcome_label in FAILURE_OUTCOMES else "CHOP_NO_FOLLOWTHROUGH"
    return FailurePatternRecord(
        failure_id=str(uuid5(NAMESPACE_URL, f"tradevision:memory-failure:{record.memory_id}:{label}")),
        symbol=record.symbol,
        pattern_id=record.pattern_id,
        outcome_label=label,  # type: ignore[arg-type]
        failure_reason=_failure_reason(label),
        contributing_factors=[record.reason, f"session={record.session_phase}", f"market_state={record.market_state}"],
        severity="high" if label in {"SL_HIT", "FAKE_BREAKOUT"} else "medium",
        created_at=now_iso(),
    )


def _failure_reason(label: str) -> str:
    if label == "FAKE_BREAKOUT":
        return "fake breakout"
    if label == "SL_HIT":
        return "stop loss hit"
    if label == "RETEST_FAIL":
        return "retest failed"
    if label == "CHOP_NO_FOLLOWTHROUGH":
        return "chop no follow-through"
    return "non-continuation outcome"


def _failure_factors(outcome: OutcomeLabelResult) -> list[str]:
    factors = [outcome.reason, f"mfe={outcome.mfe}", f"mae={outcome.mae}"]
    if outcome.fakeout_detected:
        factors.append("early fakeout detected")
    if outcome.bars_to_sl is not None:
        factors.append(f"bars_to_sl={outcome.bars_to_sl}")
    return factors


def _no_trade_lessons(failures: list[FailurePatternRecord]) -> list[str]:
    if not failures:
        return ["No failure memory yet; keep minimum evidence guard active."]
    lessons = []
    counts = Counter(f.failure_reason for f in failures)
    for reason, count in counts.most_common(5):
        lessons.append(f"{reason}: {count} stored cases; require extra confirmation before similar entries.")
    return lessons


def _mock_predicted_probability(pattern_id: str) -> float:
    if "continuation" in pattern_id or "support" in pattern_id:
        return 64.0
    if "fakeout" in pattern_id or "retest" in pattern_id:
        return 42.0
    if "lunch" in pattern_id or "compression" in pattern_id:
        return 28.0
    return 50.0


def _evidence_quality(sample_count: int) -> str:
    if sample_count >= 100:
        return "STRONG"
    if sample_count >= MINIMUM_SAMPLE_SIZE:
        return "MEDIUM"
    return "LOW"


def _audit_fields(request: OutcomeLabelRequest, evaluated_bars: int) -> dict[str, object]:
    return {
        "entry_price": request.entry_price,
        "stop_loss": request.stop_loss,
        "target": request.target,
        "entry_timestamp_ns": request.entry_timestamp_ns,
        "max_holding_bars": request.max_holding_bars,
        "evaluated_bars": evaluated_bars,
        "causal_rule": "Outcome labeling reads only bars at or after entry in the supplied replay/simulation slice.",
    }


def _run_id(request: OutcomeLabelRequest) -> str:
    return str(uuid5(NAMESPACE_URL, f"tradevision:outcome:{request.series.symbol}:{request.pattern_id}:{request.entry_price}:{request.stop_loss}:{request.target}:{len(request.series.bars)}"))
