from __future__ import annotations

import random

from ..models import (
    CandleNeighborEffectSpec,
    HarmonicGeometrySpec,
    PatternActivityRecord,
    PatternTaxonomyEntry,
    PatternTaxonomyGate,
    PatternTaxonomyReport,
    PatternTaxonomyRequest,
    TrendlineRespectEvidence,
    now_iso,
)


TAXONOMY_VERSION = "pattern-market-structure-taxonomy.v0.70"
LIFECYCLE_STATES = ["forming", "confirmed", "failed", "expired", "developing_not_decision_safe"]
ANATOMY_FEATURES = [
    "body_size",
    "body_pct_of_range",
    "upper_wick_size",
    "lower_wick_size",
    "upper_wick_pct_of_range",
    "lower_wick_pct_of_range",
    "upper_wick_to_body_ratio",
    "lower_wick_to_body_ratio",
    "total_wick_to_body_ratio",
    "close_location_value",
    "open_location_value",
    "no_upper_wick",
    "no_lower_wick",
    "no_wick_full_body",
    "large_body_no_wick",
    "small_body_large_wick",
    "same_direction_body_sequence",
    "opposite_direction_body_sequence",
    "body_expansion_sequence",
    "body_compression_sequence",
    "wick_expansion_sequence",
    "wick_compression_sequence",
    "wick_cluster_direction",
    "nearby_candle_confirmation",
    "nearby_candle_rejection",
    "nearby_candle_absorption",
    "nearby_candle_exhaustion",
]


def build_pattern_taxonomy_report(request: PatternTaxonomyRequest) -> PatternTaxonomyReport:
    symbol = request.symbol.upper()
    entries = _entries()
    activity_records = _activity_records(request, entries) if request.include_activity_records else []
    harmonic = HarmonicGeometrySpec(
        pattern_names=["Gartley", "Bat", "Butterfly", "Crab", "Deep Crab", "Cypher", "AB=CD", "Three Drives"],
        anchor_fields=["x_time", "a_time", "b_time", "c_time", "d_time", "x_price", "a_price", "b_price", "c_price", "d_price"],
        ratio_measurements=["XA_AB", "AB_BC", "BC_CD", "XA_AD", "extension_confluence"],
        ratio_tolerance_pct=5.0,
        completion_zone_required=True,
        invalidation_zone_required=True,
        detector_version=TAXONOMY_VERSION,
    )
    trendline = TrendlineRespectEvidence(
        touch_count=4,
        normalized_touch_error=0.018,
        close_through_count=1,
        slope_stability=0.86,
        recency_score=0.74,
        volume_response=0.63,
        post_touch_excursion_atr=0.82,
        trendline_respect_score=0.71,
        objective_evidence_required=True,
    )
    candle_neighbor = CandleNeighborEffectSpec(
        anatomy_features=ANATOMY_FEATURES,
        local_windows=[
            "previous_1_candle",
            "previous_2_candles",
            "previous_3_candles",
            "previous_5_candles",
            "next_outcome_window_for_historical_labels_only",
        ],
        no_wick_detection_required=True,
        neighbor_confirmation_required=True,
        historical_next_window_labels_only=True,
    )
    families = {entry.family for entry in entries}
    lifecycle_ok = all(entry.lifecycle_states for entry in entries)
    decorative_blocked = all(entry.decorative_only_blocked for entry in entries)
    activity_required = all(entry.activity_record_required for entry in entries)
    gates = _gates(families, lifecycle_ok, decorative_blocked, activity_required, harmonic, trendline, candle_neighbor)
    return PatternTaxonomyReport(
        taxonomy_version=TAXONOMY_VERSION,
        generated_at=now_iso(),
        symbol=symbol,
        timeframe=request.timeframe,
        entry_count=len(entries),
        required_family_count=len(families),
        entries=entries,
        harmonic_geometry=harmonic,
        trendline_respect_evidence=trendline,
        candle_neighbor_effect=candle_neighbor,
        activity_records=activity_records,
        all_chart_structures_require_activity_records=activity_required,
        all_entries_have_lifecycle_contracts=lifecycle_ok,
        decorative_patterns_blocked=decorative_blocked,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.70 is a taxonomy and contract registry, not a live detector promotion.",
            "Chart-visible structures must produce point-in-time activity records before they influence similarity.",
            "Trendline respect requires objective evidence; visual line drawing alone is not accepted.",
        ],
    )


def _entries() -> list[PatternTaxonomyEntry]:
    return [
        _entry(
            "candle_anatomy_patterns",
            "Candle Anatomy and Multi-Candle Patterns",
            "candle",
            "body_wick_neighbor_effect",
            [
                "inside bar",
                "outside bar",
                "engulfing",
                "pin bar",
                "doji/indecision",
                "marubozu/trend candle",
                "morning/evening reversal sequence",
                "three-bar continuation/reversal",
                "wick cluster",
                "failed follow-through",
                "absorption-like candle",
                "exhaustion-like candle",
                "abnormal print",
            ],
            ["open", "high", "low", "close", "volume", "neighbor_window"],
            ANATOMY_FEATURES,
        ),
        _entry(
            "price_swing_structure",
            "Price and Swing Structure",
            "swing",
            "market_structure_path",
            [
                "HH/HL uptrend",
                "LH/LL downtrend",
                "range/balance",
                "compression",
                "expansion",
                "break of structure",
                "change of character",
                "failed break",
                "liquidity sweep",
                "retest",
                "spring/upthrust",
                "double/triple top or bottom",
                "head and shoulders/inverse",
                "rounded base/top",
                "flag/pennant/wedge/triangle/channel",
            ],
            ["swing_highs", "swing_lows", "close", "atr"],
            ["structure_label", "swing_points", "break_level", "invalidation_zone"],
        ),
        _entry(
            "harmonic_geometry",
            "Harmonic and Geometric Patterns",
            "harmonic",
            "fibonacci_geometry",
            ["Gartley", "Bat", "Butterfly", "Crab", "Deep Crab", "Cypher", "AB=CD", "Three Drives", "zigzag swing geometry"],
            ["zigzag_points", "fib_ratios", "high", "low", "close"],
            ["anchor_timestamps", "anchor_prices", "ratio_measurements", "completion_zone", "invalidation_zone"],
        ),
        _entry(
            "level_interaction",
            "Level Interaction",
            "level",
            "vwap_cpr_pivot_trendline_gap",
            [
                "VWAP hold/reclaim/rejection/cross",
                "anchored VWAP interaction",
                "CPR and pivot interaction",
                "PDH/PDL and PWH/PWL interaction",
                "opening range/ORB interaction",
                "volume-profile POC/VAH/VAL interaction",
                "supply/demand zone interaction",
                "support/resistance respect",
                "trendline respect/break/false break/retest",
                "gap edge and gap-fill interaction",
                "circuit-limit proximity",
            ],
            ["levels", "close", "volume", "atr", "touch_history"],
            ["level_state", "distance_to_level", "respect_score", "false_break_risk"],
        ),
        _entry(
            "flow_participation",
            "Flow and Participation",
            "flow",
            "volume_money_flow_order_flow_proxy",
            [
                "volume expansion/contraction",
                "relative volume",
                "MFI/CMF accumulation-distribution context",
                "effort versus result",
                "absorption proxy",
                "exhaustion proxy",
                "delta/volume-profile proxy",
                "liquidity vacuum",
                "opening auction imbalance proxy",
                "closing drive",
            ],
            ["volume", "body_pct", "range", "mfi", "cmf", "vwap"],
            ["activity_strength", "absorption_score", "exhaustion_score", "participation_context"],
        ),
        _entry(
            "universal_indicator_activity",
            "Universal Indicator Activity Discovery",
            "indicator_activity",
            "indicator_detector_algorithm_activity",
            [
                "trendline detectors",
                "curve pattern detectors",
                "harmonic pattern detectors",
                "Fibonacci retracement/extension detectors",
                "Elliott wave detectors",
                "candle pattern detectors",
                "inside/outside candle detectors",
                "VWAP and anchored VWAP engines",
                "Bollinger/Keltner/band engines",
                "CPR, pivot, ORB, and volume-profile engines",
                "support/resistance detectors",
                "market-structure engines",
                "liquidity/sweep/order-block/FVG engines",
                "momentum oscillators",
                "volume and money-flow indicators",
                "ML/probability-grid indicators",
            ],
            ["indicator_observations", "pattern_sources", "outcome_labels"],
            ["activity_present", "activity_type", "activity_quality", "outcome_distribution_after_activity"],
        ),
        _entry(
            "kronos_forecast_path_features",
            "Kronos Forecast Path Features",
            "forecast",
            "forecast_path_activity",
            ["trend path", "range path", "fakeout path", "target-before-stop path", "stop-before-target path"],
            ["forecasted_ohlcv_path", "shared_snapshot_hash", "barrier_projection"],
            ["path_shape", "barrier_sequence", "forecast_conflict_state", "forecast_expiry"],
        ),
    ]


def _entry(
    pattern_id: str,
    display_name: str,
    family: str,
    subfamily: str,
    pattern_names: list[str],
    required_inputs: list[str],
    output_fields: list[str],
) -> PatternTaxonomyEntry:
    return PatternTaxonomyEntry(
        pattern_id=pattern_id,
        display_name=display_name,
        family=family,  # type: ignore[arg-type]
        subfamily=subfamily,
        pattern_names=pattern_names,
        required_inputs=required_inputs,
        output_fields=output_fields,
        lifecycle_states=LIFECYCLE_STATES,  # type: ignore[arg-type]
        point_in_time_safe=True,
        detector_version=TAXONOMY_VERSION,
        lineage_source=f"trade_vision.behavior.pattern_taxonomy.{pattern_id}",
        decorative_only_blocked=True,
        contributes_to_similarity=True,
        activity_record_required=True,
        objective_evidence_fields=[
            "activity_present",
            "activity_strength",
            "activity_quality",
            "activity_confirmation_state",
            "activity_invalidation_state",
            "outcome_distribution_after_activity",
        ],
        notes=["Detector output must be point-in-time and must not use future confirmation before decision time."],
    )


def _activity_records(request: PatternTaxonomyRequest, entries: list[PatternTaxonomyEntry]) -> list[PatternActivityRecord]:
    rng = random.Random(f"{TAXONOMY_VERSION}:{request.symbol}:{request.timeframe}:{request.seed}")
    base_time_ns = 1_714_698_900_000_000_000
    records: list[PatternActivityRecord] = []
    for index, entry in enumerate(entries):
        direction = ["long", "short", "neutral", "mixed"][index % 4]
        strength = 0.35 + rng.random() * 0.45
        start = base_time_ns + index * 300_000_000_000
        duration = 2 + index
        records.append(
            PatternActivityRecord(
                activity_id=f"activity-{entry.pattern_id}",
                source_id=entry.pattern_id,
                activity_present=True,
                activity_type=entry.pattern_names[0],
                activity_direction=direction,  # type: ignore[arg-type]
                activity_strength=round(strength, 4),
                activity_start_time=start,
                activity_end_time=start + duration * 60_000_000_000,
                activity_duration_bars=duration,
                activity_price_zone=f"{round(100 + index * 1.5, 2)}-{round(101 + index * 1.5, 2)}",
                activity_timeframe=request.timeframe,
                activity_parameters={"detector_version": TAXONOMY_VERSION, "pattern_count": len(entry.pattern_names)},
                activity_quality=round(min(0.95, strength + 0.12), 4),
                activity_confirmation_state="confirmed",
                activity_invalidation_state=None,
                bars_before_outcome=5 + index,
                outcome_distribution_after_activity={
                    "continuation": round(0.42 + rng.random() * 0.18, 4),
                    "reversal": round(0.20 + rng.random() * 0.15, 4),
                    "range": round(0.18 + rng.random() * 0.12, 4),
                    "fakeout": round(0.08 + rng.random() * 0.10, 4),
                },
                reciprocal_signal_candidate=entry.family in {"indicator_activity", "flow"} and index % 2 == 0,
                point_in_time_safe=True,
            )
        )
    return records


def _gates(
    families: set[str],
    lifecycle_ok: bool,
    decorative_blocked: bool,
    activity_required: bool,
    harmonic: HarmonicGeometrySpec,
    trendline: TrendlineRespectEvidence,
    candle_neighbor: CandleNeighborEffectSpec,
) -> list[PatternTaxonomyGate]:
    required = {"candle", "swing", "harmonic", "level", "flow", "indicator_activity", "forecast"}
    return [
        _gate("TV-V070-001", "Required pattern families present", required.issubset(families), f"families={sorted(families)}", "Register every required pattern family."),
        _gate("TV-V070-002", "Lifecycle states declared", lifecycle_ok, f"states={LIFECYCLE_STATES}", "Every detector must declare lifecycle states."),
        _gate("TV-V070-003", "Harmonic geometry fields present", harmonic.completion_zone_required and harmonic.invalidation_zone_required, "completion and invalidation zones required", "Require anchors, ratios, completion, and invalidation zones."),
        _gate("TV-V070-004", "Trendline respect is objective", trendline.objective_evidence_required and trendline.touch_count > 0, f"touch_count={trendline.touch_count}, score={trendline.trendline_respect_score}", "Require touch count, error, close-through, slope, recency, volume, and excursion evidence."),
        _gate("TV-V070-005", "Candle neighbor effect memory declared", candle_neighbor.no_wick_detection_required and candle_neighbor.neighbor_confirmation_required, f"anatomy_features={len(candle_neighbor.anatomy_features)}", "Include wick/body/no-wick and neighbor-window features."),
        _gate("TV-V070-006", "Decorative-only patterns blocked", decorative_blocked and activity_required, "All chart structures require activity records.", "Block chart-only decorative structures from similarity and decisions."),
        _gate("TV-V070-007", "Research-only safety", True, "trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true", "Keep taxonomy read-only."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str) -> PatternTaxonomyGate:
    return PatternTaxonomyGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )
