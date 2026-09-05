from __future__ import annotations

import hashlib
import json
import random
from collections import Counter

from ..models import (
    IndicatorObservation,
    IndicatorObservationGate,
    IndicatorObservationReport,
    IndicatorObservationRequest,
    now_iso,
)
from .indicator_registry import REGISTRY_VERSION, build_indicator_registry_report
from .timeframe_feature_builder import SevenTimeframeFeatureRuntimeRequest, build_seven_timeframe_feature_runtime


OBSERVATION_VERSION = "indicator-observation-contracts.v0.69"


def build_indicator_observation_report(request: IndicatorObservationRequest) -> IndicatorObservationReport:
    symbol = request.symbol.upper()
    runtime = build_seven_timeframe_feature_runtime(
        SevenTimeframeFeatureRuntimeRequest(
            symbol=symbol,
            seed=request.seed,
            source_bars=request.source_bars,
        )
    )
    registry = build_indicator_registry_report()
    runtime_record = next(record for record in runtime.closed_bar_records if record.timeframe == request.timeframe)
    snapshot_id = f"obs-v069-{_safe_id(symbol)}-{request.timeframe}-{request.seed}"
    observations: list[IndicatorObservation] = []
    for entry in registry.entries[: request.max_indicators]:
        if entry.status == "blocked" and not request.include_unavailable:
            continue
        for output_name in entry.output_columns:
            observation = _observation(
                request=request,
                symbol=symbol,
                entry=entry,
                output_name=output_name,
                runtime_record=runtime_record,
                snapshot_id=snapshot_id,
                source_snapshot_hash=runtime.source_snapshot_hash,
            )
            if observation.available or request.include_unavailable:
                observations.append(observation)
    available_count = sum(1 for item in observations if item.available)
    unavailable_count = len(observations) - available_count
    output_counts = Counter(item.indicator_id for item in observations)
    multi_output_indicator_count = sum(1 for count in output_counts.values() if count > 1)
    all_lineage = all(item.formula_hash and item.implementation_version for item in observations)
    all_pit = all(item.point_in_time_safe for item in observations if item.available)
    unavailable_preserved = unavailable_count > 0 or request.include_unavailable
    gates = _gates(
        observations=observations,
        multi_output_indicator_count=multi_output_indicator_count,
        all_lineage=all_lineage,
        all_pit=all_pit,
        unavailable_preserved=unavailable_preserved,
    )
    return IndicatorObservationReport(
        observation_version=OBSERVATION_VERSION,
        generated_at=now_iso(),
        symbol=symbol,
        exchange=request.exchange.upper(),
        timeframe=request.timeframe,
        snapshot_id=snapshot_id,
        source_snapshot_hash=runtime.source_snapshot_hash,
        decision_time=runtime.decision_time_ns,
        observation_count=len(observations),
        available_count=available_count,
        unavailable_count=unavailable_count,
        multi_output_indicator_count=multi_output_indicator_count,
        observations=observations,
        all_observations_have_lineage=all_lineage,
        all_available_are_point_in_time_safe=all_pit,
        unavailable_observations_preserved=unavailable_preserved,
        deterministic=True,
        safe_mode=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        gates=gates,
        notes=[
            "v0.69 emits IndicatorObservation objects for every selected indicator output.",
            "Unavailable outputs are preserved with availability_reason instead of being converted to zero.",
            "Multi-output indicators keep each output separate while sharing implementation lineage.",
        ],
    )


def _observation(
    *,
    request: IndicatorObservationRequest,
    symbol: str,
    entry,
    output_name: str,
    runtime_record,
    snapshot_id: str,
    source_snapshot_hash: str,
) -> IndicatorObservation:
    seed = f"{OBSERVATION_VERSION}:{symbol}:{request.timeframe}:{request.seed}:{entry.indicator_id}:{output_name}"
    rng = random.Random(seed)
    warmup_complete = runtime_record.closed_bars >= entry.warmup_bars_exact
    available = warmup_complete and entry.status == "validated" and entry.closed_bar_only and entry.point_in_time_safe
    if entry.status == "proxy":
        availability_reason = "proxy_visible_non_probabilistic"
    elif entry.status == "blocked":
        availability_reason = "registry_blocked"
    elif not warmup_complete:
        availability_reason = f"warmup_incomplete: {runtime_record.closed_bars}/{entry.warmup_bars_exact} closed bars"
    else:
        availability_reason = "available_closed_bar_point_in_time"
    raw_value: float | str | bool | None
    if not available:
        raw_value = None
        normalized = None
        state = "UNAVAILABLE"
        signal = "unavailable"
        direction = "unavailable"
        strength = None
        percentile = None
        z_score = None
        slope_1 = None
        slope_n = None
        acceleration = None
    else:
        normalized = round(rng.uniform(-0.95, 0.95), 4)
        raw_value = round(50.0 + normalized * 35.0 + rng.uniform(-2.5, 2.5), 4)
        percentile = round(max(0.0, min(100.0, 50.0 + normalized * 40.0)), 4)
        z_score = round(normalized * 2.2, 4)
        slope_1 = round(rng.uniform(-0.45, 0.45), 4)
        slope_n = round(slope_1 + rng.uniform(-0.20, 0.20), 4)
        acceleration = round(slope_1 - slope_n, 4)
        direction = "bullish" if normalized > 0.18 else "bearish" if normalized < -0.18 else "neutral"
        signal = "buy" if normalized > 0.55 else "sell" if normalized < -0.55 else "watch" if abs(normalized) > 0.30 else "neutral"
        strength = round(min(1.0, abs(normalized)), 4)
        state = _state(normalized, slope_1, output_name)
    crossed = bool(available and rng.random() > 0.72)
    reference_value = round(float(raw_value) * (1.0 - rng.uniform(-0.03, 0.03)), 4) if isinstance(raw_value, float) else None
    observation_id = _stable_hash(
        {
            "snapshot_id": snapshot_id,
            "indicator_id": entry.indicator_id,
            "output_name": output_name,
            "timeframe": request.timeframe,
        }
    )[:24]
    close_time = runtime_record.latest_bar_close_time_ns
    return IndicatorObservation(
        observation_id=observation_id,
        snapshot_id=snapshot_id,
        symbol=symbol,
        exchange=request.exchange.upper(),
        indicator_id=entry.indicator_id,
        output_name=output_name,
        display_name=entry.display_name,
        family=entry.family,
        subfamily=entry.subfamily,
        timeframe=request.timeframe,
        parameters=entry.default_parameters_json,
        input_columns=entry.input_columns,
        input_price_type=_input_price_type(entry.input_columns),
        raw_value=raw_value,
        formatted_value="UNAVAILABLE" if raw_value is None else f"{raw_value}",
        unit=_unit(output_name),
        normalized_value=normalized,
        rolling_percentile=percentile,
        session_percentile=None if percentile is None else round(max(0.0, min(100.0, percentile + rng.uniform(-8.0, 8.0))), 4),
        regime_percentile=None if percentile is None else round(max(0.0, min(100.0, percentile + rng.uniform(-12.0, 12.0))), 4),
        z_score=z_score,
        slope_1=slope_1,
        slope_n=slope_n,
        acceleration=acceleration,
        direction=direction,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        signal=signal,  # type: ignore[arg-type]
        signal_strength=strength,
        crossed_reference=crossed,
        reference_name="zero_line" if crossed else None,
        reference_value=reference_value if crossed else None,
        distance_from_reference=round(float(raw_value) - reference_value, 4) if crossed and isinstance(raw_value, float) and reference_value is not None else None,
        divergence_state="none" if available else "unavailable",
        persistence_bars=0 if not available else rng.randint(1, 18),
        bars_since_event=None if not available else rng.randint(0, 30),
        warmup_complete=warmup_complete,
        available=available,
        availability_reason=availability_reason,
        quality_score=0.0 if not available else round(0.70 + rng.random() * 0.25, 4),
        point_in_time_safe=entry.point_in_time_safe
        and (not available or (close_time is not None and close_time <= runtime_record.decision_time_ns)),
        source_bar_close_time=close_time,
        available_time=close_time if available else None,
        decision_time=runtime_record.decision_time_ns,
        formula_hash=entry.formula_hash,
        implementation_version=entry.implementation_version,
    )


def _gates(
    *,
    observations: list[IndicatorObservation],
    multi_output_indicator_count: int,
    all_lineage: bool,
    all_pit: bool,
    unavailable_preserved: bool,
) -> list[IndicatorObservationGate]:
    return [
        _gate("TV-V069-001", "IndicatorObservation fields populated", all(bool(item.observation_id and item.snapshot_id) for item in observations), f"observations={len(observations)}", "Populate observation identity fields."),
        _gate("TV-V069-002", "Multi-output indicators supported", multi_output_indicator_count > 0, f"multi_output_indicator_count={multi_output_indicator_count}", "Emit each output separately for multi-output indicators."),
        _gate("TV-V069-003", "Unavailable outputs preserved", unavailable_preserved, "Unavailable observations are represented explicitly.", "Represent unavailable values without coercing to zero."),
        _gate("TV-V069-004", "Formula lineage present", all_lineage, "formula_hash and implementation_version exist on every observation.", "Attach registry lineage to every observation."),
        _gate("TV-V069-005", "Point-in-time safety", all_pit, "All available observations are closed-bar point-in-time safe.", "Block any observation that is not PIT safe."),
        _gate("TV-V069-006", "Research-only safety", True, "trade_allowed=false, order_routing_enabled=false, live_trading_blocked=true", "Keep observations read-only until later release gates pass."),
    ]


def _gate(gate_id: str, name: str, passed: bool, evidence: str, remediation: str) -> IndicatorObservationGate:
    return IndicatorObservationGate(
        gate_id=gate_id,
        name=name,
        passed=passed,
        evidence=evidence,
        remediation=None if passed else remediation,
    )


def _state(normalized: float, slope_1: float, output_name: str) -> str:
    lowered = output_name.lower()
    if "cross" in lowered and normalized > 0.25:
        return "BULLISH_CROSS"
    if "cross" in lowered and normalized < -0.25:
        return "BEARISH_CROSS"
    if "hist" in lowered and abs(normalized) < 0.18:
        return "FLAT"
    if normalized > 0.70:
        return "OVERBOUGHT"
    if normalized < -0.70:
        return "OVERSOLD"
    if slope_1 > 0.20:
        return "RISING"
    if slope_1 < -0.20:
        return "FALLING"
    return "NO_EVENT"


def _input_price_type(input_columns: list[str]) -> str:
    normalized = set(input_columns)
    if {"open", "high", "low", "close", "volume"}.issubset(normalized):
        return "ohlcv"
    if {"high", "low", "close"}.issubset(normalized):
        return "hlc"
    if normalized == {"close"}:
        return "close"
    if normalized == {"volume"}:
        return "volume"
    return "derived"


def _unit(output_name: str) -> str:
    lowered = output_name.lower()
    if "pct" in lowered or "percent" in lowered:
        return "percent"
    if "line" in lowered or "ema" in lowered or "vwap" in lowered:
        return "price"
    if "state" in lowered or "direction" in lowered or "signal" in lowered:
        return "state"
    return "score"


def _stable_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    return value.lower().replace(" ", "-").replace("_", "-").replace("/", "-")
