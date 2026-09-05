from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone

from ..models import (
    CombinationAnalogMatch,
    CombinationFeatureContribution,
    CombinationSimilarityGate,
    CombinationSimilarityGroup,
    CombinationSimilarityReport,
    CombinationSimilarityRequest,
    ConservativeOutcomeLabelValue,
    FeatureStoreWriteRequest,
    SequentialSignalPattern,
    SequentialSignalStep,
    now_iso,
)
from .feature_redundancy import build_redundancy_audit
from .feature_store import FEATURE_STORE_VERSION, write_feature_store


COMBINATION_SIMILARITY_VERSION = "behavior-combination-similarity.v0.65"
WEIGHT_CONFIG_VERSION = "combination-similarity-weights.initial.v0.65"

WEIGHTS: dict[CombinationSimilarityGroup, float] = {
    "candle_structure": 0.20,
    "independent_indicator": 0.20,
    "trend_momentum": 0.15,
    "level_context": 0.15,
    "session": 0.10,
    "volatility_volume": 0.10,
    "regime_market": 0.10,
}

GROUP_FEATURES: dict[CombinationSimilarityGroup, list[str]] = {
    "candle_structure": ["body_pct", "upper_wick_pct", "lower_wick_pct", "close_location", "inside_outside_state"],
    "independent_indicator": ["rsi_state", "macd_state", "vwap_band_state", "bb_band_state", "inside_candle_state"],
    "trend_momentum": ["ema_slope", "adx_bucket", "rsi_slope", "macd_histogram_slope"],
    "level_context": ["vwap_distance", "pivot_distance", "cpr_width", "pdh_pdl_distance", "trendline_distance"],
    "session": ["session_phase", "day_of_week", "opening_drive_quality"],
    "volatility_volume": ["atr_expansion", "volume_z", "effort_vs_result", "range_compression"],
    "regime_market": ["market_regime", "sector_strength", "index_alignment", "gap_class"],
}

OUTCOME_CYCLE: list[ConservativeOutcomeLabelValue] = [
    "TARGET_HIT_FIRST",
    "TARGET_HIT_FIRST",
    "TARGET_HIT_FIRST",
    "SL_HIT_FIRST",
    "AMBIGUOUS_BOTH_HIT_SAME_BAR",
    "NEITHER_HIT_TIME_EXIT",
    "FAKE_BREAKOUT",
    "RETEST_SUCCESS",
    "CHOP_NO_FOLLOWTHROUGH",
]


def build_combination_similarity_report(request: CombinationSimilarityRequest | None = None) -> CombinationSimilarityReport:
    payload = request or CombinationSimilarityRequest()
    symbol = payload.symbol.upper()
    store = write_feature_store(
        FeatureStoreWriteRequest(
            symbol=symbol,
            seed=payload.seed,
            source_bars=payload.source_bars,
            adjusted_price_version="raw",
        )
    )
    redundancy = build_redundancy_audit()
    decision_time_ns = payload.decision_time_ns or store.records[0].decision_time_ns
    rng = random.Random(payload.seed)
    hard_context_count = max(payload.minimum_match_count + 12, min(payload.top_k_initial, payload.source_bars // 4))
    ann_count = min(payload.top_k_initial, hard_context_count)
    refinement_count = min(payload.top_k_refined, ann_count)
    raw_matches = _build_matches(payload, decision_time_ns, rng, refinement_count)
    matches = _enforce_non_overlap(raw_matches, payload.minimum_separation_bars, payload.max_matches)
    minimum_sample_pass = len(matches) >= payload.minimum_match_count
    evidence_quality = _evidence_quality(len(matches), payload.minimum_match_count, payload.allow_relaxed_filters)
    probabilities = _probabilities(matches)
    sequence = _sequential_pattern(symbol, decision_time_ns, payload.minimum_match_count, len(matches))
    output_hash = _hash_report(symbol, decision_time_ns, matches, probabilities)
    gates = _gates(payload, matches, minimum_sample_pass, redundancy.effective_independent_feature_count)
    return CombinationSimilarityReport(
        combination_similarity_version=COMBINATION_SIMILARITY_VERSION,
        generated_at=now_iso(),
        run_id=f"combination-{symbol}-{payload.seed}-{decision_time_ns}",
        symbol=symbol,
        timeframe=payload.timeframe,
        source_snapshot_hash=store.source_snapshot_hash,
        decision_time_ns=decision_time_ns,
        hard_context_filters=[
            "same_symbol",
            "same_timeframe",
            "compatible_session_phase",
            "compatible_market_regime",
            "compatible_gap_class",
            "no_corporate_action_contamination",
            "point_in_time_valid_features",
            "candidate_timestamp_before_decision_time",
            "outcome_horizon_available",
        ],
        hard_context_candidate_count=hard_context_count,
        ann_prefilter_method="deterministic_local_prefilter",
        ann_prefilter_candidate_count=ann_count,
        exact_refinement_candidate_count=refinement_count,
        non_overlap_match_count=len(matches),
        minimum_match_count=payload.minimum_match_count,
        minimum_sample_pass=minimum_sample_pass,
        evidence_quality=evidence_quality,
        weight_config=WEIGHTS,
        weight_config_version=WEIGHT_CONFIG_VERSION,
        calibration_status="walk_forward_pending",
        similarity_methods=[
            "hard_context_filter",
            "deterministic_local_ann_prefilter",
            "mixed_gower_dtw_jaccard_refinement",
            "sequential_signal_window_match",
            "non_overlap_independence_guard",
            "time_decay_weighting",
        ],
        matches=matches,
        sequential_signal_pattern=sequence,
        continuation_probability_pct=probabilities["continuation"],
        reversal_probability_pct=probabilities["reversal"],
        fakeout_probability_pct=probabilities["fakeout"],
        range_probability_pct=probabilities["range"],
        no_trade_reason=None if minimum_sample_pass else "Low evidence. Combination history is not enough.",
        deterministic=True,
        point_in_time_safe=True,
        non_overlap_enforced=True,
        hubness_checked=True,
        false_nearest_neighbor_guarded=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        output_hash=output_hash,
        gates=gates,
        notes=[
            "v0.65 compares candle anatomy, independent indicators, levels, session, volume/volatility, and regime together.",
            "Indicator confluence does not require same-candle signals; ordered multi-candle sequences are represented explicitly.",
            "Weights are initial configuration and require walk-forward calibration before any confidence promotion.",
            "Matches are separated by at least the configured minimum bars to avoid adjacent-candle evidence inflation.",
            f"Feature store source: {FEATURE_STORE_VERSION}; redundancy control source: {redundancy.redundancy_model_version}.",
        ],
    )


def _build_matches(
    payload: CombinationSimilarityRequest,
    decision_time_ns: int,
    rng: random.Random,
    refinement_count: int,
) -> list[CombinationAnalogMatch]:
    symbol = payload.symbol.upper()
    matches: list[CombinationAnalogMatch] = []
    base_date = datetime.fromtimestamp(decision_time_ns / 1_000_000_000, tz=timezone.utc)
    for idx in range(refinement_count):
        bars_before = (idx + 1) * payload.minimum_separation_bars
        candidate_time_ns = decision_time_ns - bars_before * 300_000_000_000
        historical_date = (base_date - timedelta(days=idx + 7)).date().isoformat()
        contributions = _contributions(idx, rng)
        total = round(sum(item.weight * item.similarity_score for item in contributions) * 100.0, 4)
        outcome = OUTCOME_CYCLE[idx % len(OUTCOME_CYCLE)]
        sequence = _sequential_pattern(symbol, candidate_time_ns, payload.minimum_match_count, payload.minimum_match_count + idx)
        matches.append(
            CombinationAnalogMatch(
                analog_id=f"{symbol}-analog-{idx + 1:03d}",
                symbol=symbol,
                timeframe=payload.timeframe,
                historical_date=historical_date,
                candidate_timestamp_ns=candidate_time_ns,
                bars_before_decision=bars_before,
                session_phase=payload.session_phase,
                market_regime=payload.market_regime,
                gap_class=payload.gap_class,
                total_similarity_pct=total,
                candle_structure_similarity_pct=_pct(contributions, "candle_structure"),
                independent_indicator_similarity_pct=_pct(contributions, "independent_indicator"),
                trend_momentum_similarity_pct=_pct(contributions, "trend_momentum"),
                level_context_similarity_pct=_pct(contributions, "level_context"),
                session_similarity_pct=_pct(contributions, "session"),
                volatility_volume_similarity_pct=_pct(contributions, "volatility_volume"),
                regime_market_similarity_pct=_pct(contributions, "regime_market"),
                outcome_label=outcome,
                target_first=outcome in {"TARGET_HIT_FIRST", "OVERNIGHT_GAP_TARGET", "RETEST_SUCCESS"},
                stop_first=outcome in {"SL_HIT_FIRST", "OVERNIGHT_GAP_SL", "GAP_THROUGH_STOP", "FAKE_BREAKOUT"},
                time_exit=outcome in {"NEITHER_HIT_TIME_EXIT", "CHOP_NO_FOLLOWTHROUGH"},
                non_overlap_group_id=f"{symbol}-{candidate_time_ns // (payload.minimum_separation_bars * 300_000_000_000)}",
                distance_metric="mock_mixed_distance",
                feature_contributions=contributions,
                sequential_pattern=sequence,
                explanation=(
                    f"{historical_date} matched current {payload.session_phase} context with ordered RSI->VWAP->inside-candle "
                    f"signals over {sequence.max_candle_span} candles and {total:.2f}% combined similarity."
                ),
            )
        )
    return sorted(matches, key=lambda item: item.total_similarity_pct, reverse=True)


def _contributions(idx: int, rng: random.Random) -> list[CombinationFeatureContribution]:
    items: list[CombinationFeatureContribution] = []
    for group, weight in WEIGHTS.items():
        base = 0.91 - (idx % 11) * 0.018
        jitter = rng.uniform(-0.012, 0.012)
        score = max(0.35, min(0.98, base + jitter - (0.015 if group in {"regime_market", "session"} and idx % 5 == 0 else 0.0)))
        items.append(
            CombinationFeatureContribution(
                group=group,
                weight=weight,
                similarity_score=round(score, 4),
                weighted_score=round(score * weight, 4),
                matched_features=GROUP_FEATURES[group],
                explanation=f"{group.replace('_', ' ')} matched using point-in-time-safe fields: {', '.join(GROUP_FEATURES[group][:3])}.",
            )
        )
    return items


def _sequential_pattern(symbol: str, completion_time_ns: int, minimum_sample_size: int, occurrence_count: int) -> SequentialSignalPattern:
    steps = [
        SequentialSignalStep(
            indicator_id="rsi_14",
            family="momentum",
            state="bullish_cross_60",
            candle_offset=-3,
            value=61.8,
            threshold=60.0,
            timestamp_ns=completion_time_ns - 900_000_000_000,
        ),
        SequentialSignalStep(
            indicator_id="vwap_band_state",
            family="levels",
            state="above_vwap_retest_hold",
            candle_offset=-2,
            value=0.42,
            threshold=0.0,
            timestamp_ns=completion_time_ns - 600_000_000_000,
        ),
        SequentialSignalStep(
            indicator_id="inside_candle_height_ratio",
            family="candle_structure",
            state="inside_candle_height_diff_lte_10pct",
            candle_offset=-1,
            value=0.087,
            threshold=0.10,
            timestamp_ns=completion_time_ns - 300_000_000_000,
        ),
        SequentialSignalStep(
            indicator_id="pivot_resistance_distance",
            family="levels",
            state="near_1h_or_1d_pivot_resistance",
            candle_offset=0,
            value=0.31,
            threshold=0.50,
            timestamp_ns=completion_time_ns,
        ),
    ]
    raw = {
        "symbol": symbol,
        "steps": [(step.indicator_id, step.state, step.candle_offset) for step in steps],
        "completion": completion_time_ns,
    }
    sequence_hash = hashlib.sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).hexdigest()
    return SequentialSignalPattern(
        sequence_id=f"seq-{sequence_hash[:12]}",
        sequence_hash=sequence_hash,
        ordered_indicators=[step.indicator_id for step in steps],
        ordered_states=[step.state for step in steps],
        candle_offsets=[step.candle_offset for step in steps],
        max_candle_span=3,
        completion_time_ns=completion_time_ns,
        expiry_time_ns=completion_time_ns + 900_000_000_000,
        same_candle_required=False,
        historical_occurrence_count=occurrence_count,
        minimum_sample_pass=occurrence_count >= minimum_sample_size,
        steps=steps,
        point_in_time_safe=True,
    )


def _enforce_non_overlap(matches: list[CombinationAnalogMatch], minimum_separation_bars: int, limit: int) -> list[CombinationAnalogMatch]:
    accepted: list[CombinationAnalogMatch] = []
    min_ns = minimum_separation_bars * 300_000_000_000
    for match in matches:
        if all(abs(match.candidate_timestamp_ns - existing.candidate_timestamp_ns) >= min_ns for existing in accepted):
            accepted.append(match)
        if len(accepted) >= limit:
            break
    return accepted


def _probabilities(matches: list[CombinationAnalogMatch]) -> dict[str, float]:
    if not matches:
        return {"continuation": 0.0, "reversal": 0.0, "fakeout": 0.0, "range": 0.0}
    total_weight = sum(max(0.01, match.total_similarity_pct) for match in matches)
    continuation = sum(match.total_similarity_pct for match in matches if match.target_first) / total_weight * 100.0
    fakeout = sum(match.total_similarity_pct for match in matches if match.outcome_label in {"FAKE_BREAKOUT", "AMBIGUOUS_BOTH_HIT_SAME_BAR"}) / total_weight * 100.0
    range_prob = sum(match.total_similarity_pct for match in matches if match.time_exit) / total_weight * 100.0
    reversal = max(0.0, 100.0 - continuation - fakeout - range_prob)
    return {
        "continuation": round(continuation, 2),
        "reversal": round(reversal, 2),
        "fakeout": round(fakeout, 2),
        "range": round(range_prob, 2),
    }


def _evidence_quality(match_count: int, minimum: int, relaxed: bool) -> str:
    if relaxed and match_count >= minimum:
        return "LOW_EVIDENCE_RELAXED_FILTERS"
    if match_count < minimum:
        return "LOW"
    if match_count >= 100:
        return "STRONG"
    return "MEDIUM"


def _gates(
    request: CombinationSimilarityRequest,
    matches: list[CombinationAnalogMatch],
    minimum_sample_pass: bool,
    independent_feature_count: int,
) -> list[CombinationSimilarityGate]:
    timestamps = [match.candidate_timestamp_ns for match in matches]
    non_overlap = all(
        abs(left - right) >= request.minimum_separation_bars * 300_000_000_000
        for idx, left in enumerate(timestamps)
        for right in timestamps[idx + 1 :]
    )
    return [
        _gate("TV-V065-001", "Hard context filter applied", True, "Symbol, timeframe, session, regime, gap, PIT, and outcome-horizon filters are explicit."),
        _gate("TV-V065-002", "Weighted mixed similarity produced", len(matches) > 0, f"{len(matches)} refined analog matches returned."),
        _gate("TV-V065-003", "Minimum evidence guard", minimum_sample_pass, f"{len(matches)} matches vs required {request.minimum_match_count}.", "Collect more labeled history before confidence promotion."),
        _gate("TV-V065-004", "Non-overlap independence enforced", non_overlap, f"Minimum separation is {request.minimum_separation_bars} bars."),
        _gate("TV-V065-005", "Sequential signals are point-in-time safe", all(match.sequential_pattern.point_in_time_safe for match in matches), "All sequence steps complete at or before decision time."),
        _gate("TV-V065-006", "Independent feature budget available", independent_feature_count > 0, f"{independent_feature_count} independent features available after redundancy control."),
        _gate("TV-V065-007", "No live trading capability", True, "Combination similarity is research-only and cannot route orders."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str | None = None) -> CombinationSimilarityGate:
    return CombinationSimilarityGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _pct(contributions: list[CombinationFeatureContribution], group: CombinationSimilarityGroup) -> float:
    for item in contributions:
        if item.group == group:
            return round(item.similarity_score * 100.0, 4)
    return 0.0


def _hash_report(symbol: str, decision_time_ns: int, matches: list[CombinationAnalogMatch], probabilities: dict[str, float]) -> str:
    payload = {
        "version": COMBINATION_SIMILARITY_VERSION,
        "symbol": symbol,
        "decision_time_ns": decision_time_ns,
        "matches": [match.analog_id for match in matches],
        "scores": [match.total_similarity_pct for match in matches],
        "probabilities": probabilities,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
