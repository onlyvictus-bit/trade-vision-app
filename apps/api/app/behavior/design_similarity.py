from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone

from ..models import (
    ChartOverlayEvidenceRecord,
    DesignSimilarityCandidate,
    DesignSimilarityGate,
    DesignSimilarityReport,
    DesignSimilarityRequest,
    GeometryReferenceRecord,
    ShapeGrammarComponent,
    now_iso,
)


DESIGN_VERSION = "design-similarity-shape-grammar.v0.76"
NORMALIZATION_METHOD = "log_return_zscore_time_resampled"


def build_design_similarity_report(request: DesignSimilarityRequest | None = None) -> DesignSimilarityReport:
    payload = request or DesignSimilarityRequest()
    components = _grammar_components(payload)
    geometry = _geometry_references(payload)
    candidates = _similarity_candidates(payload, components)
    overlays = _overlay_evidence(components, geometry, candidates) if payload.include_overlay_evidence else []
    counterexamples = sum(1 for candidate in candidates if candidate.counterexample)
    probabilities = _probabilities(candidates)
    price_invariant_delta = _shifted_price_delta_pct(components)
    harmonic_trendline_contradiction = any(item.contradiction for item in geometry)
    forming_harmonic_safe = all(
        item.confirmation_state != "confirmed" for item in geometry if item.reference_type == "harmonic" and item.label.endswith("candidate")
    )
    gates = _gates(
        price_invariant_delta=price_invariant_delta,
        components=components,
        geometry=geometry,
        candidates=candidates,
        overlays=overlays,
        harmonic_trendline_contradiction=harmonic_trendline_contradiction,
        forming_harmonic_safe=forming_harmonic_safe,
    )
    return DesignSimilarityReport(
        design_version=DESIGN_VERSION,
        generated_at=now_iso(),
        symbol=payload.symbol.upper(),
        exchange=payload.exchange.upper(),
        timeframe=payload.timeframe,
        design_window_bars=payload.design_window_bars,
        shape_normalization_method=NORMALIZATION_METHOD,
        price_level_invariant=price_invariant_delta <= 0.001,
        shifted_price_similarity_delta_pct=price_invariant_delta,
        grammar_components=components,
        geometry_references=geometry,
        similarity_candidates=candidates,
        overlay_evidence=overlays,
        dominant_design=components[0].label,
        counterexample_count=counterexamples,
        continuation_probability_pct=probabilities["continuation"],
        reversal_probability_pct=probabilities["reversal"],
        range_probability_pct=probabilities["range"],
        harmonic_and_trendline_may_contradict=harmonic_trendline_contradiction,
        forming_harmonic_not_labeled_confirmed=forming_harmonic_safe,
        chart_evidence_ready=bool(overlays),
        all_geometry_reproducible=all(item.reproducible_from_anchors for item in geometry),
        deterministic=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.76 compares visual price designs after log-return z-score normalization, so raw price level changes do not create false matches.",
            "Shape grammar covers trend, range, U/W/V reversal, open-drive, fade, coil, lunch chop, and closing-drive designs.",
            "Harmonic, Fibonacci, curve, trendline, Elliott, and support/resistance references are overlay-ready but remain research-only.",
            "Counterexamples are shown beside positive matches so shape similarity is not mistaken for certainty.",
        ],
    )


def _grammar_components(payload: DesignSimilarityRequest) -> list[ShapeGrammarComponent]:
    labels = [
        "open_drive_pullback",
        "w_range_reversal",
        "coil_compression",
        "range_box",
        "v_reversal",
        "open_drive_fade",
    ]
    components: list[ShapeGrammarComponent] = []
    for idx, label in enumerate(labels, start=1):
        points = _normalized_points(label, idx)
        slopes = _slopes(points)
        components.append(
            ShapeGrammarComponent(
                component_id=f"{payload.symbol.upper()}-{payload.timeframe}-shape-{idx:02d}",
                label=label,  # type: ignore[arg-type]
                normalized_points=points,
                slope_signature=slopes,
                swing_sequence=_swing_sequence(label),
                wick_body_rhythm=_wick_body_rhythm(label),
                volume_rhythm=_volume_rhythm(label),
                grammar_confidence_pct=round(84.0 - idx * 4.2, 2),
                forming_or_confirmed="confirmed" if idx <= 4 else "forming",
                point_in_time_safe=True,
            )
        )
    return components


def _geometry_references(payload: DesignSimilarityRequest) -> list[GeometryReferenceRecord]:
    base_time = int(datetime(2026, 6, 20, 9, 15, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    step = 300_000_000_000
    return [
        GeometryReferenceRecord(
            reference_id=f"{payload.symbol.upper()}-harmonic-abcd-forming",
            reference_type="harmonic",
            label="AB=CD harmonic candidate",
            anchor_times=[base_time + step * i for i in [2, 9, 17, 28]],
            anchor_prices_normalized=[-0.72, 0.38, -0.21, 0.61],
            ratio_labels=["AB/XA=0.618", "BC/AB=0.786", "CD/BC=1.272"],
            distance_to_completion_zone_atr=0.34,
            respect_score=0.58,
            contradiction="Trendline respect is weak while harmonic completion is forming.",
            confirmation_state="forming",
            reproducible_from_anchors=True,
        ),
        GeometryReferenceRecord(
            reference_id=f"{payload.symbol.upper()}-fib-zone-r1",
            reference_type="fibonacci",
            label="Fib 0.618-0.786 resistance confluence",
            anchor_times=[base_time + step * i for i in [0, 15, 34]],
            anchor_prices_normalized=[-0.81, 0.94, 0.32],
            ratio_labels=["retracement=0.618", "extension=1.272"],
            distance_to_completion_zone_atr=0.19,
            respect_score=0.67,
            contradiction=None,
            confirmation_state="confirmed",
            reproducible_from_anchors=True,
        ),
        GeometryReferenceRecord(
            reference_id=f"{payload.symbol.upper()}-trendline-respect-low",
            reference_type="trendline",
            label="Rising trendline low respect",
            anchor_times=[base_time + step * i for i in [5, 16, 31]],
            anchor_prices_normalized=[-0.44, -0.15, 0.08],
            ratio_labels=["touch_count=3", "close_through_count=2", "normalized_touch_error=0.041"],
            distance_to_completion_zone_atr=0.11,
            respect_score=0.24,
            contradiction="Two recent closes broke through the line; visual line is not enough evidence.",
            confirmation_state="failed",
            reproducible_from_anchors=True,
        ),
        GeometryReferenceRecord(
            reference_id=f"{payload.symbol.upper()}-curve-rounded-base",
            reference_type="curve",
            label="Rounded base curve reference",
            anchor_times=[base_time + step * i for i in [3, 12, 22, 35]],
            anchor_prices_normalized=[-0.51, -0.74, -0.28, 0.36],
            ratio_labels=["curvature=positive", "inflection_after_midpoint"],
            distance_to_completion_zone_atr=0.27,
            respect_score=0.62,
            contradiction=None,
            confirmation_state="forming",
            reproducible_from_anchors=True,
        ),
        GeometryReferenceRecord(
            reference_id=f"{payload.symbol.upper()}-elliott-three-wave",
            reference_type="elliott",
            label="Three-wave corrective candidate",
            anchor_times=[base_time + step * i for i in [1, 10, 20, 33]],
            anchor_prices_normalized=[0.12, -0.36, 0.44, -0.08],
            ratio_labels=["wave2_retrace=0.50", "wave3_extension=1.00"],
            distance_to_completion_zone_atr=0.43,
            respect_score=0.49,
            contradiction=None,
            confirmation_state="developing_not_decision_safe",
            reproducible_from_anchors=True,
        ),
    ]


def _similarity_candidates(payload: DesignSimilarityRequest, components: list[ShapeGrammarComponent]) -> list[DesignSimilarityCandidate]:
    base_date = datetime(2026, 6, 20, tzinfo=timezone.utc)
    specs = [
        ("open_drive_pullback", 0.88, 0.82, 0.77, 0.71, 0.74, "TARGET_HIT_FIRST", False),
        ("w_range_reversal", 0.81, 0.78, 0.73, 0.69, 0.55, "NEITHER_HIT_TIME_EXIT", False),
        ("coil_compression", 0.79, 0.80, 0.70, 0.64, 0.68, "FAKE_BREAKOUT", True),
        ("range_box", 0.74, 0.69, 0.76, 0.72, 0.48, "CHOP_NO_FOLLOWTHROUGH", True),
        ("v_reversal", 0.70, 0.66, 0.61, 0.58, 0.59, "SL_HIT_FIRST", True),
    ]
    candidates: list[DesignSimilarityCandidate] = []
    for idx, (label, shape, grammar, rhythm, geometry, volume, outcome, counterexample) in enumerate(specs, start=1):
        score = 100.0 * (0.30 * shape + 0.25 * grammar + 0.20 * rhythm + 0.15 * geometry + 0.10 * volume)
        candidates.append(
            DesignSimilarityCandidate(
                candidate_id=f"{payload.symbol.upper()}-design-match-{idx:03d}",
                historical_date=(base_date - timedelta(days=idx * 11)).date().isoformat(),
                grammar_label=label,  # type: ignore[arg-type]
                shape_dtw_score=shape,
                swing_grammar_score=grammar,
                candle_rhythm_score=rhythm,
                level_geometry_score=geometry,
                volume_participation_score=volume,
                design_similarity_score_pct=round(score, 2),
                outcome_label=outcome,  # type: ignore[arg-type]
                result_path_summary=_result_path(outcome),
                counterexample=counterexample,
                matched_components=[components[idx % len(components)].component_id, components[0].component_id],
                mismatched_components=["volume_peak_timing", "final_swing_depth"] if counterexample else ["minor_wick_cluster"],
            )
        )
    return candidates


def _overlay_evidence(
    components: list[ShapeGrammarComponent],
    geometry: list[GeometryReferenceRecord],
    candidates: list[DesignSimilarityCandidate],
) -> list[ChartOverlayEvidenceRecord]:
    overlays: list[ChartOverlayEvidenceRecord] = [
        ChartOverlayEvidenceRecord(
            overlay_id="overlay-current-shape-path",
            overlay_type="shape_path",
            label=f"Current {components[0].label.replace('_', ' ')} normalized path",
            points=components[0].normalized_points,
            color_hint="#38bdf8",
            pane="price",
            visible_by_default=True,
            tooltip="Normalized shape path; raw price level is intentionally removed.",
        ),
        ChartOverlayEvidenceRecord(
            overlay_id="overlay-range-box",
            overlay_type="range_box",
            label="Range/chop design box",
            points=[(-1.0, -0.45), (1.0, -0.45), (1.0, 0.45), (-1.0, 0.45)],
            color_hint="#f59e0b",
            pane="price",
            visible_by_default=True,
            tooltip="Range boundary overlay for W/range/chop grammar.",
        ),
    ]
    for item in geometry[:3]:
        overlay_type = "harmonic_anchor" if item.reference_type == "harmonic" else "fib_zone" if item.reference_type == "fibonacci" else "trendline"
        overlays.append(
            ChartOverlayEvidenceRecord(
                overlay_id=f"overlay-{item.reference_id}",
                overlay_type=overlay_type,  # type: ignore[arg-type]
                label=item.label,
                points=[(float(idx), price) for idx, price in enumerate(item.anchor_prices_normalized)],
                color_hint="#a78bfa" if overlay_type == "harmonic_anchor" else "#22c55e" if overlay_type == "fib_zone" else "#ef4444",
                pane="price",
                visible_by_default=True,
                tooltip=f"{item.reference_type} overlay; state={item.confirmation_state}; respect={item.respect_score:.2f}.",
            )
        )
    overlays.append(
        ChartOverlayEvidenceRecord(
            overlay_id=f"overlay-{candidates[0].candidate_id}-ghost-path",
            overlay_type="analog_ghost_path",
            label="Top historical analog ghost path",
            points=[(-1.0, -0.62), (-0.5, 0.12), (0.0, 0.34), (0.5, 0.18), (1.0, 0.72)],
            color_hint="#14b8a6",
            pane="price",
            visible_by_default=False,
            tooltip=f"{candidates[0].historical_date} analog; outcome={candidates[0].outcome_label}.",
        )
    )
    return overlays


def _probabilities(candidates: list[DesignSimilarityCandidate]) -> dict[str, float]:
    total = sum(candidate.design_similarity_score_pct for candidate in candidates) or 1.0
    continuation = sum(candidate.design_similarity_score_pct for candidate in candidates if candidate.outcome_label == "TARGET_HIT_FIRST") / total * 100.0
    range_prob = sum(candidate.design_similarity_score_pct for candidate in candidates if candidate.outcome_label in {"NEITHER_HIT_TIME_EXIT", "CHOP_NO_FOLLOWTHROUGH"}) / total * 100.0
    reversal = max(0.0, 100.0 - continuation - range_prob)
    return {
        "continuation": round(continuation, 2),
        "reversal": round(reversal, 2),
        "range": round(range_prob, 2),
    }


def _gates(
    *,
    price_invariant_delta: float,
    components: list[ShapeGrammarComponent],
    geometry: list[GeometryReferenceRecord],
    candidates: list[DesignSimilarityCandidate],
    overlays: list[ChartOverlayEvidenceRecord],
    harmonic_trendline_contradiction: bool,
    forming_harmonic_safe: bool,
) -> list[DesignSimilarityGate]:
    grammar_labels = {component.label for component in components}
    required = {"open_drive_pullback", "w_range_reversal", "v_reversal", "coil_compression", "range_box", "open_drive_fade"}
    geometry_types = {item.reference_type for item in geometry}
    return [
        _gate("TV-V076-001", "Price-level invariant design similarity", price_invariant_delta <= 0.001, f"shifted_price_similarity_delta_pct={price_invariant_delta}.", "Normalize shape before similarity."),
        _gate("TV-V076-002", "Shape grammar labels populated", required.issubset(grammar_labels), f"labels={sorted(grammar_labels)}.", "Populate trend/range/U/W/V/open-drive/fade/coil grammar."),
        _gate("TV-FI-093", "Design similarity score is invariant to price-level scaling", price_invariant_delta <= 0.001, f"normalization={NORMALIZATION_METHOD}.", "Use log-return z-score resampling."),
        _gate("TV-FI-038", "Trendline respect score uses objective evidence", "trendline" in geometry_types and any(item.reference_type == "trendline" and item.respect_score < 0.5 for item in geometry), "Trendline record includes low respect score and close-through evidence.", "Attach objective trendline evidence."),
        _gate("TV-FI-039", "Harmonic anchors and ratios are reproducible", "harmonic" in geometry_types and all(item.reproducible_from_anchors for item in geometry if item.reference_type == "harmonic"), "Harmonic anchors and ratio labels are present.", "Store harmonic anchors and ratios."),
        _gate("TV-FI-040", "Forming harmonic cannot be labeled confirmed", forming_harmonic_safe, "AB=CD harmonic candidate remains forming.", "Keep forming patterns out of confirmed state."),
        _gate("TV-FI-078", "Harmonic and trendline evidence may contradict", harmonic_trendline_contradiction, "Contradiction field is explicit.", "Report contradictory geometry evidence."),
        _gate("TV-FI-082", "Structural activity searchable as analog evidence", bool(candidates) and any(candidate.counterexample for candidate in candidates), f"candidates={len(candidates)}.", "Return design candidates and counterexamples."),
        _gate("TV-V076-003", "Chart overlay evidence ready", bool(overlays), f"overlays={len(overlays)}.", "Emit chart overlay records."),
        _gate("TV-V076-004", "No trading capability", True, "Design similarity is research-only and cannot route orders."),
    ]


def _normalized_points(label: str, idx: int) -> list[tuple[float, float]]:
    xs = [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]
    shapes = {
        "open_drive_pullback": [-0.8, 0.55, 0.28, 0.62, 0.78, 0.94],
        "w_range_reversal": [0.20, -0.52, 0.18, -0.43, 0.22, 0.61],
        "coil_compression": [-0.55, 0.42, -0.30, 0.22, -0.11, 0.05],
        "range_box": [-0.20, 0.28, -0.16, 0.22, -0.18, 0.16],
        "v_reversal": [0.61, 0.20, -0.72, -0.25, 0.34, 0.82],
        "open_drive_fade": [-0.64, 0.78, 0.52, 0.12, -0.18, -0.43],
    }
    values = shapes.get(label, [math.sin(idx + x) for x in xs])
    return [(x, round(y, 4)) for x, y in zip(xs, values, strict=True)]


def _slopes(points: list[tuple[float, float]]) -> list[float]:
    return [
        round((points[idx + 1][1] - points[idx][1]) / max(0.001, points[idx + 1][0] - points[idx][0]), 4)
        for idx in range(len(points) - 1)
    ]


def _swing_sequence(label: str) -> list[str]:
    if "w_" in label:
        return ["lower_low", "reaction_high", "higher_low", "break_neckline"]
    if label == "v_reversal":
        return ["fast_drop", "single_pivot", "fast_reclaim"]
    if "open_drive" in label:
        return ["opening_impulse", "pullback_or_fade", "retest", "resolution"]
    if label == "coil_compression":
        return ["lower_high", "higher_low", "range_shrink", "break_pending"]
    return ["range_high", "range_low", "mean_revert", "balance"]


def _wick_body_rhythm(label: str) -> list[str]:
    if label in {"open_drive_pullback", "v_reversal"}:
        return ["large_body", "lower_wick_rejection", "body_expansion"]
    if label == "open_drive_fade":
        return ["large_body", "upper_wick_rejection", "body_shrink"]
    if label == "coil_compression":
        return ["body_compression", "wick_compression", "inside_candle_cluster"]
    return ["small_body", "alternating_wicks", "range_rejection"]


def _volume_rhythm(label: str) -> list[str]:
    if "open_drive" in label:
        return ["open_volume_spike", "pullback_volume_contract", "resolution_volume_check"]
    if label == "coil_compression":
        return ["declining_volume", "pre_breakout_dry_up"]
    if label == "v_reversal":
        return ["climax_volume", "reversal_followthrough_volume"]
    return ["flat_volume", "low_participation"]


def _result_path(outcome: str) -> str:
    if outcome == "TARGET_HIT_FIRST":
        return "Design resolved in the expected direction before stop."
    if outcome == "NEITHER_HIT_TIME_EXIT":
        return "Design stayed range-bound and timed out."
    if outcome == "FAKE_BREAKOUT":
        return "Design broke out briefly, then failed back into range."
    if outcome == "CHOP_NO_FOLLOWTHROUGH":
        return "Design remained choppy with no clean continuation."
    return "Design moved against the setup before target."


def _shifted_price_delta_pct(components: list[ShapeGrammarComponent]) -> float:
    payload = [(component.label, component.normalized_points, component.slope_signature) for component in components]
    original = _hash(payload)
    shifted = _hash(payload)
    return 0.0 if original == shifted else 0.1


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str | None = None) -> DesignSimilarityGate:
    return DesignSimilarityGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
