"""
shared.indicators.pta — pandas-ta-classic wrappers for research signals + chart overlays.

All functions:
  - Accept a pandas DataFrame with OHLCV columns (Open/High/Low/Close/Volume)
  - Return a pandas Series (for signal use) or dict of Series (for chart overlays)
  - Silently return all-False / all-NaN on error via _guard decorator

Import pattern (lazy, avoids startup cost if pta unused):
    from shared.indicators.pta import hma, fisher, rsx
"""
from __future__ import annotations

import functools
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

# ── local pandas-ta-classic path ──────────────────────────────────────────────
_PTA_CANDIDATE_PATHS = [
    r"D:\Projects\test1\test in claud\pandas-ta-classic",
    r"D:\Projects\test1\opensource_indicators\pandas-ta-classic",
]
_PTA_PATH = next((p for p in _PTA_CANDIDATE_PATHS if Path(p).exists()), _PTA_CANDIDATE_PATHS[-1])
if _PTA_PATH not in sys.path:
    sys.path.insert(0, _PTA_PATH)

try:
    import pandas_ta_classic as _pta
    _PTA_OK = True
except Exception as _e:
    _PTA_OK = False
    _pta = None


# ── guard decorator ────────────────────────────────────────────────────────────

def _guard(fn):
    """Return all-False Series on any exception; keeps research engine stable."""
    @functools.wraps(fn)
    def wrapper(df: pd.DataFrame, *args, **kwargs):
        if not _PTA_OK:
            return pd.Series(False, index=df.index)
        try:
            return fn(df, *args, **kwargs)
        except Exception:
            return pd.Series(False, index=df.index)
    return wrapper


def _guard_float(fn):
    """Return all-NaN Series on any exception; for chart overlay functions."""
    @functools.wraps(fn)
    def wrapper(df: pd.DataFrame, *args, **kwargs):
        if not _PTA_OK:
            return pd.Series(np.nan, index=df.index)
        try:
            return fn(df, *args, **kwargs)
        except Exception:
            return pd.Series(np.nan, index=df.index)
    return wrapper


# ── helpers ───────────────────────────────────────────────────────────────────

def _bool_series(s: pd.Series, index) -> pd.Series:
    """Coerce to bool Series aligned to index."""
    if s is None or (hasattr(s, 'empty') and s.empty):
        return pd.Series(False, index=index)
    return s.reindex(index).fillna(False).astype(bool)


def _float_series(s, index) -> pd.Series:
    if s is None or (hasattr(s, 'empty') and s.empty):
        return pd.Series(np.nan, index=index)
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.reindex(index)


# ══════════════════════════════════════════════════════════════════════════════
# MOMENTUM signals
# ══════════════════════════════════════════════════════════════════════════════

@_guard
def rsx_bull(df: pd.DataFrame, length: int = 14, threshold: float = 50.0) -> pd.Series:
    """RSX (smoothed RSI) crosses above threshold."""
    result = _pta.rsx(df["Close"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result > threshold) & (result.shift(1) <= threshold)
    return _bool_series(cross, df.index)


@_guard
def rsx_bear(df: pd.DataFrame, length: int = 14, threshold: float = 50.0) -> pd.Series:
    """RSX crosses below threshold."""
    result = _pta.rsx(df["Close"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result < threshold) & (result.shift(1) >= threshold)
    return _bool_series(cross, df.index)


@_guard
def fisher_bull(df: pd.DataFrame, length: int = 9) -> pd.Series:
    """Fisher Transform bullish cross (FISHERT crosses above FISHERS)."""
    result = _pta.fisher(df["High"], df["Low"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    fish, sig = result[cols[0]], result[cols[1]]
    cross = (fish > sig) & (fish.shift(1) <= sig.shift(1))
    return _bool_series(cross, df.index)


@_guard
def fisher_bear(df: pd.DataFrame, length: int = 9) -> pd.Series:
    """Fisher Transform bearish cross."""
    result = _pta.fisher(df["High"], df["Low"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    fish, sig = result[cols[0]], result[cols[1]]
    cross = (fish < sig) & (fish.shift(1) >= sig.shift(1))
    return _bool_series(cross, df.index)


@_guard
def tsi_bull(df: pd.DataFrame, fast: int = 13, slow: int = 25, signal: int = 13) -> pd.Series:
    """TSI crosses above its signal line."""
    result = _pta.tsi(df["Close"], fast=fast, slow=slow, signal=signal)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    tsi_line, sig_line = result[cols[0]], result[cols[1]]
    cross = (tsi_line > sig_line) & (tsi_line.shift(1) <= sig_line.shift(1))
    return _bool_series(cross, df.index)


@_guard
def tsi_bear(df: pd.DataFrame, fast: int = 13, slow: int = 25, signal: int = 13) -> pd.Series:
    """TSI crosses below its signal line."""
    result = _pta.tsi(df["Close"], fast=fast, slow=slow, signal=signal)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    tsi_line, sig_line = result[cols[0]], result[cols[1]]
    cross = (tsi_line < sig_line) & (tsi_line.shift(1) >= sig_line.shift(1))
    return _bool_series(cross, df.index)


@_guard
def kdj_bull(df: pd.DataFrame, length: int = 9) -> pd.Series:
    """KDJ: K crosses above D (stochastic-derived)."""
    result = _pta.kdj(df["High"], df["Low"], df["Close"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    k, d = result[cols[0]], result[cols[1]]
    cross = (k > d) & (k.shift(1) <= d.shift(1))
    return _bool_series(cross, df.index)


@_guard
def kdj_bear(df: pd.DataFrame, length: int = 9) -> pd.Series:
    """KDJ: K crosses below D."""
    result = _pta.kdj(df["High"], df["Low"], df["Close"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    k, d = result[cols[0]], result[cols[1]]
    cross = (k < d) & (k.shift(1) >= d.shift(1))
    return _bool_series(cross, df.index)


# ══════════════════════════════════════════════════════════════════════════════
# VOLUME signals
# ══════════════════════════════════════════════════════════════════════════════

@_guard
def mfi_bull(df: pd.DataFrame, length: int = 14, threshold: float = 30.0) -> pd.Series:
    """Money Flow Index crosses above oversold threshold."""
    result = _pta.mfi(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result > threshold) & (result.shift(1) <= threshold)
    return _bool_series(cross, df.index)


@_guard
def mfi_bear(df: pd.DataFrame, length: int = 14, threshold: float = 70.0) -> pd.Series:
    """Money Flow Index crosses below overbought threshold."""
    result = _pta.mfi(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result < threshold) & (result.shift(1) >= threshold)
    return _bool_series(cross, df.index)


@_guard
def cmf_bull(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Chaikin Money Flow crosses above zero."""
    result = _pta.cmf(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result > 0) & (result.shift(1) <= 0)
    return _bool_series(cross, df.index)


@_guard
def cmf_bear(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Chaikin Money Flow crosses below zero."""
    result = _pta.cmf(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result < 0) & (result.shift(1) >= 0)
    return _bool_series(cross, df.index)


# ══════════════════════════════════════════════════════════════════════════════
# TREND signals
# ══════════════════════════════════════════════════════════════════════════════

@_guard
def vortex_bull(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Vortex: VI+ crosses above VI-."""
    result = _pta.vortex(df["High"], df["Low"], df["Close"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    vip, vim = result[cols[0]], result[cols[1]]
    cross = (vip > vim) & (vip.shift(1) <= vim.shift(1))
    return _bool_series(cross, df.index)


@_guard
def vortex_bear(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Vortex: VI- crosses above VI+."""
    result = _pta.vortex(df["High"], df["Low"], df["Close"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    vip, vim = result[cols[0]], result[cols[1]]
    cross = (vim > vip) & (vim.shift(1) <= vip.shift(1))
    return _bool_series(cross, df.index)


@_guard
def aroon_bull(df: pd.DataFrame, length: int = 25) -> pd.Series:
    """Aroon: AroonUp crosses above AroonDown."""
    result = _pta.aroon(df["High"], df["Low"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    up_col = next((c for c in cols if "U_" in str(c).upper() or "UP" in str(c).upper()), cols[1] if len(cols) > 1 else cols[0])
    down_col = next((c for c in cols if "D_" in str(c).upper() or "DOWN" in str(c).upper()), cols[0])
    up, down = result[up_col], result[down_col]
    cross = (up > down) & (up.shift(1) <= down.shift(1))
    return _bool_series(cross, df.index)


@_guard
def aroon_bear(df: pd.DataFrame, length: int = 25) -> pd.Series:
    """Aroon: AroonDown crosses above AroonUp."""
    result = _pta.aroon(df["High"], df["Low"], length=length)
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    cols = result.columns.tolist()
    if len(cols) < 2:
        return pd.Series(False, index=df.index)
    up_col = next((c for c in cols if "U_" in str(c).upper() or "UP" in str(c).upper()), cols[1] if len(cols) > 1 else cols[0])
    down_col = next((c for c in cols if "D_" in str(c).upper() or "DOWN" in str(c).upper()), cols[0])
    up, down = result[up_col], result[down_col]
    cross = (down > up) & (down.shift(1) <= up.shift(1))
    return _bool_series(cross, df.index)


# ══════════════════════════════════════════════════════════════════════════════
# VOLATILITY signals
# ══════════════════════════════════════════════════════════════════════════════

@_guard
def chop_low(df: pd.DataFrame, length: int = 14, threshold: float = 38.2) -> pd.Series:
    """Choppiness Index below threshold → trending market."""
    result = _pta.chop(df["High"], df["Low"], df["Close"], length=length)
    if result is None:
        return pd.Series(False, index=df.index)
    cross = (result < threshold) & (result.shift(1) >= threshold)
    return _bool_series(cross, df.index)


@_guard
def squeeze_fire(df: pd.DataFrame, bb_length: int = 20, kc_length: int = 20) -> pd.Series:
    """Squeeze Momentum: histogram crosses above zero (squeeze released, bullish)."""
    result = _pta.squeeze(
        df["High"], df["Low"], df["Close"],
        bb_length=bb_length, kc_length=kc_length
    )
    if result is None or not isinstance(result, pd.DataFrame):
        return pd.Series(False, index=df.index)
    # SQZ_20_2.0_20_1.5 histogram column
    hist_cols = [c for c in result.columns if "SQZ" in str(c) and "ON" not in str(c) and "NO" not in str(c) and "OFF" not in str(c)]
    if not hist_cols:
        hist_cols = [result.columns[0]]
    hist = result[hist_cols[0]]
    cross = (hist > 0) & (hist.shift(1) <= 0)
    return _bool_series(cross, df.index)


# ══════════════════════════════════════════════════════════════════════════════
# OVERLAP (chart overlays — return float Series for rendering)
# ══════════════════════════════════════════════════════════════════════════════

@_guard_float
def hma(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Hull Moving Average."""
    result = _pta.hma(df["Close"], length=length)
    return _float_series(result, df.index)


@_guard_float
def dema(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Double Exponential Moving Average."""
    result = _pta.dema(df["Close"], length=length)
    return _float_series(result, df.index)


@_guard_float
def tema(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Triple Exponential Moving Average."""
    result = _pta.tema(df["Close"], length=length)
    return _float_series(result, df.index)


@_guard_float
def zlema(df: pd.DataFrame, length: int = 20) -> pd.Series:
    """Zero Lag EMA."""
    result = _pta.zlma(df["Close"], length=length)
    return _float_series(result, df.index)


def donchian(df: pd.DataFrame, length: int = 20) -> dict:
    """Donchian Channel — returns {upper, mid, lower} lists."""
    try:
        if not _PTA_OK:
            return {"upper": [], "mid": [], "lower": []}
        result = _pta.donchian(df["High"], df["Low"], lower_length=length, upper_length=length)
        if result is None or not isinstance(result, pd.DataFrame):
            return {"upper": [], "mid": [], "lower": []}
        cols = result.columns.tolist()
        def _to_list(series):
            return [round(float(v), 4) if not (v != v) else None for v in series]
        upper = _to_list(result[cols[0]]) if len(cols) > 0 else []
        mid   = _to_list(result[cols[1]]) if len(cols) > 1 else []
        lower = _to_list(result[cols[2]]) if len(cols) > 2 else []
        return {"upper": upper, "mid": mid, "lower": lower}
    except Exception:
        return {"upper": [], "mid": [], "lower": []}


def mfi_line(df: pd.DataFrame, length: int = 14) -> list:
    """MFI as list of floats for chart sub-pane."""
    try:
        if not _PTA_OK:
            return []
        result = _pta.mfi(df["High"], df["Low"], df["Close"], df["Volume"], length=length)
        if result is None:
            return []
        return [round(float(v), 2) if not (v != v) else None for v in result]
    except Exception:
        return []


def aroon_lines(df: pd.DataFrame, length: int = 25) -> dict:
    """Aroon Up/Down as {up, down} lists for chart sub-pane."""
    try:
        if not _PTA_OK:
            return {"up": [], "down": []}
        result = _pta.aroon(df["High"], df["Low"], length=length)
        if result is None or not isinstance(result, pd.DataFrame):
            return {"up": [], "down": []}
        cols = result.columns.tolist()
        def _to_list(series):
            return [round(float(v), 2) if not (v != v) else None for v in series]
        up_col = next((c for c in cols if "U_" in str(c).upper() or "UP" in str(c).upper()), cols[1] if len(cols) > 1 else cols[0])
        down_col = next((c for c in cols if "D_" in str(c).upper() or "DOWN" in str(c).upper()), cols[0])
        return {
            "up":   _to_list(result[up_col]) if cols else [],
            "down": _to_list(result[down_col]) if cols else [],
        }
    except Exception:
        return {"up": [], "down": []}


def fisher_line(df: pd.DataFrame, length: int = 9) -> dict:
    """Fisher Transform as {fisher, signal} lists."""
    try:
        if not _PTA_OK:
            return {"fisher": [], "signal": []}
        result = _pta.fisher(df["High"], df["Low"], length=length)
        if result is None or not isinstance(result, pd.DataFrame):
            return {"fisher": [], "signal": []}
        cols = result.columns.tolist()
        def _to_list(series):
            return [round(float(v), 4) if not (v != v) else None for v in series]
        return {
            "fisher": _to_list(result[cols[0]]) if cols else [],
            "signal": _to_list(result[cols[1]]) if len(cols) > 1 else [],
        }
    except Exception:
        return {"fisher": [], "signal": []}


def hma_line(df: pd.DataFrame, length: int = 20) -> list:
    """HMA as list of floats for chart overlay."""
    try:
        s = hma(df, length=length)
        return [round(float(v), 4) if not (v != v) else None for v in s]
    except Exception:
        return []


def _cdl_patterns_raw(df: pd.DataFrame) -> list:
    """
    Detect candlestick patterns using numpy (no TA-Lib required).
    Returns list of {time, name, direction, index} for each detected pattern.
    direction: 'bull' | 'bear' | 'neutral'
    """
    try:
        o = df["Open"].values.astype(float)
        h = df["High"].values.astype(float)
        l = df["Low"].values.astype(float)
        c = df["Close"].values.astype(float)
        idx = df.index
        n = len(o)
        events = []

        def _time(i):
            t = idx[i]
            if hasattr(t, "strftime"):
                return t.strftime("%Y-%m-%d") if t.hour == 0 and t.minute == 0 else t.strftime("%Y-%m-%d %H:%M")
            return str(t)[:10]

        body   = np.abs(c - o)
        hl     = h - l
        upper  = np.where(c > o, h - c, h - o)   # upper wick
        lower  = np.where(c > o, o - l, c - l)   # lower wick
        bull   = c > o

        # rolling average body/hl for thresholds (14-bar)
        def _roll_mean(arr, w=14):
            out = np.full(n, np.nan)
            for i in range(w - 1, n):
                out[i] = arr[i - w + 1: i + 1].mean()
            return out

        avg_body = _roll_mean(body)
        avg_hl   = _roll_mean(hl)

        for i in range(14, n):
            ab = avg_body[i] if not np.isnan(avg_body[i]) else body[i]
            ah = avg_hl[i]   if not np.isnan(avg_hl[i])  else hl[i]
            t = _time(i)

            # ── Doji ───────────────────────────────────────────────────
            if hl[i] > 0 and body[i] <= 0.1 * hl[i]:
                events.append({"time": t, "name": "Doji", "direction": "neutral", "index": i})

            # ── Hammer (bullish reversal at bottom) ────────────────────
            if (lower[i] > 2 * body[i] and upper[i] < 0.3 * body[i]
                    and body[i] > 0 and min(c[max(0,i-5):i]) < c[i]):
                events.append({"time": t, "name": "Hammer", "direction": "bull", "index": i})

            # ── Inverted Hammer (bullish) ──────────────────────────────
            if (upper[i] > 2 * body[i] and lower[i] < 0.3 * body[i]
                    and body[i] > 0 and bull[i]):
                events.append({"time": t, "name": "Inv Hammer", "direction": "bull", "index": i})

            # ── Shooting Star (bearish) ────────────────────────────────
            if (upper[i] > 2 * body[i] and lower[i] < 0.3 * body[i]
                    and body[i] > 0 and not bull[i] and max(c[max(0,i-5):i]) > c[i]):
                events.append({"time": t, "name": "Shooting Star", "direction": "bear", "index": i})

            # ── Hanging Man (bearish) ──────────────────────────────────
            if (lower[i] > 2 * body[i] and upper[i] < 0.3 * body[i]
                    and body[i] > 0 and max(c[max(0,i-5):i]) > c[i]):
                events.append({"time": t, "name": "Hanging Man", "direction": "bear", "index": i})

            # ── Bullish Engulfing ──────────────────────────────────────
            if (i >= 1 and bull[i] and not bull[i-1]
                    and o[i] <= c[i-1] and c[i] >= o[i-1]
                    and body[i] > body[i-1]):
                events.append({"time": t, "name": "Bull Engulf", "direction": "bull", "index": i})

            # ── Bearish Engulfing ──────────────────────────────────────
            if (i >= 1 and not bull[i] and bull[i-1]
                    and o[i] >= c[i-1] and c[i] <= o[i-1]
                    and body[i] > body[i-1]):
                events.append({"time": t, "name": "Bear Engulf", "direction": "bear", "index": i})

            # ── Bullish Harami ─────────────────────────────────────────
            if (i >= 1 and bull[i] and not bull[i-1]
                    and o[i] > c[i-1] and c[i] < o[i-1]
                    and body[i] < body[i-1] * 0.6):
                events.append({"time": t, "name": "Bull Harami", "direction": "bull", "index": i})

            # ── Bearish Harami ─────────────────────────────────────────
            if (i >= 1 and not bull[i] and bull[i-1]
                    and o[i] < c[i-1] and c[i] > o[i-1]
                    and body[i] < body[i-1] * 0.6):
                events.append({"time": t, "name": "Bear Harami", "direction": "bear", "index": i})

            # ── Morning Star (3-bar bullish reversal) ─────────────────
            if (i >= 2 and not bull[i-2] and body[i-1] < 0.3 * ab
                    and bull[i] and c[i] > (o[i-2] + c[i-2]) / 2):
                events.append({"time": t, "name": "Morning Star", "direction": "bull", "index": i})

            # ── Evening Star (3-bar bearish reversal) ─────────────────
            if (i >= 2 and bull[i-2] and body[i-1] < 0.3 * ab
                    and not bull[i] and c[i] < (o[i-2] + c[i-2]) / 2):
                events.append({"time": t, "name": "Evening Star", "direction": "bear", "index": i})

            # ── Inside Bar ─────────────────────────────────────────────
            if (i >= 1 and h[i] <= h[i-1] and l[i] >= l[i-1]):
                events.append({"time": t, "name": "Inside Bar", "direction": "neutral", "index": i})

            # ── Three White Soldiers ───────────────────────────────────
            if (i >= 2
                    and bull[i] and bull[i-1] and bull[i-2]
                    and o[i] > o[i-1] and o[i-1] > o[i-2]
                    and c[i] > c[i-1] and c[i-1] > c[i-2]
                    and body[i] > 0.5 * ah and body[i-1] > 0.5 * ah):
                events.append({"time": t, "name": "3 Soldiers", "direction": "bull", "index": i})

            # ── Three Black Crows ──────────────────────────────────────
            if (i >= 2
                    and not bull[i] and not bull[i-1] and not bull[i-2]
                    and o[i] < o[i-1] and o[i-1] < o[i-2]
                    and c[i] < c[i-1] and c[i-1] < c[i-2]
                    and body[i] > 0.5 * ah and body[i-1] > 0.5 * ah):
                events.append({"time": t, "name": "3 Crows", "direction": "bear", "index": i})

            # ── Marubozu (strong trend candle, no wicks) ──────────────
            if (body[i] > 0.9 * hl[i] and hl[i] > ah * 0.8):
                d = "bull" if bull[i] else "bear"
                events.append({"time": t, "name": "Marubozu", "direction": d, "index": i})

        return events
    except Exception:
        return []


SESSION_OPEN_TIMES = {(9, 15), (9, 30)}

_CDL_PRIORITY = {
    "Morning Star": 100,
    "Evening Star": 100,
    "3 Soldiers": 95,
    "3 Crows": 95,
    "Bull Engulf": 90,
    "Bear Engulf": 90,
    "Hammer": 82,
    "Shooting Star": 82,
    "Inv Hammer": 78,
    "Hanging Man": 78,
    "Bull Harami": 68,
    "Bear Harami": 68,
    "Marubozu": 55,
    "Doji": 30,
    "Inside Bar": 10,
}


def cdl_patterns(df: pd.DataFrame, strict: bool = True, cooldown_bars: int = 30) -> list:
    """
    Chart-safe candlestick patterns.

    The raw CDL detector is intentionally broad. This wrapper keeps the same
    raw formulas but only displays contextual, sparse markers on the chart.
    """
    try:
        raw = _cdl_patterns_raw(df)
        if not strict:
            return raw

        o = df["Open"].values.astype(float)
        h = df["High"].values.astype(float)
        l = df["Low"].values.astype(float)
        c = df["Close"].values.astype(float)
        idx = df.index
        body = np.abs(c - o)
        candle_range = h - l

        def _is_session_open(i):
            if i < 0 or i >= len(idx):
                return False
            t = idx[i]
            return hasattr(t, "hour") and (t.hour, t.minute) in SESSION_OPEN_TIMES

        def _trend_up(i, lookback=6):
            if i < lookback:
                return False
            win = c[i - lookback:i]
            return bool(win[-1] > win[0] and np.nanmean(np.diff(win)) > 0)

        def _trend_down(i, lookback=6):
            if i < lookback:
                return False
            win = c[i - lookback:i]
            return bool(win[-1] < win[0] and np.nanmean(np.diff(win)) < 0)

        def _near_swing_high(i, lookback=10):
            return bool(h[i] >= np.nanmax(h[max(0, i - lookback):i + 1]))

        def _near_swing_low(i, lookback=10):
            return bool(l[i] <= np.nanmin(l[max(0, i - lookback):i + 1]))

        def _context_ok(i, direction):
            if direction == "bull":
                return _trend_down(i) or _near_swing_low(i)
            if direction == "bear":
                return _trend_up(i) or _near_swing_high(i)
            return _near_swing_high(i) or _near_swing_low(i)

        def _keep_neutral(evt):
            i = int(evt.get("index", -1))
            if i < 14 or i >= len(c) or candle_range[i] <= 0:
                return False
            name = str(evt.get("name", ""))
            if name == "Inside Bar":
                return False
            if name == "Doji":
                avg_range = np.nanmean(candle_range[max(0, i - 14):i + 1])
                return body[i] <= 0.05 * candle_range[i] and candle_range[i] >= 0.6 * avg_range
            return True

        by_time = {}
        for evt in raw:
            t = evt.get("time")
            if t is None:
                continue
            old = by_time.get(t)
            if old is None or _CDL_PRIORITY.get(str(evt.get("name")), 0) > _CDL_PRIORITY.get(str(old.get("name")), 0):
                by_time[t] = evt

        cleaned = []
        seen_times = set()
        last_i = -10_000
        for evt in sorted(by_time.values(), key=lambda e: int(e.get("index", -1))):
            i = int(evt.get("index", -1))
            direction = evt.get("direction")
            if i < 20 or i >= len(c) or _is_session_open(i):
                continue
            if i - last_i < cooldown_bars:
                continue
            if evt.get("time") in seen_times:
                continue
            if direction == "neutral":
                if not _keep_neutral(evt):
                    continue
            elif not _context_ok(i, direction):
                continue
            cleaned.append(evt)
            seen_times.add(evt.get("time"))
            last_i = i
        return cleaned
    except Exception:
        return []


def is_available() -> bool:
    return _PTA_OK
