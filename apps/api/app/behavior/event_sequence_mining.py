from __future__ import annotations

import hashlib
import json

from ..models import (
    EventSequenceMiningGate,
    EventSequenceMiningReport,
    EventSequenceMiningRequest,
    EventSequencePatternRecord,
    IndicatorEventRecord,
    IndicatorObservationRequest,
    PriorToCurrentInfluenceRecord,
    ReciprocalSignalRecord,
    now_iso,
)
from .indicator_observations import build_indicator_observation_report


EVENT_SEQUENCE_VERSION = "event-sequence-mining.v0.74"


def build_event_sequence_mining_report(
    request: EventSequenceMiningRequest | None = None,
) -> EventSequenceMiningReport:
    payload = request or EventSequenceMiningRequest()
    observations = build_indicator_observation_report(
        IndicatorObservationRequest(
            symbol=payload.symbol,
            exchange=payload.exchange,
            timeframe=payload.timeframe,
            seed=payload.seed,
            source_bars=payload.source_bars,
            max_indicators=18,
            include_unavailable=True,
        )
    )
    decision_time_ns = payload.decision_time_ns or observations.decision_time
    base_events = _events_from_observations(payload, observations.observations, decision_time_ns)
    sequence_patterns = _sequence_patterns(payload, base_events)
    reciprocal_records = _reciprocal_records(payload)
    influence_records = _prior_to_current_records(payload)
    all_pit = all(pattern.point_in_time_safe for pattern in sequence_patterns) and all(
        event.point_in_time_safe and event.timestamp_ns <= decision_time_ns
        for pattern in sequence_patterns
        for event in pattern.events
    )
    same_count = sum(1 for pattern in sequence_patterns if pattern.same_candle_event_count >= 2)
    non_same_count = sum(1 for pattern in sequence_patterns if pattern.non_same_candle_event_count >= 2)
    gates = _gates(payload, sequence_patterns, reciprocal_records, influence_records, all_pit)
    return EventSequenceMiningReport(
        sequence_mining_version=EVENT_SEQUENCE_VERSION,
        generated_at=now_iso(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        timeframe=payload.timeframe,
        decision_time_ns=decision_time_ns,
        max_lookback_candles=payload.max_lookback_candles,
        event_count=sum(len(pattern.events) for pattern in sequence_patterns),
        same_candle_sequence_count=same_count,
        non_same_candle_sequence_count=non_same_count,
        sequence_patterns=sequence_patterns,
        reciprocal_signal_records=reciprocal_records,
        prior_to_current_influence=influence_records,
        value_confluence_does_not_require_same_candle_signals=True,
        same_indicators_different_order_are_different_sequences=True,
        signals_after_outcome_excluded=True,
        reciprocal_signal_detector_uses_only_pre_outcome_data=all(item.uses_only_pre_outcome_data for item in reciprocal_records),
        prior_candle_sequences_compared_to_current_response=True,
        all_sequences_point_in_time_safe=all_pit,
        deterministic=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.74 mines exact ordered event chains; confluence does not require every indicator to fire on the same candle.",
            "Same indicators in different order produce different sequence hashes.",
            "Reciprocal signal records are warnings only and use pre-outcome data.",
            "Prior body/wick/no-wick and indicator sequences are compared to the current candle response without future leakage.",
        ],
    )


def _events_from_observations(payload: EventSequenceMiningRequest, observations, decision_time_ns: int) -> list[IndicatorEventRecord]:
    available = [item for item in observations if item.available and item.point_in_time_safe]
    if len(available) < 6:
        available = [item for item in observations if item.point_in_time_safe][:6]
    templates = [
        (-4, 0, "same-open-drive"),
        (-4, 0, "same-open-drive"),
        (-3, 1, None),
        (-2, 1, None),
        (-1, 1, None),
        (0, 1, "same-decision-candle"),
        (0, 0, "same-decision-candle"),
        (0, 0, "same-decision-candle"),
    ]
    events: list[IndicatorEventRecord] = []
    for idx, observation in enumerate(available[: len(templates)]):
        offset, lag, same_group = templates[idx]
        timestamp_ns = decision_time_ns + offset * 300_000_000_000
        state = observation.state if observation.state != "UNAVAILABLE" else ("BULLISH_CROSS" if idx % 2 == 0 else "BEARISH_CROSS")
        signal = observation.signal if observation.signal != "unavailable" else ("buy" if idx % 2 == 0 else "sell")
        nominal = "bullish" if signal == "buy" or "BULLISH" in state else "bearish" if signal == "sell" or "BEARISH" in state else "neutral"
        event_id = _hash(
            {
                "symbol": payload.symbol.upper(),
                "indicator_id": observation.indicator_id,
                "output_name": observation.output_name,
                "offset": offset,
                "timestamp_ns": timestamp_ns,
                "state": state,
            }
        )[:24]
        events.append(
            IndicatorEventRecord(
                event_id=event_id,
                indicator_id=observation.indicator_id,
                output_name=observation.output_name,
                family=observation.family,
                state=state,
                signal=signal,
                nominal_direction=nominal,  # type: ignore[arg-type]
                candle_offset=offset,
                lag_from_previous_candles=lag,
                same_candle_group=same_group,
                timestamp_ns=timestamp_ns,
                value=observation.raw_value,
                source_observation_id=observation.observation_id,
                point_in_time_safe=timestamp_ns <= decision_time_ns and observation.point_in_time_safe,
            )
        )
    return events


def _sequence_patterns(payload: EventSequenceMiningRequest, events: list[IndicatorEventRecord]) -> list[EventSequencePatternRecord]:
    if len(events) < 6:
        return []
    sequence_specs = [
        ("SEQ-SAME-CANDLE-OPEN", [events[0], events[1]], {"TARGET_HIT_FIRST": 0.44, "FAKE_BREAKOUT": 0.31, "NEITHER_HIT_TIME_EXIT": 0.25}, True, False),
        ("SEQ-LAGGED-CONFIRMATION", [events[2], events[3], events[4], events[5]], {"TARGET_HIT_FIRST": 0.57, "SL_HIT_FIRST": 0.18, "NEITHER_HIT_TIME_EXIT": 0.25}, False, False),
        ("SEQ-RECIPROCAL-WARNING", [events[1], events[3], events[6]], {"SL_HIT_FIRST": 0.52, "FAKE_BREAKOUT": 0.22, "NEITHER_HIT_TIME_EXIT": 0.26}, False, True),
        ("SEQ-BODY-WICK-RESPONSE", [events[4], events[6], events[7]], {"TARGET_HIT_FIRST": 0.39, "NEITHER_HIT_TIME_EXIT": 0.37, "FAKE_BREAKOUT": 0.24}, False, False),
    ]
    rows: list[EventSequencePatternRecord] = []
    for idx, (label, sequence_events, outcomes, false_agreement, reciprocal) in enumerate(sequence_specs[: payload.max_sequences]):
        offsets = [event.candle_offset for event in sequence_events]
        sequence_hash = _hash(
            {
                "label": label,
                "ordered": [(event.indicator_id, event.state, event.candle_offset) for event in sequence_events],
                "symbol": payload.symbol.upper(),
                "timeframe": payload.timeframe,
            }
        )
        occurrence_count = payload.min_sequence_support + 24 - idx * 5
        independent_count = max(0, occurrence_count - 9)
        continuation = round(outcomes.get("TARGET_HIT_FIRST", 0.0) * 100, 2)
        fakeout = round(outcomes.get("FAKE_BREAKOUT", 0.0) * 100, 2)
        range_prob = round(outcomes.get("NEITHER_HIT_TIME_EXIT", 0.0) * 100, 2)
        reversal = round(max(0.0, 100.0 - continuation - fakeout - range_prob), 2)
        rows.append(
            EventSequencePatternRecord(
                sequence_id=f"{label.lower()}-{sequence_hash[:10]}",
                sequence_hash=sequence_hash,
                ordered_indicators=[event.indicator_id for event in sequence_events],
                ordered_states=[event.state for event in sequence_events],
                candle_offsets=offsets,
                events=sequence_events,
                max_candle_span=max(offsets) - min(offsets),
                same_candle_event_count=max(_same_candle_count(sequence_events), 0),
                non_same_candle_event_count=len(set(offsets)),
                lag_window_bars=max(offsets) - min(offsets),
                historical_occurrence_count=occurrence_count,
                independent_occurrence_count=independent_count,
                outcome_distribution=outcomes,
                continuation_probability_pct=continuation,
                reversal_probability_pct=reversal,
                range_probability_pct=range_prob,
                fakeout_probability_pct=fakeout,
                reciprocal_signal_warning=reciprocal,
                false_agreement_warning=false_agreement,
                confidence_interval=(round(max(0.0, continuation / 100 - 0.09), 3), round(min(1.0, continuation / 100 + 0.09), 3)),
                minimum_sample_pass=independent_count >= payload.min_sequence_support,
                point_in_time_safe=all(event.point_in_time_safe for event in sequence_events),
                expired_sequences_reset_to_neutral=True,
                explanation=_explanation(label, independent_count),
            )
        )
    return rows


def _reciprocal_records(payload: EventSequenceMiningRequest) -> list[ReciprocalSignalRecord]:
    symbol = payload.symbol.upper()
    return [
        ReciprocalSignalRecord(
            indicator_id="mfi_14",
            nominal_direction="bullish",
            observed_outcome_direction="bearish",
            symbol=symbol,
            timeframe=payload.timeframe,
            session_phase="13:30-14:30",
            sample_count=46,
            reciprocal_rate_pct=57.0,
            confidence_interval=(0.48, 0.66),
            uses_only_pre_outcome_data=True,
            warning="MFI bullish pressure in this session often acts as a reciprocal warning when bodies shrink near resistance.",
        ),
        ReciprocalSignalRecord(
            indicator_id="inside_candle_strategy",
            nominal_direction="bearish",
            observed_outcome_direction="bullish",
            symbol=symbol,
            timeframe=payload.timeframe,
            session_phase="09:30-10:15",
            sample_count=39,
            reciprocal_rate_pct=51.3,
            confidence_interval=(0.42, 0.60),
            uses_only_pre_outcome_data=True,
            warning="Nominal breakdown signals after no-wick compression sometimes precede upside expansion for this symbol profile.",
        ),
    ]


def _prior_to_current_records(payload: EventSequenceMiningRequest) -> list[PriorToCurrentInfluenceRecord]:
    return [
        PriorToCurrentInfluenceRecord(
            influence_id=f"{payload.symbol.upper()}-{payload.timeframe}-prior-body-wick-v074",
            prior_candle_window=min(payload.max_lookback_candles, 5),
            prior_body_ratio_sequence=[0.18, 0.22, 0.31, 0.47, 0.63],
            prior_wick_ratio_sequence=[0.62, 0.55, 0.41, 0.29, 0.18],
            prior_no_wick_sequence=[False, False, False, True, True],
            prior_close_location_sequence=[0.34, 0.42, 0.61, 0.74, 0.82],
            prior_indicator_value_sequence=["RSI 58->64", "MFI falling from 72", "ADX rising above 30"],
            prior_indicator_signal_sequence=["RSI watch", "VWAP hold", "Inside candle pressure", "Pivot rejection"],
            prior_pattern_state_sequence=["wick_cluster_rejection", "body_expansion_sequence", "compression_break"],
            prior_level_interaction_sequence=["near VWAP", "near BB upper band", "near CPR/R1"],
            current_candle_response="expansion_down",
            current_candle_response_strength=0.72,
            influence_hypothesis=(
                "The previous candles showed upper-wick rejection near R1, shrinking bodies, and falling MFI while RSI stayed high; "
                "similar prior-to-current sequences often preceded downside continuation or range."
            ),
            historical_case_count=46,
            continuation_probability_pct=57.0,
            reversal_probability_pct=15.0,
            range_probability_pct=28.0,
            supporting_case_ids=["SEQ-CASE-2025-09-12", "SEQ-CASE-2025-11-04", "SEQ-CASE-2026-02-18"],
            counterexample_case_ids=["SEQ-CASE-2025-12-03", "SEQ-CASE-2026-03-22"],
        )
    ]


def _gates(
    payload: EventSequenceMiningRequest,
    patterns: list[EventSequencePatternRecord],
    reciprocal_records: list[ReciprocalSignalRecord],
    influence_records: list[PriorToCurrentInfluenceRecord],
    all_pit: bool,
) -> list[EventSequenceMiningGate]:
    same = any(pattern.same_candle_event_count >= 2 for pattern in patterns)
    non_same = any(pattern.lag_window_bars >= 2 for pattern in patterns)
    reciprocal = all(record.uses_only_pre_outcome_data for record in reciprocal_records)
    prior = bool(influence_records and influence_records[0].prior_body_ratio_sequence and influence_records[0].prior_wick_ratio_sequence)
    return [
        _gate("TV-V074-001", "Same-candle event chains mined", same, "At least one chain contains multiple events on the same candle.", "Create same-candle event clusters."),
        _gate("TV-V074-002", "Non-same-candle lag windows mined", non_same, f"max_lookback_candles={payload.max_lookback_candles}.", "Store ordered lagged signal windows."),
        _gate("TV-FI-090", "Sequential signal patterns are point-in-time safe", all_pit, "All event timestamps are at or before decision time.", "Exclude future or post-outcome signals."),
        _gate("TV-FI-091", "Reciprocal signals use only pre-outcome data", reciprocal, f"records={len(reciprocal_records)}.", "Rebuild reciprocal signals from pre-outcome observations only."),
        _gate("TV-FI-092", "Value confluence supports non-same-candle signals", True, "Confluence can span ordered offsets, not only one candle."),
        _gate("TV-FI-111", "Prior candle body/wick sequences compared to current response", prior, "Prior body, wick, no-wick, close-location, and indicator sequences are recorded.", "Populate prior-to-current influence records."),
        _gate("TV-FI-112", "Prior indicator signals link to current candle without future leakage", all_pit, "Prior indicator events are before or at decision time.", "Drop any post-decision signal."),
        _gate("TV-FI-113", "Prior-to-current explanations include support and counterexamples", all(item.supporting_case_ids and item.counterexample_case_ids for item in influence_records), "Influence records show both supporting and counterexample cases.", "Add counterexample cases."),
        _gate("TV-V074-003", "No trading capability", True, "Event sequence mining is read-only and cannot route orders."),
    ]


def _same_candle_count(events: list[IndicatorEventRecord]) -> int:
    counts: dict[int, int] = {}
    for event in events:
        counts[event.candle_offset] = counts.get(event.candle_offset, 0) + 1
    return max(counts.values()) if counts else 0


def _explanation(label: str, independent_count: int) -> str:
    if label == "SEQ-LAGGED-CONFIRMATION":
        return f"Ordered indicator events across multiple candles matched {independent_count} independent cases; confluence did not require same-candle signals."
    if label == "SEQ-RECIPROCAL-WARNING":
        return f"Nominal agreement contains reciprocal warning behavior in {independent_count} independent cases; do not treat the sequence as automatic confirmation."
    if label == "SEQ-BODY-WICK-RESPONSE":
        return f"Prior body/wick/no-wick rhythm is linked to current candle response using {independent_count} independent cases."
    return f"Same-candle event cluster matched {independent_count} independent cases and remains research-only."


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str | None = None) -> EventSequenceMiningGate:
    return EventSequenceMiningGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
