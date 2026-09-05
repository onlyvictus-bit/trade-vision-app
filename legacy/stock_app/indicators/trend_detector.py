"""
trend_detector.py — Support/Resistance Trend Line Detection
============================================================
Algorithm:
  1. Find swing highs (local maxima) and swing lows (local minima) using
     a rolling window of `pivot_bars` on each side.
  2. Group nearby pivots (within `cluster_pct` % of each other).
  3. Fit a linear regression through each group of >= `min_touches` pivots.
  4. Classify each line as support or resistance.
  5. Keep only lines whose most recent touch is within `max_age_bars`.

Returns list of trend line dicts with keys:
  slope, intercept, r2, touches, start_bar, end_bar,
  start_price, end_price, line_type ('support'|'resistance'),
  start_ts, end_ts, color
"""

import numpy as np
import pandas as pd

PIVOT_BARS   = 5     # bars on each side to confirm a swing point
MIN_TOUCHES  = 3     # minimum pivot touches to form a line
MAX_AGE_BARS = 100   # ignore lines whose last touch is older than this
CLUSTER_PCT  = 0.012 # group pivots within 1.2% price band
MAX_LINES    = 10    # max lines to return (strongest R² kept)

_SUPPORT_COLOR    = "#22c55e"   # green
_RESISTANCE_COLOR = "#ef4444"   # red


def _find_pivots(prices: np.ndarray, side_bars: int) -> np.ndarray:
    """Return boolean mask of local extrema positions."""
    n = len(prices)
    pivots = np.zeros(n, dtype=bool)
    for i in range(side_bars, n - side_bars):
        window = prices[i - side_bars : i + side_bars + 1]
        if prices[i] == window.max() or prices[i] == window.min():
            pivots[i] = True
    return pivots


def _cluster_pivots(indices: np.ndarray, prices: np.ndarray,
                    cluster_pct: float) -> list:
    """
    Group indices whose prices are within cluster_pct of each other.
    Returns list of groups, each group is a list of bar indices.
    Only returns groups with >= 2 members.
    """
    if len(indices) == 0:
        return []
    sorted_idx = indices[np.argsort(prices[indices])]
    groups = [[sorted_idx[0]]]
    for idx in sorted_idx[1:]:
        ref_price = prices[groups[-1][-1]]
        if abs(prices[idx] - ref_price) / max(ref_price, 1e-10) <= cluster_pct:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return [g for g in groups if len(g) >= 2]


def _fit_line(indices: np.ndarray, prices: np.ndarray) -> tuple:
    """
    Linear regression through (index, price) pairs.
    Returns (slope, intercept, r2).
    """
    x = indices.astype(float)
    y = prices[indices]
    if len(x) < 2:
        return 0.0, float(y.mean()), 0.0
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 1e-10 else 1.0
    return float(slope), float(intercept), float(r2)


def detect_trend_lines(
    df: pd.DataFrame,
    is_intraday: bool = True,
    idx_to_ts: dict = None,
    pivot_bars:   int   = PIVOT_BARS,
    min_touches:  int   = MIN_TOUCHES,
    max_age_bars: int   = MAX_AGE_BARS,
    cluster_pct:  float = CLUSTER_PCT,
    max_lines:    int   = MAX_LINES,
) -> list:
    """
    Detect support/resistance trend lines.

    Parameters
    ----------
    df         : OHLCV DataFrame with DatetimeIndex (columns: open,high,low,close,volume).
    is_intraday: Unused here; kept for API symmetry with curve detector.
    idx_to_ts  : {bar_index: timestamp} mapping (same encoding as curve patterns).
                 If None, bar indices are used as timestamps.
    pivot_bars  : bars on each side required to confirm a swing point.
    min_touches : minimum pivot touches to form a trend line.
    max_age_bars: lines whose last pivot is older than this many bars are excluded.
    cluster_pct : price proximity threshold for grouping pivots (fraction).
    max_lines   : maximum number of lines to return (highest R² kept).

    Returns
    -------
    list of dicts with keys: slope, intercept, r2, touches, start_bar, end_bar,
    start_price, end_price, line_type, start_ts, end_ts, color, pivot_bars (list of indices)
    """
    n     = len(df)
    highs = df["high"].values.astype(float)
    lows  = df["low"].values.astype(float)
    idx_map = idx_to_ts or {}

    if n < pivot_bars * 2 + min_touches:
        return []

    # ── Find pivot highs (resistance candidates) ─────────────────────────────
    hi_pivot_mask = _find_pivots(highs, pivot_bars)
    hi_pivots     = np.where(hi_pivot_mask)[0]
    # Only keep pivots within max_age_bars of the last bar
    hi_pivots = hi_pivots[hi_pivots >= n - max_age_bars]

    # ── Find pivot lows (support candidates) ──────────────────────────────────
    lo_pivot_mask = _find_pivots(lows, pivot_bars)
    lo_pivots     = np.where(lo_pivot_mask)[0]
    lo_pivots     = lo_pivots[lo_pivots >= n - max_age_bars]

    lines = []

    def _process_group(group: list, prices: np.ndarray, line_type: str) -> None:
        group_arr = np.array(sorted(group))
        if len(group_arr) < min_touches:
            return
        slope, intercept, r2 = _fit_line(group_arr, prices)
        if r2 < 0.30:
            return
        start_bar = int(group_arr[0])
        end_bar   = int(group_arr[-1])
        # Extend projected end to just beyond last pivot
        end_bar_ext = min(n - 1, end_bar + pivot_bars * 2)
        start_price = float(slope * start_bar + intercept)
        end_price   = float(slope * end_bar_ext + intercept)
        color = _RESISTANCE_COLOR if line_type == "resistance" else _SUPPORT_COLOR
        lines.append({
            "slope":       round(slope, 6),
            "intercept":   round(intercept, 4),
            "r2":          round(r2, 4),
            "touches":     len(group_arr),
            "start_bar":   start_bar,
            "end_bar":     end_bar_ext,
            "start_price": round(start_price, 2),
            "end_price":   round(end_price, 2),
            "line_type":   line_type,
            "start_ts":    idx_map.get(start_bar, start_bar),
            "end_ts":      idx_map.get(end_bar_ext, end_bar_ext),
            "color":       color,
            "pivot_bars":  group_arr.tolist(),
        })

    # ── Process resistance lines (from pivot highs) ───────────────────────────
    for group in _cluster_pivots(hi_pivots, highs, cluster_pct):
        _process_group(group, highs, "resistance")

    # ── Process support lines (from pivot lows) ───────────────────────────────
    for group in _cluster_pivots(lo_pivots, lows, cluster_pct):
        _process_group(group, lows, "support")

    # Sort by R² descending, keep top max_lines
    lines.sort(key=lambda x: -x["r2"])
    return lines[:max_lines]
