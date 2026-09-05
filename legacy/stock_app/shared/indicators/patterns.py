"""
shared.indicators.patterns — thin wrappers around indicators/ folder for use as
research signals. Accessed via lazy sys.path (same pattern as server.py uses).

Safe for import in research/signals/ — never imports server.py.

Elliott Wave is intentionally excluded (ML model, too slow for grid search).
Harmonics excluded from grid search loop but available as one-shot pre-filter.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

# Ensure indicators/ directory is on path (same approach as server.py)
_IND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "indicators")
if _IND_DIR not in sys.path:
    sys.path.insert(0, _IND_DIR)


def sr_near_price(
    df: pd.DataFrame,
    symbol: str,
    interval: str = "1d",
    proximity_pct: float = 0.5,
) -> pd.Series:
    """
    Returns a boolean Series: True on bars where close is within proximity_pct%
    of a horizontal S/R level detected by horizontal_sr.py.

    Used as a pre-filter signal (entry only near key levels).
    proximity_pct=0.5 means within 0.5% of the level.
    """
    try:
        from horizontal_sr import get_horizontal_sr_levels

        closes = df["Close"].values.astype(float)
        highs  = df["High"].values.astype(float)
        lows   = df["Low"].values.astype(float)

        prices = np.concatenate([highs, lows, closes])
        levels = get_horizontal_sr_levels(prices)
        if len(levels) == 0:
            return pd.Series(False, index=df.index)

        result = pd.Series(False, index=df.index)
        tol = proximity_pct / 100.0
        for i, price in enumerate(closes):
            for lvl in levels:
                if abs(price - lvl) / max(abs(lvl), 1e-9) <= tol:
                    result.iloc[i] = True
                    break
        return result
    except Exception:
        return pd.Series(False, index=df.index)


def near_trendline(
    df: pd.DataFrame,
    proximity_pct: float = 0.3,
) -> pd.Series:
    """
    Returns True on bars where close is within proximity_pct% of a detected
    trendline (simple swing-point regression, no external calls).

    Runs purely on the OHLCV data — no symbol/interval required.
    """
    try:
        closes = df["Close"].values.astype(float)
        highs  = df["High"].values.astype(float)
        lows   = df["Low"].values.astype(float)
        n = len(closes)
        if n < 10:
            return pd.Series(False, index=df.index)

        # Simple trendline: linear regression of swing lows / swing highs
        idx = np.arange(n)

        # Swing lows (support trendline)
        swing_mask = np.zeros(n, dtype=bool)
        for i in range(2, n - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                swing_mask[i] = True
        support_line = np.full(n, np.nan)
        if swing_mask.sum() >= 2:
            xi = idx[swing_mask]
            yi = lows[swing_mask]
            m, b = np.polyfit(xi, yi, 1)
            support_line = m * idx + b

        # Swing highs (resistance trendline)
        swing_mask2 = np.zeros(n, dtype=bool)
        for i in range(2, n - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                swing_mask2[i] = True
        resist_line = np.full(n, np.nan)
        if swing_mask2.sum() >= 2:
            xi2 = idx[swing_mask2]
            yi2 = highs[swing_mask2]
            m2, b2 = np.polyfit(xi2, yi2, 1)
            resist_line = m2 * idx + b2

        tol = proximity_pct / 100.0
        result = np.zeros(n, dtype=bool)
        for i in range(n):
            p = closes[i]
            if not np.isnan(support_line[i]):
                lvl = support_line[i]
                if abs(p - lvl) / max(abs(lvl), 1e-9) <= tol:
                    result[i] = True
            if not np.isnan(resist_line[i]):
                lvl2 = resist_line[i]
                if abs(p - lvl2) / max(abs(lvl2), 1e-9) <= tol:
                    result[i] = True

        return pd.Series(result, index=df.index)
    except Exception:
        return pd.Series(False, index=df.index)


def harmonic_active(
    df: pd.DataFrame,
    symbol: str = "STOCK",
) -> pd.Series:
    """
    Returns True on bars where a harmonic pattern (XABCD) was detected.
    Uses pyharmonics library — same as home chart.

    IMPORTANT: Call this ONCE before the backtest loop as a pre-filter,
    not inside the signal evaluation loop — it is slow (~1-3s per call).
    Returns last-bar boolean (pattern active on most recent bar).
    """
    try:
        import sys as _sys
        _pyh = r"D:\Projects\test1\opensource_indicators\pyharmonics\src"
        if _pyh not in _sys.path:
            _sys.path.insert(0, _pyh)

        from pyharmonics.scanner import Scanner
        from pyharmonics import Harmonics

        closes = df["Close"].values.astype(float)
        highs  = df["High"].values.astype(float)
        lows   = df["Low"].values.astype(float)

        scanner = Scanner(highs, lows, closes)
        scanner.scan()
        patterns = scanner.get_patterns()

        result = pd.Series(False, index=df.index)
        if patterns:
            # Mark last 3 bars as "pattern active" — signal fires near completion
            for i in range(max(0, len(df) - 3), len(df)):
                result.iloc[i] = True
        return result
    except Exception:
        return pd.Series(False, index=df.index)
