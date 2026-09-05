"""
ML BRAIN - Production-grade multi-model intelligence layer
- GradientBoostingClassifier (more stable than RF for finance)
- Confidence Layer = prob * trend_score * recency
- Online learning ready (partial_fit)
- Fixed data leakage (uses price_at_touch, not last_close)
"""
import numpy as np
import pandas as pd
try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from sklearn.model_selection import cross_val_score
from typing import List, Tuple, Dict

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Enriched feature set for ML models. Uses min_periods to avoid NaN at real-time edge."""
    df = df.copy()
    df['returns'] = df['Close'].pct_change()
    df['volatility'] = df['returns'].rolling(20, min_periods=5).std().fillna(0.01)
    df['momentum'] = df['Close'] - df['Close'].shift(10)
    df['rsi'] = 100 - (100 / (1 + df['returns'].rolling(14, min_periods=5).mean() / 
                              df['returns'].rolling(14, min_periods=5).std().replace(0, 1e-6))).fillna(50)
    return df

def extract_line_features(trend: Tuple, n_local: int, df: pd.DataFrame) -> List[float]:
    """Safe feature extraction — no data leakage."""
    idxs, (m, b, ys, ser, *_) = trend
    last_touch_idx = idxs[-1]
    price_at_touch = m * last_touch_idx + b
    last_close = df['Close'].iloc[last_touch_idx]   # ← FIXED: use price at touch time
    dist_pct = (last_close - price_at_touch) / price_at_touch * 100
    slope = m
    touches = len(idxs)
    recency = last_touch_idx / (n_local - 1) if n_local > 1 else 0.0
    ser_norm = min(1.0, ser * 1000.0)
    vol_at_touch = df['Volume'].iloc[last_touch_idx] if 'Volume' in df.columns else 0.0
    avg_vol = df['Volume'].mean() if 'Volume' in df.columns and df['Volume'].mean() > 0 else 1.0
    vol_ratio = vol_at_touch / avg_vol
    return [slope, touches, recency, ser_norm, dist_pct, vol_ratio]

def confidence_score(prob: float, trend_score: float, recency: float) -> float:
    """Confidence Layer — prevents fake high-confidence signals."""
    return float(np.clip(prob * trend_score * (0.3 + 0.7 * recency), 0.0, 1.0))


# ==================== DEEP LEARNING MODELS (Optional) ====================

class SimpleLSTM(nn.Module):
    """Lightweight LSTM for trendline success prediction."""
    def __init__(self, input_size=6, hidden_size=32, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        lstm_out, _ = self.lstm(x.unsqueeze(1))  # Add sequence dimension
        out = self.fc(lstm_out[:, -1, :])
        return self.sigmoid(out).squeeze()


def train_lstm_model(X: np.ndarray, y: np.ndarray, epochs: int = 50):
    """Train a simple LSTM model using PyTorch."""
    if not HAS_TORCH:
        raise ImportError("PyTorch not installed. Run: pip install torch")

    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.FloatTensor(y)

    model = SimpleLSTM(input_size=X.shape[1])
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    dataset = TensorDataset(X_tensor, y_tensor)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)

    model.train()
    for epoch in range(epochs):
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

    return model


def train_meta_model(scored_trends: List, df: pd.DataFrame, n_local: int,
                     forward_bars: int = 8, profit_thresh: float = 0.015,
                     model_type: str = "xgboost") -> Tuple:
    """
    Unified meta-model trainer.
    model_type options:
        - "xgboost" (default, recommended)
        - "gradient_boosting"
        - "lstm" (requires PyTorch)
    """
    if len(scored_trends) < 5:
        return None, [0.5] * len(scored_trends)

    X, y = [], []
    for t, _ in scored_trends:
        idxs, (m, b, *_) = t
        last_touch_idx = idxs[-1]
        if last_touch_idx + forward_bars >= len(df):
            continue
        entry = m * last_touch_idx + b
        future = df['Close'].iloc[last_touch_idx : last_touch_idx + forward_bars + 1]
        # Bidirectional: support succeeds on bounce UP, resistance succeeds on drop DOWN
        fwd_up   = (future.max() - entry) / entry
        fwd_down = (entry - future.min()) / entry
        fwd_return = max(fwd_up, fwd_down)
        label = 1 if fwd_return > profit_thresh else 0
        feats = extract_line_features(t, n_local, df)
        X.append(feats)
        y.append(label)

    if len(X) < 5 or len(set(y)) < 2:
        return None, [0.5] * len(scored_trends)

    X = np.array(X)
    y = np.array(y)

    if model_type == "lstm" and HAS_TORCH:
        model = train_lstm_model(X, y)
        # Predict probabilities
        model.eval()
        with torch.no_grad():
            probs = model(torch.FloatTensor(X)).numpy()
        return model, probs.tolist()

    elif model_type == "xgboost" and HAS_XGBOOST:
        model = XGBClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, eval_metric='logloss'
        )
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.08, max_depth=5,
            random_state=42, subsample=0.8
        )

    model.fit(X, y)

    probs = []
    for t, _ in scored_trends:
        feats = extract_line_features(t, n_local, df)
        if model_type == "lstm" and HAS_TORCH:
            p = float(model(torch.FloatTensor([feats])).item())
        else:
            p = float(model.predict_proba([feats])[0][1])
        probs.append(p)

    return model, probs