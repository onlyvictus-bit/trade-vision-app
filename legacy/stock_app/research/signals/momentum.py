"""
research.signals.momentum — Momentum signals (10 signals)
==========================================================
RSI, MACD, Stochastic, CCI, Williams %R.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import register_signal


# ── helpers ───────────────────────────────────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs = gain / loss.replace(0, 1e-10)
    return 100 - 100 / (1 + rs)


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, 1e-10)
    d = k.rolling(d_period).mean()
    return k, d


def _rolling_mad(vals: np.ndarray, period: int) -> np.ndarray:
    """Mean absolute deviation over a rolling window — pure NumPy, no Python callback."""
    n = len(vals)
    result = np.full(n, np.nan)
    for i in range(period - 1, n):
        w = vals[i - period + 1 : i + 1]
        result[i] = np.mean(np.abs(w - np.mean(w)))
    return result


def _cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(period).mean()
    mad = pd.Series(_rolling_mad(tp.values, period), index=tp.index)
    return (tp - sma) / (0.015 * mad).replace(0, 1e-10)


def _williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    return -100 * (high_max - df["close"]) / (high_max - low_min).replace(0, 1e-10)


# ── RSI ───────────────────────────────────────────────────────────────────

@register_signal(
    name="rsi_oversold",
    category="momentum",
    direction="bullish",
    params={"period": 14, "threshold": 30},
    param_grid={"period": [10, 14, 21], "threshold": [25, 30, 35]},
    tags=["rsi", "mean-reversion"],
)
def _rsi_oversold(df: pd.DataFrame, p: dict) -> pd.Series:
    rsi = _rsi(df["close"], p["period"])
    thresh = p["threshold"]
    return (rsi > thresh) & (rsi.shift(1) <= thresh)


@register_signal(
    name="rsi_overbought",
    category="momentum",
    direction="bearish",
    params={"period": 14, "threshold": 70},
    param_grid={"period": [10, 14, 21], "threshold": [65, 70, 75]},
    tags=["rsi", "mean-reversion"],
)
def _rsi_overbought(df: pd.DataFrame, p: dict) -> pd.Series:
    rsi = _rsi(df["close"], p["period"])
    thresh = p["threshold"]
    return (rsi < thresh) & (rsi.shift(1) >= thresh)


@register_signal(
    name="rsi_momentum_bull",
    category="momentum",
    direction="bullish",
    params={"period": 14},
    param_grid={"period": [10, 14, 21]},
    tags=["rsi", "momentum"],
)
def _rsi_momentum_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    rsi = _rsi(df["close"], p["period"])
    return (rsi > 50) & (rsi.shift(1) <= 50)


# ── MACD ──────────────────────────────────────────────────────────────────

@register_signal(
    name="macd_cross_bull",
    category="momentum",
    direction="bullish",
    params={"fast": 12, "slow": 26, "signal": 9},
    param_grid={"fast": [8, 12], "slow": [21, 26], "signal": [7, 9]},
    tags=["macd", "crossover"],
)
def _macd_cross_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    macd_line, signal_line, _ = _macd(df["close"], p["fast"], p["slow"], p["signal"])
    return (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))


@register_signal(
    name="macd_cross_bear",
    category="momentum",
    direction="bearish",
    params={"fast": 12, "slow": 26, "signal": 9},
    param_grid={"fast": [8, 12], "slow": [21, 26], "signal": [7, 9]},
    tags=["macd", "crossover"],
)
def _macd_cross_bear(df: pd.DataFrame, p: dict) -> pd.Series:
    macd_line, signal_line, _ = _macd(df["close"], p["fast"], p["slow"], p["signal"])
    return (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))


@register_signal(
    name="macd_hist_bull",
    category="momentum",
    direction="bullish",
    params={"fast": 12, "slow": 26, "signal": 9},
    param_grid={"fast": [8, 12], "slow": [21, 26], "signal": [7, 9]},
    tags=["macd", "histogram"],
)
def _macd_hist_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    _, _, hist = _macd(df["close"], p["fast"], p["slow"], p["signal"])
    return (hist > 0) & (hist.shift(1) <= 0)


# ── Stochastic ────────────────────────────────────────────────────────────

@register_signal(
    name="stoch_cross_bull",
    category="momentum",
    direction="bullish",
    params={"k_period": 14, "d_period": 3, "low_zone": 20},
    param_grid={"k_period": [9, 14], "d_period": [3, 5], "low_zone": [15, 20, 25]},
    tags=["stochastic", "crossover"],
)
def _stoch_cross_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    k, d = _stochastic(df, p["k_period"], p["d_period"])
    low = p["low_zone"]
    return (k > d) & (k.shift(1) <= d.shift(1)) & (k < low + 20)


@register_signal(
    name="stoch_cross_bear",
    category="momentum",
    direction="bearish",
    params={"k_period": 14, "d_period": 3, "high_zone": 80},
    param_grid={"k_period": [9, 14], "d_period": [3, 5], "high_zone": [75, 80, 85]},
    tags=["stochastic", "crossover"],
)
def _stoch_cross_bear(df: pd.DataFrame, p: dict) -> pd.Series:
    k, d = _stochastic(df, p["k_period"], p["d_period"])
    high = p["high_zone"]
    return (k < d) & (k.shift(1) >= d.shift(1)) & (k > high - 20)


# ── CCI ───────────────────────────────────────────────────────────────────

@register_signal(
    name="cci_oversold",
    category="momentum",
    direction="bullish",
    params={"period": 20, "threshold": -100},
    param_grid={"period": [14, 20], "threshold": [-150, -100]},
    tags=["cci", "mean-reversion"],
)
def _cci_oversold(df: pd.DataFrame, p: dict) -> pd.Series:
    cci = _cci(df, p["period"])
    thresh = p["threshold"]
    return (cci > thresh) & (cci.shift(1) <= thresh)


# ── Williams %R ───────────────────────────────────────────────────────────

@register_signal(
    name="wr_oversold",
    category="momentum",
    direction="bullish",
    params={"period": 14, "threshold": -80},
    param_grid={"period": [10, 14, 21], "threshold": [-85, -80]},
    tags=["williams_r", "mean-reversion"],
)
def _wr_oversold(df: pd.DataFrame, p: dict) -> pd.Series:
    wr = _williams_r(df, p["period"])
    thresh = p["threshold"]
    return (wr > thresh) & (wr.shift(1) <= thresh)
