"""
research.engine.backtester — VectorBT vectorized backtester
=============================================================
Single-pass vectorized backtest using vectorbt.Portfolio.from_signals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Map yfinance interval strings → VectorBT freq aliases
_INTERVAL_TO_FREQ: Dict[str, str] = {
    "1m":  "1min",
    "2m":  "2min",
    "3m":  "3min",
    "5m":  "5min",
    "15m": "15min",
    "30m": "30min",
    "60m": "1h",
    "1h":  "1h",
    "4h":  "4h",
    "90m": "90min",
    "1d":  "1D",
    "5d":  "5D",
    "1wk": "1W",
    "1mo": "1ME",
    "3mo": "3ME",
}


@dataclass
class BacktestResult:
    """Container for single backtest output."""
    trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    profit_factor: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    max_drawdown: float = 0.0
    avg_duration: float = 0.0
    expectancy: float = 0.0
    kelly_fraction: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    trade_log: List[Dict[str, Any]] = field(default_factory=list)


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Convert vectorbt metric to safe float."""
    try:
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _compute_kelly(win_rate: float, profit_factor: float) -> float:
    """Kelly criterion: K = W - (1-W)/R where W=win_rate, R=avg_win/avg_loss."""
    if profit_factor <= 0 or win_rate <= 0:
        return 0.0
    # profit_factor = gross_wins / gross_losses
    # avg_win/avg_loss ≈ profit_factor * (1 - win_rate) / win_rate
    r = profit_factor * (1 - win_rate) / win_rate if win_rate < 1 else profit_factor
    kelly = win_rate - (1 - win_rate) / max(r, 1e-10)
    return max(0.0, min(kelly, 1.0))


def run_vectorbt_backtest(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    sl_pct: float = 0.02,
    tp_pct: float = 0.04,
    commission: float = 0.001,
    slippage: float = 0.0005,
    initial_capital: float = 100_000,
    direction: str = "long",
    interval: str = "1d",
    strict_lag: bool = True,
) -> BacktestResult:
    """
    Run a single vectorized backtest.

    Parameters
    ----------
    df : DataFrame with 'close' column (lowercase).
    entries / exits : boolean Series aligned with df.
    sl_pct / tp_pct : stop-loss / take-profit as fraction (0.02 = 2%).
    commission + slippage : per-side cost assumptions.
    initial_capital : starting cash.
    direction : "long" or "short".
    interval : yfinance interval string ("1m", "5m", "1h", "1d", etc.) used
               to set the VectorBT freq so Sharpe/Sortino annualisation is correct.

    Returns
    -------
    BacktestResult with all 10 KPIs + equity curve + trade log.
    """
    close = df["close"]

    # Ensure entries/exits aligned
    entries = entries.reindex(close.index, fill_value=False).fillna(False).astype(bool)
    exits = exits.reindex(close.index, fill_value=False).fillna(False).astype(bool)
    if strict_lag:
        entries = entries.shift(1).fillna(False).astype(bool)
        exits = exits.shift(1).fillna(False).astype(bool)

    # If no entries at all, return empty result
    if entries.sum() == 0:
        return BacktestResult()

    # Resolve VectorBT freq from interval string (critical for correct Sharpe annualisation)
    vbt_freq = _INTERVAL_TO_FREQ.get(interval.lower(), None)
    if vbt_freq is None:
        # Try to infer from the DatetimeIndex
        try:
            inferred = pd.infer_freq(close.index)
            vbt_freq = inferred or "1D"
        except Exception:
            vbt_freq = "1D"

    try:
        import vectorbt as vbt

        pf = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            sl_stop=sl_pct,
            tp_stop=tp_pct,
            fees=commission,
            slippage=slippage,
            init_cash=initial_capital,
            freq=vbt_freq,
            direction="both" if direction == "short" else "longonly",
        )
    except Exception:
        return BacktestResult()

    # Extract metrics safely
    n_trades = int(_safe_float(pf.trades.count(), 0))
    if n_trades == 0:
        return BacktestResult()

    wr = _safe_float(pf.trades.win_rate())
    pf_ratio = _safe_float(pf.trades.profit_factor(), 0)

    result = BacktestResult(
        trades=n_trades,
        win_rate=wr,
        total_return=_safe_float(pf.total_return()),
        profit_factor=pf_ratio,
        sharpe=_safe_float(pf.sharpe_ratio()),
        sortino=_safe_float(pf.sortino_ratio()),
        calmar=_safe_float(pf.calmar_ratio()),
        max_drawdown=_safe_float(pf.max_drawdown()),
        expectancy=_safe_float(pf.trades.expectancy()),
        kelly_fraction=_compute_kelly(wr, pf_ratio),
    )

    # Equity curve (downsample to ~250 points)
    equity = pf.value()
    if len(equity) > 250:
        step = max(1, len(equity) // 250)
        equity = equity.iloc[::step]
    result.equity_curve = [round(float(v), 2) for v in equity.values]

    # Trade log (first 200 trades)
    try:
        records = pf.trades.records_readable
        if len(records) > 200:
            records = records.head(200)
        result.trade_log = records.to_dict("records")
    except Exception:
        result.trade_log = []

    # Compute avg duration
    try:
        durations = pf.trades.duration
        result.avg_duration = _safe_float(durations.mean())
    except Exception:
        result.avg_duration = 0.0

    return result


def run_vectorbt_backtest_batch(
    df: pd.DataFrame,
    entries_list: List[pd.Series],
    sl_stops: List[float],
    tp_stops: List[float],
    commission: float = 0.001,
    slippage: float = 0.0005,
    initial_capital: float = 100_000,
    direction: str = "long",
    interval: str = "1d",
    strict_lag: bool = True,
) -> List[BacktestResult]:
    """
    Batch version of run_vectorbt_backtest.

    Runs ONE Portfolio.from_signals() call with N columns (one per entry/SL/TP combo)
    instead of N separate calls.  Significantly faster for sweep_params mode where a
    single signal combo has many (param × risk) variants.

    Parameters
    ----------
    entries_list : list of boolean Series, one per variant
    sl_stops / tp_stops : parallel lists of SL/TP fractions for each variant

    Returns
    -------
    List of BacktestResult, same length as entries_list.
    Falls back to individual calls if VectorBT batch call fails.
    """
    n = len(entries_list)
    if n == 0:
        return []
    if n == 1:
        return [run_vectorbt_backtest(
            df, entries_list[0], pd.Series(False, index=df.index),
            sl_pct=sl_stops[0], tp_pct=tp_stops[0],
            commission=commission, slippage=slippage,
            initial_capital=initial_capital, direction=direction,
            interval=interval, strict_lag=strict_lag,
        )]

    close = df["close"]
    vbt_freq = _INTERVAL_TO_FREQ.get(interval.lower(), None)
    if vbt_freq is None:
        try:
            vbt_freq = pd.infer_freq(close.index) or "1D"
        except Exception:
            vbt_freq = "1D"

    # Build entries matrix (n_bars × n_variants) with lag applied
    aligned = []
    for e in entries_list:
        s = e.reindex(close.index, fill_value=False).fillna(False).astype(bool)
        if strict_lag:
            s = s.shift(1).fillna(False).astype(bool)
        aligned.append(s)

    # Skip columns with no entries
    active_idx = [i for i, s in enumerate(aligned) if s.sum() > 0]
    if not active_idx:
        return [BacktestResult()] * n

    active_entries = pd.concat([aligned[i] for i in active_idx], axis=1)
    active_entries.columns = list(range(len(active_idx)))
    active_sl = np.array([sl_stops[i] for i in active_idx])
    active_tp = np.array([tp_stops[i] for i in active_idx])
    exits_mat = pd.DataFrame(False, index=close.index, columns=active_entries.columns)

    try:
        import vectorbt as vbt
        pf = vbt.Portfolio.from_signals(
            close=close,
            entries=active_entries,
            exits=exits_mat,
            sl_stop=active_sl,
            tp_stop=active_tp,
            fees=commission,
            slippage=slippage,
            init_cash=initial_capital,
            freq=vbt_freq,
            direction="both" if direction == "short" else "longonly",
        )
    except Exception:
        # Batch failed — fall back to individual calls
        results = [BacktestResult()] * n
        for orig_i, s_e, sl, tp in zip(active_idx,
                                        [aligned[i] for i in active_idx],
                                        active_sl, active_tp):
            try:
                results[orig_i] = run_vectorbt_backtest(
                    df, s_e, pd.Series(False, index=df.index),
                    sl_pct=float(sl), tp_pct=float(tp),
                    commission=commission, slippage=slippage,
                    initial_capital=initial_capital, direction=direction,
                    interval=interval, strict_lag=False,  # already lagged above
                )
            except Exception:
                pass
        return results

    # Extract per-column metrics
    results: List[BacktestResult] = [BacktestResult()] * n
    for col_pos, orig_i in enumerate(active_idx):
        try:
            col = pf[col_pos] if hasattr(pf, "__getitem__") else pf
            n_trades = int(_safe_float(col.trades.count(), 0))
            if n_trades == 0:
                continue
            wr = _safe_float(col.trades.win_rate())
            pf_ratio = _safe_float(col.trades.profit_factor(), 0)
            r = BacktestResult(
                trades=n_trades,
                win_rate=wr,
                total_return=_safe_float(col.total_return()),
                profit_factor=pf_ratio,
                sharpe=_safe_float(col.sharpe_ratio()),
                sortino=_safe_float(col.sortino_ratio()),
                calmar=_safe_float(col.calmar_ratio()),
                max_drawdown=_safe_float(col.max_drawdown()),
                expectancy=_safe_float(col.trades.expectancy()),
                kelly_fraction=_compute_kelly(wr, pf_ratio),
            )
            equity = col.value()
            if len(equity) > 250:
                equity = equity.iloc[::max(1, len(equity) // 250)]
            r.equity_curve = [round(float(v), 2) for v in equity.values]
            try:
                records = col.trades.records_readable
                r.trade_log = records.head(200).to_dict("records")
            except Exception:
                r.trade_log = []
            try:
                r.avg_duration = _safe_float(col.trades.duration.mean())
            except Exception:
                pass
            results[orig_i] = r
        except Exception:
            pass

    return results
