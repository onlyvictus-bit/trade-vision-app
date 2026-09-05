"""
adv_trend_brain.py — ML Brain for Advanced Trendline Detector
==============================================================
Adapted from D:/Projects/test1/test in claud/New folder/part 2/ml/brain.py
Changes:
  - Stripped: torch, SimpleLSTM, train_lstm_model (PyTorch not required)
  - Stripped: LSTM branch from train_meta_model()
  - Added:    train_meta_model_persistent() — uses ml_store for 24h TTL
  - Column convention: df uses uppercase cols (Close, Volume) from yfinance raw

Feature vector (6 public features per line):
  [slope, touches, recency, error, distance_pct, volume_ratio]
"""
import numpy as np
import pandas as pd

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

ADV_TREND_FEATURE_NAMES = ["slope", "touches", "recency", "error", "distance_pct", "volume_ratio"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich df (uppercase cols from yfinance) with returns/volatility/momentum/rsi."""
    df = df.copy()
    df['returns']    = df['Close'].pct_change()
    df['volatility'] = df['returns'].rolling(20, min_periods=5).std().fillna(0.01)
    df['momentum']   = df['Close'] - df['Close'].shift(10)
    rsi_mean = df['returns'].rolling(14, min_periods=5).mean()
    rsi_std  = df['returns'].rolling(14, min_periods=5).std().replace(0, 1e-6)
    df['rsi'] = (100 - (100 / (1 + rsi_mean / rsi_std))).fillna(50)
    return df


def extract_line_features(trend, n_local: int, df: pd.DataFrame) -> list:
    """
    Extract 6 features for a single trendline (no data leakage).

    trend : (idxs, (m, b, ys, ser, *_))   — trendln format
    n_local : total bars in df
    df    : DataFrame with uppercase cols 'Close', 'Volume' from yfinance
    """
    idxs, (m, b, ys, ser, *_) = trend
    last_touch_idx = int(idxs[-1])
    price_at_touch = float(m * last_touch_idx + b)
    last_close     = float(df['Close'].iloc[last_touch_idx])
    dist_pct       = (last_close - price_at_touch) / (price_at_touch or 1e-9) * 100
    slope          = float(m)
    touches        = float(len(idxs))
    recency        = last_touch_idx / (n_local - 1) if n_local > 1 else 0.0
    ser_norm       = float(min(1.0, ser * 1000.0))
    vol_at_touch   = float(df['Volume'].iloc[last_touch_idx]) if 'Volume' in df.columns else 0.0
    avg_vol        = float(df['Volume'].mean()) if 'Volume' in df.columns and df['Volume'].mean() > 0 else 1.0
    vol_ratio      = vol_at_touch / avg_vol if avg_vol > 0 else 0.0
    return [slope, touches, recency, ser_norm, dist_pct, vol_ratio]


def extract_line_feature_dict(trend, n_local: int, df: pd.DataFrame) -> dict:
    vals = extract_line_features(trend, n_local, df)
    return {k: float(v) for k, v in zip(ADV_TREND_FEATURE_NAMES, vals)}


def confidence_score(prob: float, trend_score: float, recency: float) -> float:
    """
    Composite confidence = prob × trend_score × (0.3 + 0.7 × recency).
    Penalises old trendlines (low recency) even if ML prob is high.
    Returns float in [0, 1].
    """
    return float(np.clip(prob * trend_score * (0.3 + 0.7 * recency), 0.0, 1.0))


def _get_model_cls_kwargs():
    """Return (model_class, kwargs) for the best available classifier."""
    if HAS_XGBOOST:
        return XGBClassifier, dict(
            n_estimators=200, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, eval_metric='logloss',
        )
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier, dict(
        n_estimators=150, learning_rate=0.08, max_depth=5,
        random_state=42, subsample=0.8,
    )


def _fit_calibrated_model(model_cls, model_kwargs, X, y):
    """Fit a probability-calibrated classifier when enough labelled samples exist."""
    base = model_cls(**model_kwargs)
    if len(X) >= 18 and len(set(y)) >= 2:
        try:
            from sklearn.calibration import CalibratedClassifierCV
            try:
                calibrated = CalibratedClassifierCV(estimator=base, method='sigmoid', cv=3)
            except TypeError:
                calibrated = CalibratedClassifierCV(base_estimator=base, method='sigmoid', cv=3)
            calibrated.fit(X, y)
            raw_for_importance = model_cls(**model_kwargs)
            raw_for_importance.fit(X, y)
            return calibrated, raw_for_importance, True
        except Exception:
            pass
    base.fit(X, y)
    return base, base, False


def _trend_and_type(item):
    """Accept old (trend, score) and new (trend, score, line_type) training rows."""
    if len(item) >= 3:
        return item[0], item[2]
    return item[0], 'support'


def _atr_at(df: pd.DataFrame, idx: int) -> float:
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    close = df['Close'].astype(float)
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean().iloc[idx]
    if pd.isna(atr) or atr <= 0:
        atr = max(float(close.iloc[idx]) * 0.01, 1e-6)
    return float(atr)


def _target_before_stop_label(trend, line_type: str, df: pd.DataFrame,
                              forward_bars: int = 24, rr: float = 2.0) -> int | None:
    """
    Direction-aware meta label.
    - Resistance break = long continuation if target hits before stop.
    - Support break = short continuation if target hits before stop.
    Ambiguous/unfinished samples are ignored.
    """
    idxs, (m, b, *_) = trend
    i = int(idxs[-1])
    if i + forward_bars >= len(df) or i <= 0:
        return None
    close = float(df['Close'].iloc[i])
    prev_close = float(df['Close'].iloc[i - 1])
    line_price = float(m * i + b)
    prev_line = float(m * (i - 1) + b)
    atr = _atr_at(df, i)

    side = None
    if line_type == 'resistance' and prev_close <= prev_line and close > line_price:
        side = 'long'
    elif line_type == 'support' and prev_close >= prev_line and close < line_price:
        side = 'short'
    else:
        # No confirmed break: label as whether the line respected price action.
        if line_type == 'support':
            side = 'long' if close >= line_price else None
        else:
            side = 'short' if close <= line_price else None
    if side is None:
        return None

    entry = close
    if side == 'long':
        stop = line_price - atr
        risk = entry - stop
        if risk <= 0:
            return None
        target = entry + rr * risk
        for j in range(i + 1, i + forward_bars + 1):
            if float(df['Low'].iloc[j]) <= stop:
                return 0
            if float(df['High'].iloc[j]) >= target:
                return 1
    else:
        stop = line_price + atr
        risk = stop - entry
        if risk <= 0:
            return None
        target = entry - rr * risk
        for j in range(i + 1, i + forward_bars + 1):
            if float(df['High'].iloc[j]) >= stop:
                return 0
            if float(df['Low'].iloc[j]) <= target:
                return 1
    return None


def train_meta_model(scored_trends: list, df: pd.DataFrame, n_local: int,
                      forward_bars: int = 8, profit_thresh: float = 0.015):
    """
    Train a meta-model on historical trendline outcomes (no persistence).

    scored_trends : list of (trend, score)
    df            : yfinance raw DataFrame (uppercase Close, Volume)
    Returns (model | None, probs list)
    """
    if len(scored_trends) < 5:
        return None, [0.5] * len(scored_trends)

    X, y = [], []
    for item in scored_trends:
        t, line_type = _trend_and_type(item)
        idxs, (m, b, *_) = t
        last_touch_idx = int(idxs[-1])
        if last_touch_idx + forward_bars >= len(df):
            continue
        label = _target_before_stop_label(t, line_type, df, forward_bars=max(forward_bars, 8))
        if label is None:
            continue
        X.append(extract_line_features(t, n_local, df))
        y.append(label)

    if len(X) < 5 or len(set(y)) < 2:
        return None, [0.5] * len(scored_trends)

    X = np.array(X)
    y = np.array(y)
    model_cls, model_kwargs = _get_model_cls_kwargs()
    model, _, _ = _fit_calibrated_model(model_cls, model_kwargs, X, y)
    probs = [
        float(model.predict_proba([extract_line_features(t, n_local, df)])[0][1])
        for t, _ in scored_trends
    ]
    return model, probs


def train_meta_model_persistent(symbol: str, interval: str, scored_trends: list,
                                  df: pd.DataFrame, n_local: int,
                                  forward_bars: int = 8, profit_thresh: float = 0.015):
    """
    Train (or load cached) meta-model and record metrics to ml_store.

    Returns (model | None, probs list, ml_metrics_dict | None)
    - If a valid 24h-cached model exists, skips training and returns cached metrics.
    - ml_metrics_dict is None when training fails or fewer than 5 samples.
    """
    _has_store = False
    try:
        from ml_store import (load_model, save_model, record_metrics,
                               get_latest_metric, train_val_split, cross_val_accuracy)
        _has_store = True
    except Exception:
        pass

    # ── Try loading a valid cached model (24h TTL) ────────────────────────
    if _has_store:
        cached = load_model(symbol, interval, 'adv_trend')
        if cached is not None:
            try:
                probs = [
                    float(cached.predict_proba([extract_line_features(t, n_local, df)])[0][1])
                    for t, _ in scored_trends
                ]
            except Exception:
                probs = [0.5] * len(scored_trends)
            ml_metrics = get_latest_metric(symbol, interval, 'adv_trend')
            return cached, probs, ml_metrics

    # ── Build training dataset ────────────────────────────────────────────
    if len(scored_trends) < 5:
        return None, [0.5] * len(scored_trends), None

    X_all, y_all = [], []
    for item in scored_trends:
        t, line_type = _trend_and_type(item)
        idxs, (m, b, *_) = t
        last_touch_idx = int(idxs[-1])
        if last_touch_idx + forward_bars >= len(df):
            continue
        label = _target_before_stop_label(t, line_type, df, forward_bars=max(forward_bars, 24))
        if label is None:
            continue
        X_all.append(extract_line_features(t, n_local, df))
        y_all.append(label)

    if len(X_all) < 5 or len(set(y_all)) < 2:
        return None, [0.5] * len(scored_trends), None

    X_v = np.array(X_all)
    y_v = np.array(y_all)

    model_cls, model_kwargs = _get_model_cls_kwargs()

    # Train on full dataset
    model, importance_model, calibrated = _fit_calibrated_model(model_cls, model_kwargs, X_v, y_v)
    train_acc = float((model.predict(X_v) == y_v).mean())

    # Chronological val split + CV
    val_acc = train_acc
    cv_mean, cv_std = 0.5, 0.0
    if _has_store:
        try:
            X_tr, X_va, y_tr, y_va = train_val_split(X_v, y_v, val_frac=0.20)
            m_tr = model_cls(**model_kwargs)
            m_tr.fit(X_tr, y_tr)
            if len(X_va) > 0 and len(set(y_va)) >= 2:
                val_acc = float((m_tr.predict(X_va) == y_va).mean())
            elif len(X_va) > 0:
                val_acc = float((m_tr.predict(X_va) == y_va).mean())
            else:
                val_acc = train_acc
            cv_mean, cv_std = cross_val_accuracy(model_cls, X_v, y_v, k=3, **model_kwargs)
        except Exception:
            pass

    # Feature importance
    feat_imp = {}
    if hasattr(importance_model, 'feature_importances_'):
        for name, imp in zip(ADV_TREND_FEATURE_NAMES, importance_model.feature_importances_):
            feat_imp[name] = float(imp)

    # Persist model + record metrics
    ml_metrics_row = None
    if _has_store:
        try:
            save_model(model, symbol, interval, 'adv_trend')
            record_metrics(
                symbol=symbol, interval=interval, model_type='adv_trend',
                n_samples=len(X_v), n_pos=int(y_v.sum()), n_neg=int((y_v == 0).sum()),
                train_acc=train_acc, val_acc=val_acc,
                cv_mean=cv_mean, cv_std=cv_std,
                feature_imp={**feat_imp, "_calibrated": float(1 if calibrated else 0)},
            )
            ml_metrics_row = get_latest_metric(symbol, interval, 'adv_trend')
        except Exception:
            pass

    # Score all signals
    try:
        probs = [
            float(model.predict_proba([extract_line_features(t, n_local, df)])[0][1])
            for t, _ in scored_trends
        ]
    except Exception:
        probs = [0.5] * len(scored_trends)

    return model, probs, ml_metrics_row
