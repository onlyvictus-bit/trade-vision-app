"""
research.signals.volatility — Volatility signals (4 signals)
=============================================================
Bollinger Band squeeze/break, Keltner break, ATR expansion.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import register_signal


# ── helpers ───────────────────────────────────────────────────────────────

def _bb(close: pd.Series, period: int = 20, std_mult: float = 2.0):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    width = (upper - lower) / sma
    return upper, lower, width


def _keltner(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5):
    ema = df["close"].ewm(span=period, adjust=False).mean()
    atr = (df["high"] - df["low"]).rolling(period).mean()
    upper = ema + atr_mult * atr
    lower = ema - atr_mult * atr
    return upper, lower


# ── Bollinger Band Squeeze Break ──────────────────────────────────────────

@register_signal(
    name="bb_squeeze_break_bull",
    category="volatility",
    direction="bullish",
    params={"period": 20, "std_mult": 2.0, "squeeze_pct": 0.04},
    param_grid={"period": [15, 20], "std_mult": [1.5, 2.0], "squeeze_pct": [0.03, 0.04, 0.05]},
    tags=["bollinger", "squeeze", "breakout"],
)
def _bb_squeeze_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    upper, lower, width = _bb(df["close"], p["period"], p["std_mult"])
    squeeze = width < p["squeeze_pct"]
    was_squeeze = squeeze.shift(1).fillna(False)
    break_upper = df["close"] > upper
    return was_squeeze & break_upper


@register_signal(
    name="bb_squeeze_break_bear",
    category="volatility",
    direction="bearish",
    params={"period": 20, "std_mult": 2.0, "squeeze_pct": 0.04},
    param_grid={"period": [15, 20], "std_mult": [1.5, 2.0], "squeeze_pct": [0.03, 0.04, 0.05]},
    tags=["bollinger", "squeeze", "breakout"],
)
def _bb_squeeze_bear(df: pd.DataFrame, p: dict) -> pd.Series:
    upper, lower, width = _bb(df["close"], p["period"], p["std_mult"])
    squeeze = width < p["squeeze_pct"]
    was_squeeze = squeeze.shift(1).fillna(False)
    break_lower = df["close"] < lower
    return was_squeeze & break_lower


# ── Keltner Channel Break ────────────────────────────────────────────────

@register_signal(
    name="keltner_break_bull",
    category="volatility",
    direction="bullish",
    params={"period": 20, "atr_mult": 1.5},
    param_grid={"period": [15, 20], "atr_mult": [1.0, 1.5, 2.0]},
    tags=["keltner", "breakout"],
)
def _keltner_break_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    upper, _ = _keltner(df, p["period"], p["atr_mult"])
    return (df["close"] > upper) & (df["close"].shift(1) <= upper.shift(1))


# ── ATR Expansion ─────────────────────────────────────────────────────────

@register_signal(
    name="atr_expansion",
    category="volatility",
    direction="bullish",
    params={"period": 14, "lookback": 20, "mult": 1.5},
    param_grid={"period": [10, 14], "lookback": [15, 20], "mult": [1.3, 1.5, 2.0]},
    tags=["atr", "expansion"],
)
def _atr_expansion(df: pd.DataFrame, p: dict) -> pd.Series:
    atr = (df["high"] - df["low"]).rolling(p["period"]).mean()
    atr_past = atr.shift(p["lookback"])
    return (atr > p["mult"] * atr_past) & (atr.shift(1) <= p["mult"] * atr_past.shift(1))
