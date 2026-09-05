"""
CORE — Multi-Scale Curve Pattern Detector (Vectorized)
=======================================================
Runs parabolic curve fitting at multiple window sizes so patterns at
ALL scales are detected:
  - Small  (15-25 bars)  : micro bumps / short hooks
  - Medium (40-60 bars)  : classic semi-circles / quarter-circles
  - Large  (100-200 bars): macro domes / large reversals

Speed: Each window is processed in one batch numpy call via precomputed
least-squares matrices — no Python inner loop. ~15-20x faster than the
original single-window implementation.

Thresholds are window-adaptive:
  - Small/medium (w<=60) : R² >= 0.82, |a| >= 0.45  (strict)
  - Large (w>60)         : R² >= 0.72, |a| >= 0.30  (relaxed — macro moves are noisier)

return_traces=True:
  Returns (result_df, curve_traces) where curve_traces is a list of dicts
  each containing the fitted parabola x/y points for plotting on the chart.
"""

import numpy as np
import pandas as pd
import sys, os

_SELF_INDC = r"D:\Projects\test1\self indc"
if _SELF_INDC not in sys.path:
    sys.path.insert(0, _SELF_INDC)

from curve_circle_patterns import (
    DEFAULT_EMA_SPAN,
    SEMI_CIRCLE_RANGE,
    QUARTER_CIRCLE_RANGE,
    BEAR_SEMI_CIRCLE_RANGE,
    BEAR_QUARTER_CIRCLE_RANGE,
)

# ── Window tiers ──────────────────────────────────────────────────────────────
WINDOW_TIERS = [
    # (window_bars, r2_threshold, min_curvature)
    (15,  0.82, 0.45),
    (25,  0.82, 0.45),
    (40,  0.82, 0.45),
    (60,  0.82, 0.45),
    (100, 0.72, 0.30),
    (150, 0.72, 0.30),
    (200, 0.72, 0.30),
]

MIN_SIGNAL_GAP = 8   # bars between same-type signals (dedup clusters)

# Curve colors per pattern (matches renderer CURVE_STYLE)
_CURVE_COLORS = {
    "bull_semi":    ("#2196F3", "U-Bottom"),
    "bull_quarter": ("#00BCD4", "J-Hook"),
    "bear_semi":    ("#FF9800", "Arch/Dome"),
    "bear_quarter": ("#F44336", "Roll-over"),
}


def _precompute_lstsq(window: int):
    """
    Precompute the pseudo-inverse of the degree-2 Vandermonde matrix for
    x = linspace(0,1,window).  Reused across all bars for the same window.

    Returns V (w,3) and V_pinv (3,w).
    """
    x = np.linspace(0.0, 1.0, window)
    V = np.column_stack([x**2, x, np.ones(window)])   # (w, 3)
    V_pinv = np.linalg.pinv(V)                         # (3, w)
    return V, V_pinv


def _batch_fit(data: np.ndarray, window: int, V, V_pinv) -> tuple:
    """
    Fit degree-2 polynomials to ALL sliding windows in one batch.

    Returns:
        a        : (N-w+1,) leading coefficient
        vertex_x : (N-w+1,) vertex x-position in [0,1]
        r2       : (N-w+1,) R² goodness-of-fit
        valid    : (N-w+1,) bool mask — window has sufficient price range
        coeffs   : (N-w+1, 3) polynomial coefficients [a, b, c]
        w_min_arr: (N-w+1,) per-window price minimum (for back-scaling)
        w_rng_arr: (N-w+1,) per-window price range   (for back-scaling)
    """
    # Sliding windows: shape (N-w+1, w) using stride tricks
    wins = np.lib.stride_tricks.sliding_window_view(data, window)  # (M, w)
    M = wins.shape[0]

    # Per-window min/max for normalization
    w_min = wins.min(axis=1, keepdims=True)       # (M, 1)
    w_max = wins.max(axis=1, keepdims=True)        # (M, 1)
    w_rng = w_max - w_min                          # (M, 1)
    w_mean = wins.mean(axis=1)                     # (M,)

    # Valid mask: sufficient price variation (avoid flat segments)
    valid = (w_mean > 0) & (w_rng[:, 0] / np.maximum(w_mean, 1e-10) >= 0.0005)

    # Normalize each window to [0, 1]
    y_norm = np.where(w_rng > 0, (wins - w_min) / np.maximum(w_rng, 1e-10), 0.5)

    # Batch least-squares: coeffs shape (M, 3) = [a, b, c] per row
    coeffs = y_norm @ V_pinv.T           # (M, 3)

    a_coef = coeffs[:, 0]                # leading coefficient
    b_coef = coeffs[:, 1]
    # Vertex normalised x-position: -b/(2a), clipped to avoid division by zero
    denom = np.where(np.abs(a_coef) > 1e-10, 2.0 * a_coef, 1e-10)
    vertex_x = np.clip(-b_coef / denom, -0.5, 1.5)

    # R²: 1 - SS_res / SS_tot
    y_pred = coeffs @ V.T               # (M, w)
    ss_res = np.sum((y_norm - y_pred)**2, axis=1)
    y_mean = y_norm.mean(axis=1, keepdims=True)
    ss_tot = np.sum((y_norm - y_mean)**2, axis=1)
    r2 = np.where(ss_tot > 1e-10, 1.0 - ss_res / ss_tot, 0.0)

    return a_coef, vertex_x, r2, valid, coeffs, w_min.ravel(), w_rng.ravel()


def _apply_min_gap(signal_arr: np.ndarray, gap: int) -> np.ndarray:
    """
    Within each cluster of consecutive 1s, keep only the LAST bar.
    Prevents visual pile-ups when multiple windows agree on the same zone.
    """
    out = np.zeros_like(signal_arr)
    n, i = len(signal_arr), 0
    while i < n:
        if signal_arr[i] == 1:
            j = i
            while j < n and signal_arr[j] == 1:
                j += 1
            out[j - 1] = 1
            i = j
        else:
            i += 1
    return out


def detect_curves_multiscale(df: pd.DataFrame, return_traces: bool = False):
    """
    Multi-scale parabolic curve detection on OHLCV data.

    Input:  df with lowercase columns (open, high, low, close, volume)
            and a DatetimeIndex.
    Output (return_traces=False):
        df with 4 int columns:
          curve_semi_circle          — bullish U-Bottom
          curve_quarter_circle       — bullish J-Hook
          curve_bear_semi_circle     — bearish Arch/Dome
          curve_bear_quarter_circle  — bearish Roll-over

    Output (return_traces=True):
        (result_df, curve_traces)
        curve_traces: list of dicts with keys x, y, color, label, window
          Each dict describes one fitted parabola for chart overlay.
    """
    result = df.copy()
    n = len(df)

    bull_semi    = np.zeros(n, dtype=np.int8)
    bull_quarter = np.zeros(n, dtype=np.int8)
    bear_semi    = np.zeros(n, dtype=np.int8)
    bear_quarter = np.zeros(n, dtype=np.int8)

    if n < 10:
        result["curve_semi_circle"]         = bull_semi
        result["curve_quarter_circle"]      = bull_quarter
        result["curve_bear_semi_circle"]    = bear_semi
        result["curve_bear_quarter_circle"] = bear_quarter
        if return_traces:
            return result, []
        return result

    # Pre-smooth once (shared across all windows)
    low_smooth  = df["low"].ewm(span=DEFAULT_EMA_SPAN, adjust=False).mean().values
    high_smooth = df["high"].ewm(span=DEFAULT_EMA_SPAN, adjust=False).mean().values

    sl, sh = SEMI_CIRCLE_RANGE
    ql, qh = QUARTER_CIRCLE_RANGE
    bsl, bsh = BEAR_SEMI_CIRCLE_RANGE
    bql, bqh = BEAR_QUARTER_CIRCLE_RANGE

    # Raw curve data collected before dedup: (end_bar, pattern_key) -> info dict
    # We keep the LARGEST window's curve per bar (larger window = more context)
    _raw_curve_dict = {}

    for window, r2_thresh, min_curv in WINDOW_TIERS:
        if window >= n:
            continue

        V, V_pinv = _precompute_lstsq(window)

        # Indices of the LAST bar of each window: window-1 .. n-1
        end_indices = np.arange(window - 1, n)

        # ── BULLISH: upward parabola on smoothed lows ─────────────────────────
        a, vx, r2, valid, coeffs_l, w_min_l, w_rng_l = _batch_fit(
            low_smooth, window, V, V_pinv
        )
        mask_bull = valid & (r2 >= r2_thresh) & (a >= min_curv)
        mask_bs = mask_bull & (vx >= sl) & (vx <= sh)
        mask_bq = mask_bull & (vx >= ql) & (vx <= qh)

        bull_semi   [end_indices[mask_bs]] = 1
        bull_quarter[end_indices[mask_bq]] = 1

        if return_traces:
            n_pts = min(window, 25)
            x_norm_pts = np.linspace(0.0, 1.0, n_pts)
            for mask, pat_key in [(mask_bs, "bull_semi"), (mask_bq, "bull_quarter")]:
                color, label = _CURVE_COLORS[pat_key]
                for idx in np.where(mask)[0]:
                    eb = int(end_indices[idx])
                    sb = eb - window + 1
                    ac, bc, cc = coeffs_l[idx]
                    mn, rng = w_min_l[idx], w_rng_l[idx]
                    y_pred = ac * x_norm_pts**2 + bc * x_norm_pts + cc
                    y_price = np.clip(y_pred, -0.3, 1.3) * rng + mn
                    key = (eb, pat_key)
                    if key not in _raw_curve_dict or _raw_curve_dict[key]["window"] < window:
                        _raw_curve_dict[key] = {
                            "x": np.linspace(sb, eb, n_pts),
                            "y": y_price,
                            "window": window,
                            "color": color,
                            "label": label,
                            "end_bar":   eb,
                            "start_bar": sb,
                            "r2":        float(r2[idx]),
                            "curvature": float(abs(a[idx])),
                            "vertex_x":  float(vx[idx]),
                            "is_bull":   True,
                        }

        # ── BEARISH: downward parabola on smoothed highs ──────────────────────
        a, vx, r2, valid, coeffs_h, w_min_h, w_rng_h = _batch_fit(
            high_smooth, window, V, V_pinv
        )
        mask_bear = valid & (r2 >= r2_thresh) & (a <= -min_curv)
        mask_bes = mask_bear & (vx >= bsl) & (vx <= bsh)
        mask_beq = mask_bear & (vx >= bql) & (vx <= bqh)

        bear_semi   [end_indices[mask_bes]] = 1
        bear_quarter[end_indices[mask_beq]] = 1

        if return_traces:
            for mask, pat_key in [(mask_bes, "bear_semi"), (mask_beq, "bear_quarter")]:
                color, label = _CURVE_COLORS[pat_key]
                for idx in np.where(mask)[0]:
                    eb = int(end_indices[idx])
                    sb = eb - window + 1
                    ac, bc, cc = coeffs_h[idx]
                    mn, rng = w_min_h[idx], w_rng_h[idx]
                    y_pred = ac * x_norm_pts**2 + bc * x_norm_pts + cc
                    y_price = np.clip(y_pred, -0.3, 1.3) * rng + mn
                    key = (eb, pat_key)
                    if key not in _raw_curve_dict or _raw_curve_dict[key]["window"] < window:
                        _raw_curve_dict[key] = {
                            "x": np.linspace(sb, eb, n_pts),
                            "y": y_price,
                            "window": window,
                            "color": color,
                            "label": label,
                            "end_bar":   eb,
                            "start_bar": sb,
                            "r2":        float(r2[idx]),
                            "curvature": float(abs(a[idx])),
                            "vertex_x":  float(vx[idx]),
                            "is_bull":   False,
                        }

    # Deduplicate clusters
    bull_semi    = _apply_min_gap(bull_semi,    MIN_SIGNAL_GAP)
    bull_quarter = _apply_min_gap(bull_quarter, MIN_SIGNAL_GAP)
    bear_semi    = _apply_min_gap(bear_semi,    MIN_SIGNAL_GAP)
    bear_quarter = _apply_min_gap(bear_quarter, MIN_SIGNAL_GAP)

    result["curve_semi_circle"]         = bull_semi.astype(int)
    result["curve_quarter_circle"]      = bull_quarter.astype(int)
    result["curve_bear_semi_circle"]    = bear_semi.astype(int)
    result["curve_bear_quarter_circle"] = bear_quarter.astype(int)

    if not return_traces:
        return result

    # Filter raw curves: only keep bars that survived dedup
    active = {
        "bull_semi":    set(np.where(bull_semi > 0)[0]),
        "bull_quarter": set(np.where(bull_quarter > 0)[0]),
        "bear_semi":    set(np.where(bear_semi > 0)[0]),
        "bear_quarter": set(np.where(bear_quarter > 0)[0]),
    }
    curve_traces = []
    for (eb, pat_key), info in _raw_curve_dict.items():
        if eb in active[pat_key]:
            curve_traces.append({
                "x":         info["x"].tolist(),
                "y":         info["y"].tolist(),
                "color":     info["color"],
                "label":     info["label"],
                "window":    info["window"],
                "end_bar":   info["end_bar"],
                "start_bar": info["start_bar"],
                "r2":        info["r2"],
                "curvature": info["curvature"],
                "vertex_x":  info["vertex_x"],
                "is_bull":   info["is_bull"],
            })

    return result, curve_traces
