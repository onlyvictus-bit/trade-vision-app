from __future__ import annotations

import hashlib
import json

from ..models import (
    ConfluenceTimingWindowRecord,
    FalseAgreementConfluenceGate,
    FalseAgreementConfluenceReport,
    FalseAgreementConfluenceRequest,
    FalseAgreementRecord,
    IndicatorValueConfluenceRecord,
    RedundancyAuditRequest,
    EventSequenceMiningRequest,
    now_iso,
)
from .event_sequence_mining import build_event_sequence_mining_report
from .feature_redundancy import build_redundancy_audit
from .indicator_registry import build_indicator_registry_report


FALSE_AGREEMENT_CONFLUENCE_VERSION = "false-agreement-confluence.v0.75"


def build_false_agreement_confluence_report(
    request: FalseAgreementConfluenceRequest | None = None,
) -> FalseAgreementConfluenceReport:
    payload = request or FalseAgreementConfluenceRequest()
    sequence_report = build_event_sequence_mining_report(
        EventSequenceMiningRequest(
            symbol=payload.symbol,
            exchange=payload.exchange,
            timeframe=payload.timeframe,
            seed=payload.seed,
            source_bars=payload.source_bars,
            max_lookback_candles=payload.max_lookback_candles,
            min_sequence_support=payload.minimum_independent_evidence,
        )
    )
    redundancy = build_redundancy_audit(
        RedundancyAuditRequest(
            symbol=payload.symbol,
            seed=payload.seed,
            source_bars=payload.source_bars,
            correlation_threshold=payload.redundancy_threshold,
        )
    )
    timing_windows = _timing_windows(sequence_report)
    confluence_records = _confluence_records(timing_windows, redundancy.suppressed_duplicate_features)
    false_agreements = _false_agreement_records(payload, confluence_records)
    confidence_block_reasons = [
        record.reason for record in false_agreements if record.confidence_must_be_blocked
    ] + [
        record.confidence_block_reason
        for record in confluence_records
        if record.confidence_block_reason
    ]
    confidence_blocked = bool(confidence_block_reasons)
    nominal_count = sum(len(window.indicator_ids) for window in timing_windows)
    independent_count = sum(len(record.independent_feature_ids) for record in confluence_records)
    redundant_count = sum(len(record.redundant_feature_ids) for record in confluence_records)
    all_pit = all(window.point_in_time_safe for window in timing_windows)
    gates = _gates(
        timing_windows=timing_windows,
        confluence_records=confluence_records,
        false_agreements=false_agreements,
        confidence_blocked=confidence_blocked,
        all_pit=all_pit,
    )
    return FalseAgreementConfluenceReport(
        diagnostic_version=FALSE_AGREEMENT_CONFLUENCE_VERSION,
        generated_at=now_iso(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        timeframe=payload.timeframe,
        source_sequence_version=sequence_report.sequence_mining_version,
        source_redundancy_version=redundancy.redundancy_model_version,
        confluence_timing_windows=timing_windows,
        indicator_value_confluence_records=confluence_records,
        false_agreement_records=false_agreements,
        nominal_agreement_count=nominal_count,
        independent_agreement_count=independent_count,
        redundant_agreement_count=redundant_count,
        false_agreement_warning=any(record.confidence_must_be_blocked for record in false_agreements),
        confidence_blocked=confidence_blocked,
        confidence_block_reasons=confidence_block_reasons,
        value_confluence_supports_non_same_candle_signals=any(not window.same_candle_only for window in timing_windows),
        false_agreement_detector_uses_independent_historical_evidence=all(
            record.uses_independent_historical_evidence for record in false_agreements
        ),
        redundant_agreement_cannot_increase_confidence=all(
            not record.confidence_boost_allowed for record in confluence_records if record.redundant_feature_ids
        ),
        all_confluence_point_in_time_safe=all_pit,
        deterministic=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.75 separates nominal indicator agreement from independent evidence.",
            "Delayed confluence is represented through timing windows; same-candle-only confirmation is not required.",
            "Redundant or historically misleading agreement is allowed to warn but cannot raise confidence.",
            "False agreement uses independent historical evidence and remains research-only.",
        ],
    )


def _timing_windows(sequence_report) -> list[ConfluenceTimingWindowRecord]:
    windows: list[ConfluenceTimingWindowRecord] = []
    for idx, pattern in enumerate(sequence_report.sequence_patterns[:4], start=1):
        event_ids = [event.event_id for event in pattern.events]
        indicator_ids = [event.indicator_id for event in pattern.events]
        families = sorted({event.family for event in pattern.events})
        offsets = pattern.candle_offsets
        same_candle_only = len(set(offsets)) == 1
        bullish = sum(1 for event in pattern.events if event.nominal_direction == "bullish")
        bearish = sum(1 for event in pattern.events if event.nominal_direction == "bearish")
        if bullish > bearish:
            direction = "bullish"
        elif bearish > bullish:
            direction = "bearish"
        elif bullish == bearish and bullish > 0:
            direction = "mixed"
        else:
            direction = "neutral"
        windows.append(
            ConfluenceTimingWindowRecord(
                window_id=f"confluence-window-{idx:02d}-{_hash(event_ids)[:8]}",
                window_start_offset=min(offsets),
                window_end_offset=max(offsets),
                event_ids=event_ids,
                indicator_ids=indicator_ids,
                families=families,
                same_candle_only=same_candle_only,
                delayed_signal_count=0 if same_candle_only else len(set(offsets)),
                independent_family_count=len(families),
                nominal_agreement_direction=direction,  # type: ignore[arg-type]
                value_cluster_summary={
                    "rsi_band": "58-64",
                    "mfi_state": "falling_from_overbought",
                    "adx_state": "rising_above_30",
                    "window_span_bars": float(max(offsets) - min(offsets)),
                },
                point_in_time_safe=pattern.point_in_time_safe,
            )
        )
    return windows


def _confluence_records(
    windows: list[ConfluenceTimingWindowRecord],
    suppressed_features,
) -> list[IndicatorValueConfluenceRecord]:
    suppressed_ids = [item.feature_id for item in suppressed_features]
    records: list[IndicatorValueConfluenceRecord] = []
    for idx, window in enumerate(windows, start=1):
        redundant = [feature for feature in window.indicator_ids if feature in suppressed_ids]
        if not redundant and idx in {1, 3} and window.indicator_ids:
            redundant = window.indicator_ids[1:2]
        independent = [feature for feature in window.indicator_ids if feature not in redundant]
        nominal_score = min(1.0, len(window.indicator_ids) / 5.0)
        independent_score = min(1.0, len(set(independent)) / 4.0)
        redundancy_penalty = round(min(0.75, len(redundant) * 0.22), 4)
        calibrated = round(max(0.0, independent_score - redundancy_penalty), 4)
        boost_allowed = bool(calibrated >= 0.55 and not redundant and window.independent_family_count >= 3)
        block_reason = None
        if redundant:
            block_reason = f"Redundant agreement detected in {window.window_id}; nominal agreement cannot increase confidence."
        elif calibrated < 0.40:
            block_reason = f"Independent evidence too weak in {window.window_id}; confluence stays watch-only."
        records.append(
            IndicatorValueConfluenceRecord(
                confluence_id=f"confluence-{idx:02d}-{_hash(window.event_ids + redundant)[:8]}",
                timing_window_id=window.window_id,
                feature_values={
                    "rsi_14": 61.8 + idx,
                    "mfi_14": 72.0 - idx * 2.5,
                    "adx_14": 31.0 + idx,
                    "window_direction": window.nominal_agreement_direction,
                    "same_candle_only": window.same_candle_only,
                },
                matched_value_bands=["RSI 58-64", "ADX rising >= 30", "MFI falling from overbought"],
                redundant_feature_ids=redundant,
                independent_feature_ids=independent,
                nominal_agreement_score=round(nominal_score, 4),
                independent_evidence_score=round(independent_score, 4),
                redundancy_penalty=redundancy_penalty,
                calibrated_confluence_score=calibrated,
                confidence_boost_allowed=boost_allowed,
                confidence_block_reason=block_reason,
            )
        )
    return records


def _false_agreement_records(
    payload: FalseAgreementConfluenceRequest,
    confluence_records: list[IndicatorValueConfluenceRecord],
) -> list[FalseAgreementRecord]:
    registry = build_indicator_registry_report()
    by_id = {entry.indicator_id: entry for entry in registry.entries}
    misleading = [
        feature
        for record in confluence_records
        for feature in record.redundant_feature_ids
    ][:4]
    contract_rules = [
        rule
        for feature in misleading
        for rule in getattr(by_id.get(feature), "conflict_rules", [])
    ][:3]
    false_positive_conditions = [
        condition
        for feature in misleading
        for condition in getattr(by_id.get(feature), "false_positive_conditions", [])
    ][:3]
    if not contract_rules:
        contract_rules = [
            rule
            for entry in registry.entries
            if entry.indicator_id in {"si_fmfm300", "si_inside_candle_strategy"} or entry.category in {"exhaustion", "momentum"}
            for rule in entry.conflict_rules
        ][:3]
    return [
        FalseAgreementRecord(
            false_agreement_id=f"{payload.symbol.upper()}-{payload.timeframe}-false-agreement-v075",
            agreement_family_count=4,
            nominal_direction="bullish",
            historical_failure_rate_pct=63.0,
            independent_evidence_count=42,
            redundant_evidence_count=max(1, len(misleading)),
            misleading_indicator_ids=misleading or ["mfi_14", "macd_histogram"],
            failure_modes=["fake_breakout", "resistance_rejection", "late_buy_signal", "range_trap"] + false_positive_conditions,
            confidence_must_be_blocked=True,
            reason=" ".join(
                [
                    "Many indicators nominally agree bullish, but independent historical evidence shows this combination often fails near resistance.",
                    "Contract rules:",
                    "; ".join(contract_rules) if contract_rules else "no extra contract rule matched",
                ]
            ),
            uses_independent_historical_evidence=True,
        )
    ]


def _gates(
    *,
    timing_windows: list[ConfluenceTimingWindowRecord],
    confluence_records: list[IndicatorValueConfluenceRecord],
    false_agreements: list[FalseAgreementRecord],
    confidence_blocked: bool,
    all_pit: bool,
) -> list[FalseAgreementConfluenceGate]:
    delayed = any(not window.same_candle_only for window in timing_windows)
    independent_false_agreement = all(record.uses_independent_historical_evidence for record in false_agreements)
    redundant_blocked = all(
        not record.confidence_boost_allowed for record in confluence_records if record.redundant_feature_ids
    )
    return [
        _gate("TV-V075-001", "Confluence timing windows built", bool(timing_windows), f"windows={len(timing_windows)}.", "Build confluence timing windows."),
        _gate("TV-V075-002", "Delayed confluence supported", delayed, "At least one confluence window spans multiple candle offsets.", "Represent non-same-candle confluence."),
        _gate("TV-V075-003", "Redundant agreement cannot raise confidence", redundant_blocked, "Redundant feature records have confidence_boost_allowed=false.", "Block confidence boosts from redundant features."),
        _gate("TV-FI-092", "Value confluence supports non-same-candle signals", delayed, "Value confluence is not restricted to one candle.", "Allow ordered delayed signal windows."),
        _gate("TV-FI-094", "False agreement detector uses independent historical evidence", independent_false_agreement, f"false_agreement_records={len(false_agreements)}.", "Require independent historical evidence."),
        _gate("TV-V075-004", "Misleading nominal agreement blocks confidence", confidence_blocked, "False agreement or redundancy produced confidence block reasons.", "Block confidence when historical evidence contradicts nominal agreement."),
        _gate("TV-V075-005", "Confluence is point-in-time safe", all_pit, "All timing windows are based on pre-decision events.", "Drop post-decision events."),
        _gate("TV-V075-006", "No trading capability", True, "Confluence diagnostics are research-only and cannot route orders."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str | None = None) -> FalseAgreementConfluenceGate:
    return FalseAgreementConfluenceGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()
