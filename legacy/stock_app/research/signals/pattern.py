"""
research.signals.pattern — Pattern signals (3 signals)
========================================================
SMC Fair Value Gap, Elliott impulse, U-Bottom curve.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import register_signal


# ── SMC Fair Value Gap (Bullish) ──────────────────────────────────────────

@register_signal(
    name="smc_fvg_bull",
    category="pattern",
    direction="bullish",
    params={"min_gap_pct": 0.002},
    param_grid={"min_gap_pct": [0.001, 0.002, 0.003]},
    tags=["smc", "fair_value_gap"],
)
def _smc_fvg_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    # Bullish FVG: bar[i-2].high < bar[i].low (gap between candle 1's high and candle 3's low)
    high_2back = df["high"].shift(2)
    low_curr = df["low"]
    gap = (low_curr - high_2back) / df["close"].replace(0, 1e-10)

    # Bullish candle in middle
    mid_bull = df["close"].shift(1) > df["open"].shift(1)

    return (gap > p["min_gap_pct"]) & mid_bull


# ── Elliott Impulse (Simplified) ──────────────────────────────────────────

@register_signal(
    name="elliott_impulse_bull",
    category="pattern",
    direction="bullish",
    params={"lookback": 30, "min_fib_score": 1, "min_move": 0.03},
    param_grid={"lookback": [20, 30, 50], "min_fib_score": [1, 2, 3], "min_move": [0.02, 0.03, 0.05]},
    tags=["elliott", "impulse"],
)
def _elliott_impulse(df: pd.DataFrame, p: dict) -> pd.Series:
    """Simplified Elliott: 5-wave impulse pattern detected via swing highs/lows."""
    lb = p["lookback"]
    close = df["close"]

    # Detect a strong up-move with corrections
    # Wave 1+3+5 up, wave 2+4 correction
    ret_from_low = (close - close.rolling(lb).min()) / close.rolling(lb).min().replace(0, 1e-10)
    pullback = 1 - close / close.rolling(lb // 3).max()

    # Strong up move with healthy pullbacks
    strong_up = ret_from_low > float(p.get("min_move", 0.03))
    correction = (pullback > 0.02) & (pullback < 0.05)  # 2-5% correction
    vol_confirm = df["volume"] > df["volume"].rolling(lb).mean()

    fib_score = (
        strong_up.fillna(False).astype(int)
        + correction.shift(1).fillna(False).astype(int)
        + vol_confirm.fillna(False).astype(int)
    )
    return fib_score >= p["min_fib_score"]


# ── U-Bottom Curve ────────────────────────────────────────────────────────

@register_signal(
    name="curve_ubottom",
    category="pattern",
    direction="bullish",
    params={"lookback": 20, "curvature_thresh": 0.001},
    param_grid={"lookback": [15, 20, 30], "curvature_thresh": [0.0005, 0.001, 0.002]},
    tags=["curve", "u-bottom"],
)
def _curve_ubottom(df: pd.DataFrame, p: dict) -> pd.Series:
    """Detect U-shaped bottom: falling then rising close with volume confirmation."""
    lb = p["lookback"]
    close = df["close"]

    # Second derivative of smoothed close (curvature)
    smooth = close.rolling(lb // 2).mean()
    d1 = smooth.diff()
    d2 = d1.diff()

    # Positive curvature (concave up) with volume spike
    positive_curve = d2 > p["curvature_thresh"] * close
    vol_spike = df["volume"] > 1.5 * df["volume"].rolling(lb).mean()

    # Price near recent low
    near_low = close < close.rolling(lb).mean() * 1.02

    return positive_curve & vol_spike & near_low
