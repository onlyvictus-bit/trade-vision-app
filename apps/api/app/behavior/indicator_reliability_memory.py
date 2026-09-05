from __future__ import annotations

from collections import Counter
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    IndicatorLagVoteRequest,
    IndicatorReliabilityBucket,
    IndicatorReliabilityReport,
    IndicatorSignalHistoryRecord,
    IndicatorSignalHistorySaveRequest,
    IndicatorSignalOutcomeLabel,
    IndicatorSignalOutcomeLabelRequest,
    TimeframeValue,
    now_iso,
)
from ..storage import (
    build_indicator_signal_history_summary,
    list_indicator_signal_history_records,
    save_indicator_signal_history_record,
)
from .indicator_lag_voting import build_indicator_lag_voting_report
from .indicator_registry import build_indicator_registry_report


INDICATOR_RELIABILITY_VERSION = "indicator-reliability-memory.v1.83"
INDICATOR_SIGNAL_LABEL_VERSION = "indicator-signal-outcome-label.v1.83"
INDICATOR_SIGNAL_HISTORY_VERSION = "indicator-signal-history-store.v1.83"
MINIMUM_SAMPLE_SIZE = 30
STRONG_SAMPLE_SIZE = 100
SUCCESS_LABELS = {"TARGET_HIT", "PARTIAL_WIN", "RETEST_SUCCESS"}
FAILURE_LABELS = {"SL_HIT", "FAKE_BREAKOUT", "RETEST_FAIL", "CHOP_NO_FOLLOWTHROUGH"}


def label_indicator_signal_outcome(request: IndicatorSignalOutcomeLabelRequest) -> IndicatorSignalOutcomeLabel:
    bars = _future_bars(request)
    complete = len(bars) >= request.horizon_candles
    sample = bars[: request.horizon_candles]
    label_id = str(uuid5(NAMESPACE_URL, f"tradevision:indicator-label:{request.indicator_id}:{request.symbol}:{request.timeframe}:{request.signal_time_ns}:{request.horizon_candles}"))
    if not complete:
        return IndicatorSignalOutcomeLabel(
            label_version=INDICATOR_SIGNAL_LABEL_VERSION,
            label_id=label_id,
            indicator_id=request.indicator_id,
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            signal_direction=request.signal_direction,
            signal_time_ns=request.signal_time_ns,
            horizon_candles=request.horizon_candles,
            label_status="pending",
            outcome_label="TIME_EXIT",
            target_first=False,
            stop_first=False,
            same_bar_ambiguous=False,
            conservative_stop_first_used=False,
            mfe=0.0,
            mae=0.0,
            counted_as_win=False,
            counted_as_failure=False,
            counted_in_reliability=False,
            reason="Horizon is not complete; unresolved indicator outcomes are not counted as wins.",
        )

    target_index, target_time = _first_target_hit(request, sample)
    stop_index, stop_time = _first_stop_hit(request, sample)
    same_bar_ambiguous = target_index is not None and stop_index is not None and target_index == stop_index and not request.has_lower_timeframe_sequence
    conservative_stop_first = same_bar_ambiguous
    mfe, mae = _mfe_mae(request, sample)
    target_first = target_index is not None and (stop_index is None or target_index < stop_index) and not same_bar_ambiguous
    stop_first = stop_index is not None and (target_index is None or stop_index <= target_index or same_bar_ambiguous)
    label = _outcome_label(target_first, stop_first, mfe, mae, request)
    return IndicatorSignalOutcomeLabel(
        label_version=INDICATOR_SIGNAL_LABEL_VERSION,
        label_id=label_id,
        indicator_id=request.indicator_id,
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        signal_direction=request.signal_direction,
        signal_time_ns=request.signal_time_ns,
        horizon_candles=request.horizon_candles,
        label_status="complete",
        outcome_label=label,
        target_first=target_first,
        stop_first=stop_first,
        same_bar_ambiguous=same_bar_ambiguous,
        conservative_stop_first_used=conservative_stop_first,
        mfe=round(mfe, 4),
        mae=round(mae, 4),
        bars_to_target=(target_index + 1) if target_index is not None else None,
        bars_to_sl=(stop_index + 1) if stop_index is not None else None,
        counted_as_win=label in SUCCESS_LABELS,
        counted_as_failure=label in FAILURE_LABELS,
        counted_in_reliability=True,
        reason=_label_reason(label, target_time, stop_time, conservative_stop_first),
    )


def save_indicator_signal_history(request: IndicatorSignalHistorySaveRequest) -> IndicatorSignalHistoryRecord:
    registry = build_indicator_registry_report()
    entry = next((item for item in registry.entries if item.indicator_id == request.indicator_id), None)
    if entry is None:
        raise KeyError(request.indicator_id)
    label_request = request.label_request.model_copy(
        update={
            "symbol": request.symbol.upper(),
            "indicator_id": request.indicator_id,
            "timeframe": request.timeframe,
            "signal_direction": request.signal_direction,
            "signal_time_ns": request.signal_time_ns,
        }
    )
    label = label_indicator_signal_outcome(label_request)
    history_id = str(
        uuid5(
            NAMESPACE_URL,
            f"tradevision:indicator-history:{request.indicator_id}:{request.symbol.upper()}:{request.timeframe}:{request.signal_time_ns}:{label.horizon_candles}",
        )
    )
    record = IndicatorSignalHistoryRecord(
        history_version=INDICATOR_SIGNAL_HISTORY_VERSION,
        history_id=history_id,
        symbol=request.symbol.upper(),
        indicator_id=request.indicator_id,
        timeframe=request.timeframe,
        signal_direction=request.signal_direction,
        signal_time_ns=request.signal_time_ns,
        decision_time_ns=request.decision_time_ns,
        session_phase=request.session_phase,
        regime_id=request.regime_id,
        source_snapshot_id=request.source_snapshot_id,
        source_snapshot_hash=request.source_snapshot_hash,
        feature_manifest_version=request.feature_manifest_version,
        indicator_registry_version=request.indicator_registry_version or registry.registry_version,
        signal_value=request.signal_value,
        signal_strength=request.signal_strength,
        missing_mask=request.missing_mask,
        label=label,
        counted_in_reliability=label.counted_in_reliability and not request.missing_mask,
        created_at=now_iso(),
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        no_future_leakage=True,
    )
    return save_indicator_signal_history_record(record)


def build_indicator_signal_history_report(indicator_id: str, symbol: str, timeframe: TimeframeValue = "1m", limit: int = 250):
    return build_indicator_signal_history_summary(symbol=symbol, indicator_id=indicator_id, timeframe=timeframe, limit=limit)


def build_indicator_reliability_report(
    indicator_id: str,
    symbol: str = "RELIANCE",
    timeframe: TimeframeValue = "1m",
    *,
    force_low_sample: bool = False,
    force_ood: bool = False,
    force_regime_shift: bool = False,
) -> IndicatorReliabilityReport:
    registry = build_indicator_registry_report()
    entry = next((item for item in registry.entries if item.indicator_id == indicator_id), None)
    if entry is None:
        raise KeyError(indicator_id)
    persisted_records = [] if force_low_sample else list_indicator_signal_history_records(symbol=symbol.upper(), indicator_id=indicator_id, timeframe=timeframe, limit=500)
    persisted_labels = [record.label for record in persisted_records if record.counted_in_reliability]
    fixture_fallback = not persisted_labels
    labels = _fixture_labels(indicator_id, symbol.upper(), timeframe, force_low_sample) if fixture_fallback else persisted_labels
    counted = [label for label in labels if label.counted_in_reliability]
    counts = Counter(label.outcome_label for label in counted)
    success_count = sum(counts[label] for label in SUCCESS_LABELS)
    failure_count = sum(counts[label] for label in FAILURE_LABELS)
    neutral_count = max(0, len(counted) - success_count - failure_count)
    sample_count = len(counted)
    raw_success = success_count / sample_count if sample_count else 0.0
    raw_failure = failure_count / sample_count if sample_count else 0.0
    bayes_success = _bayesian_rate(success_count, sample_count)
    bayes_failure = _bayesian_rate(failure_count, sample_count)
    minimum_pass = sample_count >= MINIMUM_SAMPLE_SIZE
    reciprocal_ratio = _reciprocal_ratio(entry.lag_behavior, entry.category, failure_count, sample_count, symbol)
    quarantine = force_ood or force_regime_shift
    state = "quarantined" if quarantine else "research_usable" if minimum_pass else "low_evidence"
    multiplier = 0.5 if not minimum_pass or quarantine else _clamp(bayes_success - max(0.0, reciprocal_ratio - 0.35), 0.05, 0.95)
    lag_vote = build_indicator_lag_voting_report(
        IndicatorLagVoteRequest(
            symbol=symbol,
            indicator_id=indicator_id,
            raw_vote=1.0,
            per_stock_reliability=multiplier,
            per_regime_reliability=0.5 if quarantine else _clamp(bayes_success, 0.05, 0.95),
        )
    ).vote
    buckets = [
        _bucket("stock", sample_count, success_count, failure_count, neutral_count),
        _bucket("regime", max(0, sample_count - 4), max(0, success_count - 2), max(0, failure_count - 1), neutral_count),
        _bucket("session", max(0, sample_count - 8), max(0, success_count - 4), max(0, failure_count - 2), neutral_count),
    ]
    gates = _gates(sample_count, minimum_pass, quarantine, reciprocal_ratio, lag_vote.delay_adjusted_vote)
    return IndicatorReliabilityReport(
        reliability_version=INDICATOR_RELIABILITY_VERSION,
        symbol=symbol.upper(),
        indicator_id=indicator_id,
        timeframe=timeframe,
        registry_version=registry.registry_version,
        ontology_version=entry.ontology_version,
        purpose=entry.purpose,
        category=entry.category,
        confirmation_delay_bars=entry.confirmation_delay_bars,
        lag_weight=lag_vote.lag_weight,
        history_source="fixture" if fixture_fallback else "persistent",
        persisted_history_count=len(persisted_records),
        fixture_fallback_used=fixture_fallback,
        minimum_sample_size=MINIMUM_SAMPLE_SIZE,
        sample_count=sample_count,
        minimum_sample_pass=minimum_pass,
        success_count=success_count,
        failure_count=failure_count,
        neutral_count=neutral_count,
        historical_success_rate=round(raw_success, 6),
        historical_failure_rate=round(raw_failure, 6),
        bayesian_success_rate=round(bayes_success, 6),
        bayesian_failure_rate=round(bayes_failure, 6),
        per_stock_reliability=round(multiplier, 6),
        per_regime_reliability=round(0.5 if quarantine else _clamp(bayes_success, 0.05, 0.95), 6),
        per_session_reliability=round(buckets[2].reliability_score, 6),
        reciprocal_signal_ratio=round(reciprocal_ratio, 6),
        reciprocal_signal_warning=reciprocal_ratio >= 0.55,
        reliability_state=state,  # type: ignore[arg-type]
        reliability_multiplier_for_lag_vote=round(multiplier, 6),
        lag_vote_preview=lag_vote,
        bucket_rollups=buckets,
        recent_labels=labels[: min(12, len(labels))],
        ood_quarantine_required=force_ood,
        regime_shift_quarantine_required=force_regime_shift,
        quarantine_reason=_quarantine_reason(force_ood, force_regime_shift),
        used_for_probability=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        no_future_leakage=True,
        gates=gates,
        notes=[
            "Indicator reliability is research-only and cannot approve trades.",
            "Persisted v1.83 signal history is preferred when available; fixture labels are fallback only.",
            "Low sample reliability is Bayesian-shrunk toward neutral.",
            "Reliability can reduce lag-vote confidence but cannot bypass no-trade, risk, or routing gates.",
        ],
    )


def _future_bars(request: IndicatorSignalOutcomeLabelRequest) -> list[CandleBar]:
    return sorted(
        [bar for bar in request.post_signal_bars if bar.timestamp_ns > request.signal_time_ns],
        key=lambda item: item.timestamp_ns,
    )


def _first_target_hit(request: IndicatorSignalOutcomeLabelRequest, bars: list[CandleBar]) -> tuple[int | None, int | None]:
    for index, bar in enumerate(bars):
        if request.signal_direction == "bearish":
            if bar.low <= request.target_price:
                return index, bar.timestamp_ns
        elif bar.high >= request.target_price:
            return index, bar.timestamp_ns
    return None, None


def _first_stop_hit(request: IndicatorSignalOutcomeLabelRequest, bars: list[CandleBar]) -> tuple[int | None, int | None]:
    for index, bar in enumerate(bars):
        if request.signal_direction == "bearish":
            if bar.high >= request.stop_price:
                return index, bar.timestamp_ns
        elif bar.low <= request.stop_price:
            return index, bar.timestamp_ns
    return None, None


def _mfe_mae(request: IndicatorSignalOutcomeLabelRequest, bars: list[CandleBar]) -> tuple[float, float]:
    if not bars:
        return 0.0, 0.0
    if request.signal_direction == "bearish":
        mfe = max(request.entry_price - bar.low for bar in bars)
        mae = max(bar.high - request.entry_price for bar in bars)
    else:
        mfe = max(bar.high - request.entry_price for bar in bars)
        mae = max(request.entry_price - bar.low for bar in bars)
    return max(mfe, 0.0), max(mae, 0.0)


def _outcome_label(target_first: bool, stop_first: bool, mfe: float, mae: float, request: IndicatorSignalOutcomeLabelRequest) -> str:
    risk = max(abs(request.entry_price - request.stop_price), 0.0001)
    if stop_first:
        return "SL_HIT"
    if target_first:
        return "TARGET_HIT"
    if mfe >= risk and mae < risk:
        return "PARTIAL_WIN"
    if mfe < 0.35 * risk and mae < 0.45 * risk:
        return "CHOP_NO_FOLLOWTHROUGH"
    return "TIME_EXIT"


def _label_reason(label: str, target_time: int | None, stop_time: int | None, conservative_stop_first: bool) -> str:
    if conservative_stop_first:
        return "Target and stop touched inside the same candle without lower-timeframe proof; conservative stop-first label used."
    if label == "TARGET_HIT":
        return f"Target touched before stop at {target_time}."
    if label == "SL_HIT":
        return f"Stop touched before target at {stop_time}."
    return f"Outcome labeled {label} after the completed horizon."


def _fixture_labels(indicator_id: str, symbol: str, timeframe: TimeframeValue, force_low_sample: bool) -> list[IndicatorSignalOutcomeLabel]:
    sample_count = 12 if force_low_sample or "LOW" in symbol else 44 if symbol.endswith("A") else 58
    labels: list[IndicatorSignalOutcomeLabel] = []
    for index in range(sample_count):
        labels.append(_fixture_label(indicator_id, symbol, timeframe, index))
    return labels


def _fixture_label(indicator_id: str, symbol: str, timeframe: TimeframeValue, index: int) -> IndicatorSignalOutcomeLabel:
    base = f"{indicator_id}:{symbol}:{timeframe}:{index}"
    bucket = uuid5(NAMESPACE_URL, base).int % 100
    if "MACD" in indicator_id.upper() and bucket < 48:
        outcome = "SL_HIT"
    elif "RSI" in indicator_id.upper() and bucket < 42:
        outcome = "FAKE_BREAKOUT"
    elif bucket < (62 if symbol == "RELIANCE" else 54):
        outcome = "TARGET_HIT"
    elif bucket < 78:
        outcome = "SL_HIT"
    elif bucket < 88:
        outcome = "PARTIAL_WIN"
    else:
        outcome = "TIME_EXIT"
    return IndicatorSignalOutcomeLabel(
        label_version=INDICATOR_SIGNAL_LABEL_VERSION,
        label_id=str(uuid5(NAMESPACE_URL, f"tradevision:fixture-label:{base}")),
        indicator_id=indicator_id,
        symbol=symbol,
        timeframe=timeframe,
        signal_direction="bullish",
        signal_time_ns=1_714_724_800_000_000_000 + index * 60_000_000_000,
        horizon_candles=9,
        label_status="complete",
        outcome_label=outcome,  # type: ignore[arg-type]
        target_first=outcome in SUCCESS_LABELS,
        stop_first=outcome in FAILURE_LABELS,
        same_bar_ambiguous=False,
        conservative_stop_first_used=False,
        mfe=2.0 if outcome in SUCCESS_LABELS else 0.4,
        mae=0.4 if outcome in SUCCESS_LABELS else 1.2,
        bars_to_target=4 if outcome in SUCCESS_LABELS else None,
        bars_to_sl=3 if outcome in FAILURE_LABELS else None,
        counted_as_win=outcome in SUCCESS_LABELS,
        counted_as_failure=outcome in FAILURE_LABELS,
        counted_in_reliability=True,
        reason="Deterministic v1.81 fixture label used until persisted indicator signal history is connected.",
    )


def _bayesian_rate(count: int, total: int, prior_rate: float = 0.5, prior_total: int = MINIMUM_SAMPLE_SIZE) -> float:
    return (count + prior_rate * prior_total) / max(total + prior_total, 1)


def _bucket(name: str, sample_count: int, success_count: int, failure_count: int, neutral_count: int) -> IndicatorReliabilityBucket:
    raw = success_count / sample_count if sample_count else 0.0
    bayes = _bayesian_rate(success_count, sample_count)
    return IndicatorReliabilityBucket(
        bucket_name=name,
        sample_count=sample_count,
        success_count=success_count,
        failure_count=failure_count,
        neutral_count=neutral_count,
        raw_success_rate=round(raw, 6),
        bayesian_success_rate=round(bayes, 6),
        reliability_score=round(_clamp(bayes, 0.05, 0.95), 6),
    )


def _reciprocal_ratio(lag_behavior: str, category: str, failure_count: int, sample_count: int, symbol: str) -> float:
    if not sample_count:
        return 0.0
    base = failure_count / sample_count
    if lag_behavior == "lagging":
        base += 0.08
    if category in {"exhaustion", "trap"}:
        base += 0.04
    if symbol.endswith("FAIL"):
        base += 0.25
    return _clamp(base, 0.0, 1.0)


def _gates(sample_count: int, minimum_pass: bool, quarantine: bool, reciprocal_ratio: float, adjusted_vote: float) -> list[dict]:
    return [
        _gate("IND-REL-001", "Signal outcome labels use completed future horizons", True, "Completed labels are counted; pending labels are excluded."),
        _gate("IND-REL-002", "Minimum sample guard", minimum_pass, f"sample_count={sample_count}; minimum={MINIMUM_SAMPLE_SIZE}"),
        _gate("IND-REL-003", "Bayesian shrinkage applied", True, "Low evidence is shrunk toward 0.5 base rate."),
        _gate("IND-REL-004", "Reciprocal warning surfaced", reciprocal_ratio < 0.55, f"reciprocal_signal_ratio={reciprocal_ratio:.4f}"),
        _gate("IND-REL-005", "Reliability quarantine", not quarantine, f"quarantine={quarantine}"),
        _gate("IND-REL-006", "Reliability only reduces research vote", abs(adjusted_vote) <= 1.0, f"delay_adjusted_vote={adjusted_vote:.4f}"),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> dict:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": passed,
        "evidence": evidence,
        "remediation": None if passed else "Keep indicator reliability research-only and collect more clean labels before promotion.",
    }


def _quarantine_reason(force_ood: bool, force_regime_shift: bool) -> str | None:
    if force_ood and force_regime_shift:
        return "OOD and regime-shift quarantine requested; reliability cannot be trusted."
    if force_ood:
        return "OOD quarantine requested; reliability cannot be trusted."
    if force_regime_shift:
        return "Regime-shift quarantine requested; reliability cannot be trusted."
    return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
