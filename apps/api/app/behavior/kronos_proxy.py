from __future__ import annotations

import hashlib
import json
import math
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid5

from ..models import (
    CandleBar,
    CandleSeries,
    KronosBacktestRequest,
    KronosBacktestResult,
    KronosForecastPath,
    KronosForecastRequest,
    KronosForecastResult,
    KronosForecastSanityCheck,
    KronosInputValidation,
    KronosMetrics,
    KronosModelInfo,
    KronosRuntimeStatus,
    KronosServiceBridgeStatus,
    ForecastExpiryMeta,
    ForecastUncertaintyMap,
    now_iso,
)
from ..state import PROJECT_ROOT


KRONOS_VERSION = "kronos-research-adapter.v0.46"
KRONOS_BRIDGE_VERSION = "kronos-service-bridge.v0.46"
EXTERNAL_KRONOS_PATH = PROJECT_ROOT / "external" / "kronos"
KRONOS_SERVICE_PATH = PROJECT_ROOT / "apps" / "kronos-service"
KRONOS_MINI_PATH = KRONOS_SERVICE_PATH / "models" / "Kronos-mini" / "model.safetensors"
KRONOS_TOKENIZER_PATH = KRONOS_SERVICE_PATH / "models" / "Kronos-Tokenizer-2k" / "model.safetensors"
KRONOS_BASE_PATH = KRONOS_SERVICE_PATH / "models" / "Kronos-base" / "model.safetensors"
KRONOS_BASE_TOKENIZER_PATH = KRONOS_SERVICE_PATH / "models" / "Kronos-Tokenizer-base" / "model.safetensors"
MAX_ALLOWED_MOVE_PCT = 18.0
DEFAULT_KRONOS_SERVICE_TIMEOUT_MS = 15_000


def build_kronos_status() -> KronosRuntimeStatus:
    repo_present = (EXTERNAL_KRONOS_PATH / ".git").exists() or (EXTERNAL_KRONOS_PATH / "model").exists() or (EXTERNAL_KRONOS_PATH / "kronos").exists()
    service_present = (KRONOS_SERVICE_PATH / "pyproject.toml").exists() or (KRONOS_SERVICE_PATH / "app.py").exists() or (KRONOS_SERVICE_PATH / "main.py").exists()
    model_present = KRONOS_MINI_PATH.exists() and KRONOS_TOKENIZER_PATH.exists()
    return KronosRuntimeStatus(
        kronos_version=KRONOS_VERSION,
        service_status="ready" if repo_present and service_present and model_present else "mock_ready" if service_present else "reserved",
        repo_path=str(EXTERNAL_KRONOS_PATH),
        repo_present=repo_present,
        service_path=str(KRONOS_SERVICE_PATH),
        service_present=service_present,
        mode="real" if model_present else "mock",
        selected_model="Kronos-mini" if model_present else "none",
        model_policy={
            "Kronos-mini": "first real adapter target",
            "Kronos-small": "optional after mini is stable",
            "Kronos-base": "installed challenger model; use only after timeframe-specific validation",
            "Kronos-large": "excluded because it is not open-source in the upstream README",
        },
        dependency_isolated=True,
        api_imports_heavy_ml=False,
        research_only=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "Kronos is isolated from the main FastAPI process.",
            "Real Kronos-mini and Kronos-base artifacts are installed locally." if model_present and KRONOS_BASE_PATH.exists() else "Real Kronos-mini is installed locally." if model_present else "Real model artifacts are not installed; mock fallback remains active.",
            "No PyTorch, qlib, Transformers, or Kronos imports are required in apps/api.",
        ],
    )


def build_kronos_service_bridge_status(
    *,
    service_url: str | None = None,
    timeout_ms: int = DEFAULT_KRONOS_SERVICE_TIMEOUT_MS,
    check_health: bool = True,
) -> KronosServiceBridgeStatus:
    resolved_url = _service_url(service_url)
    service_present = _service_present()
    if not resolved_url:
        return KronosServiceBridgeStatus(
            bridge_version=KRONOS_BRIDGE_VERSION,
            generated_at=now_iso(),
            service_url=None,
            service_configured=False,
            service_present=service_present,
            health_checked=False,
            health_ok=False,
            service_status="mock_ready" if service_present else "reserved",
            timeout_ms=timeout_ms,
            fallback_to_mock=True,
            fallback_reason="TRADEVISION_KRONOS_SERVICE_URL is not configured; using deterministic mock forecast.",
            notes=[
                "The isolated service skeleton exists, but the main API will not call it until a service URL is explicitly configured.",
                "This prevents accidental model loading inside the main API process.",
            ],
        )
    if not check_health:
        return KronosServiceBridgeStatus(
            bridge_version=KRONOS_BRIDGE_VERSION,
            generated_at=now_iso(),
            service_url=resolved_url,
            service_configured=True,
            service_present=service_present,
            health_checked=False,
            health_ok=False,
            service_status="unavailable",
            timeout_ms=timeout_ms,
            fallback_to_mock=True,
            fallback_reason="Health check skipped; bridge remains conservative.",
            notes=["Bridge status was requested without a live health probe."],
        )
    try:
        payload = _http_json("GET", f"{resolved_url}/health", timeout_ms=timeout_ms)
        ok = bool(payload.get("ok")) and bool(payload.get("research_only", True))
        return KronosServiceBridgeStatus(
            bridge_version=KRONOS_BRIDGE_VERSION,
            generated_at=now_iso(),
            service_url=resolved_url,
            service_configured=True,
            service_present=service_present,
            health_checked=True,
            health_ok=ok,
            service_status="ready" if ok else "error",
            timeout_ms=timeout_ms,
            fallback_to_mock=not ok,
            fallback_reason="Service health passed." if ok else "Service health did not prove research-only readiness.",
            notes=[
                "Health probes never grant order-routing permission.",
                "A failed probe causes deterministic mock fallback.",
            ],
        )
    except TimeoutError:
        return _bridge_error_status(resolved_url, service_present, timeout_ms, "timeout", "Kronos service health timed out; using deterministic mock fallback.")
    except (OSError, HTTPError, URLError, ValueError) as exc:
        return _bridge_error_status(resolved_url, service_present, timeout_ms, "error", f"Kronos service health failed: {type(exc).__name__}; using deterministic mock fallback.")


def kronos_models() -> list[KronosModelInfo]:
    return [
        KronosModelInfo(model_name="Kronos-mini", status="available" if KRONOS_MINI_PATH.exists() and KRONOS_TOKENIZER_PATH.exists() else "reserved", tokenizer_name="Kronos-Tokenizer-2k", allowed_for_first_real_adapter=True, reason="Installed local model used by the isolated research service."),
        KronosModelInfo(model_name="Kronos-small", status="reserved", tokenizer_name="Kronos-Tokenizer-base", allowed_for_first_real_adapter=False, reason="Optional after mini is stable."),
        KronosModelInfo(model_name="Kronos-base", status="available" if KRONOS_BASE_PATH.exists() and KRONOS_BASE_TOKENIZER_PATH.exists() else "reserved", tokenizer_name="Kronos-Tokenizer-base", allowed_for_first_real_adapter=False, reason="Installed challenger model for replay and walk-forward comparison; not automatic authority."),
        KronosModelInfo(model_name="Kronos-large", status="excluded", tokenizer_name=None, allowed_for_first_real_adapter=False, reason="Excluded because it is not open-source in the upstream README."),
    ]


def build_kronos_metrics() -> KronosMetrics:
    status = build_kronos_status()
    bridge = build_kronos_service_bridge_status(check_health=False)
    return KronosMetrics(
        metrics_version=f"{KRONOS_VERSION}.metrics",
        generated_at=now_iso(),
        service_status=status.service_status,
        inference_latency_ms=0.0,
        timeout_count=0,
        oom_count=0,
        forecast_count=0,
        service_latency_below_budget=True,
        api_imports_heavy_ml=False,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        notes=[
            "Metrics are mock/reserved until the isolated Kronos service is started and explicitly configured.",
            f"Bridge fallback reason: {bridge.fallback_reason}",
        ],
    )


def build_kronos_backtest_result(request: KronosBacktestRequest) -> KronosBacktestResult:
    scores: list[float] = []
    sanity: list[float] = []
    for idx in range(request.scenario_count):
        series = _synthetic_series(request.symbol, request.timeframe, request.seed + idx, 64)
        forecast = build_mock_kronos_forecast(
            KronosForecastRequest(
                symbol=request.symbol,
                timeframe=request.timeframe,
                seed=request.seed + idx,
                lookback_candles=64,
                forecast_horizon_bars=8,
            ),
            series,
        )
        scores.append(1.0 if forecast.forecast_path.trend_direction in {"LONG", "SHORT", "SIDEWAYS"} else 0.0)
        sanity.append(1.0 if forecast.sanity_check.passed else 0.0)
    avg_score = sum(scores) / len(scores)
    avg_sanity = sum(sanity) / len(sanity)
    payload = {"symbol": request.symbol.upper(), "seed": request.seed, "scenario_count": request.scenario_count, "score": avg_score, "sanity": avg_sanity}
    evidence_hash = _hash(payload)
    return KronosBacktestResult(
        backtest_version=f"{KRONOS_VERSION}.backtest",
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:kronos-backtest:{request.symbol}:{request.seed}:{evidence_hash}")),
        symbol=request.symbol.upper(),
        timeframe=request.timeframe,
        scenario_count=request.scenario_count,
        deterministic=True,
        average_direction_score=round(avg_score, 4),
        average_sanity_pass_rate=round(avg_sanity, 4),
        promotion_allowed=False,
        blockers=[
            "Kronos backtest is mock/replay evidence only.",
            "Real promotion requires isolated service, Indian market validation, OOS validation, and paper testing.",
        ],
        evidence_hash=evidence_hash,
        valid_until=None,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        kronos_cannot_execute_orders=True,
        kronos_cannot_override_no_trade=True,
        kronos_cannot_override_risk=True,
        notes=[
            "This deterministic backtest shell compares mock Kronos scenarios only.",
            "It intentionally cannot promote Kronos to execution authority.",
        ],
    )


def validate_kronos_input(request: KronosForecastRequest, series: CandleSeries) -> KronosInputValidation:
    blockers: list[str] = []
    warnings: list[str] = []
    future = False
    nan_inf = False
    invalid_ohlc = False
    incomplete = False
    sequence_mismatch = False
    granularity_mismatch = False

    sorted_bars = sorted(series.bars, key=lambda bar: bar.timestamp_ns)
    previous_timestamp: int | None = None
    previous_sequence = 0
    intervals: list[int] = []
    decision_time = request.decision_time_ns
    for bar in sorted_bars:
        values = [bar.open, bar.high, bar.low, bar.close, float(bar.volume)]
        if any(math.isnan(value) or math.isinf(value) for value in values):
            nan_inf = True
            blockers.append(f"NaN/Inf found at sequence {bar.sequence_number}.")
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            invalid_ohlc = True
            blockers.append(f"Invalid OHLC ordering at sequence {bar.sequence_number}.")
        if decision_time is not None and bar.timestamp_ns > decision_time:
            future = True
            blockers.append(f"Future candle rejected at sequence {bar.sequence_number}.")
        if bar.sequence_number <= previous_sequence:
            sequence_mismatch = True
            blockers.append("Sequence numbers are not strictly increasing.")
        if previous_timestamp is not None:
            interval = bar.timestamp_ns - previous_timestamp
            intervals.append(interval)
            if interval <= 0:
                sequence_mismatch = True
                blockers.append("Candle timestamps are not strictly increasing.")
        previous_timestamp = bar.timestamp_ns
        previous_sequence = bar.sequence_number
    if len(sorted_bars) < 16:
        incomplete = True
        blockers.append("Kronos requires at least 16 point-in-time candles for mock forecast.")
    if intervals:
        expected = _timeframe_ns(series.timeframe)
        if expected and any(abs(interval - expected) > max(1, int(expected * 0.05)) for interval in intervals):
            granularity_mismatch = True
            blockers.append(f"Candle granularity does not match timeframe {series.timeframe}.")
    if len(series.bars) > request.lookback_candles:
        warnings.append("Input series exceeds requested lookback; newest lookback window will be used.")

    snapshot_hash = _hash({"symbol": series.symbol, "timeframe": series.timeframe, "bars": [bar.model_dump(mode="json") for bar in sorted_bars]})
    return KronosInputValidation(
        validation_version=f"{KRONOS_VERSION}.input-validation",
        symbol=series.symbol,
        timeframe=series.timeframe,
        candle_count=len(series.bars),
        decision_time_ns=decision_time,
        passed=not blockers,
        future_candle_rejected=future,
        nan_or_inf_rejected=nan_inf,
        invalid_ohlc_rejected=invalid_ohlc,
        incomplete_candle_rejected=incomplete,
        sequence_mismatch_rejected=sequence_mismatch,
        granularity_mismatch_rejected=granularity_mismatch,
        input_snapshot_hash=snapshot_hash,
        blockers=list(dict.fromkeys(blockers)),
        warnings=warnings,
    )


def build_mock_kronos_forecast(request: KronosForecastRequest, fallback_series: CandleSeries) -> KronosForecastResult:
    series = request.series or fallback_series
    validation = validate_kronos_input(request, series)
    bars = sorted(series.bars, key=lambda bar: bar.timestamp_ns)[-request.lookback_candles :]
    last = bars[-1]
    rng = random.Random(f"kronos:{series.symbol}:{series.timeframe}:{request.seed}:{validation.input_snapshot_hash}")
    path_candles: list[dict[str, float | int]] = []
    price = last.close
    interval = _timeframe_ns(series.timeframe) or 60_000_000_000
    drift = rng.uniform(-0.12, 0.18)
    volatility = max(0.0025, min(0.018, _atr_proxy(bars[-14:]) / max(price, 0.01)))
    for idx in range(request.forecast_horizon_bars):
        open_price = price
        shock = rng.uniform(-volatility, volatility) + drift / 100.0
        close = max(0.01, open_price * (1 + shock))
        high = max(open_price, close) * (1 + rng.uniform(0.0, volatility * 0.4))
        low = min(open_price, close) * (1 - rng.uniform(0.0, volatility * 0.4))
        path_candles.append(
            {
                "timestamp_ns": last.timestamp_ns + (idx + 1) * interval,
                "open": round(open_price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": float(max(1, int(last.volume * (1 + rng.uniform(-0.12, 0.18))))),
            }
        )
        price = close
    first_close = last.close
    final_close = float(path_candles[-1]["close"])
    expected_return_pct = ((final_close - first_close) / max(first_close, 0.01)) * 100.0
    expected_move_atr = (final_close - first_close) / max(_atr_proxy(bars[-14:]), 0.01)
    direction = "LONG" if expected_return_pct > 0.18 else "SHORT" if expected_return_pct < -0.18 else "SIDEWAYS"
    continuation = max(5.0, min(90.0, 50.0 + expected_return_pct * 4.0))
    reversal = max(5.0, min(90.0, 50.0 - expected_return_pct * 4.0))
    range_prob = max(5.0, min(80.0, 55.0 - abs(expected_return_pct) * 2.5))
    uncertainty_score = max(0.05, min(0.95, volatility * 12.0))
    median = [float(item["close"]) for item in path_candles]
    band = [max(0.01, value * (0.004 + uncertainty_score * 0.018)) for value in median]
    uncertainty = ForecastUncertaintyMap(
        lower_path=[round(value - spread, 4) for value, spread in zip(median, band)],
        median_path=[round(value, 4) for value in median],
        upper_path=[round(value + spread, 4) for value, spread in zip(median, band)],
        uncertainty_score=round(uncertainty_score, 4),
        discarded_for_high_uncertainty=uncertainty_score > 0.78,
    )
    max_move = max(abs((float(item["close"]) - first_close) / max(first_close, 0.01) * 100.0) for item in path_candles)
    sanity = KronosForecastSanityCheck(
        passed=max_move <= MAX_ALLOWED_MOVE_PCT and validation.passed,
        max_allowed_move_pct=MAX_ALLOWED_MOVE_PCT,
        max_observed_move_pct=round(max_move, 4),
        impossible_move_blocked=max_move > MAX_ALLOWED_MOVE_PCT,
        reason="Mock forecast path is bounded and point-in-time checked." if max_move <= MAX_ALLOWED_MOVE_PCT and validation.passed else "Forecast blocked by validation or sanity bounds.",
    )
    expiry = _expiry(request.forecast_horizon_bars, interval)
    path = KronosForecastPath(
        scenario_id=f"kronos-mock-{series.symbol.lower()}-{request.seed}",
        path_type="sampled_forecast_path",
        candles=path_candles,
        expected_return_pct=round(expected_return_pct, 4),
        expected_move_atr=round(expected_move_atr, 4),
        trend_direction=direction,  # type: ignore[arg-type]
        range_probability=round(range_prob, 4),
        continuation_probability=round(continuation, 4),
        reversal_probability=round(reversal, 4),
    )
    payload = {
        "validation": validation.model_dump(mode="json"),
        "path": path.model_dump(mode="json"),
        "uncertainty": uncertainty.model_dump(mode="json"),
        "sanity": sanity.model_dump(mode="json"),
        "expiry": {"horizon_bars": expiry.horizon_bars, "expired": expiry.expired},
    }
    output_hash = _hash(payload)
    return KronosForecastResult(
        forecast_version=KRONOS_VERSION,
        generated_at=now_iso(),
        run_id=str(uuid5(NAMESPACE_URL, f"tradevision:kronos:{series.symbol}:{series.timeframe}:{request.seed}:{output_hash}")),
        symbol=series.symbol,
        timeframe=series.timeframe,
        source_mode="mock",
        model_name="Kronos-mock",
        model_version="kronos.mock.v0.45",
        tokenizer_name="mock-tokenizer",
        input_validation=validation,
        forecast_path=path,
        uncertainty=uncertainty,
        expiry=expiry,
        sanity_check=sanity,
        forecast_confidence=round(0.0 if not sanity.passed or uncertainty.discarded_for_high_uncertainty else max(0.05, min(0.82, 0.62 - uncertainty_score * 0.25 + abs(expected_return_pct) * 0.01)), 4),
        input_snapshot_id=request.replay_snapshot_id,
        input_snapshot_hash=validation.input_snapshot_hash,
        output_hash=output_hash,
        deterministic=True,
        no_future_leakage=validation.passed,
        research_only=True,
        trade_allowed=False,
        order_routing_enabled=False,
        live_trading_blocked=True,
        kronos_cannot_execute_orders=True,
        kronos_cannot_override_no_trade=True,
        kronos_cannot_override_risk=True,
        notes=[
            "This is a deterministic mock Kronos forecast for contract, UI, and guard validation.",
            "It is a research forecast path, not execution permission.",
            "Real Kronos inference belongs in apps/kronos-service, not apps/api.",
        ],
    )


def build_kronos_forecast_with_optional_service(
    request: KronosForecastRequest,
    fallback_series: CandleSeries,
    *,
    service_url: str | None = None,
    timeout_ms: int = DEFAULT_KRONOS_SERVICE_TIMEOUT_MS,
) -> KronosForecastResult:
    series = request.series or fallback_series
    validation = validate_kronos_input(request, series)
    if not validation.passed:
        forecast = build_mock_kronos_forecast(request, fallback_series)
        return forecast.model_copy(
            update={
                "notes": forecast.notes + ["v0.46 bridge skipped service call because input validation failed."],
                "input_validation": validation,
            }
        )
    resolved_url = _service_url(service_url)
    if not resolved_url:
        forecast = build_mock_kronos_forecast(request, fallback_series)
        return forecast.model_copy(update={"notes": forecast.notes + ["v0.46 bridge used mock fallback because no service URL is configured."]})
    service_request = request.model_copy(update={"series": series})
    try:
        payload = _http_json(
            "POST",
            f"{resolved_url}/forecast",
            body=service_request.model_dump(mode="json"),
            timeout_ms=timeout_ms,
        )
        forecast = KronosForecastResult.model_validate(payload)
        safe_forecast = forecast.model_copy(
            update={
                "source_mode": "simulation" if forecast.source_mode == "live" else forecast.source_mode,
                "research_only": True,
                "trade_allowed": False,
                "order_routing_enabled": False,
                "live_trading_blocked": True,
                "kronos_cannot_execute_orders": True,
                "kronos_cannot_override_no_trade": True,
                "kronos_cannot_override_risk": True,
                "notes": forecast.notes + ["v0.46 bridge received isolated Kronos service output and re-applied Trade Vision safety locks."],
            }
        )
        return safe_forecast
    except TimeoutError:
        reason = "v0.46 bridge timeout; deterministic mock fallback used."
    except (OSError, HTTPError, URLError, ValueError) as exc:
        reason = f"v0.46 bridge service failure ({type(exc).__name__}); deterministic mock fallback used."
    forecast = build_mock_kronos_forecast(request, fallback_series)
    return forecast.model_copy(update={"notes": forecast.notes + [reason]})


def _timeframe_ns(timeframe: str) -> int | None:
    mapping = {
        "1m": 60_000_000_000,
        "3m": 180_000_000_000,
        "5m": 300_000_000_000,
        "15m": 900_000_000_000,
        "1H": 3_600_000_000_000,
        "1D": 86_400_000_000_000,
        "1W": 604_800_000_000_000,
    }
    return mapping.get(timeframe)


def _synthetic_series(symbol: str, timeframe: str, seed: int, bars: int) -> CandleSeries:
    rng = random.Random(f"kronos-backtest:{symbol}:{timeframe}:{seed}")
    interval = _timeframe_ns(timeframe) or 300_000_000_000
    base = 1_714_724_800_000_000_000
    price = 100.0 + rng.uniform(-1.0, 1.0)
    candle_bars: list[CandleBar] = []
    for idx in range(bars):
        open_price = price
        close = max(1.0, open_price + rng.uniform(-0.35, 0.38))
        high = max(open_price, close) + rng.uniform(0.05, 0.55)
        low = min(open_price, close) - rng.uniform(0.05, 0.55)
        candle_bars.append(
            CandleBar(
                symbol=symbol.upper(),
                timeframe=timeframe,  # type: ignore[arg-type]
                timestamp_ns=base + idx * interval,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=1_000 + idx * 11,
                source="mock",
                sequence_number=idx + 1,
            )
        )
        price = close
    return CandleSeries(symbol=symbol.upper(), timeframe=timeframe, bars=candle_bars, snapshot_id=f"kronos-backtest-{seed}", schema_version="candles.kronos.backtest.v1")  # type: ignore[arg-type]


def _atr_proxy(bars: list[CandleBar]) -> float:
    if not bars:
        return 1.0
    return sum(max(bar.high - bar.low, 0.01) for bar in bars) / len(bars)


def _expiry(horizon_bars: int, interval_ns: int) -> ForecastExpiryMeta:
    generated = datetime.now(timezone.utc)
    valid_until = generated + timedelta(seconds=max(60, int((horizon_bars * interval_ns) / 1_000_000_000)))
    return ForecastExpiryMeta(
        generated_at=generated.isoformat(),
        valid_until=valid_until.isoformat(),
        horizon_bars=horizon_bars,
        expired=False,
    )


def _hash(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _service_present() -> bool:
    return (
        (KRONOS_SERVICE_PATH / "pyproject.toml").exists()
        or (KRONOS_SERVICE_PATH / "app.py").exists()
        or (KRONOS_SERVICE_PATH / "main.py").exists()
    )


def _service_url(service_url: str | None = None) -> str | None:
    raw = (service_url or os.getenv("TRADEVISION_KRONOS_SERVICE_URL") or "").strip()
    return raw.rstrip("/") if raw else None


def _bridge_error_status(
    resolved_url: str,
    service_present: bool,
    timeout_ms: int,
    status: str,
    reason: str,
) -> KronosServiceBridgeStatus:
    return KronosServiceBridgeStatus(
        bridge_version=KRONOS_BRIDGE_VERSION,
        generated_at=now_iso(),
        service_url=resolved_url,
        service_configured=True,
        service_present=service_present,
        health_checked=True,
        health_ok=False,
        service_status=status,  # type: ignore[arg-type]
        timeout_ms=timeout_ms,
        fallback_to_mock=True,
        fallback_reason=reason,
        notes=[
            "The main API survived the Kronos service failure.",
            "Forecast endpoints must fall back to deterministic mock output when the service is unhealthy.",
        ],
    )


def _http_json(method: str, url: str, *, body: object | None = None, timeout_ms: int) -> dict[str, object]:
    payload = None if body is None else json.dumps(body, sort_keys=True, default=str).encode("utf-8")
    request = Request(url, data=payload, method=method, headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_ms / 1000.0) as response:  # noqa: S310 - local configured service URL only.
            raw = response.read().decode("utf-8")
    except TimeoutError:
        raise
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Kronos service returned non-object JSON.")
    return parsed
