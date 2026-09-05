"""
trend_brain.py — ML scoring for trend line bounce/breakout probability
=======================================================================
Features (8 per trend line):
  slope_norm   : slope normalised by mean price of last 20 bars
  r2           : goodness-of-fit of the trend line
  touches_norm : number of pivot touches / 10 (capped at 1.0)
  dist_norm    : distance of current price from line at end_bar / ATR
  vol_trend    : linear slope of volume over last 10 bars (normalised)
  rsi_norm     : RSI / 100 at end_bar (0.5 if column not present)
  recency      : end_bar / (n - 1)
  span_norm    : (end_bar - start_bar) / 200

Label: 1 if price bounced >= bounce_thresh from line within forward_bars bars,
       0 if price broke through or did nothing.

Bounce direction:
  support    -> price should go UP (max future price - entry) / entry >= bounce_thresh
  resistance -> price should go DOWN (entry - min future price) / entry >= bounce_thresh
"""

import numpy as np
import pandas as pd

TREND_FEATURE_NAMES = [
    "slope_norm", "r2", "touches_norm",
    "dist_norm", "vol_trend",
    "rsi_norm", "recency", "span_norm",
]


def _extract_trend_features(tl: dict, df: pd.DataFrame) -> list:
    """Extract 8 ML features for a single trend line dict."""
    n  = len(df)
    eb = int(tl["end_bar"])
    sb = int(tl["start_bar"])

    close       = df["close"].values.astype(float)
    price_mean  = float(close[max(0, eb - 20) : eb + 1].mean()) or 1.0

    # Slope normalised by recent mean price
    slope_norm = float(tl["slope"]) / price_mean

    r2           = float(tl["r2"])
    touches_norm = min(float(tl["touches"]) / 10.0, 1.0)

    # Distance of current close from the trend line at end_bar
    line_price_at_eb = float(tl["slope"] * eb + tl["intercept"])
    atr_start        = max(0, eb - 14)
    atr_arr          = (df["high"].values[atr_start:eb] - df["low"].values[atr_start:eb])
    recent_atr       = float(atr_arr.mean()) if len(atr_arr) > 0 else max(price_mean * 0.01, 1e-6)
    dist_norm        = abs(close[eb] - line_price_at_eb) / max(recent_atr, 1e-6)

    # Volume trend over last 10 bars (slope of normalised volume)
    vol        = df["volume"].values.astype(float)
    vol_window = vol[max(0, eb - 10) : eb + 1]
    vol_mean   = float(vol_window.mean()) or 1.0
    vol_norm   = vol_window / vol_mean
    vol_trend  = float(np.polyfit(range(len(vol_norm)), vol_norm, 1)[0]) if len(vol_norm) > 1 else 0.0

    rsi_norm = float(df["rsi"].iloc[eb] / 100.0) if "rsi" in df.columns else 0.50
    recency  = float(eb) / max(n - 1, 1)
    span_norm = float(eb - sb) / 200.0

    return [slope_norm, r2, touches_norm, dist_norm, vol_trend,
            rsi_norm, recency, span_norm]


def extract_trend_features(trend_lines: list, df: pd.DataFrame) -> np.ndarray:
    """Extract features for all trend lines. Returns shape (N, 8)."""
    if not trend_lines:
        return np.empty((0, len(TREND_FEATURE_NAMES)))
    return np.array([_extract_trend_features(tl, df) for tl in trend_lines], dtype=float)


def label_trend_signals(
    trend_lines: list, df: pd.DataFrame,
    forward_bars: int = 10,
    bounce_thresh: float = 0.008,
) -> tuple:
    """
    Label each trend line: 1 = bounce, 0 = break/nothing.
    Returns (labels np.ndarray, valid_mask np.ndarray).
    A signal is valid only if there are forward_bars bars remaining after end_bar.
    """
    n = len(df)
    labels, valid = [], []
    close = df["close"].values.astype(float)
    for tl in trend_lines:
        eb = int(tl["end_bar"])
        if eb + forward_bars >= n:
            valid.append(False)
            labels.append(0)
            continue
        valid.append(True)
        entry      = float(close[eb])
        future     = close[eb : eb + forward_bars + 1]
        is_support = tl["line_type"] == "support"
        if is_support:
            fwd = (future.max() - entry) / max(entry, 1e-10)
        else:
            fwd = (entry - future.min()) / max(entry, 1e-10)
        labels.append(1 if fwd >= bounce_thresh else 0)
    return np.array(labels, dtype=int), np.array(valid, dtype=bool)


def train_trend_model_persistent(
    trend_lines: list, df: pd.DataFrame,
    symbol: str = "UNKNOWN", interval: str = "1d",
    forward_bars: int = 10, bounce_thresh: float = 0.008,
):
    """
    Train trend line bounce predictor with persistent storage via ml_store.
    Returns fitted model or None if training is not possible.
    Loads a cached model (<=24h old) if available.
    Falls back to in-memory training if ml_store is unavailable.
    """
    _has_store = False
    try:
        import sys as _sys, os as _os
        _ind = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)))
        if _ind not in _sys.path:
            _sys.path.insert(0, _ind)
        from ml_store import (
            save_model, load_model, record_metrics,
            train_val_split, cross_val_accuracy,
        )
        _has_store = True
    except Exception:
        _has_store = False

    # Try to load a cached model (ml_store.load_model returns None if >24h old)
    if _has_store:
        cached = load_model(symbol, interval, "trend")
        if cached is not None:
            return cached

    if len(trend_lines) < 6:
        return None

    X        = extract_trend_features(trend_lines, df)
    y, valid = label_trend_signals(trend_lines, df, forward_bars, bounce_thresh)
    X_v, y_v = X[valid], y[valid]

    if len(X_v) < 6 or len(set(y_v)) < 2:
        return None

    try:
        from xgboost import XGBClassifier
        model_cls    = XGBClassifier
        model_kwargs = dict(
            n_estimators=80, learning_rate=0.10, max_depth=3,
            subsample=0.8, colsample_bytree=0.8,
            min_child_weight=3, gamma=0.1,
            random_state=42, eval_metric="logloss",
        )
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        model_cls    = GradientBoostingClassifier
        model_kwargs = dict(
            n_estimators=80, learning_rate=0.10,
            max_depth=3, subsample=0.8, random_state=42,
        )

    if not _has_store:
        model = model_cls(**model_kwargs)
        model.fit(X_v, y_v)
        return model

    try:
        X_tr, X_va, y_tr, y_va = train_val_split(X_v, y_v, val_frac=0.20)
    except ValueError:
        model = model_cls(**model_kwargs)
        model.fit(X_v, y_v)
        return model

    if len(X_tr) < 4 or len(set(y_tr)) < 2:
        return None

    model = model_cls(**model_kwargs)
    model.fit(X_tr, y_tr)

    train_acc = float((model.predict(X_tr) == y_tr).mean())
    if len(X_va) > 0 and len(set(y_va)) >= 2:
        val_acc = float((model.predict(X_va) == y_va).mean())
    elif len(X_va) > 0:
        # Val set has only one class — accuracy would be misleading; use train_acc as proxy
        val_acc = train_acc
    else:
        # Empty val set — use train_acc as proxy
        val_acc = train_acc

    cv_mean, cv_std = cross_val_accuracy(model_cls, X_v, y_v, k=3, **model_kwargs)

    try:
        imp = dict(zip(TREND_FEATURE_NAMES, model.feature_importances_.tolist()))
    except AttributeError:
        imp = {}

    try:
        record_metrics(
            symbol=symbol, interval=interval, model_type="trend",
            n_samples=len(X_v), n_pos=int(y_v.sum()), n_neg=int((y_v == 0).sum()),
            train_acc=train_acc, val_acc=val_acc,
            cv_mean=cv_mean, cv_std=cv_std,
            feature_imp=imp,
        )
        save_model(model, symbol, interval, "trend")
    except Exception:
        pass  # Non-fatal: metrics/save failure should not break trend detection

    return model


def score_trend_signals(model, trend_lines: list, df: pd.DataFrame) -> list:
    """Return bounce probability (0-1) for each trend line. Falls back to 0.5."""
    if model is None or not trend_lines:
        return [0.5] * len(trend_lines)
    X = extract_trend_features(trend_lines, df)
    try:
        return model.predict_proba(X)[:, 1].tolist()
    except Exception:
        return [0.5] * len(trend_lines)
