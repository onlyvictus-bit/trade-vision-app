"""
research.signals.trend — Trend-following signals (8 signals)
=============================================================
EMA cross, Supertrend, Parabolic SAR, ADX trend.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import register_signal


# ── helpers ───────────────────────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _supertrend_loop(close: np.ndarray, upper: np.ndarray, lower: np.ndarray, period: int):
    """Core Supertrend recurrence on raw NumPy arrays — ~15x faster than pandas .iloc."""
    n = len(close)
    st = np.full(n, np.nan)
    direction = np.ones(n, dtype=np.int8)
    if period >= n:
        return st, direction
    st[period] = upper[period]
    direction[period] = -1
    for i in range(period + 1, n):
        prev_st = st[i - 1]
        prev_dir = direction[i - 1]
        if prev_dir == 1:
            curr_lower = max(lower[i], prev_st) if close[i - 1] > prev_st else lower[i]
            if close[i] < curr_lower:
                st[i] = upper[i]
                direction[i] = -1
            else:
                st[i] = curr_lower
                direction[i] = 1
        else:
            curr_upper = min(upper[i], prev_st) if close[i - 1] < prev_st else upper[i]
            if close[i] > curr_upper:
                st[i] = lower[i]
                direction[i] = 1
            else:
                st[i] = curr_upper
                direction[i] = -1
    return st, direction


# Optional Numba JIT — extra 5-10x on top of the NumPy speedup
try:
    import numba as _numba
    _supertrend_loop = _numba.njit(cache=True)(_supertrend_loop)
except Exception:
    pass  # Numba not installed — NumPy loop is still ~15x faster than pandas .iloc


def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """Returns (supertrend_line, direction) where direction=1 means bullish."""
    hl2 = (df["high"] + df["low"]) / 2
    atr = (df["high"] - df["low"]).rolling(period).mean()
    upper_s = hl2 + multiplier * atr
    lower_s = hl2 - multiplier * atr

    st_arr, dir_arr = _supertrend_loop(
        df["close"].values,
        upper_s.values,
        lower_s.values,
        period,
    )
    return (
        pd.Series(st_arr, index=df.index),
        pd.Series(dir_arr.astype(int), index=df.index),
    )


def _psar_loop(high: np.ndarray, low: np.ndarray, af_start: float, af_step: float, af_max: float):
    """Core PSAR recurrence on raw NumPy arrays — JIT-compilable."""
    n = len(high)
    psar = np.full(n, np.nan)
    direction = np.ones(n)
    af = af_start
    ep = low[0]
    psar[0] = high[0]
    direction[0] = -1.0

    for i in range(1, n):
        prev_psar = psar[i - 1]
        prev_dir = direction[i - 1]

        if prev_dir == 1:  # bullish
            psar[i] = prev_psar + af * (ep - prev_psar)
            lo_prev2 = low[i - 2] if i >= 2 else low[0]
            psar[i] = min(psar[i], low[i - 1], lo_prev2)
            if low[i] < psar[i]:
                direction[i] = -1.0
                psar[i] = ep
                af = af_start
                ep = low[i]
            else:
                direction[i] = 1.0
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:  # bearish
            psar[i] = prev_psar + af * (ep - prev_psar)
            hi_prev2 = high[i - 2] if i >= 2 else high[0]
            psar[i] = max(psar[i], high[i - 1], hi_prev2)
            if high[i] > psar[i]:
                direction[i] = 1.0
                psar[i] = ep
                af = af_start
                ep = high[i]
            else:
                direction[i] = -1.0
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)

    return psar, direction


# Optional Numba JIT for PSAR — same pattern as Supertrend
try:
    import numba as _numba
    _psar_loop = _numba.njit(cache=True)(_psar_loop)
except Exception:
    pass  # NumPy loop still fast enough


def _psar(df: pd.DataFrame, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2):
    """Parabolic SAR. Returns (psar_series, direction) where 1=bullish."""
    high = df["high"].values
    low = df["low"].values
    n = len(high)
    if n == 0:
        return pd.Series(dtype=float, index=df.index), pd.Series(dtype=float, index=df.index)

    psar_arr, dir_arr = _psar_loop(high, low, af_start, af_step, af_max)
    return pd.Series(psar_arr, index=df.index), pd.Series(dir_arr, index=df.index)


# ── EMA Cross ─────────────────────────────────────────────────────────────

@register_signal(
    name="ema_cross_bull",
    category="trend",
    direction="bullish",
    params={"fast": 9, "slow": 21},
    param_grid={"fast": [5, 9, 12], "slow": [15, 21, 30, 50]},
    tags=["crossover", "trend-following"],
)
def _ema_cross_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    fast = _ema(df["close"], p["fast"])
    slow = _ema(df["close"], p["slow"])
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))


@register_signal(
    name="ema_cross_bear",
    category="trend",
    direction="bearish",
    params={"fast": 9, "slow": 21},
    param_grid={"fast": [5, 9, 12], "slow": [15, 21, 30, 50]},
    tags=["crossover", "trend-following"],
)
def _ema_cross_bear(df: pd.DataFrame, p: dict) -> pd.Series:
    fast = _ema(df["close"], p["fast"])
    slow = _ema(df["close"], p["slow"])
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))


# ── Supertrend ────────────────────────────────────────────────────────────

@register_signal(
    name="supertrend_bull",
    category="trend",
    direction="bullish",
    params={"period": 10, "multiplier": 3.0},
    param_grid={"period": [7, 10, 14], "multiplier": [2.0, 3.0, 4.0]},
    tags=["supertrend", "trend-following"],
)
def _supertrend_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    _, direction = _supertrend(df, p["period"], p["multiplier"])
    return (direction == 1) & (direction.shift(1) == -1)


@register_signal(
    name="supertrend_bear",
    category="trend",
    direction="bearish",
    params={"period": 10, "multiplier": 3.0},
    param_grid={"period": [7, 10, 14], "multiplier": [2.0, 3.0, 4.0]},
    tags=["supertrend", "trend-following"],
)
def _supertrend_bear(df: pd.DataFrame, p: dict) -> pd.Series:
    _, direction = _supertrend(df, p["period"], p["multiplier"])
    return (direction == -1) & (direction.shift(1) == 1)


# ── Parabolic SAR ─────────────────────────────────────────────────────────

@register_signal(
    name="psar_bull",
    category="trend",
    direction="bullish",
    params={"af_start": 0.02, "af_step": 0.02, "af_max": 0.2},
    param_grid={"af_start": [0.01, 0.02, 0.03]},
    tags=["psar", "trend-following"],
)
def _psar_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    _, direction = _psar(df, p["af_start"], p["af_step"], p["af_max"])
    return (direction == 1) & (direction.shift(1) == -1)


@register_signal(
    name="psar_bear",
    category="trend",
    direction="bearish",
    params={"af_start": 0.02, "af_step": 0.02, "af_max": 0.2},
    param_grid={"af_start": [0.01, 0.02, 0.03]},
    tags=["psar", "trend-following"],
)
def _psar_bear(df: pd.DataFrame, p: dict) -> pd.Series:
    _, direction = _psar(df, p["af_start"], p["af_step"], p["af_max"])
    return (direction == -1) & (direction.shift(1) == 1)


# ── ADX Trend ─────────────────────────────────────────────────────────────

def _adx_components(df: pd.DataFrame, period: int = 14):
    """Returns (adx, plus_di, minus_di)."""
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx, plus_di, minus_di


@register_signal(
    name="adx_trend_bull",
    category="trend",
    direction="bullish",
    params={"period": 14, "adx_thresh": 25},
    param_grid={"period": [10, 14, 20], "adx_thresh": [20, 25, 30]},
    tags=["adx", "trend-strength"],
)
def _adx_trend_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    adx, plus_di, minus_di = _adx_components(df, p["period"])
    thresh = p["adx_thresh"]
    return (adx > thresh) & (adx.shift(1) <= thresh) & (plus_di > minus_di)


# ── Multi-Timeframe Trend Filter ──────────────────────────────────────────

@register_signal(
    name="ema_filter_bull_mtf",
    category="trend",
    direction="bullish",
    params={"period": 200, "tf": "1d"},
    param_grid={"period": [50, 100, 200]},
    tags=["mtf", "trend-filter"],
)
def _ema_filter_bull_mtf(df: pd.DataFrame, p: dict, context_dfs: dict | None = None) -> pd.Series:
    """True if close is above higher-timeframe EMA."""
    tf = p.get("tf", "1d")
    if not context_dfs or tf not in context_dfs:
        # Fallback to current TF if context not available
        target_df = df
    else:
        target_df = context_dfs[tf]
    
    ema = _ema(target_df["close"], p["period"])
    # Aligned target_df has same index as df
    return df["close"] > ema


@register_signal(
    name="ema_filter_bear_mtf",
    category="trend",
    direction="bearish",
    params={"period": 200, "tf": "1d"},
    param_grid={"period": [50, 100, 200]},
    tags=["mtf", "trend-filter"],
)
def _ema_filter_bear_mtf(df: pd.DataFrame, p: dict, context_dfs: dict | None = None) -> pd.Series:
    """True if close is below higher-timeframe EMA."""
    tf = p.get("tf", "1d")
    if not context_dfs or tf not in context_dfs:
        target_df = df
    else:
        target_df = context_dfs[tf]
    
    ema = _ema(target_df["close"], p["period"])
    return df["close"] < ema
