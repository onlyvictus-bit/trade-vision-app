"""
ml_store.py — Persistent model storage and metrics tracking.
=============================================================
• Saves/loads XGBoost/sklearn models via joblib.
• Records training metrics to SQLite (ml_metrics table).
• Provides train/val split + cross-validation utilities.
• Shared by curve_brain and trend_brain.

DB location: indicators/data/ml_metrics.db
Model dir  : indicators/data/models/
"""
import os
import json
import sqlite3
import hashlib
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE      = Path(__file__).parent
_DATA_DIR  = _HERE / "data"
_MODEL_DIR = _DATA_DIR / "models"
_DB_PATH   = _DATA_DIR / "ml_metrics.db"

_DATA_DIR.mkdir(exist_ok=True)
_MODEL_DIR.mkdir(exist_ok=True)

# Thresholds for model health flags
_OVERFIT_GAP_THRESHOLD  = 0.15  # train/val accuracy gap indicating overfit
_UNDERFIT_ACC_THRESHOLD = 0.55  # near-chance accuracy indicating underfit

# ── DB schema ─────────────────────────────────────────────────────────────────
_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS ml_metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT    NOT NULL,
    symbol        TEXT    NOT NULL,
    interval      TEXT    NOT NULL,
    model_type    TEXT    NOT NULL,
    n_samples     INTEGER NOT NULL,
    n_pos         INTEGER NOT NULL,
    n_neg         INTEGER NOT NULL,
    train_acc     REAL    NOT NULL,
    val_acc       REAL    NOT NULL,
    cv_mean       REAL    NOT NULL,
    cv_std        REAL    NOT NULL,
    overfit_flag  INTEGER NOT NULL DEFAULT 0,
    underfit_flag INTEGER NOT NULL DEFAULT 0,
    feature_imp   TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_metrics_symbol ON ml_metrics(symbol, interval, model_type);
"""

_DB_INITIALIZED = False

def _ensure_schema(conn: sqlite3.Connection) -> None:
    global _DB_INITIALIZED
    if not _DB_INITIALIZED:
        conn.executescript(_CREATE_SQL)
        conn.commit()
        _DB_INITIALIZED = True

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def record_metrics(
    symbol: str, interval: str, model_type: str,
    n_samples: int, n_pos: int, n_neg: int,
    train_acc: float, val_acc: float,
    cv_mean: float, cv_std: float,
    feature_imp: dict,
) -> None:
    """Insert one row into ml_metrics."""
    overfit  = int(train_acc - val_acc > _OVERFIT_GAP_THRESHOLD)
    underfit = int(val_acc < _UNDERFIT_ACC_THRESHOLD)
    row = (
        datetime.now(timezone.utc).isoformat(),
        symbol.upper(), interval, model_type,
        n_samples, n_pos, n_neg,
        round(float(train_acc), 4),
        round(float(val_acc),   4),
        round(float(cv_mean),   4),
        round(float(cv_std),    4),
        overfit, underfit,
        json.dumps({k: round(float(v), 5) for k, v in feature_imp.items()})
    )
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO ml_metrics
               (ts,symbol,interval,model_type,n_samples,n_pos,n_neg,
                train_acc,val_acc,cv_mean,cv_std,overfit_flag,underfit_flag,feature_imp)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            row,
        )
        conn.commit()


def get_recent_metrics(limit: int = 50) -> list:
    """Return most recent rows as list of dicts."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ml_metrics ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_metric(symbol: str, interval: str, model_type: str) -> dict | None:
    """Return the most recent metric row for a specific key, or None."""
    with _get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM ml_metrics
               WHERE symbol=? AND interval=? AND model_type=?
               ORDER BY id DESC LIMIT 1""",
            (symbol.upper(), interval, model_type),
        ).fetchone()
    return dict(row) if row else None


# ── Model persistence ─────────────────────────────────────────────────────────

def _model_path(symbol: str, interval: str, model_type: str) -> Path:
    key  = f"{symbol.upper()}_{interval}_{model_type}"
    name = hashlib.md5(key.encode()).hexdigest()[:12]  # 48-bit collision space; fine for <1000 model keys
    return _MODEL_DIR / f"{model_type}_{name}.pkl"


def save_model(model, symbol: str, interval: str, model_type: str) -> None:
    try:
        import joblib
        joblib.dump(model, str(_model_path(symbol, interval, model_type)))
    except Exception:
        pass  # Non-fatal: model just won't persist across restarts


def load_model(symbol: str, interval: str, model_type: str):
    """Return loaded model or None if not found / stale (>24h)."""
    try:
        import joblib
        p = _model_path(symbol, interval, model_type)
        if not p.exists():
            return None
        # Stale if saved > 24 hours ago
        age_h = (datetime.now(timezone.utc).timestamp() - p.stat().st_mtime) / 3600
        if age_h > 24:
            p.unlink(missing_ok=True)
            return None
        return joblib.load(str(p))
    except Exception:
        return None


# ── Train / val split + cross-validation ─────────────────────────────────────

def train_val_split(X: np.ndarray, y: np.ndarray, val_frac: float = 0.20):
    """
    Chronological split (no shuffle) — time-series safe.
    Raises ValueError if X has fewer than 5 samples (too small for a meaningful split).
    """
    if len(X) < 5:
        raise ValueError(f"train_val_split requires at least 5 samples, got {len(X)}")
    split = max(1, int(len(X) * (1 - val_frac)))
    return X[:split], X[split:], y[:split], y[split:]


def cross_val_accuracy(model_cls, X: np.ndarray, y: np.ndarray,
                        k: int = 3, **model_kwargs) -> tuple:
    """
    Manual k-fold CV (chronological folds).
    Returns (mean_accuracy, std_accuracy).
    """
    n      = len(X)
    fold_n = n // k
    accs   = []
    for i in range(k):
        val_start = i * fold_n
        val_end   = val_start + fold_n if i < k - 1 else n
        train_idx = list(range(0, val_start)) + list(range(val_end, n))
        val_idx   = list(range(val_start, val_end))
        if len(train_idx) < 4 or len(val_idx) < 2:
            continue
        if len(set(y[train_idx])) < 2:
            continue
        m = model_cls(**model_kwargs)
        m.fit(X[train_idx], y[train_idx])
        acc = float((m.predict(X[val_idx]) == y[val_idx]).mean())
        accs.append(acc)
    if not accs:
        return 0.5, 0.0
    return float(np.mean(accs)), float(np.std(accs))
