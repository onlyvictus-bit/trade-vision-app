"""
research.signals.volume — Volume signals (3 signals)
=====================================================
OBV divergence, VWAP cross, volume breakout.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import register_signal


# ── OBV Divergence (Bullish) ─────────────────────────────────────────────

@register_signal(
    name="obv_divergence_bull",
    category="volume",
    direction="bullish",
    params={"lookback": 20},
    param_grid={"lookback": [14, 20, 30]},
    tags=["obv", "divergence"],
)
def _obv_div_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    obv = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
    lb = p["lookback"]

    price_low = df["close"].rolling(lb).min()
    obv_low = obv.rolling(lb).min()

    # Price makes new low but OBV doesn't
    price_new_low = df["close"] <= price_low.shift(1)
    obv_higher_low = obv > obv_low.shift(1)

    return price_new_low & obv_higher_low


# ── VWAP Cross ────────────────────────────────────────────────────────────

@register_signal(
    name="vwap_cross_bull",
    category="volume",
    direction="bullish",
    params={},
    param_grid={},
    tags=["vwap", "crossover"],
)
def _vwap_cross_bull(df: pd.DataFrame, p: dict) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cum_tp_vol = (tp * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, 1e-10)
    return (df["close"] > vwap) & (df["close"].shift(1) <= vwap.shift(1))


# ── Volume Breakout ───────────────────────────────────────────────────────

@register_signal(
    name="volume_breakout",
    category="volume",
    direction="bullish",
    params={"period": 20, "mult": 2.0},
    param_grid={"period": [10, 20], "mult": [1.5, 2.0, 3.0]},
    tags=["volume", "spike"],
)
def _volume_breakout(df: pd.DataFrame, p: dict) -> pd.Series:
    vol_sma = df["volume"].rolling(p["period"]).mean()
    return df["volume"] > p["mult"] * vol_sma
