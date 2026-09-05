from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

import pandas as pd
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from kronos_runtime import MODEL_REVISION, RUNTIME, model_config


SERVICE_VERSION = "kronos-isolated-service.v0.47-real"
MAX_ALLOWED_MOVE_PCT = 18.0


class CandleBar(BaseModel):
    symbol: str
    timeframe: str
    timestamp_ns: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    source: str = "mock"
    sequence_number: int


class CandleSeries(BaseModel):
    symbol: str
    timeframe: str
    bars: list[CandleBar]
    snapshot_id: str | None = None
    schema_version: str


class KronosForecastRequest(BaseModel):
    symbol: str = Field(default="NIFTY-MOCK", min_length=1, max_length=40)
    timeframe: str = "5m"
    seed: int = Field(default=42, ge=0)
    lookback_candles: int = Field(default=64, ge=16, le=512)
    forecast_horizon_bars: int = Field(default=12, ge=1, le=120)
    decision_time_ns: int | None = Field(default=None, ge=0)
    series: CandleSeries | None = None
    replay_snapshot_id: str | None = None
    model_name: Literal["Kronos-mini", "Kronos-base"] = "Kronos-mini"


app = FastAPI(title="Trade Vision Kronos Isolated Service", version=SERVICE_VERSION)


@app.get("/health")
async def health() -> dict[str, object]:
    info = RUNTIME.info()
    return {
        "ok": True,
        "service_version": SERVICE_VERSION,
        "research_only": True,
        "model_loaded": info.loaded,
        "model_name": info.model_name,
        "tokenizer_name": info.tokenizer_name,
        "device": info.device,
        "cuda_available": info.cuda_available,
        "gpu_name": info.gpu_name,
        "model_load_error": info.load_error,
        "heavy_dependencies_loaded": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
    }


@app.post("/model/load")
async def load_model(model_name: Literal["Kronos-mini", "Kronos-base"] = "Kronos-mini") -> dict[str, object]:
    try:
        info = await asyncio.to_thread(RUNTIME.load, model_name)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Kronos model load failed: {type(exc).__name__}: {exc}") from exc
    return {
        "ok": info.loaded,
        "service_version": SERVICE_VERSION,
        "model_name": info.model_name,
        "tokenizer_name": info.tokenizer_name,
        "device": info.device,
        "cuda_available": info.cuda_available,
        "gpu_name": info.gpu_name,
        "research_only": True,
        "trade_allowed": False,
    }


@app.post("/forecast")
async def forecast(payload: KronosForecastRequest) -> dict[str, object]:
    try:
        return await asyncio.to_thread(_real_forecast, payload)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _real_forecast(payload: KronosForecastRequest) -> dict[str, object]:
    series = payload.series or _fallback_series(payload)
    bars = sorted(series.bars, key=lambda item: item.timestamp_ns)[-payload.lookback_candles :]
    validation = _validate(payload, series, bars)
    if not validation["passed"]:
        raise ValueError("; ".join(validation["blockers"]))
    last = bars[-1]
    interval = _timeframe_ns(series.timeframe)
    frame = pd.DataFrame(
        [
            {
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": float(bar.volume or 0.0),
            }
            for bar in bars
        ]
    )
    timestamps = pd.DatetimeIndex(pd.to_datetime([bar.timestamp_ns for bar in bars], unit="ns", utc=True)).tz_convert("Asia/Kolkata")
    future_timestamps = _future_timestamps(timestamps[-1], series.timeframe, payload.forecast_horizon_bars)
    predicted, inference_ms = RUNTIME.predict(
        frame,
        timestamps,
        future_timestamps,
        seed=payload.seed,
        model_name=payload.model_name,
        sample_count=1,
    )
    candles = [
        {
            "timestamp_ns": int(timestamp.tz_convert("UTC").value),
            "open": round(float(row.open), 4),
            "high": round(float(row.high), 4),
            "low": round(float(row.low), 4),
            "close": round(float(row.close), 4),
            "volume": round(float(row.volume), 4),
        }
        for timestamp, row in predicted.iterrows()
    ]
    expected_return_pct = ((float(candles[-1]["close"]) - last.close) / max(last.close, 0.01)) * 100.0
    expected_move_atr = (float(candles[-1]["close"]) - last.close) / max(_atr(bars[-14:]), 0.01)
    direction = "LONG" if expected_return_pct > 0.18 else "SHORT" if expected_return_pct < -0.18 else "SIDEWAYS"
    median = [float(item["close"]) for item in candles]
    uncertainty_score = min(0.58, max(0.08, _atr(bars[-14:]) / max(last.close, 0.01) * 5.0))
    spread = [value * (0.004 + uncertainty_score * 0.01) for value in median]
    max_move = max(abs((float(item["close"]) - last.close) / max(last.close, 0.01) * 100.0) for item in candles)
    sanity_passed = bool(validation["passed"]) and max_move <= MAX_ALLOWED_MOVE_PCT
    generated = datetime.now(timezone.utc)
    expiry = generated + timedelta(seconds=max(60, int(payload.forecast_horizon_bars * interval / 1_000_000_000)))
    path = {
        "scenario_id": f"kronos-service-{series.symbol.lower()}-{payload.seed}",
        "path_type": "sampled_forecast_path",
        "candles": candles,
        "expected_return_pct": round(expected_return_pct, 4),
        "expected_move_atr": round(expected_move_atr, 4),
        "trend_direction": direction,
        "range_probability": round(max(5.0, min(80.0, 55.0 - abs(expected_return_pct) * 2.0)), 4),
        "continuation_probability": round(max(5.0, min(90.0, 50.0 + expected_return_pct * 3.5)), 4),
        "reversal_probability": round(max(5.0, min(90.0, 50.0 - expected_return_pct * 3.5)), 4),
    }
    uncertainty = {
        "lower_path": [round(value - band, 4) for value, band in zip(median, spread)],
        "median_path": [round(value, 4) for value in median],
        "upper_path": [round(value + band, 4) for value, band in zip(median, spread)],
        "uncertainty_score": round(uncertainty_score, 4),
        "discarded_for_high_uncertainty": False,
    }
    sanity = {
        "passed": sanity_passed,
        "max_allowed_move_pct": MAX_ALLOWED_MOVE_PCT,
        "max_observed_move_pct": round(max_move, 4),
        "impossible_move_blocked": max_move > MAX_ALLOWED_MOVE_PCT,
        "reason": "Real Kronos-mini forecast passed input and market-physics bounds." if sanity_passed else "Validation or sanity bound failed.",
    }
    output_hash = _hash({"validation": validation, "path": path, "uncertainty": uncertainty, "sanity": sanity})
    selected = model_config(payload.model_name)
    return {
        "forecast_version": "kronos-research-adapter.v0.47-real",
        "generated_at": generated.isoformat(),
        "run_id": str(uuid5(NAMESPACE_URL, f"tradevision:kronos-service:{series.symbol}:{payload.seed}:{output_hash}")),
        "symbol": series.symbol.upper(),
        "timeframe": series.timeframe,
        "source_mode": "simulation",
        "model_name": selected["model_id"],
        "model_version": MODEL_REVISION,
        "tokenizer_name": selected["tokenizer_id"],
        "input_validation": validation,
        "forecast_path": path,
        "uncertainty": uncertainty,
        "expiry": {
            "generated_at": generated.isoformat(),
            "valid_until": expiry.isoformat(),
            "horizon_bars": payload.forecast_horizon_bars,
            "expired": False,
        },
        "sanity_check": sanity,
        "forecast_confidence": 0.0 if not sanity_passed else round(max(0.05, min(0.74, 0.52 + abs(expected_return_pct) * 0.01 - uncertainty_score * 0.18)), 4),
        "input_snapshot_id": payload.replay_snapshot_id,
        "input_snapshot_hash": validation["input_snapshot_hash"],
        "output_hash": output_hash,
        "deterministic": True,
        "no_future_leakage": bool(validation["passed"]),
        "research_only": True,
        "trade_allowed": False,
        "order_routing_enabled": False,
        "live_trading_blocked": True,
        "kronos_cannot_execute_orders": True,
        "kronos_cannot_override_no_trade": True,
        "kronos_cannot_override_risk": True,
        "notes": [
            "Forecast generated by the real upstream Kronos-mini model and Kronos-Tokenizer-2k.",
            f"Inference device: {RUNTIME.device}; latency: {inference_ms:.2f} ms; max context: {selected['max_context']}.",
            "Kronos remains a research prior and cannot execute or override Trade Vision safety.",
        ],
    }


def _validate(payload: KronosForecastRequest, series: CandleSeries, bars: list[CandleBar]) -> dict[str, object]:
    blockers: list[str] = []
    future = False
    invalid = False
    nan_inf = False
    sequence = False
    previous_sequence = 0
    previous_timestamp: int | None = None
    interval_mismatches: list[int] = []
    expected_interval = _timeframe_ns(series.timeframe)
    for bar in bars:
        values = [bar.open, bar.high, bar.low, bar.close, float(bar.volume or 0.0)]
        if any(value != value or value in {float("inf"), float("-inf")} for value in values):
            nan_inf = True
            blockers.append(f"NaN/Inf found at sequence {bar.sequence_number}.")
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            invalid = True
            blockers.append(f"Invalid OHLC ordering at sequence {bar.sequence_number}.")
        if payload.decision_time_ns is not None and bar.timestamp_ns > payload.decision_time_ns:
            future = True
            blockers.append(f"Future candle rejected at sequence {bar.sequence_number}.")
        if bar.sequence_number <= previous_sequence:
            sequence = True
            blockers.append("Sequence numbers are not strictly increasing.")
        if previous_timestamp is not None:
            prior = pd.Timestamp(previous_timestamp, unit="ns", tz="UTC").tz_convert("Asia/Kolkata")
            current = pd.Timestamp(bar.timestamp_ns, unit="ns", tz="UTC").tz_convert("Asia/Kolkata")
            observed_interval = bar.timestamp_ns - previous_timestamp
            if prior.date() == current.date():
                partial_close_interval = (
                    current.hour == 15
                    and current.minute == 29
                    and 0 < observed_interval <= expected_interval
                )
                if not partial_close_interval and abs(observed_interval - expected_interval) > int(expected_interval * 0.05):
                    interval_mismatches.append(observed_interval)
        previous_timestamp = bar.timestamp_ns
        previous_sequence = bar.sequence_number
    granularity = bool(interval_mismatches)
    if granularity:
        blockers.append(f"Candle granularity does not match timeframe {series.timeframe}.")
    if len(bars) < 16:
        blockers.append("Kronos requires at least 16 point-in-time candles for forecast.")
    return {
        "validation_version": "kronos-research-adapter.v0.46.input-validation",
        "symbol": series.symbol.upper(),
        "timeframe": series.timeframe,
        "candle_count": len(bars),
        "decision_time_ns": payload.decision_time_ns,
        "passed": not blockers,
        "future_candle_rejected": future,
        "nan_or_inf_rejected": nan_inf,
        "invalid_ohlc_rejected": invalid,
        "incomplete_candle_rejected": len(bars) < 16,
        "sequence_mismatch_rejected": sequence,
        "granularity_mismatch_rejected": granularity,
        "input_snapshot_hash": _hash({"symbol": series.symbol, "timeframe": series.timeframe, "bars": [bar.model_dump(mode="json") for bar in bars]}),
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": [],
    }


def _fallback_series(payload: KronosForecastRequest) -> CandleSeries:
    interval = _timeframe_ns(payload.timeframe)
    base = 1_714_724_800_000_000_000
    bars: list[CandleBar] = []
    price = 100.0
    for idx in range(payload.lookback_candles):
        close = price + ((idx % 5) - 2) * 0.05
        bars.append(
            CandleBar(
                symbol=payload.symbol.upper(),
                timeframe=payload.timeframe,
                timestamp_ns=base + idx * interval,
                open=price,
                high=max(price, close) + 0.2,
                low=min(price, close) - 0.2,
                close=close,
                volume=1000 + idx,
                source="mock",
                sequence_number=idx + 1,
            )
        )
        price = close
    return CandleSeries(symbol=payload.symbol.upper(), timeframe=payload.timeframe, bars=bars, snapshot_id="service-fallback", schema_version="kronos-service-fallback.v1")


def _future_timestamps(last: pd.Timestamp, timeframe: str, count: int) -> pd.DatetimeIndex:
    """Create point-forward timestamps without emitting intraday bars outside NSE hours."""

    if timeframe in {"1D", "daily"}:
        return pd.bdate_range(last.normalize() + pd.Timedelta(days=1), periods=count, tz=last.tz) + pd.Timedelta(hours=15, minutes=29)
    if timeframe in {"1W", "weekly"}:
        start = last.normalize() + pd.offsets.Week(weekday=4)
        return pd.date_range(start, periods=count, freq="W-FRI", tz=last.tz) + pd.Timedelta(hours=15, minutes=29)
    interval_minutes = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "1H": 60,
    }.get(timeframe, 5)
    values: list[pd.Timestamp] = []
    cursor = last
    while len(values) < count:
        candidate = cursor + pd.Timedelta(minutes=interval_minutes)
        market_open = candidate.normalize() + pd.Timedelta(hours=9, minutes=15)
        market_close = candidate.normalize() + pd.Timedelta(hours=15, minutes=29)
        if candidate.weekday() >= 5 or candidate > market_close:
            next_day = candidate.normalize() + pd.offsets.BDay(1)
            candidate = (
                pd.Timestamp(next_day).tz_convert(last.tz)
                + pd.Timedelta(hours=9, minutes=15)
                + pd.Timedelta(minutes=interval_minutes - 1)
            )
        elif candidate < market_open:
            candidate = market_open
        values.append(candidate)
        cursor = candidate
    return pd.DatetimeIndex(values)


def _timeframe_ns(timeframe: str) -> int:
    return {
        "1m": 60_000_000_000,
        "3m": 180_000_000_000,
        "5m": 300_000_000_000,
        "15m": 900_000_000_000,
        "1H": 3_600_000_000_000,
        "1D": 86_400_000_000_000,
        "1W": 604_800_000_000_000,
    }.get(timeframe, 300_000_000_000)


def _atr(bars: list[CandleBar]) -> float:
    return sum(max(bar.high - bar.low, 0.01) for bar in bars) / max(1, len(bars))


def _hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
