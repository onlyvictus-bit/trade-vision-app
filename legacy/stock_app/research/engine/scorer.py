"""
research.engine.scorer — 10-metric composite scoring (0-100)
=============================================================
Normalise each KPI to [0, 1], apply weights, scale to 0-100.
"""
from __future__ import annotations

from typing import Dict

from .backtester import BacktestResult


# ── Weight table (sum = 1.0) ──────────────────────────────────────────────

WEIGHTS: Dict[str, float] = {
    "sharpe":       0.20,
    "sortino":      0.15,
    "profit_factor": 0.15,
    "win_rate":     0.10,
    "calmar":       0.10,
    "expectancy":   0.10,
    "max_dd":       0.10,
    "trade_count":  0.05,
    "kelly":        0.05,
}


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


def compute_composite_score(r: BacktestResult) -> float:
    """
    Compute weighted composite score 0-100 from BacktestResult.

    Each metric is normalised to [0, 1]:
      - sharpe: clamp(0,4) / 4
      - sortino: clamp(0,6) / 6
      - profit_factor: clamp(0,4) / 4
      - win_rate: value (already 0-1)
      - calmar: clamp(0,5) / 5
      - expectancy: clamp(0,0.05) / 0.05
      - max_dd penalty: 1.0 - clamp(|dd|, 0, 0.5) / 0.5
      - trade_count: clamp(trades, 30, 200) / 200
      - kelly: clamp(0, 0.5) / 0.5
    """
    if r.trades == 0:
        return 0.0

    norms = {
        "sharpe":        _clamp(r.sharpe, 0, 4) / 4,
        "sortino":       _clamp(r.sortino, 0, 6) / 6,
        "profit_factor": _clamp(r.profit_factor, 0, 4) / 4,
        "win_rate":      _clamp(r.win_rate, 0, 1),
        "calmar":        _clamp(r.calmar, 0, 5) / 5,
        "expectancy":    _clamp(r.expectancy, 0, 0.05) / 0.05,
        "max_dd":        1.0 - _clamp(abs(r.max_drawdown), 0, 0.5) / 0.5,
        "trade_count":   _clamp(r.trades, 30, 200) / 200,
        "kelly":         _clamp(r.kelly_fraction, 0, 0.5) / 0.5,
    }

    score = sum(WEIGHTS[k] * norms[k] for k in WEIGHTS)
    return round(score * 100, 2)


def rank_metric_value(r: BacktestResult, metric: str) -> float:
    """Return a sortable value for a specific metric (higher = better)."""
    mapping = {
        "sharpe": r.sharpe,
        "sortino": r.sortino,
        "profit_factor": r.profit_factor,
        "win_rate": r.win_rate,
        "calmar": r.calmar,
        "expectancy": r.expectancy,
        "max_drawdown": -abs(r.max_drawdown),  # less DD = better
        "total_return": r.total_return,
        "trades": r.trades,
        "kelly": r.kelly_fraction,
        "composite": compute_composite_score(r),
    }
    return mapping.get(metric, compute_composite_score(r))
