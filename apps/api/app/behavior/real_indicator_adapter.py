from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from copy import deepcopy
from typing import Any


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
REAL_INDICATOR_CACHE_MAX_ENTRIES = 256
_REAL_INDICATOR_CACHE: OrderedDict[tuple[str, str], dict[str, Any]] = OrderedDict()


def compute_real_indicator_outputs_with_telemetry(
    candles: list[dict[str, object]],
    indicator_ids: list[str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    import pandas as pd
    from app.vendor.stock_app.shared.indicators.self_indc import compute_selected

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

    outputs: dict[str, object] = {}
    telemetry: list[dict[str, object]] = []
    for indicator_id in indicator_ids:
        cached = _get_cached_indicator(candle_hash, indicator_id)
        if cached is not None:
            payload = deepcopy(cached["payload"])
            status = str(cached["status"])
            error = cached.get("error")
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
                )
            )
            continue

        started = time.perf_counter()
        status = "computed"
        error: str | None = None
        payload: Any = None
        try:
            payload = compute_selected(df, [indicator_id]).get(indicator_id)
            if payload in ({}, [], None):
                status = "no_output"
        except Exception as exc:  # pragma: no cover - exact optional dependency failures vary by machine.
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        if status == "computed" and latency_ms > PER_INDICATOR_LATENCY_BLOCK_MS:
            status = "slow_blocked"
        elif status == "computed" and latency_ms > PER_INDICATOR_LATENCY_WARN_MS:
            status = "slow_warn"
        if status in {"computed", "slow_warn"}:
            outputs[indicator_id] = payload
        _set_cached_indicator(
            candle_hash,
            indicator_id,
            {
                "payload": deepcopy(payload),
                "status": status,
                "error": error,
                "latency_ms": latency_ms,
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
            )
        )
    return outputs, telemetry


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
) -> dict[str, object]:
    return {
        "indicator_id": indicator_id,
        "status": status,
        "latency_ms": round(latency_ms, 3),
        "source_latency_ms": round(source_latency_ms, 3),
        "output_present": output_present,
        "used_for_9c_vector": output_present,
        "cache_hit": cache_hit,
        "cache_version": REAL_INDICATOR_CACHE_VERSION,
        "error": error,
    }


def _get_cached_indicator(candle_hash: str, indicator_id: str) -> dict[str, Any] | None:
    key = (candle_hash, indicator_id)
    if key not in _REAL_INDICATOR_CACHE:
        return None
    cached = _REAL_INDICATOR_CACHE.pop(key)
    _REAL_INDICATOR_CACHE[key] = cached
    return deepcopy(cached)


def _set_cached_indicator(candle_hash: str, indicator_id: str, payload: dict[str, Any]) -> None:
    key = (candle_hash, indicator_id)
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
    return hashlib.sha256(json.dumps(stable, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
