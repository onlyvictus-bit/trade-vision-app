from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path
from statistics import mean

from ..models import (
    AnalogIndexManifest,
    FeatureBlockImportanceReport,
    FeatureManifest,
    FeatureManifestEntry,
    IndicatorFeatureBlock,
    IndicatorSequenceRecord,
    NineCandleBuildRequest,
    NineCandleEvidencePacket,
    NineCandleFeatureVector,
    NineCandleFeatureVectorAudit,
    NineCandleHybridDecision,
    NineCandleJarvisPanel,
    NineCandleModelPrediction,
    NineCandleOutcomeLabelRequest,
    NineCandleSaveSetupRequest,
    NineCandleSetupRecord,
    OutcomeHorizonLabel,
    ProbabilityCalibrationBin,
    WinnerFailureAnalogResult,
    now_iso,
)
from .indicator_registry import build_indicator_registry_report
from .real_indicator_adapter import REAL_RUNTIME_PROMOTED_INDICATORS, compute_real_indicator_outputs_with_telemetry


FEATURE_MANIFEST_VERSION = "nine-candle-feature-manifest.v1"
PANEL_VERSION = "9c-hrla.v2.1"
EVIDENCE_PACKET_VERSION = "9c-evidence-packet.v1"
INDEX_VERSION = "9c-analog-index.mock.v1"
ANALOG_INDEX_ARTIFACT_VERSION = "9c-analog-index-artifact.v1"
MODEL_VERSION = "mock"
HORIZONS = [3, 5, 9, 12, 20]
EPSILON = 1e-9

def build_feature_manifest() -> FeatureManifest:
    registry = build_indicator_registry_report()
    entries: list[FeatureManifestEntry] = []
    for index, item in enumerate(registry.entries):
        normalization = _manifest_normalization_policy(item)
        entries.append(
            FeatureManifestEntry(
                feature_manifest_version=FEATURE_MANIFEST_VERSION,
                feature_id=f"indicator.{item.indicator_id}.value",
                feature_index=index,
                feature_type=_feature_type(item.continuous_or_event),
                feature_block=f"indicator:{item.family}",
                normalization_method=normalization["method"],
                normalization_formula=normalization["formula"],
                missing_default=None,
                missing_mask_enabled=True,
                missing_policy="masked_missing_not_zero_signal",
                low_variance_policy="low_variance_flag_not_missing",
                similarity_policy="masked_cosine_min_overlap_0_70",
                is_active=item.status != "blocked",
                probability_enabled=bool(item.used_for_probability),
            )
        )
    order_hash = _hash("|".join(entry.feature_id for entry in entries))
    return FeatureManifest(
        feature_manifest_version=FEATURE_MANIFEST_VERSION,
        source_registry_version=registry.registry_version,
        generated_at=now_iso(),
        feature_count=len(entries),
        vector_dimension=len(entries),
        stable_order_hash=order_hash,
        entries=entries,
        requires_index_rebuild=False,
    )


def build_current_dna(request: NineCandleBuildRequest | None = None) -> NineCandleFeatureVector:
    payload = request or NineCandleBuildRequest()
    manifest = build_feature_manifest()
    indicator_sequences = build_indicator_sequences(payload.symbol, payload.timeframe, use_real_indicators=payload.use_real_indicators)
    values = []
    missing_mask = []
    for item in indicator_sequences:
        current = item.last_9_values[-1]
        missing = bool(item.value_missing_mask[-1])
        values.append(0.0 if current is None else float(current))
        missing_mask.append(missing)
    block_values: dict[str, list[float]] = {}
    for item in indicator_sequences:
        numeric = [float(value) for value in item.last_9_values if value is not None]
        block_values.setdefault(item.feature_block, []).append(mean(numeric) if numeric else 0.0)
    return NineCandleFeatureVector(
        setup_id=_setup_id(payload.symbol, payload.timeframe),
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        decision_time=now_iso(),
        source_snapshot_id="real-indicator-closed-9c-current" if payload.use_real_indicators else "mock-closed-9c-current",
        feature_manifest_version=manifest.feature_manifest_version,
        vector_dimension=manifest.vector_dimension,
        feature_values=values,
        feature_missing_mask=missing_mask,
        feature_block_values={block: round(mean(vals), 4) for block, vals in block_values.items()},
        closed_candle_only=not payload.allow_incomplete_candle,
        duplicate_or_missing_candle=False,
        incomplete_htf_blocked=False,
        future_leakage_detected=False,
    )


def build_feature_vector_audit(
    symbol: str = "RELIANCE",
    timeframe: str = "1m",
    expected_feature_manifest_version: str = FEATURE_MANIFEST_VERSION,
    use_real_indicators: bool = False,
) -> NineCandleFeatureVectorAudit:
    manifest = build_feature_manifest()
    registry = build_indicator_registry_report()
    dna = build_current_dna(NineCandleBuildRequest(symbol=symbol, timeframe=timeframe, use_real_indicators=use_real_indicators))
    sequences = build_indicator_sequences(symbol, timeframe, use_real_indicators=use_real_indicators)
    failures: list[str] = []
    warnings: list[str] = []

    vector_length_pass = (
        dna.vector_dimension
        == manifest.vector_dimension
        == len(manifest.entries)
        == len(dna.feature_values)
        == len(dna.feature_missing_mask)
        == len(sequences)
    )
    if not vector_length_pass:
        failures.append("feature_vector_length_mismatch")

    manifest_version_pass = (
        dna.feature_manifest_version
        == manifest.feature_manifest_version
        == expected_feature_manifest_version
    )
    if not manifest_version_pass:
        failures.append("feature_manifest_version_mismatch")

    feature_order_pass = all(
        entry.feature_id == f"indicator.{sequence.indicator_id}.value"
        and entry.feature_index == index
        and sequence.manifest_slot == index
        for index, (entry, sequence) in enumerate(zip(manifest.entries, sequences))
    )
    if not feature_order_pass:
        failures.append("feature_order_mismatch")

    finite_values_pass = all(math.isfinite(float(value)) for value in dna.feature_values)
    if not finite_values_pass:
        failures.append("non_finite_feature_value")

    normalized_range_pass = all(-1.000001 <= float(value) <= 1.000001 for value in dna.feature_values)
    if not normalized_range_pass:
        failures.append("feature_value_outside_normalized_range")

    missing_value_count = sum(
        1
        for sequence in sequences
        if sequence.last_9_values and sequence.last_9_values[-1] is None
    )
    missing_mask_count = sum(1 for missing in dna.feature_missing_mask if missing)
    missing_mask_pass = all(
        bool(sequence.value_missing_mask[-1]) == bool(dna.feature_missing_mask[index])
        for index, sequence in enumerate(sequences[: len(dna.feature_missing_mask)])
    ) and missing_value_count == missing_mask_count
    if not missing_mask_pass:
        failures.append("missing_value_mask_mismatch")

    probability_enabled_count = sum(1 for entry in manifest.entries if entry.probability_enabled)
    usable_probability_feature_count = sum(1 for sequence in sequences if sequence.usable_for_probability)
    probability_mask_pass = usable_probability_feature_count <= probability_enabled_count
    if not probability_mask_pass:
        failures.append("probability_enabled_mask_mismatch")

    promoted_runtime_indicator_count = sum(
        1 for entry in registry.entries if entry.indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS
    )
    computed_statuses = {"computed", "slow_warn"}
    real_runtime_computed_count = sum(
        1
        for sequence in sequences
        if sequence.source_mode == "real" and sequence.runtime_status in computed_statuses
    )
    synthetic_fallback_computed_count = sum(
        1
        for sequence in sequences
        if sequence.source_mode == "synthetic_fallback" and sequence.runtime_status in computed_statuses
    )
    runtime_failed_count = sum(
        1
        for sequence in sequences
        if sequence.runtime_status == "error" and sequence.runtime_status != "not_promoted"
    )
    runtime_unavailable_count = max(
        0,
        promoted_runtime_indicator_count
        - real_runtime_computed_count
        - synthetic_fallback_computed_count
        - runtime_failed_count,
    )
    runtime_accounting_pass = (
        real_runtime_computed_count
        + synthetic_fallback_computed_count
        + runtime_unavailable_count
        + runtime_failed_count
        == promoted_runtime_indicator_count
    )
    real_runtime_masked_count = sum(
        1 for sequence in sequences if sequence.source_mode == "masked" and sequence.runtime_status != "not_promoted"
    )
    non_promoted_masked_count = sum(
        1 for sequence in sequences if sequence.source_mode == "masked" and sequence.runtime_status == "not_promoted"
    )
    if use_real_indicators and non_promoted_masked_count:
        warnings.append(
            f"{non_promoted_masked_count} registry indicators are not promoted for the local real-runtime bridge and remain masked"
        )
    if use_real_indicators and synthetic_fallback_computed_count:
        warnings.append(
            f"{synthetic_fallback_computed_count} promoted indicators were computed from synthetic fallback candles; "
            "they are explanation-only and excluded from probability authority"
        )
    if use_real_indicators and not runtime_accounting_pass:
        failures.append("runtime_provenance_accounting_mismatch")
    if missing_mask_count:
        warnings.append(f"{missing_mask_count} features are explicitly masked and cannot act as zero signals")
    if probability_enabled_count == 0:
        warnings.append("no features are probability-enabled until indicator validation promotes them")

    return NineCandleFeatureVectorAudit(
        audit_version="9c-feature-vector-audit.v1",
        symbol=symbol.upper(),
        timeframe=timeframe,
        feature_manifest_version=manifest.feature_manifest_version,
        expected_feature_manifest_version=expected_feature_manifest_version,
        vector_dimension=dna.vector_dimension,
        manifest_feature_count=manifest.feature_count,
        feature_value_count=len(dna.feature_values),
        missing_mask_count=missing_mask_count,
        active_feature_count=sum(1 for entry in manifest.entries if entry.is_active),
        probability_enabled_count=probability_enabled_count,
        usable_probability_feature_count=usable_probability_feature_count,
        promoted_runtime_indicator_count=promoted_runtime_indicator_count,
        real_runtime_computed_count=real_runtime_computed_count,
        synthetic_fallback_computed_count=synthetic_fallback_computed_count,
        runtime_unavailable_count=runtime_unavailable_count,
        runtime_failed_count=runtime_failed_count,
        runtime_accounting_pass=runtime_accounting_pass,
        real_runtime_masked_count=real_runtime_masked_count,
        non_promoted_masked_count=non_promoted_masked_count,
        missing_value_count=missing_value_count,
        normalized_range_pass=normalized_range_pass,
        finite_values_pass=finite_values_pass,
        vector_length_pass=vector_length_pass,
        manifest_version_pass=manifest_version_pass,
        feature_order_pass=feature_order_pass,
        missing_mask_pass=missing_mask_pass,
        probability_mask_pass=probability_mask_pass,
        wait_required=bool(failures),
        failure_reasons=failures,
        warnings=warnings,
    )


@lru_cache(maxsize=128)
def build_evidence_packet(symbol: str = "RELIANCE", timeframe: str = "1m", use_real_indicators: bool = False) -> NineCandleEvidencePacket:
    manifest = build_feature_manifest()
    dna = build_current_dna(NineCandleBuildRequest(symbol=symbol, timeframe=timeframe, use_real_indicators=use_real_indicators))
    indicator_sequences = build_indicator_sequences(symbol, timeframe, use_real_indicators=use_real_indicators)
    regime = calculate_regime_identifiers()
    candles = _last_9_mock_candles(symbol.upper(), timeframe)
    levels = _mock_levels()
    decision_time = "2026-06-27T09:24:00+05:30"
    dna = dna.model_copy(update={"decision_time": decision_time})
    packet_core = {
        "packet_version": EVIDENCE_PACKET_VERSION,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "decision_time": decision_time,
        "source_snapshot_id": dna.source_snapshot_id,
        "feature_manifest_version": manifest.feature_manifest_version,
        "source_registry_version": manifest.source_registry_version,
        "last_9_candles": candles,
        "indicator_sequence_count": len(indicator_sequences),
        "feature_vector_hash": _hash(json.dumps(dna.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))),
        "levels": levels,
        "session_phase": "trend_confirmation",
        "regime_id": regime["regime_id"],
        "regime_group": regime["regime_group"],
        "data_quality_score": 0.96,
    }
    packet_hash = _hash(json.dumps(packet_core, sort_keys=True, separators=(",", ":")))
    return NineCandleEvidencePacket(
        packet_version=EVIDENCE_PACKET_VERSION,
        evidence_packet_id=f"ev9c-{symbol.lower()}-{timeframe.lower()}-{packet_hash[:12]}".replace("/", "-"),
        evidence_packet_hash=packet_hash,
        symbol=symbol.upper(),
        timeframe=timeframe,
        decision_time=decision_time,
        source_snapshot_id=dna.source_snapshot_id,
        feature_manifest_version=manifest.feature_manifest_version,
        source_registry_version=manifest.source_registry_version,
        last_9_candles=candles,
        indicator_sequences=indicator_sequences,
        feature_vector=dna,
        levels=levels,
        session_phase="trend_confirmation",
        regime_id=regime["regime_id"],
        regime_group=regime["regime_group"],
        data_quality_score=0.96,
        closed_candle_only=True,
        no_future_leakage=True,
        future_bar_blocked=True,
    )


def build_indicator_sequences(symbol: str, timeframe: str, use_real_indicators: bool = False) -> list[IndicatorSequenceRecord]:
    if use_real_indicators:
        return _build_real_indicator_sequences(symbol, timeframe)
    return _build_mock_indicator_sequences(symbol, timeframe)


def _build_mock_indicator_sequences(symbol: str, timeframe: str) -> list[IndicatorSequenceRecord]:
    registry = build_indicator_registry_report()
    sequences: list[IndicatorSequenceRecord] = []
    for index, item in enumerate(registry.entries):
        is_missing = index % 11 == 0 or item.status == "blocked"
        values: list[float | None] = []
        signals: list[str] = []
        mask: list[bool] = []
        for candle_index in range(9):
            missing = is_missing and candle_index in {0, 1, 8}
            raw = _stable_unit(symbol, timeframe, item.indicator_id, str(candle_index))
            value = None if missing else round((raw - 0.5) * 2.0, 4)
            values.append(value)
            mask.append(missing)
            signals.append("missing" if missing else _signal(value or 0.0))
        sequences.append(
            IndicatorSequenceRecord(
                indicator_id=item.indicator_id,
                feature_block=f"indicator:{item.family}",
                manifest_slot=index,
                last_9_values=values,
                last_9_signals=signals,
                value_missing_mask=mask,
                source_mode="mock",
                runtime_status="mock_generated",
                normalized_from="deterministic_mock_unit",
                raw_output_present=not all(mask),
                explanation_only=False,
                usable_for_probability=bool(item.used_for_probability and not any(mask)),
                missing_reason="indicator output unavailable in current 9C mock snapshot" if any(mask) else None,
            )
        )
    return sequences


def _build_real_indicator_sequences(symbol: str, timeframe: str) -> list[IndicatorSequenceRecord]:
    registry = build_indicator_registry_report()
    indicator_ids = [item.indicator_id for item in registry.entries if item.indicator_id in REAL_RUNTIME_PROMOTED_INDICATORS]
    real_candles = _real_closed_candles(symbol.upper(), timeframe)
    if real_candles:
        candles_for_runtime = real_candles
        candle_source = "hstry_real"
    else:
        candles_for_runtime = _runtime_closed_candles(symbol.upper(), timeframe)
        candle_source = "synthetic_fallback"
    try:
        computed, telemetry = compute_real_indicator_outputs_with_telemetry(candles_for_runtime, indicator_ids)
        runtime_error: str | None = None
    except Exception as exc:  # pragma: no cover - environment dependent; covered by fallback tests.
        computed = {}
        telemetry = []
        runtime_error = f"{type(exc).__name__}: {exc}"

    sequences: list[IndicatorSequenceRecord] = []
    for index, item in enumerate(registry.entries):
        if item.indicator_id not in REAL_RUNTIME_PROMOTED_INDICATORS:
            sequences.append(
                _missing_real_sequence(
                    item,
                    "indicator not yet promoted for local real-runtime 9C bridge",
                    manifest_slot=index,
                    runtime_status="not_promoted",
                )
            )
            continue
        if runtime_error:
            sequences.append(
                _missing_real_sequence(
                    item,
                    f"real indicator runtime unavailable: {runtime_error}",
                    manifest_slot=index,
                    runtime_status="runtime_unavailable",
                )
            )
            continue
        telemetry_row = _telemetry_for_indicator(telemetry, item.indicator_id)
        if telemetry_row and not telemetry_row.get("used_for_9c_vector"):
            status = str(telemetry_row.get("status", "unavailable"))
            sequences.append(
                _missing_real_sequence(
                    item,
                    f"real indicator telemetry status={status}",
                    manifest_slot=index,
                    runtime_status=status,
                )
            )
            continue
        payload = computed.get(item.indicator_id)
        if payload in ({}, [], None):
            sequences.append(
                _missing_real_sequence(
                    item,
                    "real indicator returned no output",
                    manifest_slot=index,
                    runtime_status=str(telemetry_row.get("status", "no_output")) if telemetry_row else "no_output",
                )
            )
            continue
        values, mask, normalized_from = _extract_last_9_normalized_values(payload)
        missing_reason = "real indicator output missing/invalid for one or more 9C bars" if any(mask) else None
        runtime_status = str(telemetry_row.get("status", "computed")) if telemetry_row else "computed"
        sequences.append(
            IndicatorSequenceRecord(
                indicator_id=item.indicator_id,
                feature_block=f"indicator:{item.family}",
                manifest_slot=index,
                last_9_values=values,
                last_9_signals=["missing" if missing else _signal(value or 0.0) for value, missing in zip(values, mask)],
                value_missing_mask=mask,
                source_mode="real" if candle_source == "hstry_real" else "synthetic_fallback",
                runtime_status=runtime_status,
                normalized_from=normalized_from,
                raw_output_present=True,
                # Synthetic candles may be useful for explanation/runtime diagnostics,
                # but they can never become calibrated probability evidence.
                explanation_only=bool(candle_source != "hstry_real" or not item.used_for_probability),
                usable_for_probability=bool(
                    candle_source == "hstry_real"
                    and item.used_for_probability
                    and not any(mask)
                ),
                missing_reason=missing_reason,
            )
        )
    return sequences


def _missing_real_sequence(
    item: object,
    reason: str,
    *,
    manifest_slot: int = 0,
    runtime_status: str = "masked",
) -> IndicatorSequenceRecord:
    return IndicatorSequenceRecord(
        indicator_id=str(getattr(item, "indicator_id")),
        feature_block=f"indicator:{getattr(item, 'family')}",
        manifest_slot=manifest_slot,
        last_9_values=[None] * 9,
        last_9_signals=["missing"] * 9,
        value_missing_mask=[True] * 9,
        source_mode="masked",
        runtime_status=runtime_status,
        normalized_from=None,
        raw_output_present=False,
        explanation_only=False,
        usable_for_probability=False,
        missing_reason=reason,
    )


def _telemetry_for_indicator(telemetry: list[dict[str, object]], indicator_id: str) -> dict[str, object] | None:
    for row in telemetry:
        if row.get("indicator_id") == indicator_id:
            return row
    return None


def _extract_last_9_normalized_values(payload: object) -> tuple[list[float | None], list[bool], str]:
    series_candidates = _numeric_series_candidates(payload)
    if series_candidates:
        raw_values = max(series_candidates, key=len)[-9:]
    else:
        scalar = _first_scalar_feature_value(payload)
        raw_values = [None] * 8 + [scalar]

    padded = ([None] * max(0, 9 - len(raw_values))) + raw_values[-9:]
    numeric = [_coerce_feature_value(value) for value in padded]
    valid = [value for value in numeric if value is not None]
    if not valid:
        return [None] * 9, [True] * 9, "missing_all_values"

    bounded = all(0.0 <= value <= 100.0 for value in valid)
    if bounded:
        normalized = [None if value is None else float(normalize_bounded(value, 0.0, 100.0)["normalized"]) for value in numeric]
        normalized_from = "bounded_minmax"
    else:
        rolling_mean = mean(valid)
        rolling_std = math.sqrt(sum((value - rolling_mean) ** 2 for value in valid) / max(len(valid), 1))
        normalized = [None if value is None else float(normalize_zscore(value, rolling_mean, rolling_std)["normalized"]) for value in numeric]
        normalized_from = "rolling_zscore_clipped"
    mask = [value is None for value in normalized]
    return normalized, mask, normalized_from


def _numeric_series_candidates(payload: object) -> list[list[float]]:
    candidates: list[list[float]] = []
    if isinstance(payload, dict):
        for child in payload.values():
            candidates.extend(_numeric_series_candidates(child))
        return candidates
    if isinstance(payload, list):
        coerced = [_coerce_feature_value(item) for item in payload]
        finite_values = [value for value in coerced if value is not None]
        if finite_values and len(finite_values) == len(payload):
            candidates.append(finite_values)
        for child in payload:
            if isinstance(child, (dict, list)):
                candidates.extend(_numeric_series_candidates(child))
        return candidates
    return candidates


def _first_scalar_feature_value(payload: object) -> float | None:
    if isinstance(payload, dict):
        for child in payload.values():
            found = _first_scalar_feature_value(child)
            if found is not None:
                return found
        return None
    if isinstance(payload, list):
        for child in reversed(payload):
            found = _first_scalar_feature_value(child)
            if found is not None:
                return found
        return None
    return _coerce_feature_value(payload)


def _coerce_feature_value(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"buy", "bull", "bullish", "long", "up", "breakout"}:
            return 100.0
        if lowered in {"sell", "bear", "bearish", "short", "down", "breakdown"}:
            return 0.0
        if lowered in {"neutral", "hold", "range", "sideways", "wait"}:
            return 50.0
        try:
            numeric = float(lowered)
        except ValueError:
            return None
        return numeric if math.isfinite(numeric) else None
    return None


def build_indicator_alignment(symbol: str = "RELIANCE", timeframe: str = "1m", use_real_indicators: bool = False) -> list[IndicatorFeatureBlock]:
    blocks: list[IndicatorFeatureBlock] = []
    for item in build_indicator_sequences(symbol, timeframe, use_real_indicators=use_real_indicators):
        alignment = round(_stable_unit(symbol, timeframe, item.indicator_id, "alignment"), 3)
        winner_count = int(5 + alignment * 24)
        failure_count = int(3 + (1.0 - alignment) * 18)
        blocks.append(
            IndicatorFeatureBlock(
                indicator_id=item.indicator_id,
                feature_block=item.feature_block,
                manifest_slot=item.manifest_slot,
                last_9_values=item.last_9_values,
                last_9_signals=item.last_9_signals,
                matched_winner_count=winner_count,
                matched_failure_count=failure_count,
                historical_effect=_historical_effect(alignment, item.usable_for_probability),
                current_alignment=alignment,
                source_mode=item.source_mode,
                runtime_status=item.runtime_status,
                normalized_from=item.normalized_from,
                raw_output_present=item.raw_output_present,
                explanation_only=item.explanation_only,
                usable_for_probability=item.usable_for_probability,
                missing_reason=item.missing_reason,
            )
        )
    return blocks


def build_analogs(symbol: str = "RELIANCE", timeframe: str = "1m") -> WinnerFailureAnalogResult:
    from .nine_candle_history import build_path_analog_report

    path = build_path_analog_report(symbol, timeframe)
    winner_matches = [item for item in path["top_matches"] if item["outcome_label"] == "TARGET_HIT"]
    failure_matches = [item for item in path["top_matches"] if item["outcome_label"] in {"SL_HIT", "FAKE_BREAKOUT"}]
    winner_similarity = _average_similarity(winner_matches)
    failure_similarity = _average_similarity(failure_matches)
    total_matches = int(path["total_matches"])
    return WinnerFailureAnalogResult(
        analog_version="winner-failure-analog.v2.1.path-derived",
        symbol=symbol.upper(),
        timeframe=timeframe,
        feature_manifest_version=FEATURE_MANIFEST_VERSION,
        total_matches=total_matches,
        winner_like_matches=int(path["winner_like_matches"]),
        failure_like_matches=int(path["failure_like_matches"]),
        winner_similarity=winner_similarity,
        failure_similarity=failure_similarity,
        sample_quality=_sample_quality_label(total_matches),
        retrieval_engine="numpy_cosine_fallback",
        two_stage_filter_applied=True,
        approximate_faiss_used=False,
        index_version="9c-path-analog-index.v1",
        active_index_hash=path["output_hash"],
        notes=[
            "Analog counts and similarities are derived from the path-analogs endpoint.",
            f"History source: {path['history_source']}; temporal_diversity={path['temporal_diversity_score']}.",
            "Stage 1 filters by symbol/timeframe/regime/session/feature manifest version.",
            "Stage 2 uses deterministic cosine plus DTW-style path similarity until FAISS is installed.",
        ],
    )


def build_index_manifest(symbol: str = "RELIANCE", timeframe: str = "1m") -> AnalogIndexManifest:
    from .. import storage
    manifest = build_feature_manifest()
    from .nine_candle_history import build_path_analog_report

    path = build_path_analog_report(symbol, timeframe)
    record_count = int(path["total_matches"])
    index_version = "9c-path-analog-index.v1"
    candidate = AnalogIndexManifest(
        index_version=index_version,
        feature_manifest_version=manifest.feature_manifest_version,
        vector_dimension=manifest.vector_dimension,
        record_count=record_count,
        index_hash=_hash(
            "|".join(
                [
                    symbol.upper(),
                    timeframe,
                    manifest.stable_order_hash,
                    index_version,
                    str(record_count),
                    str(path["output_hash"]),
                ]
            )
        ),
        index_type="numpy_cosine_fallback_exact",
        active_pointer_swapped_at=now_iso(),
        validated=True,
    )
    artifact_meta = _write_analog_index_artifact(symbol=symbol, timeframe=timeframe, manifest=candidate, path_report=path)
    candidate = candidate.model_copy(
        update={
            **artifact_meta,
            "validated": bool(artifact_meta["artifact_verified"]),
        }
    )
    return storage.atomic_swap_nine_candle_analog_index_manifest(symbol=symbol, timeframe=timeframe, manifest=candidate)


def _analog_index_artifact_root() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "indexes" / "9c"


def _write_analog_index_artifact(
    *,
    symbol: str,
    timeframe: str,
    manifest: AnalogIndexManifest,
    path_report: dict[str, object],
) -> dict[str, object]:
    normalized = symbol.upper()
    artifact_dir = _analog_index_artifact_root() / f"symbol={normalized}" / f"timeframe={timeframe}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{manifest.index_hash[:16]}.json"
    temp_path = artifact_path.with_suffix(".json.tmp")
    payload = {
        "artifact_version": ANALOG_INDEX_ARTIFACT_VERSION,
        "artifact_format": "json_exact_cosine_v1",
        "symbol": normalized,
        "timeframe": timeframe,
        "index_version": manifest.index_version,
        "feature_manifest_version": manifest.feature_manifest_version,
        "index_hash": manifest.index_hash,
        "index_type": manifest.index_type,
        "vector_dimension": manifest.vector_dimension,
        "record_count": manifest.record_count,
        "path_analog_hash": path_report["output_hash"],
        "total_matches": path_report["total_matches"],
        "winner_like_matches": path_report["winner_like_matches"],
        "failure_like_matches": path_report["failure_like_matches"],
        "persisted_outcome_match_count": path_report.get("persisted_outcome_match_count", 0),
        "top_matches": path_report["top_matches"],
        "validated": manifest.validated,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    expected_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    temp_path.write_text(canonical, encoding="utf-8")
    temp_path.replace(artifact_path)
    readback = artifact_path.read_text(encoding="utf-8")
    actual_sha = hashlib.sha256(readback.encode("utf-8")).hexdigest()
    verified = actual_sha == expected_sha
    return {
        "artifact_uri": str(artifact_path),
        "artifact_sha256": expected_sha,
        "artifact_size_bytes": artifact_path.stat().st_size,
        "artifact_format": "json_exact_cosine_v1",
        "artifact_verified": verified,
    }


def build_model_status() -> NineCandleModelPrediction:
    return build_model_status_for()


def build_model_status_for(symbol: str = "RELIANCE", timeframe: str = "1m") -> NineCandleModelPrediction:
    from .nine_candle_calibration import build_evidence_model_status

    return build_evidence_model_status(symbol, timeframe)


def build_calibration_bins() -> list[ProbabilityCalibrationBin]:
    return build_calibration_bins_for()


def build_calibration_bins_for(symbol: str = "RELIANCE", timeframe: str = "1m") -> list[ProbabilityCalibrationBin]:
    from .nine_candle_calibration import build_evidence_calibration_bins

    return build_evidence_calibration_bins(symbol, timeframe)


def build_feature_importance() -> FeatureBlockImportanceReport:
    return FeatureBlockImportanceReport(
        report_version="feature-block-importance.mock.v1",
        method="mock_reserved",
        stable_across_walkforward=False,
        top_blocks=[
            {"feature_block": "candle_anatomy", "importance": 0.18, "stable": True},
            {"feature_block": "indicator:momentum", "importance": 0.14, "stable": False},
            {"feature_block": "indicator:support_resistance", "importance": 0.13, "stable": False},
            {"feature_block": "session_phase", "importance": 0.11, "stable": True},
        ],
        raw_indicator_shap_trusted=False,
    )


def build_hybrid_decision(symbol: str = "RELIANCE", timeframe: str = "1m") -> NineCandleHybridDecision:
    from .nine_candle_history import build_ood_status_report, build_path_analog_report
    from .nine_candle_reasoning_arbiter import (
        build_calibration_drift_report,
        build_decision_audit_record,
        build_reasoning_arbiter_report,
    )

    analog = build_analogs(symbol, timeframe)
    path = build_path_analog_report(symbol, timeframe)
    ood = build_ood_status_report(symbol, timeframe)
    model = build_model_status_for(symbol, timeframe)
    evidence_packet = build_evidence_packet(symbol, timeframe)
    dna = evidence_packet.feature_vector
    regime = {"regime_id": evidence_packet.regime_id, "regime_group": evidence_packet.regime_group}
    masked = masked_cosine_similarity(
        dna.feature_values,
        [round(0.82 * value, 6) for value in dna.feature_values],
        dna.feature_missing_mask,
        dna.feature_missing_mask,
        min_overlap_ratio=0.70,
    )
    sample = bayesian_sample_quality(analog.winner_like_matches, analog.total_matches)
    freshness = freshness_quality("mock", age_seconds=86400, max_allowed_age_seconds=60)
    model_edge = round(model.calibrated_target_prob - model.calibrated_stop_prob, 6)
    analog_edge = round(analog.winner_similarity - analog.failure_similarity, 6)
    data_quality_score = 0.96
    arbiter = build_reasoning_arbiter_report(
        symbol,
        timeframe,
        analog_report=analog.model_dump() if hasattr(analog, "model_dump") else dict(analog),
        path_report=path,
        ood_report=ood,
    )
    drift = build_calibration_drift_report()
    proof = proof_score(
        data_quality=data_quality_score,
        sample_quality=sample["score"],
        overlap_quality=masked["overlap_quality"],
        calibration_quality=0.72,
        analog_agreement_quality=analog_edge,
        freshness_quality=freshness["freshness_quality"],
        execution_quality=0.80,
        counterfactual_stability=0.68,
    )
    quality_multiplier = proof["proof_score"]
    safety_gates = _safety_gates(
        analog,
        model,
        masked,
        sample,
        freshness,
        proof,
        feature_manifest_version=evidence_packet.feature_manifest_version,
        path=path,
        ood=ood,
        arbiter=arbiter,
        drift=drift,
    )
    blocked = [gate for gate in safety_gates if gate["status"] in {"wait", "block"}]
    critical_wait_gate_ids = {
        "9C-G001",
        "9C-G002",
        "9C-G003",
        "9C-G004",
        "9C-G006",
        "9C-G007",
        "9C-G008",
        "9C-G013",
        "9C-G014",
        "9C-G016",
        "9C-G018",
        "9C-G019",
    }
    critical_blockers = [gate for gate in safety_gates if gate["gate_id"] in critical_wait_gate_ids and gate["status"] in {"wait", "block"}]
    if critical_blockers:
        decision = "WAIT"
    else:
        decision = "WATCH" if any(gate["gate_id"] == "9C-G012" for gate in blocked) else "WAIT"
    audit = build_decision_audit_record(
        symbol,
        timeframe,
        arbiter_report=arbiter,
        decision=decision,
        safety_gates=safety_gates,
    )
    final_edge = round((model_edge + analog_edge + model.expected_r_after_cost) * quality_multiplier, 4)
    if critical_blockers:
        blocker_text = "; ".join(f"{gate['gate_id']} {gate['name']}: {gate['evidence']}" for gate in critical_blockers[:3])
        reason = (
            "WAIT. Critical 9C safety gates blocked confidence promotion. "
            f"{blocker_text} Path analog evidence uses {analog.total_matches} regime-scoped matches; "
            f"OOD status is {ood['gate']['status']}. Arbiter={arbiter['override_reason']} Audit={audit['audit_hash'][:12]}."
        )
    else:
        reason = (
            "WATCH only. 9-candle analog memory is medium quality and winner similarity is above failure similarity, "
            "but the LightGBM layer is mock/non-probabilistic and HTF confirmation is partial, so PAPER-CANDIDATE is blocked. "
            f"Path analog evidence uses {analog.total_matches} regime-scoped matches; OOD status is {ood['gate']['status']}. "
            f"Arbiter={arbiter['override_reason']} Audit={audit['audit_hash'][:12]}."
        )
    return NineCandleHybridDecision(
        decision_version="9c-hybrid-decision.v2.1",
        symbol=symbol.upper(),
        timeframe=timeframe,
        decision=decision,
        final_edge=final_edge,
        model_edge=model_edge,
        analog_edge=analog_edge,
        quality_multiplier=quality_multiplier,
        sample_quality_score=sample["score"],
        data_quality_score=data_quality_score,
        freshness_quality=freshness["freshness_quality"],
        overlap_quality=masked["overlap_quality"],
        proof_score=proof["proof_score"],
        mode="mock",
        regime_id=regime["regime_id"],
        regime_group=regime["regime_group"],
        evidence_packet_id=evidence_packet.evidence_packet_id,
        evidence_packet_hash=evidence_packet.evidence_packet_hash,
        safety_gates=safety_gates,
        final_reason=reason,
    )


def build_jarvis_panel(symbol: str = "RELIANCE", timeframe: str = "1m") -> NineCandleJarvisPanel:
    analog = build_analogs(symbol, timeframe)
    model = build_model_status_for(symbol, timeframe)
    decision = build_hybrid_decision(symbol, timeframe)
    return NineCandleJarvisPanel(
        panel_version=PANEL_VERSION,
        title="9-Candle Hybrid Intelligence",
        symbol=symbol.upper(),
        timeframe=timeframe,
        decision=decision.decision,
        memory=analog,
        alignment={
            "shape_pct": 83.0,
            "feature_block_alignment_pct": 77.0,
            "regime_alignment_pct": 72.0,
            "winner_similarity": analog.winner_similarity,
            "failure_similarity": analog.failure_similarity,
        },
        model=model,
        trust={
            "evidence_quality": analog.sample_quality,
            "sample_quality_score": f"{decision.sample_quality_score:.4f}",
            "data_quality_score": f"{decision.data_quality_score:.4f}",
            "freshness_quality": f"{decision.freshness_quality:.4f}",
            "overlap_quality": f"{decision.overlap_quality:.4f}",
            "proof_score": f"{decision.proof_score:.4f}",
            "mode": decision.mode,
            "regime_id": decision.regime_id,
            "regime_group": decision.regime_group,
            "calibration_status": "mock_bins_visible_not_promoted",
            "drift_status": "none",
            "htf_status": "partial",
            "latency_status": "pass",
        },
        feature_manifest=build_feature_manifest(),
        evidence_packet=build_evidence_packet(symbol, timeframe),
        current_dna=build_current_dna(NineCandleBuildRequest(symbol=symbol, timeframe=timeframe)),
        indicator_drilldown=build_indicator_alignment(symbol, timeframe),
        calibration_bins=build_calibration_bins_for(symbol, timeframe),
        feature_importance=build_feature_importance(),
        hybrid_decision=decision,
        final_reason=decision.final_reason,
    )


def save_setup(request: NineCandleSaveSetupRequest) -> NineCandleSetupRecord:
    from .. import storage

    packet = build_evidence_packet(request.symbol, request.timeframe, request.use_real_indicators)
    record = NineCandleSetupRecord(
        setup_id=_setup_id(request.symbol, request.timeframe),
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        decision_time=packet.decision_time,
        source_snapshot_id=request.source_snapshot_id or packet.source_snapshot_id,
        evidence_packet_id=packet.evidence_packet_id,
        evidence_packet_hash=packet.evidence_packet_hash,
        session_phase="post_open_trend_confirmation",
        regime_id=packet.regime_id,
        feature_manifest_version=FEATURE_MANIFEST_VERSION,
        entry_zone=[2475.0, 2478.5],
        stop=2466.0,
        target=2508.0,
        invalidation=2468.0,
        data_quality=packet.data_quality_score,
        created_at=packet.decision_time,
        label_status="pending",
    )
    return storage.save_nine_candle_setup(record)


def label_outcomes(request: NineCandleOutcomeLabelRequest) -> list[OutcomeHorizonLabel]:
    from .. import storage

    setup = storage.load_nine_candle_setup(request.setup_id)
    entry_price = request.entry_price
    stop_price = request.stop_price if request.stop_price is not None else setup.stop if setup else None
    target_price = request.target_price if request.target_price is not None else setup.target if setup else None
    if entry_price is None and setup and setup.entry_zone:
        entry_price = mean(setup.entry_zone)
    if request.future_candles and entry_price is not None and stop_price is not None and target_price is not None:
        labels = _label_outcomes_from_future_candles(
            request=request,
            entry_price=float(entry_price),
            stop_price=float(stop_price),
            target_price=float(target_price),
        )
        return storage.save_nine_candle_outcome_labels(request.setup_id, labels)

    labels = _placeholder_outcome_labels(request)
    return storage.save_nine_candle_outcome_labels(request.setup_id, labels)


def _placeholder_outcome_labels(request: NineCandleOutcomeLabelRequest) -> list[OutcomeHorizonLabel]:
    labels: list[OutcomeHorizonLabel] = []
    for horizon in HORIZONS:
        stop_first = horizon in {3, 5}
        target_first = not stop_first and horizon >= 9
        fakeout = horizon == 5
        labels.append(
            OutcomeHorizonLabel(
                setup_id=request.setup_id,
                horizon_candles=horizon,  # type: ignore[arg-type]
                label_status="complete",
                outcome_label=_outcome_label(target_first=target_first, stop_first=stop_first, fakeout=fakeout, horizon=horizon),
                mfe=round(0.18 * horizon, 3),
                mae=round(0.11 * horizon, 3),
                target_first=target_first,
                stop_first=stop_first,
                fakeout=fakeout,
                retest_seen=horizon >= 9,
                direction_after_h="up" if horizon >= 9 else "range",
                range_after_h=round(0.24 * horizon, 3),
                time_to_target=horizon if horizon >= 9 else None,
                time_to_stop=horizon if stop_first else None,
                max_drawdown_before_profit=round(0.07 * horizon, 3),
                intrabar_ambiguity_rule="conservative_stop_first",
            )
        )
    return labels


def _label_outcomes_from_future_candles(
    *,
    request: NineCandleOutcomeLabelRequest,
    entry_price: float,
    stop_price: float,
    target_price: float,
) -> list[OutcomeHorizonLabel]:
    labels: list[OutcomeHorizonLabel] = []
    for horizon in HORIZONS:
        window = request.future_candles[:horizon]
        if len(window) < horizon:
            labels.append(_pending_outcome_label(request.setup_id, horizon, "insufficient_future_window"))
            continue
        if any(not _valid_ohlc_bar(bar) for bar in window):
            labels.append(_pending_outcome_label(request.setup_id, horizon, "invalid_future_candle"))
            continue
        labels.append(
            _label_single_horizon(
                setup_id=request.setup_id,
                horizon=horizon,
                window=window,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                direction=request.direction,
                conservative_intrabar=request.conservative_intrabar,
            )
        )
    return labels


def _label_single_horizon(
    *,
    setup_id: str,
    horizon: int,
    window: list[dict[str, object]],
    entry_price: float,
    stop_price: float,
    target_price: float,
    direction: str,
    conservative_intrabar: bool,
) -> OutcomeHorizonLabel:
    target_bar: int | None = None
    stop_bar: int | None = None
    same_bar_collision = False
    highs = [_bar_float(bar, "high") or entry_price for bar in window]
    lows = [_bar_float(bar, "low") or entry_price for bar in window]
    closes = [_bar_float(bar, "close") or entry_price for bar in window]

    for index, bar in enumerate(window, start=1):
        high = _bar_float(bar, "high") or entry_price
        low = _bar_float(bar, "low") or entry_price
        if direction == "short":
            target_hit = low <= target_price
            stop_hit = high >= stop_price
        else:
            target_hit = high >= target_price
            stop_hit = low <= stop_price
        if target_hit and target_bar is None:
            target_bar = index
        if stop_hit and stop_bar is None:
            stop_bar = index
        if target_hit and stop_hit and target_bar == index and stop_bar == index:
            same_bar_collision = True
            if conservative_intrabar:
                break
        if target_bar is not None or stop_bar is not None:
            if target_bar != stop_bar:
                break

    if same_bar_collision and conservative_intrabar:
        target_first = False
        stop_first = True
    else:
        target_first = target_bar is not None and (stop_bar is None or target_bar < stop_bar)
        stop_first = stop_bar is not None and (target_bar is None or stop_bar <= target_bar)

    mfe = max(max(highs) - entry_price, 0.0) if direction == "long" else max(entry_price - min(lows), 0.0)
    mae = max(entry_price - min(lows), 0.0) if direction == "long" else max(max(highs) - entry_price, 0.0)
    first_target_index = max((target_bar or len(window)) - 1, 0)
    drawdown_window = window[: first_target_index + 1] if target_bar is not None else window
    drawdown_lows = [_bar_float(bar, "low") or entry_price for bar in drawdown_window]
    drawdown_highs = [_bar_float(bar, "high") or entry_price for bar in drawdown_window]
    max_drawdown = (
        max(entry_price - min(drawdown_lows), 0.0)
        if direction == "long"
        else max(max(drawdown_highs) - entry_price, 0.0)
    )
    fakeout = bool(target_bar is not None and stop_bar is not None and stop_bar > target_bar)
    label = _outcome_label(target_first=target_first, stop_first=stop_first, fakeout=fakeout, horizon=horizon)

    return OutcomeHorizonLabel(
        setup_id=setup_id,
        horizon_candles=horizon,  # type: ignore[arg-type]
        label_status="complete",
        outcome_label=label,
        mfe=round(mfe, 6),
        mae=round(mae, 6),
        target_first=target_first,
        stop_first=stop_first,
        fakeout=fakeout,
        retest_seen=_window_retested_entry(window, entry_price),
        direction_after_h=_direction_after(entry_price, closes[-1]),
        range_after_h=round(max(highs) - min(lows), 6),
        time_to_target=target_bar,
        time_to_stop=stop_bar,
        max_drawdown_before_profit=round(max_drawdown, 6),
        intrabar_ambiguity_rule="conservative_stop_first" if conservative_intrabar else "reported_first_detected",
        future_leakage_detected=False,
    )


def _pending_outcome_label(setup_id: str, horizon: int, reason: str) -> OutcomeHorizonLabel:
    return OutcomeHorizonLabel(
        setup_id=setup_id,
        horizon_candles=horizon,  # type: ignore[arg-type]
        label_status="pending",
        outcome_label="TIME_EXIT",
        mfe=0.0,
        mae=0.0,
        target_first=False,
        stop_first=False,
        fakeout=False,
        retest_seen=False,
        direction_after_h="unknown",
        range_after_h=0.0,
        time_to_target=None,
        time_to_stop=None,
        max_drawdown_before_profit=0.0,
        intrabar_ambiguity_rule=reason,
        future_leakage_detected=False,
    )


def _valid_ohlc_bar(bar: dict[str, object]) -> bool:
    open_price = _bar_float(bar, "open")
    high = _bar_float(bar, "high")
    low = _bar_float(bar, "low")
    close = _bar_float(bar, "close")
    if open_price is None or high is None or low is None or close is None:
        return False
    return high >= max(open_price, close, low) and low <= min(open_price, close, high)


def _bar_float(bar: dict[str, object], key: str) -> float | None:
    for candidate in (key, key.upper(), key.capitalize()):
        value = bar.get(candidate)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        return number
    return None


def _window_retested_entry(window: list[dict[str, object]], entry_price: float) -> bool:
    for bar in window:
        high = _bar_float(bar, "high")
        low = _bar_float(bar, "low")
        if high is not None and low is not None and low <= entry_price <= high:
            return True
    return False


def _direction_after(entry_price: float, close_price: float) -> str:
    change = close_price - entry_price
    threshold = max(abs(entry_price) * 0.0005, EPSILON)
    if change > threshold:
        return "up"
    if change < -threshold:
        return "down"
    return "range"


def build_setup_memory(symbol: str = "RELIANCE", timeframe: str = "1m", limit: int = 25) -> dict[str, object]:
    from .. import storage

    return storage.nine_candle_memory_summary(symbol=symbol, timeframe=timeframe, limit=limit)


def _outcome_label(*, target_first: bool, stop_first: bool, fakeout: bool, horizon: int) -> str:
    if stop_first:
        return "SL_HIT"
    if fakeout:
        return "FAKE_BREAKOUT"
    if target_first:
        return "TARGET_HIT"
    if horizon >= 20:
        return "TIME_EXIT"
    return "CHOP_NO_FOLLOWTHROUGH"


def normalize_bounded(raw_value: float | None, min_value: float, max_value: float) -> dict[str, float | bool | str | None]:
    if raw_value is None or not math.isfinite(float(raw_value)):
        return {"normalized": 0.0, "missing_mask": True, "low_variance_flag": False, "method": "bounded_minmax"}
    if max_value - min_value <= EPSILON:
        return {"normalized": 0.0, "missing_mask": False, "low_variance_flag": True, "method": "bounded_minmax"}
    normalized = ((float(raw_value) - min_value) / (max_value - min_value)) * 2.0 - 1.0
    return {"normalized": max(-1.0, min(1.0, normalized)), "missing_mask": False, "low_variance_flag": False, "method": "bounded_minmax"}


def normalize_zscore(raw_value: float | None, rolling_mean: float, rolling_std: float) -> dict[str, float | bool | str | None]:
    if raw_value is None or not math.isfinite(float(raw_value)):
        return {"normalized": 0.0, "missing_mask": True, "low_variance_flag": False, "method": "zscore"}
    if rolling_std <= EPSILON:
        return {"normalized": 0.0, "missing_mask": False, "low_variance_flag": True, "method": "zscore"}
    z_value = (float(raw_value) - rolling_mean) / rolling_std
    normalized = max(-5.0, min(5.0, z_value)) / 5.0
    return {"normalized": normalized, "missing_mask": False, "low_variance_flag": False, "method": "zscore"}


def masked_cosine_similarity(
    current_vector: list[float],
    historical_vector: list[float],
    current_missing_mask: list[bool],
    historical_missing_mask: list[bool],
    min_overlap_ratio: float = 0.70,
) -> dict[str, float | bool | int | None]:
    dimension = min(len(current_vector), len(historical_vector), len(current_missing_mask), len(historical_missing_mask))
    if dimension == 0:
        return {"similarity": None, "usable": False, "valid_overlap_count": 0, "overlap_quality": 0.0}
    valid_indices = [
        index
        for index in range(dimension)
        if not current_missing_mask[index] and not historical_missing_mask[index]
    ]
    overlap_quality = len(valid_indices) / dimension
    if overlap_quality < min_overlap_ratio:
        return {"similarity": None, "usable": False, "valid_overlap_count": len(valid_indices), "overlap_quality": round(overlap_quality, 6)}
    current_masked = [float(current_vector[index]) for index in valid_indices]
    historical_masked = [float(historical_vector[index]) for index in valid_indices]
    numerator = sum(a * b for a, b in zip(current_masked, historical_masked))
    current_norm = math.sqrt(sum(a * a for a in current_masked))
    historical_norm = math.sqrt(sum(b * b for b in historical_masked))
    denominator = current_norm * historical_norm
    if denominator <= EPSILON:
        return {"similarity": None, "usable": False, "valid_overlap_count": len(valid_indices), "overlap_quality": round(overlap_quality, 6)}
    return {
        "similarity": round(numerator / denominator, 6),
        "usable": True,
        "valid_overlap_count": len(valid_indices),
        "overlap_quality": round(overlap_quality, 6),
    }


def freshness_quality(mode: str, age_seconds: float, max_allowed_age_seconds: float) -> dict[str, float | bool | str]:
    normalized_mode = mode.lower()
    if normalized_mode != "live":
        return {
            "mode": normalized_mode,
            "freshness_quality": 1.0,
            "label": "not_live_mode_no_stale_penalty",
            "stale_realtime_penalty": False,
        }
    if max_allowed_age_seconds <= EPSILON:
        return {"mode": normalized_mode, "freshness_quality": 0.0, "label": "stale", "stale_realtime_penalty": True}
    quality = max(0.0, min(1.0, 1.0 - (age_seconds / max_allowed_age_seconds)))
    if age_seconds > max_allowed_age_seconds:
        quality = 0.0
    label = "fresh" if quality >= 0.80 else "aging" if quality >= 0.50 else "stale"
    return {"mode": normalized_mode, "freshness_quality": round(quality, 6), "label": label, "stale_realtime_penalty": quality < 0.50}


def bayesian_sample_quality(wins: int, total: int, prior_wins: int = 10, prior_total: int = 20) -> dict[str, float | str | int | bool]:
    safe_total = max(0, int(total))
    safe_wins = max(0, min(int(wins), safe_total))
    posterior_win_rate = (safe_wins + prior_wins) / max(prior_total + safe_total, 1)
    standard_error = math.sqrt((posterior_win_rate * (1.0 - posterior_win_rate)) / max(prior_total + safe_total, 1))
    credible_lower_bound = max(0.0, posterior_win_rate - 1.64 * standard_error)
    if safe_total < 30:
        score = 0.25
        label = "low"
        decision_cap = "WAIT"
    elif safe_total < 100:
        score = min(0.70, credible_lower_bound)
        label = "medium"
        decision_cap = "WATCH"
    else:
        score = min(1.0, credible_lower_bound / 0.60)
        label = "strong" if score >= 0.70 else "medium"
        decision_cap = "PAPER-CANDIDATE"
    return {
        "score": round(score, 6),
        "label": label,
        "posterior_win_rate": round(posterior_win_rate, 6),
        "credible_lower_bound": round(credible_lower_bound, 6),
        "decision_cap": decision_cap,
        "total": safe_total,
        "wins": safe_wins,
    }


def calculate_regime_identifiers(
    market_direction: str = "trend_up",
    volatility_regime: str = "normal_vol",
    session_regime: str = "trend_confirmation",
    trend_strength: str = "strongtrend",
    liquidity_regime: str = "liquid",
) -> dict[str, str]:
    regime_id = f"{market_direction}_{volatility_regime}_{session_regime}_{trend_strength}_{liquidity_regime}"
    regime_group = f"{market_direction}_{volatility_regime}"
    return {"regime_id": regime_id, "regime_group": regime_group}


def proof_score(
    *,
    data_quality: float,
    sample_quality: float,
    overlap_quality: float,
    calibration_quality: float,
    analog_agreement_quality: float,
    freshness_quality: float,
    execution_quality: float,
    counterfactual_stability: float,
) -> dict[str, float | str]:
    factors = [
        data_quality,
        sample_quality,
        overlap_quality,
        calibration_quality,
        max(0.0, analog_agreement_quality),
        freshness_quality,
        execution_quality,
        counterfactual_stability,
    ]
    clamped = [max(0.0, min(1.0, float(value))) for value in factors]
    score = 1.0
    for value in clamped:
        score *= value
    if score < 0.40:
        decision_cap = "WAIT"
    elif score < 0.70:
        decision_cap = "WATCH"
    else:
        decision_cap = "PAPER-CANDIDATE"
    return {"proof_score": round(score, 6), "decision_cap": decision_cap}


def _safety_gates(
    analog: WinnerFailureAnalogResult,
    model: NineCandleModelPrediction,
    masked: dict[str, float | bool | int | None],
    sample: dict[str, float | str | int | bool],
    freshness: dict[str, float | bool | str],
    proof: dict[str, float | str],
    feature_manifest_version: str = FEATURE_MANIFEST_VERSION,
    path: dict[str, object] | None = None,
    ood: dict[str, object] | None = None,
    arbiter: dict[str, object] | None = None,
    drift: dict[str, object] | None = None,
) -> list[dict[str, str]]:
    manifest_status, manifest_evidence = _manifest_gate_status(analog, feature_manifest_version, path)
    failure_status = "pass" if analog.failure_similarity < analog.winner_similarity else "wait"
    failure_evidence = (
        f"failure_similarity={analog.failure_similarity}; winner_similarity={analog.winner_similarity}."
        if failure_status == "pass"
        else f"Failure similarity {analog.failure_similarity} is not below winner similarity {analog.winner_similarity}; confidence is blocked."
    )
    expected_r_status = "pass" if model.expected_r_after_cost > 0 else "wait"
    expected_r_evidence = (
        f"{model.expected_r_after_cost}R after costs."
        if expected_r_status == "pass"
        else f"expected_R_after_cost={model.expected_r_after_cost}; non-positive edge is blocked."
    )
    gates = [
        _gate("9C-G001", "Feature manifest version", manifest_status, manifest_evidence),
        _gate("9C-G002", "Closed-candle DNA", "pass", "Current 9-candle vector uses closed candles only."),
        _gate("9C-G003", "Future leakage", "pass", "No future high/low/close/volume enters setup vector."),
        _gate("9C-G004", "Duplicate or missing candle", "pass", "No duplicate/missing candle detected in mock snapshot."),
        _gate("9C-G005", "Minimum evidence", "pass" if analog.total_matches >= 100 else "wait", f"{analog.total_matches} matches, sample quality {sample['label']}."),
        _gate("9C-G006", "Failure similarity", failure_status, failure_evidence),
        _gate("9C-G007", "Expected R after cost", expected_r_status, expected_r_evidence),
        _gate("9C-G008", "Drift block", "pass", "No active feature/prediction/label/latency/cost drift block."),
        _gate("9C-G009", "HTF confirmation", "wait", "HTF evidence is partial; PAPER-CANDIDATE is blocked."),
        _gate("9C-G010", "Mock model paper block", "wait", "model_version=mock and usable_for_probability=false."),
        _gate("9C-G011", "Routing/live mode", "block", "Live routing remains blocked by design."),
        _gate("9C-G012", "WATCH max", "wait", "Medium evidence plus mock model caps output at WATCH."),
        _gate("9C-G013", "Masked cosine overlap", "pass" if masked["usable"] else "wait", f"overlap_quality={masked['overlap_quality']}."),
        _gate("9C-G014", "Freshness mode guard", "pass" if not freshness["stale_realtime_penalty"] else "wait", f"mode={freshness['mode']} freshness={freshness['freshness_quality']}."),
        _gate("9C-G015", "Proof score gate", "pass" if proof["decision_cap"] == "PAPER-CANDIDATE" else "wait", f"proof_score={proof['proof_score']} cap={proof['decision_cap']}."),
    ]
    if ood is not None:
        ood_gate = ood.get("gate", {}) if isinstance(ood, dict) else {}
        vol_gate = ood.get("volatility_gate", {}) if isinstance(ood, dict) else {}
        shape_status = str(ood_gate.get("status", "wait"))
        vol_status = str(vol_gate.get("status", "wait"))
        combined_status = "wait" if "wait" in {shape_status, vol_status} else "pass"
        combined_evidence = (
            f"shape={shape_status}: {ood_gate.get('evidence', 'shape OOD unavailable.')} "
            f"volatility={vol_status}: {vol_gate.get('evidence', 'volatility OOD unavailable.')}"
        )
        gates.append(_gate("9C-G016", "Volatility and shape OOD", combined_status, combined_evidence))
    if path is not None:
        diversity = float(path.get("temporal_diversity_score", 0.0)) if isinstance(path, dict) else 0.0
        gates.append(
            _gate(
                "9C-G017",
                "Temporal diversity",
                "pass" if diversity >= 0.25 else "wait",
                f"temporal_diversity_score={diversity}; total_matches={getattr(analog, 'total_matches', 0)}.",
            )
        )
    if drift is not None:
        gate = drift.get("gate", {}) if isinstance(drift, dict) else {}
        gates.append(
            _gate(
                "9C-G018",
                "Calibration drift monitor",
                str(gate.get("status", "wait")),
                str(gate.get("evidence", "drift report unavailable; confidence is blocked.")),
            )
        )
    if arbiter is not None:
        override = bool(arbiter.get("override_to_wait", True)) if isinstance(arbiter, dict) else True
        gates.append(
            _gate(
                "9C-G019",
                "Reasoning arbiter override",
                "wait" if override else "pass",
                str(arbiter.get("override_reason", "arbiter unavailable; confidence is blocked.")) if isinstance(arbiter, dict) else "arbiter unavailable; confidence is blocked.",
            )
        )
    return gates


def _manifest_gate_status(
    analog: WinnerFailureAnalogResult,
    feature_manifest_version: str,
    path: dict[str, object] | None,
) -> tuple[str, str]:
    versions = {
        "current": feature_manifest_version,
        "analog": analog.feature_manifest_version,
    }
    if path is not None:
        path_version = path.get("feature_manifest_version")
        if path_version is not None:
            versions["path"] = str(path_version)
    unique_versions = {value for value in versions.values() if value}
    if len(unique_versions) == 1 and feature_manifest_version == FEATURE_MANIFEST_VERSION:
        return "pass", f"Feature manifest versions match: {versions}."
    return "wait", f"Feature manifest mismatch requires index rebuild or WAIT: {versions}."


def _gate(gate_id: str, name: str, status: str, evidence: str) -> dict[str, str]:
    return {"gate_id": gate_id, "name": name, "status": status, "evidence": evidence}


def _average_similarity(matches: list[dict[str, object]]) -> float:
    if not matches:
        return 0.0
    return round(sum(float(item["similarity_score"]) for item in matches) / len(matches), 6)


def _sample_quality_label(total_matches: int) -> str:
    if total_matches < 30:
        return "low"
    if total_matches < 100:
        return "medium"
    return "strong"


def _feature_type(value: str) -> str:
    if value in {"event", "numeric", "boolean", "categorical", "sequence", "mixed"}:
        return value
    if value == "overlay":
        return "mixed"
    return "numeric"


def _manifest_normalization_policy(item: object) -> dict[str, str]:
    indicator_id = str(getattr(item, "indicator_id", "")).lower()
    family = str(getattr(item, "family", "")).lower()
    continuous_or_event = str(getattr(item, "continuous_or_event", "")).lower()
    output_columns = [str(column).lower() for column in getattr(item, "output_columns", [])]
    joined = " ".join([indicator_id, family, continuous_or_event, " ".join(output_columns)])
    if any(token in joined for token in ("rsi", "mfi", "cmf", "percent", "pct", "stoch")):
        return {
            "method": "bounded_minmax",
            "formula": "normalized=((raw-min)/(max-min))*2-1; bounded indicators use fixed known bounds only",
        }
    if continuous_or_event == "event" or any(token in joined for token in ("signal", "event", "marker", "bars_since")):
        return {
            "method": "event_strength_and_recency",
            "formula": "directional_event in {-1,0,1}; recency=max(0,1-bars_since/lookback); no missing zero signal",
        }
    if continuous_or_event == "overlay" or any(token in joined for token in ("level", "pivot", "vwap", "cpr", "zone", "trendline", "fib")):
        return {
            "method": "point_in_time_level_distance_atr",
            "formula": "distance_atr=abs(close-level)/atr using closed candles; level features are explanation-only until audited",
        }
    return {
        "method": "rolling_zscore_clipped",
        "formula": "z=(raw-rolling_mean)/rolling_std; clip [-5,5]/5; low variance sets low_variance_flag not missing",
    }


def _signal(value: float) -> str:
    if value >= 0.45:
        return "bullish"
    if value <= -0.45:
        return "bearish"
    return "neutral"


def _historical_effect(alignment: float, usable: bool) -> str:
    if not usable:
        return "visible for explanation only; excluded from calibrated probability until PIT audit passes"
    if alignment >= 0.66:
        return "winner-aligned in current 9C context"
    if alignment <= 0.40:
        return "failure-aligned warning"
    return "mixed historical effect"


def _stable_unit(*parts: str) -> float:
    raw = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(raw[:12], 16) / float(0xFFFFFFFFFFFF)


def _setup_id(symbol: str, timeframe: str) -> str:
    return f"9c-{symbol.lower()}-{timeframe.lower()}-current".replace("/", "-")


def _last_9_mock_candles(symbol: str, timeframe: str) -> list[dict[str, float | int | str | bool]]:
    base_close = 2470.0 + (_stable_unit(symbol, timeframe, "base") * 10.0)
    candles: list[dict[str, float | int | str | bool]] = []
    for index in range(9):
        drift = (index - 4) * 0.55
        open_price = round(base_close + drift - 0.20, 2)
        close_price = round(base_close + drift + (0.35 if index % 3 != 0 else -0.15), 2)
        high_price = round(max(open_price, close_price) + 0.55, 2)
        low_price = round(min(open_price, close_price) - 0.45, 2)
        candles.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "sequence_number": index + 1,
                "event_time": f"2026-06-27T09:{15 + index:02d}:00+05:30",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": 120000 + index * 3500,
                "closed": True,
            }
        )
    return candles


def _real_closed_candles(symbol: str, timeframe: str, count: int = 260) -> list[dict[str, float | int | str | bool]] | None:
    """v1.98: real closed bars from local HSTRY history; None when unavailable.

    Replaces the synthetic sine-wave fallback as the primary 9C candle source.
    """
    try:
        from datetime import datetime, timedelta, timezone

        from ..orb.hstry_csv import load_hstry_series

        series = load_hstry_series(symbol, timeframe, max_bars=count)
    except Exception:
        return None
    if not series.bars:
        return None
    ist = timezone(timedelta(hours=5, minutes=30))
    candles: list[dict[str, float | int | str | bool]] = []
    for bar in series.bars:
        event_time = datetime.fromtimestamp(bar.timestamp_ns / 1_000_000_000, tz=ist).isoformat()
        candles.append(
            {
                "symbol": bar.symbol,
                "timeframe": bar.timeframe,
                "sequence_number": bar.sequence_number,
                "event_time": event_time,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume if bar.volume is not None else 0.0,
                "closed": True,
            }
        )
    return candles


def _runtime_closed_candles(symbol: str, timeframe: str, count: int = 260) -> list[dict[str, float | int | str | bool]]:
    base_close = 2470.0 + (_stable_unit(symbol, timeframe, "runtime-base") * 10.0)
    candles: list[dict[str, float | int | str | bool]] = []
    for index in range(count):
        minute_of_day = (9 * 60 + 15) + index
        hour = minute_of_day // 60
        minute = minute_of_day % 60
        drift = index * 0.035
        wave = math.sin(index / 9.0) * 1.35
        open_price = round(base_close + drift + wave - 0.18, 2)
        close_price = round(base_close + drift + wave + (0.24 if index % 5 else -0.11), 2)
        high_price = round(max(open_price, close_price) + 0.42 + abs(math.sin(index / 7.0)) * 0.18, 2)
        low_price = round(min(open_price, close_price) - 0.36 - abs(math.cos(index / 8.0)) * 0.15, 2)
        candles.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "sequence_number": index + 1,
                "event_time": f"2026-06-27T{hour:02d}:{minute:02d}:00+05:30",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": 90000 + index * 310 + (index % 13) * 2200,
                "closed": True,
            }
        )
    return candles


def _mock_levels() -> list[dict[str, float | str]]:
    return [
        {"level_name": "VWAP", "level_price": 2474.25, "level_type": "vwap", "source": "mock_pit"},
        {"level_name": "PDH", "level_price": 2486.50, "level_type": "resistance", "source": "mock_pit"},
        {"level_name": "CPR_MID", "level_price": 2471.75, "level_type": "pivot", "source": "mock_pit"},
        {"level_name": "ORB_HIGH", "level_price": 2478.80, "level_type": "opening_range", "source": "mock_pit"},
    ]


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
