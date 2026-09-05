"""
research.signals.pta_signals — 20 new entry/exit signals via pandas-ta-classic.

Compute functions receive (df: DataFrame, params: dict) matching the registry contract.
Uses shared.indicators.pta — zero imports from server.py.
"""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import register_signal


def _pta():
    from shared.indicators import pta as _p
    return _p


# ══════════════════════════════════════════════════════════════════════════════
# RSX (smoothed RSI)
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="rsx_bull",
    category="momentum",
    direction="bullish",
    params={"length": 14, "threshold": 50.0},
    param_grid={"length": [10, 14, 21], "threshold": [45.0, 50.0, 55.0]},
)
def rsx_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().rsx_bull(df, length=params["length"], threshold=params["threshold"])


@register_signal(
    name="rsx_bear",
    category="momentum",
    direction="bearish",
    params={"length": 14, "threshold": 50.0},
    param_grid={"length": [10, 14, 21], "threshold": [45.0, 50.0, 55.0]},
)
def rsx_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().rsx_bear(df, length=params["length"], threshold=params["threshold"])


# ══════════════════════════════════════════════════════════════════════════════
# Fisher Transform
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="fisher_bull",
    category="momentum",
    direction="bullish",
    params={"length": 9},
    param_grid={"length": [7, 9, 14]},
)
def fisher_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().fisher_bull(df, length=params["length"])


@register_signal(
    name="fisher_bear",
    category="momentum",
    direction="bearish",
    params={"length": 9},
    param_grid={"length": [7, 9, 14]},
)
def fisher_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().fisher_bear(df, length=params["length"])


# ══════════════════════════════════════════════════════════════════════════════
# KDJ
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="kdj_bull",
    category="momentum",
    direction="bullish",
    params={"length": 9},
    param_grid={"length": [9, 14]},
)
def kdj_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().kdj_bull(df, length=params["length"])


@register_signal(
    name="kdj_bear",
    category="momentum",
    direction="bearish",
    params={"length": 9},
    param_grid={"length": [9, 14]},
)
def kdj_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().kdj_bear(df, length=params["length"])


# ══════════════════════════════════════════════════════════════════════════════
# MFI
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="mfi_bull",
    category="volume",
    direction="bullish",
    params={"length": 14, "threshold": 30.0},
    param_grid={"length": [10, 14], "threshold": [25.0, 30.0, 35.0]},
)
def mfi_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().mfi_bull(df, length=params["length"], threshold=params["threshold"])


@register_signal(
    name="mfi_bear",
    category="volume",
    direction="bearish",
    params={"length": 14, "threshold": 70.0},
    param_grid={"length": [10, 14], "threshold": [65.0, 70.0, 75.0]},
)
def mfi_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().mfi_bear(df, length=params["length"], threshold=params["threshold"])


# ══════════════════════════════════════════════════════════════════════════════
# CMF
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="cmf_bull",
    category="volume",
    direction="bullish",
    params={"length": 20},
    param_grid={"length": [14, 20]},
)
def cmf_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().cmf_bull(df, length=params["length"])


@register_signal(
    name="cmf_bear",
    category="volume",
    direction="bearish",
    params={"length": 20},
    param_grid={"length": [14, 20]},
)
def cmf_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().cmf_bear(df, length=params["length"])


# ══════════════════════════════════════════════════════════════════════════════
# Vortex
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="vortex_bull",
    category="trend",
    direction="bullish",
    params={"length": 14},
    param_grid={"length": [10, 14, 21]},
)
def vortex_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().vortex_bull(df, length=params["length"])


@register_signal(
    name="vortex_bear",
    category="trend",
    direction="bearish",
    params={"length": 14},
    param_grid={"length": [10, 14, 21]},
)
def vortex_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().vortex_bear(df, length=params["length"])


# ══════════════════════════════════════════════════════════════════════════════
# Aroon
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="aroon_bull",
    category="trend",
    direction="bullish",
    params={"length": 25},
    param_grid={"length": [14, 25]},
)
def aroon_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().aroon_bull(df, length=params["length"])


@register_signal(
    name="aroon_bear",
    category="trend",
    direction="bearish",
    params={"length": 25},
    param_grid={"length": [14, 25]},
)
def aroon_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().aroon_bear(df, length=params["length"])


# ══════════════════════════════════════════════════════════════════════════════
# TSI
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="tsi_bull",
    category="momentum",
    direction="bullish",
    params={"fast": 13, "slow": 25, "signal": 13},
    param_grid={"fast": [10, 13], "slow": [20, 25], "signal": [7, 13]},
)
def tsi_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().tsi_bull(df, fast=params["fast"], slow=params["slow"], signal=params["signal"])


@register_signal(
    name="tsi_bear",
    category="momentum",
    direction="bearish",
    params={"fast": 13, "slow": 25, "signal": 13},
    param_grid={"fast": [10, 13], "slow": [20, 25], "signal": [7, 13]},
)
def tsi_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().tsi_bear(df, fast=params["fast"], slow=params["slow"], signal=params["signal"])


# ══════════════════════════════════════════════════════════════════════════════
# Volatility / Market State
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="chop_trending",
    category="volatility",
    direction="bullish",
    params={"length": 14, "threshold": 38.2},
    param_grid={"length": [9, 14], "threshold": [35.0, 38.2, 41.4]},
    tags=["filter", "market-state"],
)
def chop_trending(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().chop_low(df, length=params["length"], threshold=params["threshold"])


@register_signal(
    name="squeeze_bull",
    category="volatility",
    direction="bullish",
    params={"bb_length": 20, "kc_length": 20},
    param_grid={"bb_length": [14, 20], "kc_length": [14, 20]},
    tags=["breakout", "volatility-expansion"],
)
def squeeze_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pta().squeeze_fire(df, bb_length=params["bb_length"], kc_length=params["kc_length"])


# ══════════════════════════════════════════════════════════════════════════════
# STATISTICAL SIGNALS
# Uses rolling statistics as mean-reversion and regime signals.
# ══════════════════════════════════════════════════════════════════════════════

import numpy as np


def _zscore_series(df: pd.DataFrame, period: int) -> pd.Series:
    c = df["Close"].astype(float)
    mean = c.rolling(period, min_periods=period // 2).mean()
    std  = c.rolling(period, min_periods=period // 2).std().replace(0, np.nan)
    return ((c - mean) / std).fillna(0)


@register_signal(
    name="zscore_extreme_bull",
    category="momentum",
    direction="bullish",
    params={"period": 50, "threshold": 2.0},
    param_grid={"period": [30, 50], "threshold": [1.5, 2.0, 2.5]},
    tags=["mean-reversion", "statistical"],
)
def zscore_extreme_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Z-score < -threshold: price far below mean — mean-reversion buy signal."""
    try:
        z = _zscore_series(df, int(params["period"]))
        cross = (z < -params["threshold"]) & (z.shift(1) >= -params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="zscore_extreme_bear",
    category="momentum",
    direction="bearish",
    params={"period": 50, "threshold": 2.0},
    param_grid={"period": [30, 50], "threshold": [1.5, 2.0, 2.5]},
    tags=["mean-reversion", "statistical"],
)
def zscore_extreme_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Z-score > threshold: price far above mean — mean-reversion sell signal."""
    try:
        z = _zscore_series(df, int(params["period"]))
        cross = (z > params["threshold"]) & (z.shift(1) <= params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="entropy_low_bull",
    category="trend",
    direction="bullish",
    params={"period": 20, "threshold": 0.4},
    param_grid={"period": [14, 20], "threshold": [0.3, 0.4, 0.5]},
    tags=["market-state", "statistical", "filter"],
)
def entropy_low_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Low entropy = structured/trending market. Fires when entropy drops below threshold."""
    try:
        from scipy.stats import entropy as sp_entropy

        def _ent(arr):
            arr = arr[~np.isnan(arr)]
            if len(arr) < 5:
                return 1.0
            counts, _ = np.histogram(arr, bins=5)
            probs = counts / (counts.sum() + 1e-10)
            return float(sp_entropy(probs + 1e-10) / np.log(5))

        c = df["Close"].astype(float)
        ent = c.rolling(int(params["period"]), min_periods=5).apply(_ent, raw=True).fillna(1.0)
        cross = (ent < params["threshold"]) & (ent.shift(1) >= params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="skew_negative_bull",
    category="momentum",
    direction="bullish",
    params={"period": 30, "threshold": -0.5},
    param_grid={"period": [20, 30, 50], "threshold": [-0.3, -0.5, -1.0]},
    tags=["mean-reversion", "statistical"],
)
def skew_negative_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Returns become negatively skewed — excessive selling, contrarian buy."""
    try:
        ret = df["Close"].astype(float).pct_change()
        skew = ret.rolling(int(params["period"]), min_periods=10).skew().fillna(0)
        cross = (skew < params["threshold"]) & (skew.shift(1) >= params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="kurtosis_spike",
    category="volatility",
    direction="bullish",
    params={"period": 30, "threshold": 5.0},
    param_grid={"period": [20, 30], "threshold": [4.0, 5.0, 7.0]},
    tags=["regime", "statistical", "fat-tail"],
)
def kurtosis_spike(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Kurtosis exceeds threshold — fat-tail event detected (extreme move likely over)."""
    try:
        ret = df["Close"].astype(float).pct_change()
        kurt = ret.rolling(int(params["period"]), min_periods=10).kurt().fillna(0)
        cross = (kurt > params["threshold"]) & (kurt.shift(1) <= params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


# ══════════════════════════════════════════════════════════════════════════════
# PRICE TRANSFORM SIGNALS
# Use alternative price sources (HL2, HLC3, WCP) to generate smoother signals.
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="hlc3_ma_cross_bull",
    category="trend",
    direction="bullish",
    params={"fast": 10, "slow": 30},
    param_grid={"fast": [5, 10, 20], "slow": [20, 30, 50]},
    tags=["moving-average", "price-transform"],
)
def hlc3_ma_cross_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """HLC3 fast MA crosses above slow MA — smoother than close-based MA cross."""
    try:
        hlc3 = (df["High"] + df["Low"] + df["Close"]).astype(float) / 3
        fast = hlc3.rolling(int(params["fast"]), min_periods=1).mean()
        slow = hlc3.rolling(int(params["slow"]), min_periods=1).mean()
        cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="hlc3_ma_cross_bear",
    category="trend",
    direction="bearish",
    params={"fast": 10, "slow": 30},
    param_grid={"fast": [5, 10, 20], "slow": [20, 30, 50]},
    tags=["moving-average", "price-transform"],
)
def hlc3_ma_cross_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """HLC3 fast MA crosses below slow MA."""
    try:
        hlc3 = (df["High"] + df["Low"] + df["Close"]).astype(float) / 3
        fast = hlc3.rolling(int(params["fast"]), min_periods=1).mean()
        slow = hlc3.rolling(int(params["slow"]), min_periods=1).mean()
        cross = (fast < slow) & (fast.shift(1) >= slow.shift(1))
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="drawdown_recovery_bull",
    category="momentum",
    direction="bullish",
    params={"threshold": 0.01, "recovery_bars": 3},
    param_grid={"threshold": [0.005, 0.01, 0.02, 0.03], "recovery_bars": [2, 3, 5]},
    tags=["mean-reversion", "drawdown"],
)
def drawdown_recovery_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Price recovers from drawdown > threshold — bounce entry after pullback."""
    try:
        c = df["Close"].astype(float)
        rolling_max = c.rolling(50, min_periods=10).max()
        dd = (c - rolling_max) / rolling_max.replace(0, np.nan)
        was_deep = dd.rolling(int(params["recovery_bars"]), min_periods=1).min() < -params["threshold"]
        recovering = dd > dd.shift(1)
        signal = was_deep & recovering & (dd > -params["threshold"] / 2)
        return signal.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="log_return_momentum_bull",
    category="momentum",
    direction="bullish",
    params={"period": 10, "threshold": 0.0},
    param_grid={"period": [5, 10, 20], "threshold": [0.0, 0.001, 0.002]},
    tags=["momentum", "price-transform"],
)
def log_return_momentum_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Rolling log return crosses above threshold — sustained positive momentum."""
    try:
        c = df["Close"].astype(float)
        lr = np.log(c / c.shift(1))
        roll_lr = lr.rolling(int(params["period"]), min_periods=3).mean()
        cross = (roll_lr > params["threshold"]) & (roll_lr.shift(1) <= params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="log_return_momentum_bear",
    category="momentum",
    direction="bearish",
    params={"period": 10, "threshold": 0.0},
    param_grid={"period": [5, 10, 20], "threshold": [0.0, -0.001, -0.002]},
    tags=["momentum", "price-transform"],
)
def log_return_momentum_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Rolling log return crosses below threshold — sustained negative momentum."""
    try:
        c = df["Close"].astype(float)
        lr = np.log(c / c.shift(1))
        roll_lr = lr.rolling(int(params["period"]), min_periods=3).mean()
        cross = (roll_lr < params["threshold"]) & (roll_lr.shift(1) >= params["threshold"])
        return cross.fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


# ══════════════════════════════════════════════════════════════════════════════
# TREND STATE SIGNALS
# Boolean trend-state indicators from pandas-ta-classic.
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="amat_bull",
    category="trend",
    direction="bullish",
    params={"fast": 8, "slow": 21},
    param_grid={"fast": [6, 8, 13], "slow": [14, 21, 34]},
    tags=["trend-state", "adaptive"],
)
def amat_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """AMAT (Adaptive Moving Average Trend): trend turns bullish."""
    try:
        if not _pta().is_available():
            return pd.Series(False, index=df.index)
        import pandas_ta_classic as pta
        result = pta.amat(df["Close"], fast=int(params["fast"]), slow=int(params["slow"]))
        if result is None:
            return pd.Series(False, index=df.index)
        if isinstance(result, pd.DataFrame):
            # AMAT returns long/short columns
            cols = result.columns.tolist()
            bull_col = next((c for c in cols if "long" in str(c).lower() or "bull" in str(c).lower()), cols[0])
            s = result[bull_col]
        else:
            s = result
        cross = (s > 0) & (s.shift(1) <= 0)
        return cross.reindex(df.index, fill_value=False).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="amat_bear",
    category="trend",
    direction="bearish",
    params={"fast": 8, "slow": 21},
    param_grid={"fast": [6, 8, 13], "slow": [14, 21, 34]},
    tags=["trend-state", "adaptive"],
)
def amat_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """AMAT trend turns bearish."""
    try:
        if not _pta().is_available():
            return pd.Series(False, index=df.index)
        import pandas_ta_classic as pta
        result = pta.amat(df["Close"], fast=int(params["fast"]), slow=int(params["slow"]))
        if result is None:
            return pd.Series(False, index=df.index)
        if isinstance(result, pd.DataFrame):
            cols = result.columns.tolist()
            bear_col = next((c for c in cols if "short" in str(c).lower() or "bear" in str(c).lower()), cols[-1])
            s = result[bear_col]
        else:
            s = result
        cross = (s > 0) & (s.shift(1) <= 0)
        return cross.reindex(df.index, fill_value=False).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="ttm_trend_bull",
    category="trend",
    direction="bullish",
    params={"length": 6},
    param_grid={"length": [5, 6, 8]},
    tags=["trend-state", "ttm"],
)
def ttm_trend_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """TTM Trend turns bullish (bar color flips from red to green)."""
    try:
        if not _pta().is_available():
            return pd.Series(False, index=df.index)
        import pandas_ta_classic as pta
        result = pta.ttm_trend(df["High"], df["Low"], df["Close"], length=int(params["length"]))
        if result is None:
            return pd.Series(False, index=df.index)
        if isinstance(result, pd.DataFrame):
            s = result.iloc[:, 0]
        else:
            s = result
        cross = (s > 0) & (s.shift(1) <= 0)
        return cross.reindex(df.index, fill_value=False).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="long_run_bull",
    category="trend",
    direction="bullish",
    params={"fast": 21, "slow": 55, "slope_bars": 8, "confirm_bars": 5, "min_gap_atr": 0.15},
    param_grid={"fast": [21, 34], "slow": [55, 89]},
    tags=["trend-state", "sustained"],
)
def long_run_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Long Run: both fast and slow SMAs trending up — sustained uptrend entry."""
    try:
        c = df["Close"].astype(float)
        h = df["High"].astype(float)
        l = df["Low"].astype(float)
        fast_len = int(params["fast"])
        slow_len = int(params["slow"])
        slope_bars = int(params.get("slope_bars", 5))
        confirm_bars = int(params.get("confirm_bars", 3))
        min_gap_atr = float(params.get("min_gap_atr", 0.08))
        fast = c.ewm(span=fast_len, adjust=False, min_periods=fast_len).mean()
        slow = c.ewm(span=slow_len, adjust=False, min_periods=slow_len).mean()
        prev_close = c.shift(1)
        tr = pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=14).mean()
        state = (
            (fast > slow)
            & (c > fast)
            & (fast > fast.shift(slope_bars))
            & (slow > slow.shift(slope_bars))
            & ((fast - slow) > atr * min_gap_atr)
        )
        confirmed = state.rolling(confirm_bars, min_periods=confirm_bars).sum().eq(confirm_bars)
        return (confirmed & ~confirmed.shift(1).fillna(False)).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="short_run_bear",
    category="trend",
    direction="bearish",
    params={"fast": 21, "slow": 55, "slope_bars": 8, "confirm_bars": 5, "min_gap_atr": 0.15},
    param_grid={"fast": [21, 34], "slow": [55, 89]},
    tags=["trend-state", "sustained"],
)
def short_run_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Short Run: both fast and slow SMAs trending down — sustained downtrend entry."""
    try:
        c = df["Close"].astype(float)
        h = df["High"].astype(float)
        l = df["Low"].astype(float)
        fast_len = int(params["fast"])
        slow_len = int(params["slow"])
        slope_bars = int(params.get("slope_bars", 5))
        confirm_bars = int(params.get("confirm_bars", 3))
        min_gap_atr = float(params.get("min_gap_atr", 0.08))
        fast = c.ewm(span=fast_len, adjust=False, min_periods=fast_len).mean()
        slow = c.ewm(span=slow_len, adjust=False, min_periods=slow_len).mean()
        prev_close = c.shift(1)
        tr = pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=14).mean()
        state = (
            (fast < slow)
            & (c < fast)
            & (fast < fast.shift(slope_bars))
            & (slow < slow.shift(slope_bars))
            & ((slow - fast) > atr * min_gap_atr)
        )
        confirmed = state.rolling(confirm_bars, min_periods=confirm_bars).sum().eq(confirm_bars)
        return (confirmed & ~confirmed.shift(1).fillna(False)).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


# ══════════════════════════════════════════════════════════════════════════════
# CYCLE SIGNALS (Hilbert-based — best on 1h+ timeframes)
# NOTE: Unstable on 1m data. Included for higher-timeframe discovery jobs.
# ══════════════════════════════════════════════════════════════════════════════

@register_signal(
    name="ebsw_bull",
    category="cycles",
    direction="bullish",
    params={"length": 40, "bars": 15},
    param_grid={"length": [30, 40], "bars": [10, 15]},
    tags=["cycle", "hilbert", "experimental"],
)
def ebsw_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Even Better Sine Wave: cycle phase crosses into bullish half."""
    try:
        if not _pta().is_available():
            return pd.Series(False, index=df.index)
        import pandas_ta_classic as pta
        result = pta.ebsw(df["Close"], length=int(params["length"]), bars=int(params["bars"]))
        if result is None:
            return pd.Series(False, index=df.index)
        s = result if not isinstance(result, pd.DataFrame) else result.iloc[:, 0]
        cross = (s > 0) & (s.shift(1) <= 0)
        return cross.reindex(df.index, fill_value=False).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="ebsw_bear",
    category="cycles",
    direction="bearish",
    params={"length": 40, "bars": 15},
    param_grid={"length": [30, 40], "bars": [10, 15]},
    tags=["cycle", "hilbert", "experimental"],
)
def ebsw_bear(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """Even Better Sine Wave: cycle phase crosses into bearish half."""
    try:
        if not _pta().is_available():
            return pd.Series(False, index=df.index)
        import pandas_ta_classic as pta
        result = pta.ebsw(df["Close"], length=int(params["length"]), bars=int(params["bars"]))
        if result is None:
            return pd.Series(False, index=df.index)
        s = result if not isinstance(result, pd.DataFrame) else result.iloc[:, 0]
        cross = (s < 0) & (s.shift(1) >= 0)
        return cross.reindex(df.index, fill_value=False).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)


@register_signal(
    name="dsp_bull",
    category="cycles",
    direction="bullish",
    params={"cutoff": 0.15},
    param_grid={"cutoff": [0.1, 0.15, 0.2]},
    tags=["cycle", "dsp", "experimental"],
)
def dsp_bull(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    """DSP (Digital Signal Processing) cycle crosses above zero — bullish cycle phase."""
    try:
        if not _pta().is_available():
            return pd.Series(False, index=df.index)
        import pandas_ta_classic as pta
        result = pta.dsp(df["Close"], cutoff=float(params["cutoff"]))
        if result is None:
            return pd.Series(False, index=df.index)
        s = result if not isinstance(result, pd.DataFrame) else result.iloc[:, 0]
        cross = (s > 0) & (s.shift(1) <= 0)
        return cross.reindex(df.index, fill_value=False).fillna(False).astype(bool)
    except Exception:
        return pd.Series(False, index=df.index)
