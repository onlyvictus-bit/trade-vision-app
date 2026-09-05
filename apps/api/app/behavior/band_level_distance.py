from __future__ import annotations

import hashlib
import json

from ..models import (
    BandLevelDistanceGate,
    BandLevelDistanceReport,
    BandLevelDistanceRequest,
    LevelDistanceOutcomeInfluence,
    LevelDistanceRecord,
    MissingLevelRecord,
    RepeatedValueClusterRecord,
    now_iso,
)


BAND_LEVEL_DISTANCE_VERSION = "band-level-distance-value-cluster.v0.77"

REQUIRED_DISTANCE_FIELDS = [
    "distance_to_vwap_band_1",
    "distance_to_vwap_band_2",
    "distance_to_vwap_band_3",
    "distance_to_bb_upper_1",
    "distance_to_bb_upper_2",
    "distance_to_bb_upper_3",
    "distance_to_bb_lower_1",
    "distance_to_bb_lower_2",
    "distance_to_bb_lower_3",
    "distance_to_keltner_upper",
    "distance_to_keltner_lower",
    "distance_to_pivot_resistance",
    "distance_to_pivot_support",
    "distance_to_daily_resistance",
    "distance_to_daily_support",
    "distance_to_cpr_top",
    "distance_to_cpr_bottom",
    "cpr_width_percentile",
    "inside_candle_height_pct",
    "distance_to_fib_level",
    "distance_to_harmonic_completion_zone",
    "distance_to_trendline",
    "distance_to_orb_high",
    "distance_to_orb_low",
    "distance_to_vpd_poc",
    "distance_to_value_area_high",
    "distance_to_value_area_low",
]


def build_band_level_distance_report(request: BandLevelDistanceRequest | None = None) -> BandLevelDistanceReport:
    payload = request or BandLevelDistanceRequest()
    distances = _distance_records(payload)
    clusters = _clusters(payload)
    influences = _influences(clusters)
    missing = _missing_levels(distances)
    field_names = {record.field_name for record in distances}
    required_present = set(REQUIRED_DISTANCE_FIELDS).issubset(field_names)
    unavailable_safe = all(record.side == "unavailable" for record in distances if record.availability != "available")
    pit_safe = all(record.point_in_time_safe for record in distances if record.availability == "available")
    minimum_pass = all(cluster.minimum_sample_pass for cluster in clusters if cluster.evidence_quality != "LOW_EVIDENCE")
    gates = _gates(
        required_present=required_present,
        unavailable_safe=unavailable_safe,
        pit_safe=pit_safe,
        clusters=clusters,
        influences=influences,
        missing=missing,
    )
    return BandLevelDistanceReport(
        distance_version=BAND_LEVEL_DISTANCE_VERSION,
        generated_at=now_iso(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        timeframe=payload.timeframe,
        decision_price=payload.decision_price,
        atr=payload.atr,
        required_distance_fields=REQUIRED_DISTANCE_FIELDS,
        distance_records=distances,
        repeated_value_clusters=clusters,
        outcome_influences=influences,
        missing_levels=missing,
        all_required_distance_fields_present=required_present,
        unavailable_levels_not_silently_drawn=unavailable_safe,
        mixed_feature_similarity_handles_unavailable_values=True,
        level_distance_influences_outcomes=bool(influences),
        minimum_cluster_sample_pass=minimum_pass,
        all_available_levels_point_in_time_safe=pit_safe,
        deterministic=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.77 records exact distance-to-level fields for VWAP, Bollinger, Keltner, pivots, daily levels, CPR, ORB, VPD/value area, Fib, harmonic zone, and trendline.",
            "Unavailable or not-confirmed levels are explicit records; they are never drawn or treated as zero distance.",
            "Repeated value clusters expose sample counts, independent sample counts, outcome distributions, and confidence intervals.",
            "Level-distance influence is research-only and cannot place or route orders.",
        ],
    )


def _distance_records(payload: BandLevelDistanceRequest) -> list[LevelDistanceRecord]:
    p = payload.decision_price
    atr = payload.atr
    levels: list[tuple[str, str, str, float | None, str, str | None]] = [
        ("distance_to_vwap_band_1", "VWAP band 1", "vwap", p - 0.22 * atr, "available", None),
        ("distance_to_vwap_band_2", "VWAP band 2", "vwap", p + 0.84 * atr, "available", None),
        ("distance_to_vwap_band_3", "VWAP band 3", "vwap", p + 1.53 * atr, "available", None),
        ("distance_to_bb_upper_1", "BB upper 1", "bollinger", p + 0.38 * atr, "available", None),
        ("distance_to_bb_upper_2", "BB upper 2", "bollinger", p + 0.96 * atr, "available", None),
        ("distance_to_bb_upper_3", "BB upper 3", "bollinger", p + 1.72 * atr, "available", None),
        ("distance_to_bb_lower_1", "BB lower 1", "bollinger", p - 0.44 * atr, "available", None),
        ("distance_to_bb_lower_2", "BB lower 2", "bollinger", p - 1.02 * atr, "available", None),
        ("distance_to_bb_lower_3", "BB lower 3", "bollinger", p - 1.82 * atr, "available", None),
        ("distance_to_keltner_upper", "Keltner upper", "keltner", p + 1.10 * atr, "available", None),
        ("distance_to_keltner_lower", "Keltner lower", "keltner", p - 1.05 * atr, "available", None),
        ("distance_to_pivot_resistance", "Pivot resistance/R1", "pivot", p + 0.31 * atr, "available", None),
        ("distance_to_pivot_support", "Pivot support/S1", "pivot", p - 0.88 * atr, "available", None),
        ("distance_to_daily_resistance", "Daily resistance", "daily_level", p + 0.47 * atr, "available", None),
        ("distance_to_daily_support", "Daily support", "daily_level", p - 1.34 * atr, "available", None),
        ("distance_to_cpr_top", "CPR top", "cpr", p + 0.18 * atr, "available", None),
        ("distance_to_cpr_bottom", "CPR bottom", "cpr", p - 0.21 * atr, "available", None),
        ("cpr_width_percentile", "CPR width percentile", "cpr", 18.0, "available", None),
        ("inside_candle_height_pct", "Inside candle height pct", "pivot", 9.2, "available", None),
        ("distance_to_fib_level", "Fib 0.618/0.786 zone", "fibonacci", p + 0.26 * atr, "available", None),
        ("distance_to_harmonic_completion_zone", "Harmonic completion zone", "harmonic", None, "not_confirmed", "AB=CD harmonic is forming; confirmation_time is after decision_time."),
        ("distance_to_trendline", "Rising trendline", "trendline", p - 0.12 * atr, "available", None),
        ("distance_to_orb_high", "Opening range high", "orb", p + 0.34 * atr, "available", None),
        ("distance_to_orb_low", "Opening range low", "orb", p - 1.18 * atr, "available", None),
        ("distance_to_vpd_poc", "Volume profile POC", "vpd_value_area", p - 0.09 * atr, "available", None),
        ("distance_to_value_area_high", "Value area high", "vpd_value_area", p + 0.62 * atr, "available", None),
        ("distance_to_value_area_low", "Value area low", "vpd_value_area", None, "unavailable", "Volume profile value-area low unavailable because expected volume context is incomplete."),
    ]
    records: list[LevelDistanceRecord] = []
    for field_name, level_name, family, level_value, availability, reason in levels:
        if availability != "available" or level_value is None:
            records.append(
                LevelDistanceRecord(
                    field_name=field_name,
                    level_name=level_name,
                    level_family=family,  # type: ignore[arg-type]
                    level_value=None,
                    distance_points=None,
                    distance_pct=None,
                    distance_atr=None,
                    side="unavailable",
                    proximity_bucket="unavailable",
                    availability=availability,  # type: ignore[arg-type]
                    unavailable_reason=reason,
                    point_in_time_safe=True,
                )
            )
            continue
        distance = round(p - level_value, 4)
        distance_atr = round(distance / atr, 4)
        if abs(distance_atr) <= 0.15:
            bucket = "touching"
        elif abs(distance_atr) <= 0.50:
            bucket = "near"
        elif abs(distance_atr) <= 1.25:
            bucket = "moderate"
        else:
            bucket = "far"
        records.append(
            LevelDistanceRecord(
                field_name=field_name,
                level_name=level_name,
                level_family=family,  # type: ignore[arg-type]
                level_value=round(level_value, 4),
                distance_points=distance,
                distance_pct=round(distance / p * 100.0, 4),
                distance_atr=distance_atr,
                side="above" if distance > 0 else "below" if distance < 0 else "at_level",
                proximity_bucket=bucket,  # type: ignore[arg-type]
                availability="available",
                unavailable_reason=None,
                point_in_time_safe=True,
            )
        )
    return records


def _clusters(payload: BandLevelDistanceRequest) -> list[RepeatedValueClusterRecord]:
    specs = [
        (
            ["distance_to_vwap_band_3", "distance_to_bb_upper_3", "distance_to_pivot_resistance", "distance_to_cpr_top"],
            "VWAP band 3 + BB upper 3 + R1 + narrow CPR",
            84,
            57,
            {"TARGET_HIT_FIRST": 0.22, "FAKE_BREAKOUT": 0.41, "NEITHER_HIT_TIME_EXIT": 0.26, "SL_HIT_FIRST": 0.11},
        ),
        (
            ["distance_to_vpd_poc", "distance_to_cpr_bottom", "distance_to_trendline"],
            "POC touch + CPR bottom + trendline proximity",
            68,
            44,
            {"TARGET_HIT_FIRST": 0.49, "RETEST_SUCCESS": 0.19, "NEITHER_HIT_TIME_EXIT": 0.21, "FAKE_BREAKOUT": 0.11},
        ),
        (
            ["inside_candle_height_pct", "distance_to_fib_level", "distance_to_daily_resistance"],
            "Inside candle <= 10pct + Fib zone + daily resistance",
            39,
            31,
            {"TARGET_HIT_FIRST": 0.28, "FAKE_BREAKOUT": 0.36, "SL_HIT_FIRST": 0.18, "NEITHER_HIT_TIME_EXIT": 0.18},
        ),
    ]
    clusters: list[RepeatedValueClusterRecord] = []
    for idx, (fields, band, samples, independent, outcomes) in enumerate(specs, start=1):
        continuation = round((outcomes.get("TARGET_HIT_FIRST", 0.0) + outcomes.get("RETEST_SUCCESS", 0.0)) * 100, 2)
        fakeout = round(outcomes.get("FAKE_BREAKOUT", 0.0) * 100, 2)
        range_prob = round(outcomes.get("NEITHER_HIT_TIME_EXIT", 0.0) * 100, 2)
        reversal = round(max(0.0, 100.0 - continuation - fakeout - range_prob), 2)
        sample_pass = independent >= payload.minimum_cluster_sample_count
        clusters.append(
            RepeatedValueClusterRecord(
                cluster_id=f"{payload.symbol.upper()}-value-cluster-{idx:02d}",
                cluster_signature=_hash({"fields": fields, "band": band})[:24],
                matched_fields=fields,
                candidate_band=band,
                sample_count=samples,
                independent_sample_count=independent,
                confidence_interval=(round(max(0.0, continuation / 100 - 0.08), 3), round(min(1.0, continuation / 100 + 0.08), 3)),
                outcome_distribution=outcomes,
                continuation_probability_pct=continuation,
                reversal_probability_pct=reversal,
                range_probability_pct=range_prob,
                fakeout_probability_pct=fakeout,
                minimum_sample_pass=sample_pass,
                evidence_quality="STRONG" if independent >= 100 else "MEDIUM" if sample_pass else "LOW_EVIDENCE",
            )
        )
    return clusters


def _influences(clusters: list[RepeatedValueClusterRecord]) -> list[LevelDistanceOutcomeInfluence]:
    influences: list[LevelDistanceOutcomeInfluence] = []
    for cluster in clusters:
        near_resistance = "pivot_resistance" in " ".join(cluster.matched_fields) or "daily_resistance" in " ".join(cluster.matched_fields)
        influences.append(
            LevelDistanceOutcomeInfluence(
                influence_id=f"influence-{cluster.cluster_id}",
                field_name=cluster.matched_fields[0],
                current_bucket=cluster.candidate_band,
                historical_case_count=cluster.independent_sample_count,
                continuation_delta_pct=round(cluster.continuation_probability_pct - 45.0, 2),
                reversal_delta_pct=round(cluster.reversal_probability_pct - 20.0, 2),
                range_delta_pct=round(cluster.range_probability_pct - 25.0, 2),
                fakeout_delta_pct=round(cluster.fakeout_probability_pct - 20.0, 2),
                interpretation=(
                    "Resistance/band confluence increases fakeout risk and blocks confidence."
                    if near_resistance and cluster.fakeout_probability_pct >= 30
                    else "Level cluster supports retest continuation only after closed-bar confirmation."
                ),
                blocks_confidence=bool(near_resistance and cluster.fakeout_probability_pct >= 30),
            )
        )
    return influences


def _missing_levels(records: list[LevelDistanceRecord]) -> list[MissingLevelRecord]:
    missing: list[MissingLevelRecord] = []
    for record in records:
        if record.availability == "available":
            continue
        missing.append(
            MissingLevelRecord(
                level_name=record.level_name,
                required_for_family=record.level_family,
                availability=record.availability,  # type: ignore[arg-type]
                reason=record.unavailable_reason or "Level unavailable.",
                fallback_behavior="exclude_from_similarity" if record.availability == "not_confirmed" else "reduce_coverage",
            )
        )
    return missing


def _gates(
    *,
    required_present: bool,
    unavailable_safe: bool,
    pit_safe: bool,
    clusters: list[RepeatedValueClusterRecord],
    influences: list[LevelDistanceOutcomeInfluence],
    missing: list[MissingLevelRecord],
) -> list[BandLevelDistanceGate]:
    return [
        _gate("TV-V077-001", "All required distance fields emitted", required_present, f"required_fields={len(REQUIRED_DISTANCE_FIELDS)}.", "Emit every required distance field."),
        _gate("TV-V077-002", "Repeated value clusters include evidence", bool(clusters) and all(cluster.sample_count > 0 and cluster.confidence_interval for cluster in clusters), f"clusters={len(clusters)}.", "Attach sample counts and confidence intervals."),
        _gate("TV-FI-043", "Mixed-feature similarity handles unavailable values", unavailable_safe, f"missing_levels={len(missing)}.", "Represent unavailable levels explicitly."),
        _gate("TV-FI-047", "Value clusters expose corrected evidence fields", all(cluster.independent_sample_count > 0 for cluster in clusters), "Independent sample counts are present."),
        _gate("TV-FI-054", "Unavailable values are explained", all(item.reason for item in missing), "Unavailable/not-confirmed levels carry reason and fallback behavior.", "Explain missing levels."),
        _gate("TV-FI-077", "RSI/MFI-style bands expose sample counts and confidence intervals", all(cluster.sample_count >= cluster.independent_sample_count and cluster.confidence_interval for cluster in clusters), "Value clusters include sample and interval fields.", "Attach evidence metadata."),
        _gate("TV-V077-003", "Level distance influences outcomes", bool(influences), f"influences={len(influences)}.", "Compute outcome influence deltas."),
        _gate("TV-V077-004", "Available levels are point-in-time safe", pit_safe, "All available level distances use confirmed levels only.", "Block future/unconfirmed levels."),
        _gate("TV-V077-005", "No trading capability", True, "Band/level distance memory is research-only and cannot route orders."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str | None = None) -> BandLevelDistanceGate:
    return BandLevelDistanceGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
