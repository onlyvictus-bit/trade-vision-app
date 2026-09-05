"""
research.engine.risk_matrix — ATR-based stop-loss / take-profit
================================================================
Computes per-bar SL/TP distances using ATR, then expands across
multiple R:R ratios.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

import pandas as pd


RR_RATIOS = [1.0, 1.5, 2.0, 2.5, 3.0]


def parse_rr_ratios(rr_strings: List[str]) -> List[float]:
    """Parse "1:2" → 2.0, "1:1.5" → 1.5, etc."""
    ratios = []
    for s in rr_strings:
        parts = s.split(":")
        if len(parts) == 2:
            ratios.append(float(parts[1]) / float(parts[0]))
        else:
            ratios.append(float(s))
    return ratios


def compute_atr_sl(
    df: pd.DataFrame,
    atr_period: int = 14,
    atr_mult: float = 1.5,
) -> pd.Series:
    """ATR-based stop-loss percentage per bar."""
    atr = (df["high"] - df["low"]).rolling(atr_period).mean()
    sl_pct = (atr * atr_mult) / df["close"]
    return sl_pct.clip(lower=0.005, upper=0.10)  # floor 0.5%, cap 10%


def compute_volatility_sl(
    df: pd.DataFrame,
    lookback: int = 30,
    mult: float = 1.0,
) -> pd.Series:
    """Recent range based stop-loss percentage per bar."""
    rng = (df["high"].rolling(lookback).max() - df["low"].rolling(lookback).min()) / df["close"]
    return (rng * mult).clip(lower=0.003, upper=0.10)


def expand_rr(
    sl_pct: float,
    rr_ratios: List[float] | None = None,
) -> List[Tuple[float, float, str]]:
    """
    Given a fixed SL %, return list of (sl_pct, tp_pct, rr_label).
    """
    if rr_ratios is None:
        rr_ratios = RR_RATIOS
    return [(sl_pct, sl_pct * rr, f"1:{rr}") for rr in rr_ratios]


def build_risk_pairs(
    df: pd.DataFrame,
    mode: str = "fixed",
    rr_ratios: List[float] | None = None,
    rr_labels: List[str] | None = None,
    fixed_sl_grid: Iterable[float] | None = None,
    fixed_tp_grid: Iterable[float] | None = None,
    atr_period: int = 14,
    atr_mult: float = 1.5,
) -> List[Tuple[float, float, str]]:
    """Return scalar (sl_pct, tp_pct, label) pairs for backtesting."""
    mode = (mode or "fixed").lower()
    if mode == "fixed":
        sls = list(fixed_sl_grid or [0.003, 0.005, 0.0075, 0.01, 0.015])
        tps = list(fixed_tp_grid or [0.005, 0.01, 0.015, 0.02, 0.03])
        return [(float(sl), float(tp), f"SL{sl:.4g}_TP{tp:.4g}") for sl in sls for tp in tps if tp > 0 and sl > 0]

    if mode == "volatility":
        sl_series = compute_volatility_sl(df)
    else:
        sl_series = compute_atr_sl(df, atr_period=atr_period, atr_mult=atr_mult)

    sl = float(sl_series.median())
    if pd.isna(sl) or sl <= 0:
        sl = 0.02

    ratios = rr_ratios or RR_RATIOS
    labels = rr_labels or [f"1:{r}" for r in ratios]
    return [(sl, sl * rr, labels[i] if i < len(labels) else f"1:{rr}") for i, rr in enumerate(ratios)]
