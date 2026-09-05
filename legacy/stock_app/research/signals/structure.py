"""
research.signals.structure — Structure signals (3 signals)
===========================================================
Pivot support bounce, Fib 61.8% bounce, horizontal S/R break.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import register_signal


# ── Pivot Support Bounce ──────────────────────────────────────────────────

@register_signal(
    name="pivot_support_bounce",
    category="structure",
    direction="bullish",
    params={"bounce_pct": 0.3},
    param_grid={"bounce_pct": [0.2, 0.3, 0.4]},
    tags=["pivot", "support"],
)
def _pivot_bounce(df: pd.DataFrame, p: dict) -> pd.Series:
    # Classic floor pivots from prior day
    pp = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
    s1 = 2 * pp - df["high"].shift(1)
    s2 = pp - (df["high"].shift(1) - df["low"].shift(1))

    bar_range = df["high"] - df["low"]
    bounce = (df["close"] - df["low"]) / bar_range.replace(0, 1e-10)

    # Price touches S1 or S2, then closes in upper portion of bar
    near_s1 = (df["low"] <= s1) & (df["close"] > s1)
    near_s2 = (df["low"] <= s2) & (df["close"] > s2)
    good_bounce = bounce > p["bounce_pct"]

    return (near_s1 | near_s2) & good_bounce


# ── Fibonacci 61.8% Bounce ───────────────────────────────────────────────

@register_signal(
    name="fib_618_bounce_bull",
    category="structure",
    direction="bullish",
    params={"lookback": 50, "fib_level": 0.618, "tolerance": 0.01},
    param_grid={"lookback": [30, 50, 80], "tolerance": [0.005, 0.01, 0.015]},
    tags=["fibonacci", "retracement"],
)
def _fib_bounce(df: pd.DataFrame, p: dict) -> pd.Series:
    lb = p["lookback"]
    swing_high = df["high"].rolling(lb).max()
    swing_low = df["low"].rolling(lb).min()

    fib_price = swing_high - p["fib_level"] * (swing_high - swing_low)
    dist = (df["close"] - fib_price).abs() / df["close"].replace(0, 1e-10)

    # Close near 61.8% level AND price bouncing (close > open)
    near_fib = dist < p["tolerance"]
    bullish_bar = df["close"] > df["open"]

    return near_fib & bullish_bar


# ── Horizontal S/R Break (Bullish) ───────────────────────────────────────

@register_signal(
    name="horizontal_sr_break_bull",
    category="structure",
    direction="bullish",
    params={"lookback": 50, "n_touches": 2},
    param_grid={"lookback": [30, 50, 80], "n_touches": [2, 3]},
    tags=["support_resistance", "breakout"],
)
def _sr_break_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    lb = p["lookback"]
    # Resistance = rolling max of highs
    resistance = df["high"].rolling(lb).max()

    # Count how many bars touched this level (within 0.5%)
    near_resistance = (df["high"] > resistance * 0.995) & (df["high"] < resistance * 1.005)
    touch_count = near_resistance.rolling(lb).sum()

    # Break: close above resistance after multiple touches
    has_touches = touch_count.shift(1) >= p["n_touches"]
    breaks_above = df["close"] > resistance.shift(1)

    return has_touches & breaks_above
