"""
ML Brain — Curve Pattern Meta-Labeling
=======================================
Phase 2: Volume profile confirmation (rule-based)
  • Bullish patterns: volume should DECLINE during the window (sellers dry up)
    OR spike at the completion bar (breakout buying)
  • Bearish patterns: same idea — distribution shows as declining or spiking vol

Phase 3: XGBoost meta-labeling (11 features per signal)
  Features:
    Fit quality  : r2, curvature (|a|), vertex_x position
    Volume       : vol_slope (normalised), vol_ratio (completion vs window avg)
    Pattern size : atr_ratio (curve range / recent ATR)
    Market state : rsi_norm, volatility, price_trend_slope
    Metadata     : recency (0..1), window_norm (window/200)

  Label: did price move ≥ profit_thresh % in the expected direction
         within forward_bars bars after the signal?
"""

import numpy as np
import pandas as pd

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

FEATURE_NAMES = [
    "r2", "curvature", "vertex_x",
    "vol_slope_norm", "vol_ratio",
    "atr_ratio", "rsi_norm", "volatility",
    "recency", "window_norm", "price_trend_slope",
]


# ── Phase 2: Volume confirmation ──────────────────────────────────────────────

def volume_confirmation(tr: dict, df: pd.DataFrame) -> tuple:
    """
    Rule-based volume profile check for a single curve trace.

    Returns:
        confirmed : bool  — True if volume profile supports the pattern
        vol_score : float — 0..1 strength of confirmation
    """
    sb = tr["start_bar"]
    eb = tr["end_bar"]
    vol = df["volume"].iloc[sb : eb + 1].values.astype(float)
    if len(vol) < 3 or vol.mean() == 0:
        return True, 0.5   # insufficient data → neutral

    vol_mean = vol.mean()
    vol_norm = vol / vol_mean

    # Linear slope of normalised volume across the window
    slope = float(np.polyfit(range(len(vol)), vol_norm, 1)[0])

    # Volume at the completion bar vs window average
    last_ratio = float(vol[-1] / vol_mean)

    # Confirmed if: volume was declining (accumulation/distribution)
    #            OR completion bar had above-average volume (breakout/breakdown)
    vol_declining = slope < -0.02
    vol_spike_end = last_ratio > 1.25
    confirmed = vol_declining or vol_spike_end

    # Strength: higher when volume falls steeply or spikes sharply at end
    vol_score = float(np.clip(-slope * 4 + max(0, last_ratio - 1.0) * 0.5, 0.0, 1.0))
    return confirmed, round(vol_score, 3)


# ── Phase 3: Feature extraction ──────────────────────────────────────────────

def _extract_one(tr: dict, df: pd.DataFrame) -> list:
    """Extract 11 ML features for a single curve trace."""
    sb  = tr["start_bar"]
    eb  = tr["end_bar"]
    n   = len(df)

    # ── Fit quality (stored by curve_detector) ──
    r2        = float(tr.get("r2",        0.82))
    curvature = float(tr.get("curvature", 0.45))
    vertex_x  = float(tr.get("vertex_x",  0.50))

    # ── Volume ──
    vol = df["volume"].iloc[sb : eb + 1].values.astype(float)
    vol_mean = float(vol.mean()) if vol.mean() > 0 else 1.0
    vol_norm = vol / vol_mean
    vol_slope = float(np.polyfit(range(len(vol)), vol_norm, 1)[0]) if len(vol) > 1 else 0.0
    vol_ratio = float(vol[-1] / vol_mean)

    # ── ATR ratio (pattern height vs recent daily range) ──
    hi = df["high"].iloc[sb : eb + 1].values
    lo = df["low"].iloc[sb  : eb + 1].values
    pattern_range = float(hi.max() - lo.min())
    atr_start = max(0, eb - 14)
    atr_hi = df["high"].iloc[atr_start : eb].values
    atr_lo = df["low"].iloc[atr_start  : eb].values
    recent_atr = float((atr_hi - atr_lo).mean()) if len(atr_hi) > 0 else 1e-6
    atr_ratio = pattern_range / max(recent_atr, 1e-6)

    # ── Market state at signal bar ──
    rsi_norm   = float(df["rsi"].iloc[eb]        / 100.0) if "rsi"        in df.columns else 0.50
    volatility = float(df["volatility"].iloc[eb])          if "volatility" in df.columns else 0.01

    # ── Recency & window normalisation ──
    recency     = float(eb) / max(n - 1, 1)
    window_norm = float(tr["window"]) / 200.0

    # ── Price trend slope during window ──
    close = df["close"].iloc[sb : eb + 1].values.astype(float)
    close_mean = float(close.mean()) if close.mean() != 0 else 1.0
    price_trend = float(np.polyfit(range(len(close)), close / close_mean, 1)[0]) if len(close) > 1 else 0.0

    return [r2, curvature, vertex_x,
            vol_slope, vol_ratio,
            atr_ratio, rsi_norm, volatility,
            recency, window_norm, price_trend]


def extract_curve_features(traces: list, df: pd.DataFrame) -> np.ndarray:
    if not traces:
        return np.empty((0, len(FEATURE_NAMES)))
    return np.array([_extract_one(tr, df) for tr in traces], dtype=float)


# ── Phase 3: Labelling ────────────────────────────────────────────────────────

def label_curve_signals(traces: list, df: pd.DataFrame,
                         forward_bars: int = 10,
                         profit_thresh: float = 0.015) -> tuple:
    """
    Forward-return label for each signal.
    Bullish → 1 if max-future-price ≥ entry * (1 + profit_thresh)
    Bearish → 1 if min-future-price ≤ entry * (1 - profit_thresh)

    Returns (labels np.ndarray, valid_mask np.ndarray).
    """
    n = len(df)
    labels, valid = [], []
    for tr in traces:
        eb      = tr["end_bar"]
        is_bull = tr["is_bull"]
        if eb + forward_bars >= n:
            valid.append(False);  labels.append(0);  continue
        valid.append(True)
        entry  = float(df["close"].iloc[eb])
        future = df["close"].iloc[eb : eb + forward_bars + 1].values
        if is_bull:
            fwd = (future.max() - entry) / max(entry, 1e-10)
        else:
            fwd = (entry - future.min()) / max(entry, 1e-10)
        labels.append(1 if fwd > profit_thresh else 0)
    return np.array(labels, dtype=int), np.array(valid, dtype=bool)


# ── Phase 3: Training ─────────────────────────────────────────────────────────

def train_curve_model(traces: list, df: pd.DataFrame,
                       forward_bars: int = 10,
                       profit_thresh: float = 0.015):
    """
    Train curve meta-model on curve signal features.
    Prefers XGBoost; falls back to GradientBoostingClassifier if not installed.

    Returns fitted model or None when:
      • Fewer than 8 labelable traces
      • Only one class present in labels
    """
    if len(traces) < 8:
        return None

    X          = extract_curve_features(traces, df)
    y, valid   = label_curve_signals(traces, df, forward_bars, profit_thresh)
    X_v, y_v   = X[valid], y[valid]

    if len(X_v) < 8 or len(set(y_v)) < 2:
        return None

    if HAS_XGBOOST:
        model = XGBClassifier(
            n_estimators     = 120,
            learning_rate    = 0.08,
            max_depth        = 4,
            subsample        = 0.8,
            colsample_bytree = 0.8,
            min_child_weight = 3,
            gamma            = 0.15,
            reg_alpha        = 0.1,
            reg_lambda       = 1.5,
            random_state     = 42,
            eval_metric      = "logloss",
        )
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators  = 120,
            learning_rate = 0.08,
            max_depth     = 4,
            subsample     = 0.8,
            random_state  = 42,
        )

    model.fit(X_v, y_v)
    return model


def train_curve_model_persistent(
    traces: list, df: pd.DataFrame,
    symbol: str = "UNKNOWN", interval: str = "1d",
    forward_bars: int = 10, profit_thresh: float = 0.015,
):
    """
    Train curve meta-model, save via ml_store, record metrics.
    Returns fitted model (or cached model if fresh enough), or None.
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
        cached = load_model(symbol, interval, "curve")
        if cached is not None:
            return cached

    if len(traces) < 8:
        return None

    X        = extract_curve_features(traces, df)
    y, valid = label_curve_signals(traces, df, forward_bars, profit_thresh)
    X_v, y_v = X[valid], y[valid]

    if len(X_v) < 8 or len(set(y_v)) < 2:
        return None

    if HAS_XGBOOST:
        from xgboost import XGBClassifier
        model_cls = XGBClassifier
        model_kwargs = dict(
            n_estimators=120, learning_rate=0.08, max_depth=4,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
            gamma=0.15, reg_alpha=0.1, reg_lambda=1.5,
            random_state=42, eval_metric="logloss",
        )
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        model_cls = GradientBoostingClassifier
        model_kwargs = dict(
            n_estimators=120, learning_rate=0.08,
            max_depth=4, subsample=0.8, random_state=42,
        )

    if not _has_store:
        # Fallback: in-memory training only (no persistence)
        model = model_cls(**model_kwargs)
        model.fit(X_v, y_v)
        return model

    # Chronological train/val split (80/20)
    try:
        X_tr, X_va, y_tr, y_va = train_val_split(X_v, y_v, val_frac=0.20)
    except ValueError:
        # Too few samples for split — fall back to full training, no metrics
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
        val_acc = train_acc

    cv_mean, cv_std = cross_val_accuracy(model_cls, X_v, y_v, k=3, **model_kwargs)

    imp = feature_importance(model)

    try:
        record_metrics(
            symbol=symbol, interval=interval, model_type="curve",
            n_samples=len(X_v), n_pos=int(y_v.sum()), n_neg=int((y_v == 0).sum()),
            train_acc=train_acc, val_acc=val_acc,
            cv_mean=cv_mean, cv_std=cv_std,
            feature_imp=imp,
        )
        save_model(model, symbol, interval, "curve")
    except Exception:
        pass  # Non-fatal: metrics/save failure should not break pattern detection

    return model


def score_curve_signals(model, traces: list, df: pd.DataFrame) -> list:
    """Return XGBoost probability (0–1) for each trace. Falls back to 0.5."""
    if model is None or not traces:
        return [0.5] * len(traces)
    X = extract_curve_features(traces, df)
    return model.predict_proba(X)[:, 1].tolist()


def feature_importance(model) -> dict:
    """Return {feature_name: importance} sorted descending. Empty if model None."""
    if model is None:
        return {}
    try:
        imp = model.feature_importances_
        return dict(sorted(zip(FEATURE_NAMES, imp), key=lambda x: -x[1]))
    except AttributeError:
        return {}
