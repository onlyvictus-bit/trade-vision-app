from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Mapping


REAL_RUNTIME_PROMOTED_INDICATORS = {
    "si_adaptive_flow",
    "si_bahai",
    "si_bb_break",
    "si_bos",
    "si_cdl",
    "si_cdl_mb",
    "si_choch",
    "si_cpr",
    "si_cpr_v4",
    "si_cm_strg_pivt",
    "si_dbl",
    "si_dual_ma_osc",
    "si_fib",
    "si_fmfm300",
    "si_fractal",
    "si_fvg",
    "si_hourly_pvt",
    "si_hs",
    "si_ichi_trend_osc",
    "si_impulse",
    "si_inside_candle_strategy",
    "si_inside_out",
    "si_liq_intelg",
    "si_liquidity_entry",
    "si_lrb",
    "si_macd_ta",
    "si_mk_inside",
    "si_mp_va",
    "si_nbar",
    "si_ob",
    "si_outside_rev",
    "si_rsi_div",
    "si_rsi_ss",
    "si_sbs",
    "si_sfp",
    "si_st_talipp",
    "si_strg_pivt",
    "si_sweep_inside_rr",
    "si_swing_break",
    "si_swing_str",
    "si_three_inside",
    "si_trend_sig",
    "si_trendln",
    "si_twin_range",
    "si_vwap_bb_ml_conf",
    "si_vwap_conf",
    "si_vwap_super",
    "si_wekly_pivot",
    "si_zz_swing",
}

PER_INDICATOR_LATENCY_WARN_MS = 250.0
PER_INDICATOR_LATENCY_BLOCK_MS = 800.0
REAL_INDICATOR_CACHE_VERSION = "real-indicator-adapter-cache.v1"
INDICATOR_EVIDENCE_VERSION = "indicator-evidence.v1"
REAL_INDICATOR_CACHE_MAX_ENTRIES = 256
GENERIC_VENDOR_WARMUP_BARS = 20

# Cache identity includes calculation version, the exact input-window hash,
# indicator id and normalized parameter hash. Symbol-only or symbol+timeframe
# caching is forbidden because it can replay evidence across a different D2
# state.
_REAL_INDICATOR_CACHE: OrderedDict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()


@dataclass(frozen=True, slots=True)
class IndicatorEvidence:
    """Bounded canonical M3.1-D indicator observation.

    This is sensory evidence only. It has no voting, final-band, paper or
    execution authority. ``evidence_hash`` intentionally excludes operational
    cache-hit/latency observations so the canonical calculation identity stays
    deterministic across cold/warm cache replay of the same source window.
    """

    indicator_id: str
    family: str
    dependency_family: str
    correlation_group: str
    value: object | None
    direction: str
    strength: float | None
    quality: str
    warmup_complete: bool
    warmup_required_bars: int
    output_present: bool
    status: str
    reason_code: str | None
    reason: str | None
    source_window_hash: str
    source_snapshot_hash: str | None
    source_timeframe: str | None
    sample_size: int
    parameter_hash: str
    output_hash: str | None
    evidence_hash: str
    calculation_version: str = INDICATOR_EVIDENCE_VERSION
    used_for_probability: bool = False
    may_set_final_band: bool = False
    may_execute: bool = False


@dataclass(frozen=True, slots=True)
class IndicatorMetadata:
    family: str
    dependency_family: str
    correlation_group: str
    visual_type: str
    warmup_required_bars: int


def compute_real_indicator_outputs_with_telemetry(
    candles: list[dict[str, object]],
    indicator_ids: list[str],
    *,
    parameters_by_indicator: Mapping[str, Mapping[str, object]] | None = None,
    source_snapshot_hash: str | None = None,
    source_timeframe: str | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Compute promoted indicators on one DataFrame and normalize evidence.

    Compatibility is preserved: callers still receive ``(outputs, telemetry)``
    and the legacy lowercase ``status`` field. M3.1-D adds a nested canonical
    ``evidence`` record plus flat metadata used by bounded receipts/context.

    Important semantics:
    - ERROR / NO_SIGNAL / NO_OUTPUT / WARMUP / DEPENDENCY_UNAVAILABLE are never
      converted to numeric zero.
    - slow-blocked calculations are not emitted as usable outputs.
    - a zero/non-finite volume input conservatively withholds indicators whose
      declared dependency family needs volume; zero is not assumed to mean a
      valid missing-volume substitute.
    """

    import pandas as pd
    from app.vendor.stock_app.shared.indicators.self_indc import (
        SELF_INDC_REGISTRY,
        compute_selected,
    )

    parameters_by_indicator = parameters_by_indicator or {}
    candle_hash = _candles_hash(candles)
    rows = [
        {
            "Open": candle["open"],
            "High": candle["high"],
            "Low": candle["low"],
            "Close": candle["close"],
            "Volume": candle["volume"],
        }
        for candle in candles
    ]
    index = pd.to_datetime([candle["event_time"] for candle in candles])
    df = pd.DataFrame(rows, index=index)
    dataframe_build_count = 1

    outputs: dict[str, object] = {}
    telemetry: list[dict[str, object]] = []
    for indicator_id in indicator_ids:
        registry_meta = SELF_INDC_REGISTRY.get(indicator_id)
        metadata = _indicator_metadata(indicator_id, registry_meta)
        params = dict(parameters_by_indicator.get(indicator_id, {}))
        parameter_hash = _stable_hash(params)
        cache_key = _indicator_cache_key(candle_hash, indicator_id, parameter_hash)

        if indicator_id not in REAL_RUNTIME_PROMOTED_INDICATORS or registry_meta is None:
            evidence = _make_evidence(
                indicator_id=indicator_id,
                metadata=metadata,
                payload=None,
                canonical_status="UNSUPPORTED",
                reason_code="UNSUPPORTED",
                reason="Indicator is not in the promoted real-runtime allowlist.",
                warmup_complete=len(candles) >= metadata.warmup_required_bars,
                source_window_hash=candle_hash,
                source_snapshot_hash=source_snapshot_hash,
                source_timeframe=source_timeframe,
                sample_size=len(candles),
                parameter_hash=parameter_hash,
            )
            telemetry.append(
                _telemetry_row(
                    indicator_id=indicator_id,
                    status="unsupported",
                    latency_ms=0.0,
                    output_present=False,
                    error=None,
                    cache_hit=False,
                    source_latency_ms=0.0,
                    evidence=evidence,
                    dataframe_build_count=dataframe_build_count,
                )
            )
            continue

        if _dependency_unavailable(metadata, candles):
            evidence = _make_evidence(
                indicator_id=indicator_id,
                metadata=metadata,
                payload=None,
                canonical_status="DEPENDENCY_UNAVAILABLE",
                reason_code="DEPENDENCY_UNAVAILABLE",
                reason=(
                    "Indicator depends on valid volume input, but at least one source bar has "
                    "missing, non-finite or non-positive volume. The dependency is withheld "
                    "instead of treating zero as neutral evidence."
                ),
                warmup_complete=len(candles) >= metadata.warmup_required_bars,
                source_window_hash=candle_hash,
                source_snapshot_hash=source_snapshot_hash,
                source_timeframe=source_timeframe,
                sample_size=len(candles),
                parameter_hash=parameter_hash,
            )
            telemetry.append(
                _telemetry_row(
                    indicator_id=indicator_id,
                    status="dependency_unavailable",
                    latency_ms=0.0,
                    output_present=False,
                    error=None,
                    cache_hit=False,
                    source_latency_ms=0.0,
                    evidence=evidence,
                    dataframe_build_count=dataframe_build_count,
                )
            )
            continue

        cached = _get_cached_indicator(cache_key)
        if cached is not None:
            payload = deepcopy(cached["payload"])
            status = str(cached["status"])
            error = cached.get("error")
            evidence_dict = deepcopy(cached["evidence"])
            if status in {"computed", "slow_warn"}:
                outputs[indicator_id] = payload
            telemetry.append(
                _telemetry_row(
                    indicator_id=indicator_id,
                    status=status,
                    latency_ms=0.0,
                    output_present=indicator_id in outputs,
                    error=error,
                    cache_hit=True,
                    source_latency_ms=float(cached.get("latency_ms", 0.0)),
                    evidence=evidence_dict,
                    dataframe_build_count=dataframe_build_count,
                )
            )
            continue

        started = time.perf_counter()
        status = "computed"
        canonical_status = "COMPUTED"
        reason_code: str | None = None
        reason: str | None = None
        error: str | None = None
        payload: Any = None
        warmup_complete = len(candles) >= metadata.warmup_required_bars
        try:
            vendor_params = {indicator_id: params} if params else None
            payload = compute_selected(df, [indicator_id], params=vendor_params).get(indicator_id)
            if payload in ({}, [], None):
                if not warmup_complete:
                    status = "insufficient_warmup"
                    canonical_status = "INSUFFICIENT_WARMUP"
                    reason_code = "INSUFFICIENT_BARS"
                    reason = (
                        f"{len(candles)} bars are below the deterministic warmup estimate "
                        f"of {metadata.warmup_required_bars}."
                    )
                elif metadata.visual_type == "marker-only" or metadata.family in {"pattern", "structure"}:
                    status = "no_signal"
                    canonical_status = "NO_SIGNAL"
                    reason_code = "NO_SIGNAL"
                    reason = "Indicator calculated successfully but emitted no signal event."
                else:
                    status = "no_output"
                    canonical_status = "NO_OUTPUT"
                    reason_code = "NO_OUTPUT"
                    reason = "Indicator calculation returned no bounded output payload."
        except Exception as exc:  # pragma: no cover - exact optional dependency failures vary by machine.
            status = "error"
            canonical_status = "ERROR"
            reason_code = "CALCULATION_ERROR"
            error = f"{type(exc).__name__}: {exc}"
            reason = error
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        if status == "computed" and latency_ms > PER_INDICATOR_LATENCY_BLOCK_MS:
            status = "slow_blocked"
            canonical_status = "SLOW_BLOCKED"
            reason_code = "LATENCY_BLOCK"
            reason = (
                f"Indicator runtime {latency_ms:.3f} ms exceeded the "
                f"{PER_INDICATOR_LATENCY_BLOCK_MS:.0f} ms block threshold."
            )
        elif status == "computed" and latency_ms > PER_INDICATOR_LATENCY_WARN_MS:
            status = "slow_warn"
            canonical_status = "COMPUTED"
            reason_code = "LATENCY_WARNING"
            reason = (
                f"Indicator runtime {latency_ms:.3f} ms exceeded the "
                f"{PER_INDICATOR_LATENCY_WARN_MS:.0f} ms warning threshold."
            )

        if status in {"computed", "slow_warn"}:
            outputs[indicator_id] = payload

        evidence = _make_evidence(
            indicator_id=indicator_id,
            metadata=metadata,
            payload=payload if status in {"computed", "slow_warn"} else None,
            canonical_status=canonical_status,
            reason_code=reason_code,
            reason=reason,
            warmup_complete=warmup_complete,
            source_window_hash=candle_hash,
            source_snapshot_hash=source_snapshot_hash,
            source_timeframe=source_timeframe,
            sample_size=len(candles),
            parameter_hash=parameter_hash,
        )
        _set_cached_indicator(
            cache_key,
            {
                "payload": deepcopy(payload),
                "status": status,
                "error": error,
                "latency_ms": latency_ms,
                "evidence": deepcopy(evidence),
            },
        )
        telemetry.append(
            _telemetry_row(
                indicator_id=indicator_id,
                status=status,
                latency_ms=latency_ms,
                output_present=indicator_id in outputs,
                error=error,
                cache_hit=False,
                source_latency_ms=latency_ms,
                evidence=evidence,
                dataframe_build_count=dataframe_build_count,
            )
        )
    return outputs, telemetry


def build_indicator_evidence_summary(telemetry: list[dict[str, object]]) -> dict[str, object]:
    """Return a deterministic bounded accounting summary for canonical receipts.

    Operational cache-hit/latency data is summarized separately from the
    deterministic canonical evidence hash. Later orchestration can use this
    helper without re-running any indicator.
    """

    evidence_rows = [
        item.get("evidence")
        for item in telemetry
        if isinstance(item.get("evidence"), dict)
    ]
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    dependency_counts: dict[str, int] = {}
    correlation_groups: dict[str, int] = {}
    evidence_hashes: list[str] = []
    for row in evidence_rows:
        assert isinstance(row, dict)
        status = str(row.get("status", "ERROR"))
        family = str(row.get("family", "other"))
        dependency = str(row.get("dependency_family", "unknown"))
        correlation = str(row.get("correlation_group", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        dependency_counts[dependency] = dependency_counts.get(dependency, 0) + 1
        correlation_groups[correlation] = correlation_groups.get(correlation, 0) + 1
        evidence_hash = row.get("evidence_hash")
        if evidence_hash:
            evidence_hashes.append(str(evidence_hash))

    deterministic = {
        "calculation_version": INDICATOR_EVIDENCE_VERSION,
        "requested_count": len(telemetry),
        "accounted_count": len(evidence_rows),
        "status_counts": dict(sorted(status_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "dependency_family_counts": dict(sorted(dependency_counts.items())),
        "correlation_group_counts": dict(sorted(correlation_groups.items())),
        "evidence_hashes": sorted(evidence_hashes),
    }
    operational = {
        "cache_hit_count": sum(bool(item.get("cache_hit")) for item in telemetry),
        "cache_miss_count": sum(not bool(item.get("cache_hit")) for item in telemetry),
        "max_source_latency_ms": max(
            [float(item.get("source_latency_ms", 0.0)) for item in telemetry] or [0.0]
        ),
        "indicator_dataframe_build_count": max(
            [
                int((item.get("runtime_audit") or {}).get("indicator_dataframe_build_count", 0))
                for item in telemetry
                if isinstance(item.get("runtime_audit"), dict)
            ]
            or [0]
        ),
    }
    return {
        **deterministic,
        "canonical_evidence_hash": _stable_hash(deterministic),
        "operational": operational,
        "used_for_probability": False,
        "may_set_final_band": False,
        "may_execute": False,
    }


def clear_real_indicator_runtime_cache() -> None:
    _REAL_INDICATOR_CACHE.clear()


def compute_pta_marker_outputs_with_telemetry(
    candles: list[dict[str, object]],
    indicator_ids: list[str],
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    import pandas as pd
    from app.vendor.stock_app.shared.indicators import pta
    from app.vendor.stock_app.shared.indicators.pta_signal_markers import compute_selected

    rows = [
        {
            "Open": candle["open"],
            "High": candle["high"],
            "Low": candle["low"],
            "Close": candle["close"],
            "Volume": candle["volume"],
        }
        for candle in candles
    ]
    index = pd.to_datetime([candle["event_time"] for candle in candles])
    df = pd.DataFrame(rows, index=index)
    dependency_available = bool(pta.is_available())

    outputs: dict[str, object] = {}
    telemetry: list[dict[str, object]] = []
    for indicator_id in indicator_ids:
        started = time.perf_counter()
        status = "computed"
        error: str | None = None
        payload: Any = None
        try:
            payload = compute_selected(df, [indicator_id]).get(indicator_id)
            if payload in ({}, [], None):
                status = "no_signal" if dependency_available else "dependency_unavailable"
        except Exception as exc:  # pragma: no cover - exact optional dependency failures vary by machine.
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        if status in {"computed", "no_signal"}:
            outputs[indicator_id] = payload or []
        telemetry.append(
            {
                "indicator_id": indicator_id,
                "status": status,
                "latency_ms": latency_ms,
                "output_present": indicator_id in outputs,
                "event_count": len(payload) if isinstance(payload, list) else 0,
                "used_for_9c_vector": False,
                "used_for_probability": False,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "error": error,
            }
        )
    return outputs, telemetry, {
        "dependency": "pandas_ta_classic",
        "dependency_available": dependency_available,
        "compute_source": "vendor.stock_app.shared.indicators.pta_signal_markers",
    }


def _telemetry_row(
    *,
    indicator_id: str,
    status: str,
    latency_ms: float,
    output_present: bool,
    error: str | None,
    cache_hit: bool,
    source_latency_ms: float,
    evidence: dict[str, object] | IndicatorEvidence,
    dataframe_build_count: int,
) -> dict[str, object]:
    evidence_dict = asdict(evidence) if isinstance(evidence, IndicatorEvidence) else deepcopy(evidence)
    canonical_runtime_status = status
    legacy_status = _legacy_runtime_status(
        status,
        canonical_route=bool(
            evidence_dict.get("source_snapshot_hash")
            or evidence_dict.get("source_timeframe")
        ),
    )
    return {
        "indicator_id": indicator_id,
        # ``status`` is a compatibility projection for pre-M3.1 callers. The
        # canonical Decision Spine consumes ``canonical_status`` / ``evidence``.
        # This prevents an old REST telemetry enum from forcing loss of the new
        # epistemic distinctions.
        "status": legacy_status,
        "canonical_runtime_status": canonical_runtime_status,
        "canonical_status": evidence_dict.get("status"),
        "latency_ms": round(latency_ms, 3),
        "source_latency_ms": round(source_latency_ms, 3),
        "output_present": output_present,
        "used_for_9c_vector": output_present,
        "used_for_probability": False,
        "cache_hit": cache_hit,
        "cache_version": REAL_INDICATOR_CACHE_VERSION,
        "error": error,
        "indicator_family": evidence_dict.get("family"),
        "dependency_family": evidence_dict.get("dependency_family"),
        "correlation_group": evidence_dict.get("correlation_group"),
        "warmup_complete": evidence_dict.get("warmup_complete"),
        "calculation_version": INDICATOR_EVIDENCE_VERSION,
        "evidence_hash": evidence_dict.get("evidence_hash"),
        "evidence": evidence_dict,
        "runtime_audit": {
            "indicator_dataframe_build_count": dataframe_build_count,
        },
    }


def _legacy_runtime_status(status: str, *, canonical_route: bool) -> str:
    """Project new epistemic states onto the pre-M3.1 lowercase enum only.

    Canonical callers always carry D2 provenance and therefore receive the
    richer lowercase runtime state unchanged. Legacy callers without D2
    provenance retain the old REST/runtime vocabulary while the nested
    ``IndicatorEvidence.status`` remains fully typed and lossless.
    """

    if canonical_route:
        return status
    if status in {"no_signal", "insufficient_warmup", "dependency_unavailable", "unsupported"}:
        return "no_output"
    return status


def _make_evidence(
    *,
    indicator_id: str,
    metadata: IndicatorMetadata,
    payload: object | None,
    canonical_status: str,
    reason_code: str | None,
    reason: str | None,
    warmup_complete: bool,
    source_window_hash: str,
    source_snapshot_hash: str | None,
    source_timeframe: str | None,
    sample_size: int,
    parameter_hash: str,
) -> dict[str, object]:
    normalized = _normalize_payload(payload)
    output_present = canonical_status == "COMPUTED" and payload not in ({}, [], None)
    quality = _quality_for_status(canonical_status, reason_code)
    output_hash = _stable_hash(payload) if output_present else None
    deterministic = {
        "indicator_id": indicator_id,
        "family": metadata.family,
        "dependency_family": metadata.dependency_family,
        "correlation_group": metadata.correlation_group,
        "value": normalized["value"] if output_present else None,
        "direction": normalized["direction"] if output_present else "unknown",
        "strength": normalized["strength"] if output_present else None,
        "quality": quality,
        "warmup_complete": warmup_complete,
        "warmup_required_bars": metadata.warmup_required_bars,
        "output_present": output_present,
        "status": canonical_status,
        "reason_code": reason_code,
        "reason": reason,
        "source_window_hash": source_window_hash,
        "source_snapshot_hash": source_snapshot_hash,
        "source_timeframe": source_timeframe,
        "sample_size": sample_size,
        "parameter_hash": parameter_hash,
        "output_hash": output_hash,
        "calculation_version": INDICATOR_EVIDENCE_VERSION,
        "used_for_probability": False,
        "may_set_final_band": False,
        "may_execute": False,
    }
    evidence_hash = _stable_hash(deterministic)
    evidence = IndicatorEvidence(
        indicator_id=indicator_id,
        family=metadata.family,
        dependency_family=metadata.dependency_family,
        correlation_group=metadata.correlation_group,
        value=deterministic["value"],
        direction=str(deterministic["direction"]),
        strength=deterministic["strength"],  # type: ignore[arg-type]
        quality=quality,
        warmup_complete=warmup_complete,
        warmup_required_bars=metadata.warmup_required_bars,
        output_present=output_present,
        status=canonical_status,
        reason_code=reason_code,
        reason=reason,
        source_window_hash=source_window_hash,
        source_snapshot_hash=source_snapshot_hash,
        source_timeframe=source_timeframe,
        sample_size=sample_size,
        parameter_hash=parameter_hash,
        output_hash=output_hash,
        evidence_hash=evidence_hash,
    )
    return asdict(evidence)


def _indicator_metadata(indicator_id: str, registry_meta: object | None) -> IndicatorMetadata:
    raw_category = str(getattr(registry_meta, "category", "other") or "other").strip().lower()
    visual_type = str(getattr(registry_meta, "visual_type", "unknown") or "unknown").strip().lower()
    family = _canonical_family(raw_category, indicator_id)
    dependency = _dependency_family(indicator_id, family)
    correlation = _correlation_group(indicator_id, family)
    warmup = _warmup_required_bars(indicator_id, registry_meta)
    return IndicatorMetadata(
        family=family,
        dependency_family=dependency,
        correlation_group=correlation,
        visual_type=visual_type,
        warmup_required_bars=warmup,
    )


def _canonical_family(raw_category: str, indicator_id: str) -> str:
    category = raw_category.replace("_", "-")
    if "pattern" in category or "candle" in category:
        return "pattern"
    if "trend" in category:
        return "trend"
    if "momentum" in category or "osc" in category:
        return "momentum"
    if "volatil" in category or "range" in category:
        return "volatility"
    if "volume" in category or "flow" in category:
        return "volume"
    if "structure" in category or "smart" in category or "liquid" in category:
        return "structure"
    if "level" in category or "pivot" in category or "support" in category:
        return "levels"

    lowered = indicator_id.lower()
    if "rsi" in lowered or "macd" in lowered or "osc" in lowered:
        return "momentum"
    if any(token in lowered for token in ("vwap", "pivot", "pivt", "cpr", "fib")):
        return "levels"
    if any(token in lowered for token in ("bos", "choch", "liq", "sweep", "fvg", "_ob", "swing", "sfp")):
        return "structure"
    if any(token in lowered for token in ("trend", "ichi", "super", "_ma_")):
        return "trend"
    if any(token in lowered for token in ("bb", "range", "impulse")):
        return "volatility"
    return "other"


def _dependency_family(indicator_id: str, family: str) -> str:
    lowered = indicator_id.lower()
    if any(token in lowered for token in ("vwap", "liq", "flow", "mp_va", "volume")):
        return "ohlcv-volume"
    if any(token in lowered for token in ("cpr", "pivot", "pivt", "hourly", "wekly", "fib")):
        return "session-ohlc"
    if family in {"volume"}:
        return "ohlcv-volume"
    return "ohlc-price"


def _correlation_group(indicator_id: str, family: str) -> str:
    lowered = indicator_id.lower()
    if "rsi" in lowered:
        return "momentum-rsi"
    if "macd" in lowered:
        return "momentum-macd"
    if any(token in lowered for token in ("_ma_", "trend_sig", "ichi", "super")):
        return "trend-moving-average"
    if "vwap" in lowered:
        return "levels-vwap"
    if any(token in lowered for token in ("cpr", "pivot", "pivt", "fib")):
        return "levels-pivot"
    if any(token in lowered for token in ("bos", "choch", "swing", "fvg", "_ob", "liq", "sweep", "sfp")):
        return "structure-liquidity"
    if family == "pattern":
        return "price-candle-pattern"
    if "range" in lowered or "bb" in lowered:
        return "volatility-range"
    # Unknown relationships are kept separate rather than falsely asserting
    # independence or correlation.
    return f"indicator:{indicator_id}"


def _warmup_required_bars(indicator_id: str, registry_meta: object | None) -> int:
    candidates = [GENERIC_VENDOR_WARMUP_BARS]
    defaults = getattr(registry_meta, "default_params", {}) or {}
    if isinstance(defaults, Mapping):
        for key, value in defaults.items():
            key_l = str(key).lower()
            if not any(
                token in key_l
                for token in ("len", "length", "period", "window", "lookback", "bars", "slow", "fast")
            ):
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                numeric = int(value)
                if 2 <= numeric <= 400:
                    candidates.append(numeric)
    for token in re.findall(r"\d+", indicator_id):
        numeric = int(token)
        if 20 <= numeric <= 400:
            candidates.append(numeric)
    return max(candidates)


def _dependency_unavailable(metadata: IndicatorMetadata, candles: list[dict[str, object]]) -> bool:
    if metadata.dependency_family != "ohlcv-volume":
        return False
    for candle in candles:
        volume = candle.get("volume")
        if volume is None or isinstance(volume, bool):
            return True
        try:
            numeric = float(volume)
        except (TypeError, ValueError):
            return True
        if not math.isfinite(numeric) or numeric <= 0.0:
            return True
    return False


def _normalize_payload(payload: object | None) -> dict[str, object | None]:
    direction = "unknown"
    value: object | None = None
    strength: float | None = None

    if isinstance(payload, list):
        latest = next((item for item in reversed(payload) if isinstance(item, Mapping)), None)
        if latest is not None:
            direction = _normalize_direction(latest.get("direction"))
            value = _small_scalar(latest.get("value"))
            strength = _normalize_strength(latest.get("strength") or latest.get("confidence") or latest.get("score"))
    elif isinstance(payload, Mapping):
        direction = _normalize_direction(
            payload.get("direction")
            or payload.get("bias")
            or payload.get("trend")
            or payload.get("signal")
            or payload.get("state")
        )
        strength = _normalize_strength(
            payload.get("strength") or payload.get("confidence") or payload.get("score")
        )
        for key in ("value", "last", "current", "rsi", "macd", "histogram", "score"):
            candidate = _small_scalar(payload.get(key))
            if candidate is not None:
                value = candidate
                break
        if direction == "unknown" and isinstance(payload.get("signals"), list):
            signals = payload.get("signals") or []
            latest = next((item for item in reversed(signals) if isinstance(item, Mapping)), None)
            if latest is not None:
                direction = _normalize_direction(latest.get("direction"))
                if value is None:
                    value = _small_scalar(latest.get("value"))
                if strength is None:
                    strength = _normalize_strength(
                        latest.get("strength") or latest.get("confidence") or latest.get("score")
                    )
    else:
        value = _small_scalar(payload)

    return {"value": value, "direction": direction, "strength": strength}


def _small_scalar(value: object | None) -> object | None:
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        numeric = float(value)
        return round(numeric, 8) if math.isfinite(numeric) else None
    text = str(value)
    return text[:64] if len(text) <= 64 else None


def _normalize_direction(value: object | None) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip().lower().replace("_", "-")
    bullish = {"bull", "bullish", "buy", "long", "up", "positive", "+1", "1"}
    bearish = {"bear", "bearish", "sell", "short", "down", "negative", "-1"}
    neutral = {"neutral", "flat", "sideways", "none", "0"}
    if text in bullish:
        return "bullish"
    if text in bearish:
        return "bearish"
    if text in neutral:
        return "neutral"
    return "unknown"


def _normalize_strength(value: object | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    if 0.0 <= numeric <= 1.0:
        return round(numeric, 6)
    if 0.0 <= numeric <= 100.0:
        return round(numeric / 100.0, 6)
    return None


def _quality_for_status(status: str, reason_code: str | None) -> str:
    if status == "COMPUTED" and reason_code == "LATENCY_WARNING":
        return "WARN"
    if status == "COMPUTED":
        return "GOOD"
    if status == "NO_SIGNAL":
        return "NO_SIGNAL"
    if status == "NO_OUTPUT":
        return "NO_OUTPUT"
    if status == "INSUFFICIENT_WARMUP":
        return "WARMUP_INCOMPLETE"
    if status in {"DEPENDENCY_UNAVAILABLE", "SLOW_BLOCKED", "UNSUPPORTED"}:
        return "UNAVAILABLE"
    return "ERROR"


def _indicator_cache_key(candle_hash: str, indicator_id: str, parameter_hash: str) -> tuple[str, str, str, str]:
    return (INDICATOR_EVIDENCE_VERSION, candle_hash, indicator_id, parameter_hash)


def _get_cached_indicator(key: tuple[str, str, str, str]) -> dict[str, Any] | None:
    if key not in _REAL_INDICATOR_CACHE:
        return None
    cached = _REAL_INDICATOR_CACHE.pop(key)
    _REAL_INDICATOR_CACHE[key] = cached
    return deepcopy(cached)


def _set_cached_indicator(key: tuple[str, str, str, str], payload: dict[str, Any]) -> None:
    _REAL_INDICATOR_CACHE[key] = deepcopy(payload)
    while len(_REAL_INDICATOR_CACHE) > REAL_INDICATOR_CACHE_MAX_ENTRIES:
        _REAL_INDICATOR_CACHE.popitem(last=False)


def _candles_hash(candles: list[dict[str, object]]) -> str:
    stable = [
        {
            "event_time": candle.get("event_time"),
            "open": candle.get("open"),
            "high": candle.get("high"),
            "low": candle.get("low"),
            "close": candle.get("close"),
            "volume": candle.get("volume"),
        }
        for candle in candles
    ]
    return _stable_hash(stable)


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
