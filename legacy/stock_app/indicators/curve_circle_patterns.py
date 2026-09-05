"""
curve_circle_patterns.py
========================
Detects bullish AND bearish curve patterns across all timeframes.

Uses Min-Max geometric normalisation so the same R² / curvature thresholds
work regardless of timeframe or price scale.

BULLISH patterns (fitted to smoothed LOWS, parabola opens upward a > 0)
------------------------------------------------------------------------
  curve_semi_circle      : vertex at 38-62% of window  → U-Bottom (lows formed a trough)
  curve_quarter_circle   : vertex at  0-25% of window  → J-Hook   (lows bottomed, now hooking up)

BEARISH patterns (fitted to smoothed HIGHS, parabola opens downward a < 0)
---------------------------------------------------------------------------
  curve_bear_semi_circle : vertex at 38-62% of window  → Arch/Dome (highs formed a peak, now declining)
  curve_bear_quarter_circle: vertex at 75-100% of window → Roll-over (highs just peaked, now turning down)

Signal output columns (consumed by signal_adapter.py / run_strategy):
  curve_semi_circle        -- 1 when a bullish U-Bottom completes
  curve_quarter_circle     -- 1 when a bullish J-Hook completes
  curve_bear_semi_circle   -- 1 when a bearish Arch/Dome completes
  curve_bear_quarter_circle-- 1 when a bearish Roll-over completes
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REQUIRED_PRICE_COLUMNS = ("open", "high", "low", "close", "volume")

# --- per-timeframe window sizes (bars) -----------------------------------
# Larger windows give smoother but laggier fits; tune as desired.
_TF_WINDOW: dict[str, int] = {
    "1":    25,   # 1-minute  — short because micro-structure is noisy
    "3":    30,
    "5":    35,
    "15":   40,
    "30":   40,
    "60":   45,   # 1-hour
    "240":  45,   # 4-hour
    "1440": 50,   # 1-day
}
DEFAULT_WINDOW   = 40        # fallback if timeframe cannot be inferred
DEFAULT_EMA_SPAN = 3         # smoothing applied to Low before fitting
R2_THRESHOLD     = 0.82      # minimum goodness-of-fit to qualify a pattern
MIN_CURVATURE    = 0.45      # minimum parabola opening (a-coefficient after normalisation)

# vertex x-position boundaries (normalised 0..1)
# Bullish (lows, upward parabola)
SEMI_CIRCLE_RANGE         = (0.38, 0.62)   # U-Bottom: trough in the middle
QUARTER_CIRCLE_RANGE      = (0.00, 0.25)   # J-Hook:   trough at start, hooking up

# Bearish (highs, downward parabola)
BEAR_SEMI_CIRCLE_RANGE    = (0.38, 0.62)   # Arch/Dome: peak in the middle
BEAR_QUARTER_CIRCLE_RANGE = (0.75, 1.00)   # Roll-over: peak near the right end

DEFAULT_RELIANCE_ROOT = Path(
    r"D:\Projects\test1\indicator_data\reliance_timeframes"
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _infer_timeframe_minutes(df: pd.DataFrame) -> str:
    """
    Estimate timeframe from median bar spacing and return the nearest
    key present in _TF_WINDOW.  Falls back to the closest numerical key.
    """
    if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 3:
        return str(DEFAULT_WINDOW)

    deltas_min = (
        pd.Series(df.index).diff().dropna().dt.total_seconds() / 60
    )
    median_min = deltas_min.median()

    # Map to the nearest standard resolution
    candidates = {int(k): k for k in _TF_WINDOW}
    nearest = min(candidates.keys(), key=lambda x: abs(x - median_min))
    return candidates[nearest]


def _fit_curve(y_smooth: np.ndarray) -> tuple[float, float, float, np.ndarray]:
    """
    Fit a degree-2 polynomial to normalised series.

    Uses raw numpy scaling (faster than MinMaxScaler in tight loops).
    Returns (a, vertex_x_norm, r2, y_predicted_norm).
    """
    n     = len(y_smooth)
    s_min = y_smooth.min()
    s_max = y_smooth.max()
    y_norm = (y_smooth - s_min) / (s_max - s_min)   # [0, 1]
    x_norm = np.linspace(0.0, 1.0, n)

    coeffs      = np.polyfit(x_norm, y_norm, 2)
    a, b, _     = coeffs
    y_pred_norm = np.polyval(coeffs, x_norm)
    r2          = float(r2_score(y_norm, y_pred_norm))

    vertex_x = -b / (2.0 * a) if a != 0.0 else 0.5

    return a, vertex_x, r2, y_pred_norm


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scan df for bullish AND bearish curve pattern completions.

    Accepts any OHLCV DataFrame with a DatetimeIndex (UTC preferred).
    Works correctly for all standard timeframes because geometry is
    normalised per window.

    Returns df with four additional boolean-as-int columns:
      curve_semi_circle          -- bullish U-Bottom (from lows)
      curve_quarter_circle       -- bullish J-Hook   (from lows)
      curve_bear_semi_circle     -- bearish Arch/Dome (from highs)
      curve_bear_quarter_circle  -- bearish Roll-over (from highs)
    """
    result   = df.copy()
    n        = len(df)
    bull_semi    = np.zeros(n, dtype=np.int8)
    bull_quarter = np.zeros(n, dtype=np.int8)
    bear_semi    = np.zeros(n, dtype=np.int8)
    bear_quarter = np.zeros(n, dtype=np.int8)

    if n < 10:
        result["curve_semi_circle"]          = bull_semi
        result["curve_quarter_circle"]       = bull_quarter
        result["curve_bear_semi_circle"]     = bear_semi
        result["curve_bear_quarter_circle"]  = bear_quarter
        return result

    tf_key = _infer_timeframe_minutes(df)
    window = _TF_WINDOW.get(tf_key, DEFAULT_WINDOW)
    window = min(window, n)

    # Pre-smooth lows and highs once
    low_smooth  = df["low"].ewm(span=DEFAULT_EMA_SPAN, adjust=False).mean().values
    high_smooth = df["high"].ewm(span=DEFAULT_EMA_SPAN, adjust=False).mean().values

    for end in range(window - 1, n):
        start = end - window + 1

        # --- BULLISH: fit upward parabola to smoothed lows -------------------
        seg_low   = low_smooth[start : end + 1]
        rng_low   = seg_low.max() - seg_low.min()
        mean_low  = seg_low.mean()
        if mean_low > 0 and (rng_low / mean_low) >= 0.0005:
            a, vertex_x, r2, _ = _fit_curve(seg_low)
            if r2 >= R2_THRESHOLD and a >= MIN_CURVATURE:
                sl, sh = SEMI_CIRCLE_RANGE
                ql, qh = QUARTER_CIRCLE_RANGE
                if sl <= vertex_x <= sh:
                    bull_semi[end] = 1
                elif ql <= vertex_x <= qh:
                    bull_quarter[end] = 1

        # --- BEARISH: fit downward parabola to smoothed highs ----------------
        seg_high  = high_smooth[start : end + 1]
        rng_high  = seg_high.max() - seg_high.min()
        mean_high = seg_high.mean()
        if mean_high > 0 and (rng_high / mean_high) >= 0.0005:
            a, vertex_x, r2, _ = _fit_curve(seg_high)
            # Bearish: parabola must open downward (a < -MIN_CURVATURE)
            if r2 >= R2_THRESHOLD and a <= -MIN_CURVATURE:
                bsl, bsh = BEAR_SEMI_CIRCLE_RANGE
                bql, bqh = BEAR_QUARTER_CIRCLE_RANGE
                if bsl <= vertex_x <= bsh:
                    bear_semi[end] = 1
                elif bql <= vertex_x <= bqh:
                    bear_quarter[end] = 1

    result["curve_semi_circle"]         = bull_semi.astype(int)
    result["curve_quarter_circle"]      = bull_quarter.astype(int)
    result["curve_bear_semi_circle"]    = bear_semi.astype(int)
    result["curve_bear_quarter_circle"] = bear_quarter.astype(int)
    return result


# ---------------------------------------------------------------------------
# Strategy bridge (consumed by the Trading Strategy Comparator / optimizer)
# ---------------------------------------------------------------------------

def run_strategy(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Thin bridge so the combo-optimizer can call this module directly.

    Normalises the index to a DatetimeIndex when raw CSV columns are present,
    runs calculate_indicators, then resets to a RangeIndex for the optimizer.
    """
    df = frame.copy()
    ts_col = None

    if "timestamp" in df.columns:
        ts_col = df["timestamp"].copy()
        if "datetime" in df.columns:
            dt_idx = pd.to_datetime(df["datetime"], utc=True)
        else:
            dt_idx = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.set_index(dt_idx)
        df.index.name = "timestamp"

    result = calculate_indicators(df)

    if ts_col is not None and not isinstance(result.index, pd.RangeIndex):
        result = result.reset_index(drop=True)

    return result


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _normalize_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols):
        df.loc[:, numeric_cols] = df.loc[:, numeric_cols].mask(
            df.loc[:, numeric_cols] == 1e100, np.nan
        )
    return df


def _attach_timestamp_index(df: pd.DataFrame) -> pd.DataFrame:
    indexed = df.copy()
    if isinstance(indexed.index, pd.DatetimeIndex):
        return indexed.sort_index()
    if "timestamp" in indexed.columns:
        dt_index = pd.to_datetime(indexed["timestamp"], unit="s", utc=True)
    elif "datetime" in indexed.columns:
        dt_index = pd.to_datetime(indexed["datetime"], utc=True)
    else:
        raise ValueError(
            "Input data must provide a DatetimeIndex or a `timestamp`/`datetime` column."
        )
    indexed.index = dt_index
    indexed.index.name = "timestamp"
    return indexed.sort_index()


def load_csv_data(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    raw = pd.read_csv(csv_path, low_memory=False)
    raw = _normalize_missing_values(raw)
    return _attach_timestamp_index(raw)


# ---------------------------------------------------------------------------
# Optional visualisation
# ---------------------------------------------------------------------------

def plot_last_pattern(df: pd.DataFrame, result: pd.DataFrame,
                      window: int | None = None) -> None:
    """
    Plot the most recent Semi-Circle or Quarter-Circle detection.
    Call only in interactive / notebook sessions.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping plot.")
        return

    # Find last signal (prefer semi-circle, fall back to quarter-circle)
    for col, label, color in [
        ("curve_semi_circle",    "Semi-Circle (U-Bottom)", "crimson"),
        ("curve_quarter_circle", "Quarter-Circle (J-Hook)", "darkorange"),
    ]:
        hits = result.index[result[col] == 1]
        if len(hits) == 0:
            continue

        last_bar = hits[-1]
        bar_loc  = result.index.get_loc(last_bar)

        if window is None:
            tf_key = _infer_timeframe_minutes(df)
            w = _TF_WINDOW.get(tf_key, DEFAULT_WINDOW)
        else:
            w = window

        start_loc = max(0, bar_loc - w + 1)
        seg       = result.iloc[start_loc : bar_loc + 1].copy()

        low_smooth = df["low"].ewm(span=DEFAULT_EMA_SPAN, adjust=False).mean()
        seg_smooth = low_smooth.iloc[start_loc : bar_loc + 1].values

        _, vertex_x, r2, y_pred_norm = _fit_curve(seg_smooth)

        scaler = MinMaxScaler()
        scaler.fit(seg_smooth.reshape(-1, 1))
        y_pred_real = scaler.inverse_transform(y_pred_norm.reshape(-1, 1)).flatten()

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(seg.index, seg["close"],         label="Close",           color="black",      lw=1.5)
        ax.plot(seg.index, seg_smooth,            label="Smoothed Low",    color="steelblue",  lw=1.2, alpha=0.7)
        ax.plot(seg.index, y_pred_real,           label="Fitted Curve",    color=color,        lw=2.5, ls="--")

        vtx_idx   = int(vertex_x * (len(seg) - 1))
        vtx_price = y_pred_real[vtx_idx]
        ax.scatter(seg.index[vtx_idx], vtx_price, color="limegreen", s=180,
                   zorder=5, label="Vertex (bottom)")

        ax.set_title(
            f"{label}  |  R²={r2:.3f}  |  last bar: {last_bar}",
            fontsize=13, fontweight="bold"
        )
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        return

    print("No curve pattern found in result to plot.")


# ---------------------------------------------------------------------------
# CLI entry-point — multi-timeframe batch run
# ---------------------------------------------------------------------------

def _run_single(path: Path, label: str) -> dict:
    df     = load_csv_data(path)
    result = calculate_indicators(df)
    return {
        "tf":              label,
        "bars":            len(df),
        "bull_semi":       int(result["curve_semi_circle"].sum()),
        "bull_jhook":      int(result["curve_quarter_circle"].sum()),
        "bear_semi":       int(result["curve_bear_semi_circle"].sum()),
        "bear_rollover":   int(result["curve_bear_quarter_circle"].sum()),
    }


def main(root: Path = DEFAULT_RELIANCE_ROOT) -> int:
    """
    Run the detector against every RELIANCE_*_*.csv file in `root`
    and print a per-timeframe summary table.
    """
    csv_files = sorted(root.glob("RELIANCE_*.csv"))
    if not csv_files:
        print(f"No CSV files found in: {root}")
        return 1

    rows = []
    for csv_path in csv_files:
        # Extract timeframe label from filename, e.g. "1m", "15m", "1hr", "1day"
        parts = csv_path.stem.split("_")          # ['RELIANCE', '15m', '5029bars']
        tf_label = parts[1] if len(parts) >= 2 else csv_path.stem
        try:
            rows.append(_run_single(csv_path, tf_label))
        except Exception as exc:
            print(f"  [SKIP] {csv_path.name}: {exc}")

    if not rows:
        print("No files could be processed.")
        return 1

    summary = pd.DataFrame(rows).set_index("tf")
    print("\nCurve Pattern Detection — All Timeframes")
    print("=" * 76)
    print(summary.to_string())
    print()

    for _, row in summary.iterrows():
        b = row["bars"] or 1
        print(
            f"  {row.name:<8}  bars={row['bars']:>6}  "
            f"BULL semi={row['bull_semi']:>4} ({row['bull_semi']/b*100:.1f}%)  "
            f"j-hook={row['bull_jhook']:>4} ({row['bull_jhook']/b*100:.1f}%)  "
            f"BEAR dome={row['bear_semi']:>4} ({row['bear_semi']/b*100:.1f}%)  "
            f"rollover={row['bear_rollover']:>4} ({row['bear_rollover']/b*100:.1f}%)"
        )

    return 0


if __name__ == "__main__":
    data_root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RELIANCE_ROOT
    raise SystemExit(main(data_root))
