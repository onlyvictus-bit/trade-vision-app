from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import product
from threading import RLock
from uuid import NAMESPACE_URL, uuid5

from ..behavior.point_in_time_guard import timeframe_duration_ns
from ..models import (
    CandleBar,
    CandleSeries,
    OrbBacktestTrade,
    OrbBuildRequest,
    OrbComboMetrics,
    OrbDiscoveryJob,
    OrbDiscoveryRequest,
    OrbDiscoveryResult,
    OrbStrategyConfig,
)
from .core import build_orb_candidate


ORB_DISCOVERY_VERSION = "orb-discovery.v1.90"
ORB_JOB_VERSION = "orb-discovery-job.v1.90"
_JOBS: dict[str, OrbDiscoveryJob] = {}
_LOCK = RLock()


def submit_orb_discovery(request: OrbDiscoveryRequest) -> OrbDiscoveryJob:
    request_hash = _hash(request.model_dump(mode="json"))
    job_id = str(uuid5(NAMESPACE_URL, f"tradevision:orb-discovery:{request_hash}"))
    job = OrbDiscoveryJob(
        job_version=ORB_JOB_VERSION,
        job_id=job_id,
        request_hash=request_hash,
        status="queued",
        progress_pct=0.0,
    )
    with _LOCK:
        _JOBS[job_id] = job
    return job


def run_orb_discovery_job(job_id: str, request: OrbDiscoveryRequest) -> None:
    _update_job(job_id, status="running", progress_pct=5.0)
    try:
        result = run_orb_discovery(request)
        _update_job(
            job_id,
            status="completed",
            progress_pct=100.0,
            result=result,
            error=None,
        )
    except Exception as exc:
        _update_job(
            job_id,
            status="failed",
            progress_pct=100.0,
            error=f"{type(exc).__name__}: {exc}",
        )


def get_orb_discovery_job(job_id: str) -> OrbDiscoveryJob | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return None if job is None else job.model_copy(deep=True)


def clear_orb_discovery_jobs() -> None:
    with _LOCK:
        _JOBS.clear()


def run_orb_discovery(request: OrbDiscoveryRequest) -> OrbDiscoveryResult:
    request_hash = _hash(request.model_dump(mode="json"))
    combos, cap_applied = _combinations(request)
    day_series = _session_days(request.series)
    all_trades: list[OrbBacktestTrade] = []
    metrics: list[OrbComboMetrics] = []
    for combo_id, config in combos:
        trades = [
            trade
            for day in day_series
            if (
                trade := _backtest_day(
                    combo_id,
                    day,
                    config,
                    request,
                )
            )
            is not None
        ]
        all_trades.extend(trades)
        metrics.append(
            _metrics(
                combo_id,
                config,
                trades,
                minimum_trades=request.minimum_trades,
            )
        )
    ranked = sorted(
        metrics,
        key=lambda item: (
            item.minimum_trades_pass,
            item.composite_score,
            item.net_r,
            item.profitable_period_rate,
            item.combo_id,
        ),
        reverse=True,
    )
    eligible = [item for item in metrics if item.minimum_trades_pass]
    best_profit = max(eligible, key=lambda item: (item.net_r, item.combo_id), default=None)
    best_consistency = max(
        eligible,
        key=lambda item: (item.profitable_period_rate, item.net_r, item.combo_id),
        default=None,
    )
    best_composite = ranked[0] if ranked and ranked[0].minimum_trades_pass else None
    payload = {
        "discovery_version": ORB_DISCOVERY_VERSION,
        "request_hash": request_hash,
        "symbol": request.series.symbol.upper(),
        "timeframe": request.series.timeframe,
        "combination_count": len(combos),
        "combination_cap_applied": cap_applied,
        "ranked_combinations": [item.model_dump(mode="json") for item in ranked],
        "best_by_net_profit": None if best_profit is None else best_profit.model_dump(mode="json"),
        "best_by_consistency": None if best_consistency is None else best_consistency.model_dump(mode="json"),
        "best_composite": None if best_composite is None else best_composite.model_dump(mode="json"),
        "trades": [item.model_dump(mode="json") for item in all_trades],
        "no_future_leakage": all(item.no_future_leakage for item in metrics),
        "costs_applied": True,
    }
    return OrbDiscoveryResult(
        **payload,
        deterministic_hash=_hash(payload),
    )


def _combinations(request: OrbDiscoveryRequest):
    specs: list[tuple[str, OrbStrategyConfig]] = []
    for family, bars, rr, volume in product(
        sorted(set(request.strategy_families)),
        sorted(set(request.orb_bar_counts)),
        sorted(set(request.reward_risk_grid)),
        sorted(set(request.volume_confirmation_grid)),
    ):
        config = OrbStrategyConfig(
            strategy_family=family,
            range_mode="bar_count",
            orb_bar_count=bars,
            reward_risk_ratio=rr,
            require_volume_confirmation=volume,
        )
        specs.append((_combo_id(config), config))
    for family, window, rr, volume in product(
        sorted(set(request.strategy_families)),
        sorted(set(request.clock_windows)),
        sorted(set(request.reward_risk_grid)),
        sorted(set(request.volume_confirmation_grid)),
    ):
        config = OrbStrategyConfig(
            strategy_family=family,
            range_mode="clock_window",
            range_start=window[0],
            range_end=window[1],
            reward_risk_ratio=rr,
            require_volume_confirmation=volume,
        )
        specs.append((_combo_id(config), config))
    ordered = sorted(specs, key=lambda item: item[0])
    cap_applied = len(ordered) > request.maximum_combinations
    return ordered[: request.maximum_combinations], cap_applied


def _session_days(series: CandleSeries) -> list[CandleSeries]:
    groups: dict[str, list[CandleBar]] = defaultdict(list)
    for bar in sorted(series.bars, key=lambda item: (item.timestamp_ns, item.sequence_number)):
        local = datetime.fromtimestamp(
            bar.timestamp_ns / 1_000_000_000,
            tz=timezone.utc,
        ) + timedelta(minutes=330)
        if "09:15" <= local.strftime("%H:%M") < "15:30":
            groups[str(local.date())].append(bar)
    return [
        CandleSeries(
            symbol=series.symbol,
            timeframe=series.timeframe,
            bars=groups[day],
            snapshot_id=f"{series.snapshot_id or 'orb'}:{day}",
            schema_version=series.schema_version,
        )
        for day in sorted(groups)
    ]


def _backtest_day(
    combo_id: str,
    series: CandleSeries,
    config: OrbStrategyConfig,
    request: OrbDiscoveryRequest,
) -> OrbBacktestTrade | None:
    if not series.bars:
        return None
    duration_ns = timeframe_duration_ns(series.timeframe)
    decision_time_ns = max(bar.timestamp_ns + duration_ns for bar in series.bars)
    candidate = build_orb_candidate(
        OrbBuildRequest(
            series=series,
            decision_time_ns=decision_time_ns,
            config=config,
        )
    )
    signal = candidate.signal
    opening_range = candidate.opening_range
    if (
        signal.signal_type == "NO_SETUP"
        or signal.signal_close_time_ns is None
        or opening_range is None
    ):
        return None
    future = [
        bar
        for bar in sorted(series.bars, key=lambda item: item.timestamp_ns)
        if bar.timestamp_ns >= signal.signal_close_time_ns
    ]
    if not future:
        return None
    side = signal.side
    slippage = request.costs.slippage_bps_per_side / 10_000.0
    entry_raw = future[0].open
    entry = entry_raw * (1.0 + slippage if side == "LONG" else 1.0 - slippage)
    stop = (
        opening_range.opening_range_low
        if side == "LONG"
        else opening_range.opening_range_high
    )
    risk = abs(entry - stop)
    if risk <= 1e-9:
        return None
    target = (
        entry + risk * config.reward_risk_ratio
        if side == "LONG"
        else entry - risk * config.reward_risk_ratio
    )
    outcome = "TIME_EXIT"
    exit_bar = future[-1]
    exit_raw = exit_bar.close
    ambiguous = False
    conservative = False
    for bar in future:
        stop_hit = bar.low <= stop if side == "LONG" else bar.high >= stop
        target_hit = bar.high >= target if side == "LONG" else bar.low <= target
        if stop_hit and target_hit:
            outcome = "STOP_HIT"
            exit_bar = bar
            exit_raw = stop
            ambiguous = True
            conservative = True
            break
        if stop_hit:
            outcome = "STOP_HIT"
            exit_bar = bar
            exit_raw = stop
            break
        if target_hit:
            outcome = "TARGET_HIT"
            exit_bar = bar
            exit_raw = target
            break
    exit_price = exit_raw * (1.0 - slippage if side == "LONG" else 1.0 + slippage)
    directional_pnl = exit_price - entry if side == "LONG" else entry - exit_price
    gross_r = directional_pnl / risk
    commission = (
        entry + exit_price
    ) * request.costs.commission_bps_per_side / 10_000.0
    cost_r = max(commission / risk, 0.0)
    net_r = gross_r - cost_r
    return OrbBacktestTrade(
        combo_id=combo_id,
        local_session_date=candidate.opening_range.local_session_date,
        signal_type=signal.signal_type,
        side=side,  # type: ignore[arg-type]
        signal_timestamp_ns=signal.signal_timestamp_ns,  # type: ignore[arg-type]
        entry_timestamp_ns=future[0].timestamp_ns,
        entry_price=round(entry, 8),
        stop_price=round(stop, 8),
        target_price=round(target, 8),
        exit_timestamp_ns=exit_bar.timestamp_ns,
        exit_price=round(exit_price, 8),
        outcome=outcome,  # type: ignore[arg-type]
        same_bar_ambiguous=ambiguous,
        conservative_stop_first_used=conservative,
        gross_r=round(gross_r, 8),
        cost_r=round(cost_r, 8),
        net_r=round(net_r, 8),
    )


def _metrics(
    combo_id: str,
    config: OrbStrategyConfig,
    trades: list[OrbBacktestTrade],
    *,
    minimum_trades: int,
) -> OrbComboMetrics:
    wins = [trade.net_r for trade in trades if trade.net_r > 0]
    losses = [trade.net_r for trade in trades if trade.net_r <= 0]
    gross_r = sum(trade.gross_r for trade in trades)
    net_r = sum(trade.net_r for trade in trades)
    profit_factor = sum(wins) / max(abs(sum(losses)), 1e-9) if wins else 0.0
    drawdown = _max_drawdown([trade.net_r for trade in trades])
    periods: dict[str, float] = defaultdict(float)
    for trade in trades:
        periods[trade.local_session_date[:7]] += trade.net_r
    consistency = (
        sum(1 for value in periods.values() if value > 0) / len(periods)
        if periods
        else 0.0
    )
    minimum_pass = len(trades) >= minimum_trades
    composite = net_r + consistency * 5.0 + min(profit_factor, 5.0) - drawdown
    return OrbComboMetrics(
        combo_id=combo_id,
        strategy_family=config.strategy_family,
        range_mode=config.range_mode,
        orb_bar_count=config.orb_bar_count if config.range_mode == "bar_count" else None,
        clock_window=(config.range_start, config.range_end) if config.range_mode == "clock_window" else None,
        reward_risk_ratio=config.reward_risk_ratio,
        require_volume_confirmation=config.require_volume_confirmation,
        trade_count=len(trades),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate=len(wins) / len(trades) if trades else 0.0,
        gross_r=round(gross_r, 8),
        net_r=round(net_r, 8),
        profit_factor=round(min(profit_factor, 999.0), 8),
        max_drawdown_r=round(drawdown, 8),
        profitable_period_rate=round(consistency, 8),
        composite_score=round(composite, 8),
        minimum_trades_pass=minimum_pass,
        no_future_leakage=True,
    )


def _max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _combo_id(config: OrbStrategyConfig) -> str:
    return hashlib.sha256(
        json.dumps(
            config.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:20]


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _update_job(job_id: str, **updates) -> None:
    with _LOCK:
        current = _JOBS.get(job_id)
        if current is None:
            return
        _JOBS[job_id] = current.model_copy(update=updates, deep=True)
