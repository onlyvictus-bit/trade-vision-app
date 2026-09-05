"""
adv_trend_detector.py — Advanced Trendline Detection via trendln
=================================================================
Adapted from D:/Projects/test1/test in claud/New folder/part 2/core/trend_detector.py
Changes:
  - Stripped: @st.cache_data, streamlit, plotly
  - Fixed: trendln sys.path (absolute, not relative)
  - Changed: from .deduplicator → from deduplicator (same indicators/ folder)
  - Added: extract_trendline_events() — per-bar TOUCH / BREAK scanning
"""
import sys
import os
import numpy as np
import pandas as pd

# ── trendln library (external repo, not installed as package) ─────────────
_TRENDLN_PATH = r'D:\Projects\test1\test in claud\trendln'
if os.path.isdir(_TRENDLN_PATH) and _TRENDLN_PATH not in sys.path:
    sys.path.insert(0, _TRENDLN_PATH)

from deduplicator import cluster_trendlines  # same indicators/ folder

try:
    from trendln import calc_support_resistance, METHOD_NUMDIFF, METHOD_NSQUREDLOGN
    HAS_TRENDLN = True
except ImportError:
    HAS_TRENDLN = False

MULTI_WINDOWS = [20, 40, 72, 125, 200]


def _true_range_atr(lows: np.ndarray, highs: np.ndarray, closes: np.ndarray, length: int = 14) -> np.ndarray:
    """Simple rolling ATR used by the deterministic fallback detector."""
    prev = np.r_[closes[0], closes[:-1]]
    tr = np.maximum.reduce([highs - lows, np.abs(highs - prev), np.abs(lows - prev)])
    atr = pd.Series(tr).rolling(length, min_periods=1).mean().to_numpy(float)
    return np.where(np.isfinite(atr) & (atr > 0), atr, np.nanmedian(tr[np.isfinite(tr)]) or 1.0)


def _pivot_indices(values: np.ndarray, start: int, end: int, kind: str, wing: int = 3) -> np.ndarray:
    """Find local swing highs/lows inside [start, end]."""
    out = []
    lo = max(start + wing, wing)
    hi = min(end - wing, len(values) - wing - 1)
    for i in range(lo, hi + 1):
        window = values[i - wing:i + wing + 1]
        if kind == 'low' and values[i] <= np.nanmin(window):
            out.append(i)
        elif kind == 'high' and values[i] >= np.nanmax(window):
            out.append(i)
    return np.asarray(out, dtype=int)


def _fit_constrained_line(x: np.ndarray, y: np.ndarray, prices: np.ndarray,
                          start: int, end: int, line_type: str,
                          tol: float):
    """
    Fit a slope/intercept through swing points and shift it so support stays
    below lows and resistance stays above highs. Returns trendln-compatible tuple.
    """
    if len(x) < 2:
        return None
    try:
        m, b = np.polyfit(x.astype(float), y.astype(float), 1)
    except Exception:
        return None

    segment_x = np.arange(start, end + 1)
    segment_prices = prices[start:end + 1]
    line = m * segment_x + b
    residual = segment_prices - line
    if line_type == 'support':
        b += float(np.nanmin(residual))  # shift down to respect lows
    else:
        b += float(np.nanmax(residual))  # shift up to respect highs

    line = m * segment_x + b
    residual = segment_prices - line
    if line_type == 'support':
        violations = np.sum(residual < -tol)
        touch_mask = np.abs(residual) <= tol
    else:
        violations = np.sum(residual > tol)
        touch_mask = np.abs(residual) <= tol
    if violations > max(2, int(len(segment_x) * 0.08)):
        return None

    touch_idxs = segment_x[touch_mask]
    if len(touch_idxs) < 3:
        return None
    denom = max(float(np.nanmean(np.abs(segment_prices))), 1e-9)
    ser = float(np.sqrt(np.nanmean(np.square(residual[touch_mask]))) / denom)
    ys = [float(m * i + b) for i in touch_idxs]
    return (touch_idxs.astype(int), (float(m), float(b), ys, ser, 0.0, 0.0))


def _segment_extreme_anchors(values: np.ndarray, start: int, end: int, kind: str) -> np.ndarray:
    """Fallback anchors for smooth trends with few formal pivots."""
    chunks = np.array_split(np.arange(start, end + 1), 4)
    anchors = [start, end]
    for chunk in chunks:
        if len(chunk) == 0:
            continue
        vals = values[chunk]
        rel = int(np.nanargmin(vals) if kind == 'low' else np.nanargmax(vals))
        anchors.append(int(chunk[rel]))
    return np.asarray(sorted(set(anchors)), dtype=int)


def detect_optimized_trendlines(lows: np.ndarray, highs: np.ndarray, closes: np.ndarray,
                                n_local: int, min_touches: int = 3):
    """
    Deterministic support/resistance detector inspired by TrendLineAutomation.
    It is dependency-free and keeps recent/live lines available when trendln is
    missing or returns no useful candidates.
    """
    if n_local < 20:
        return [], []
    atr = _true_range_atr(lows, highs, closes)
    all_sup, all_res = [], []
    for w in MULTI_WINDOWS:
        if w >= n_local:
            continue
        step = max(6, w // 3)
        first_end = max(w - 1, n_local - 220)
        end_points = list(range(first_end, n_local, step))
        if not end_points or end_points[-1] != n_local - 1:
            end_points.append(n_local - 1)
        for end in end_points:
            start = max(0, end - w + 1)
            tol = max(float(np.nanmedian(atr[start:end + 1])) * 0.18,
                      float(np.nanmedian(closes[start:end + 1])) * 0.001)

            low_piv = _pivot_indices(lows, start, end, 'low')
            high_piv = _pivot_indices(highs, start, end, 'high')
            if len(low_piv) < min_touches:
                low_piv = _segment_extreme_anchors(lows, start, end, 'low')
            if len(high_piv) < min_touches:
                high_piv = _segment_extreme_anchors(highs, start, end, 'high')
            if len(low_piv) >= min_touches:
                t = _fit_constrained_line(low_piv, lows[low_piv], lows, start, end, 'support', tol)
                if t is not None:
                    all_sup.append(t)
            if len(high_piv) >= min_touches:
                t = _fit_constrained_line(high_piv, highs[high_piv], highs, start, end, 'resistance', tol)
                if t is not None:
                    all_res.append(t)
    return all_sup, all_res


def detect_all_trendlines(lows: np.ndarray, highs: np.ndarray,
                           n_local: int, errpct: float = 0.008):
    """
    Detect support + resistance trendlines across multiple windows.
    Raises ImportError if trendln is not available.
    Returns (all_support_lines, all_resistance_lines).
    Each line is a trendln tuple: (idxs, (m, b, ys, ser, intcpt_err, area)).
    """
    if not HAS_TRENDLN:
        raise ImportError(
            f"trendln library not found. Expected at: {_TRENDLN_PATH}\n"
            "Clone from https://github.com/GregoryMorse/trendln and place at that path."
        )
    all_sup, all_res = [], []
    for w in MULTI_WINDOWS:
        if w >= n_local:
            continue
        try:
            mins, maxs = calc_support_resistance(
                (lows, highs),
                extmethod=METHOD_NUMDIFF,
                method=METHOD_NSQUREDLOGN,
                window=w, errpct=errpct, accuracy=2,
            )
            _, _, mintrend, _ = mins
            _, _, maxtrend, _ = maxs
            all_sup.extend(mintrend)
            all_res.extend(maxtrend)
        except Exception as e:
            print(f"[WARN] adv_trendln window={w} failed: {str(e)[:120]}")
    return all_sup, all_res


def score_trendline(trend, n_local: int) -> float:
    """
    Score in [0, 1] based on touch count, standard error, and recency.
    More touches + lower error + more recent → higher score.
    """
    idxs, (m, b, ys, ser, intcpt_err, area) = trend
    touch_score   = min(1.0, (len(idxs) - 2) / 5.0)
    ser_score     = 1.0 / (1.0 + ser * 1000.0)
    recency_score = float(idxs[-1]) / (n_local - 1) if n_local > 1 else 0.0
    return float(np.clip(touch_score * 0.5 + ser_score * 0.3 + recency_score * 0.2, 0.0, 1.0))


def prepare_trendlines(trends, min_touches: int, max_lines: int, n_local: int):
    """
    Filter by min_touches, score, sort descending, return top max_lines.
    Returns list of (trend, score) tuples.
    """
    scored = [
        (t, score_trendline(t, n_local))
        for t in trends
        if len(t[0]) >= min_touches
    ]
    scored.sort(key=lambda x: -x[1])
    return scored[:max_lines]


def extract_trendline_events(typed_scored_trends, closes: np.ndarray,
                              idx_to_ts: dict, errpct: float = 0.008) -> list:
    """
    Scan every bar between start_bar and end_bar of each trendline for:
      TOUCH: |close - line_price| / line_price < errpct
      BREAK: sign(close - line_price) flips vs previous bar

    Parameters
    ----------
    typed_scored_trends : list of (trend, score, line_type)
        trend  = (idxs, (m, b, ys, ser, intcpt_err, area))
        line_type = 'support' | 'resistance'
    closes      : np.ndarray, close prices indexed 0..n-1
    idx_to_ts   : dict, bar_index → timestamp (int unix or 'YYYY-MM-DD')
    errpct      : float, fraction of line_price for TOUCH detection

    Returns
    -------
    list of dicts with keys: type, ts, bar_price, line_price, line_type, color
    """
    events = []
    n = len(closes)

    for line_no, (t, trend_score, line_type) in enumerate(typed_scored_trends):
        idxs, (m, b, *_) = t
        start_bar = int(idxs[0])
        end_bar   = int(idxs[-1])
        line_color = '#22c55e' if line_type == 'support' else '#ef4444'

        prev_side = None
        for i in range(start_bar, min(end_bar + 1, n)):
            if i not in idx_to_ts:
                continue
            close      = float(closes[i])
            line_price = float(m * i + b)
            if line_price <= 0:
                prev_side = None
                continue

            dist_pct = abs(close - line_price) / line_price
            side     = 1 if close >= line_price else -1

            # TOUCH: price within errpct of line
            if dist_pct < errpct:
                events.append({
                    'type':       'TOUCH',
                    'line_id':    line_no,
                    'ts':         idx_to_ts[i],
                    'bar_price':  round(close, 2),
                    'line_price': round(line_price, 2),
                    'line_type':  line_type,
                    'color':      line_color,
                })

            # BREAK: price crossed to opposite side vs previous bar
            if prev_side is not None and side != prev_side:
                # Bull-break (price rose above line) = green; bear-break = red
                break_color = '#22c55e' if side > 0 else '#ef4444'
                events.append({
                    'type':       'BREAK',
                    'line_id':    line_no,
                    'ts':         idx_to_ts[i],
                    'bar_price':  round(close, 2),
                    'line_price': round(line_price, 2),
                    'line_type':  line_type,
                    'color':      break_color,
                })

                # Retest / failed-break annotation within the next few bars.
                for j in range(i + 1, min(i + 7, n)):
                    if j not in idx_to_ts:
                        continue
                    jp = float(m * j + b)
                    if jp <= 0:
                        continue
                    jdist = abs(float(closes[j]) - jp) / jp
                    jside = 1 if float(closes[j]) >= jp else -1
                    if jdist < errpct:
                        events.append({
                            'type':       'RETEST',
                            'line_id':    line_no,
                            'ts':         idx_to_ts[j],
                            'bar_price':  round(float(closes[j]), 2),
                            'line_price': round(jp, 2),
                            'line_type':  line_type,
                            'color':      '#38bdf8',
                        })
                        break
                    if jside != side:
                        events.append({
                            'type':       'FAILED_BREAK',
                            'line_id':    line_no,
                            'ts':         idx_to_ts[j],
                            'bar_price':  round(float(closes[j]), 2),
                            'line_price': round(jp, 2),
                            'line_type':  line_type,
                            'color':      '#f59e0b',
                        })
                        break

            prev_side = side

    return events


__all__ = [
    'detect_all_trendlines', 'score_trendline', 'prepare_trendlines',
    'detect_optimized_trendlines', 'cluster_trendlines', 'extract_trendline_events', 'HAS_TRENDLN',
    'MULTI_WINDOWS',
]
