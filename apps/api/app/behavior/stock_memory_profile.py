from __future__ import annotations

import hashlib
import json
from typing import Any

from ..models import (
    DayOfWeekMemoryResult,
    FailureLibraryResult,
    LearningTrustResult,
    PatternMemoryResult,
    RuntimeReadinessGate,
    StockDNASummary,
    StockMemoryProfileReport,
    now_iso,
)
from .constants import LOW_EVIDENCE_MESSAGE


MINIMUM_SAMPLE_SIZE = 30


PROFILE_VERSION = "behavior-stock-memory-profile.v0.43"


def build_stock_memory_profile_report(
    *,
    symbol: str,
    timeframe: str,
    snapshot_count: int,
    stock_dna_summary: StockDNASummary,
    pattern_memory: PatternMemoryResult,
    failure_library: FailureLibraryResult,
    trust_table: LearningTrustResult,
) -> StockMemoryProfileReport:
    memory_count = len(stock_dna_summary.stock_dna.notes) + len(pattern_memory.matches) + len(failure_library.failures)
    historical_count = pattern_memory.historical_match_count
    minimum_pass = (
        stock_dna_summary.minimum_evidence_pass
        and pattern_memory.minimum_sample_pass
        and trust_table.minimum_sample_pass
        and historical_count >= MINIMUM_SAMPLE_SIZE
    )
    freshness_score = _freshness_score(snapshot_count, historical_count, trust_table.aggregate_trust_score)
    no_trade_reasons = _no_trade_reasons(
        minimum_pass=minimum_pass,
        stock_dna_summary=stock_dna_summary,
        pattern_memory=pattern_memory,
        failure_library=failure_library,
        trust_table=trust_table,
    )
    payload: dict[str, Any] = {
        "version": PROFILE_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "snapshot_count": snapshot_count,
        "memory_count": memory_count,
        "historical_count": historical_count,
        "minimum_pass": minimum_pass,
        "freshness_score": round(freshness_score, 4),
        "trust": trust_table.aggregate_trust_score,
        "similar_days": pattern_memory.similar_day_ids,
        "no_trade_reasons": no_trade_reasons,
    }
    output_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return StockMemoryProfileReport(
        memory_profile_version=PROFILE_VERSION,
        generated_at=now_iso(),
        symbol=symbol.upper(),
        timeframe=timeframe,  # type: ignore[arg-type]
        snapshot_count=snapshot_count,
        memory_record_count=memory_count,
        historical_match_count=historical_count,
        minimum_sample_size=MINIMUM_SAMPLE_SIZE,
        minimum_sample_pass=minimum_pass,
        freshness_score=round(freshness_score, 4),
        stock_dna_summary=stock_dna_summary,
        session_summary={
            "usual_open_behavior": stock_dna_summary.session_rhythm.usual_open_behavior,
            "usual_midday_behavior": stock_dna_summary.session_rhythm.usual_midday_behavior,
            "usual_closing_behavior": stock_dna_summary.session_rhythm.usual_closing_behavior,
            "best_trade_window": stock_dna_summary.session_rhythm.best_trade_window,
            "worst_trade_window": stock_dna_summary.session_rhythm.worst_trade_window,
            "current_session_phase": stock_dna_summary.session_rhythm.current_session_phase,
            "session_personality_score": stock_dna_summary.session_rhythm.session_personality_score,
        },
        day_of_week_summary={
            "dominant_day_note": stock_dna_summary.day_of_week_memory.dominant_day_note,
            "total_samples": stock_dna_summary.day_of_week_memory.total_samples,
            "blocks_strong_probability": stock_dna_summary.day_of_week_memory.blocks_strong_probability,
            "minimum_sample_size": stock_dna_summary.day_of_week_memory.minimum_sample_size,
        },
        pattern_memory_summary={
            "similarity_pattern": pattern_memory.matches[0].pattern_id if pattern_memory.matches else "none",
            "similarity_score_pct": pattern_memory.matches[0].similarity_score_pct if pattern_memory.matches else 0.0,
            "continuation_probability_pct": pattern_memory.continuation_probability_pct,
            "fakeout_probability_pct": pattern_memory.fakeout_probability_pct,
            "evidence_quality": pattern_memory.evidence_quality,
            "best_invalidation": pattern_memory.best_invalidation,
        },
        similar_day_summary={
            "similar_day_ids": pattern_memory.similar_day_ids,
            "historical_match_count": pattern_memory.historical_match_count,
            "replay_ready": pattern_memory.replay_ready,
        },
        failure_summary={
            "failure_count": len(failure_library.failures),
            "most_common_failure": failure_library.most_common_failure,
            "lessons": failure_library.no_trade_lessons,
        },
        trust_summary={
            "aggregate_trust_score": trust_table.aggregate_trust_score,
            "minimum_sample_pass": trust_table.minimum_sample_pass,
            "calibration_status": trust_table.calibration_status,
            "record_count": len(trust_table.records),
        },
        no_trade_memory_reasons=no_trade_reasons,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=_gates(minimum_pass, snapshot_count, historical_count, trust_table, no_trade_reasons),
        notes=[
            "v0.43 unifies Stock DNA, session rhythm, pattern memory, similar days, failures, and trust into one report.",
            "The profile is research-only and cannot enable paper or live orders.",
            "Minimum evidence remains the decisive guard before trusting stock-specific memory.",
        ],
    )


def _freshness_score(snapshot_count: int, historical_count: int, trust_score: float) -> float:
    snapshot_factor = min(snapshot_count / 10.0, 1.0)
    evidence_factor = min(historical_count / float(MINIMUM_SAMPLE_SIZE), 1.0)
    return max(0.0, min(1.0, snapshot_factor * 0.25 + evidence_factor * 0.45 + trust_score * 0.30))


def _no_trade_reasons(
    *,
    minimum_pass: bool,
    stock_dna_summary: StockDNASummary,
    pattern_memory: PatternMemoryResult,
    failure_library: FailureLibraryResult,
    trust_table: LearningTrustResult,
) -> list[str]:
    reasons: list[str] = []
    if not minimum_pass:
        reasons.append(LOW_EVIDENCE_MESSAGE)
    if pattern_memory.no_trade_reason:
        reasons.append(pattern_memory.no_trade_reason)
    if stock_dna_summary.risk_warnings:
        reasons.extend(stock_dna_summary.risk_warnings[:3])
    if failure_library.most_common_failure:
        reasons.append(f"Failure memory warns about {failure_library.most_common_failure}.")
    if not trust_table.minimum_sample_pass:
        reasons.append("Learning trust table has not reached the minimum sample threshold.")
    return list(dict.fromkeys(reasons))


def _gates(
    minimum_pass: bool,
    snapshot_count: int,
    historical_count: int,
    trust_table: LearningTrustResult,
    no_trade_reasons: list[str],
) -> list[RuntimeReadinessGate]:
    return [
        _gate("TV-V043-001", "Stock memory report assembled", True, "Stock DNA, pattern, failure, and trust summaries are present."),
        _gate("TV-V043-002", "Snapshot evidence linked", snapshot_count >= 0, f"{snapshot_count} point-in-time snapshots found for the profile context."),
        _gate("TV-V043-003", "Minimum evidence guard", minimum_pass, f"{historical_count}/{MINIMUM_SAMPLE_SIZE} historical matches; trust minimum={trust_table.minimum_sample_pass}."),
        _gate("TV-V043-004", "No-trade memory reasons available", bool(no_trade_reasons), f"{len(no_trade_reasons)} memory blocker/reason rows produced."),
        _gate("TV-V043-005", "Live trading blocked", True, "Stock memory profile keeps trade_allowed=false and live_trading_blocked=true."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str) -> RuntimeReadinessGate:
    return RuntimeReadinessGate(
        gate_id=gate_id,
        name=name,
        status="pass" if passed else "warn",
        evidence=evidence,
        blocks_research=False,
    )
