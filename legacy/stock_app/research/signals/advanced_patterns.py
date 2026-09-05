"""
research.signals.advanced_patterns — S/R and trendline proximity signals.

Compute functions receive (df: DataFrame, params: dict) matching the registry contract.
Uses shared.indicators.patterns — no server.py import.
"""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .base import register_signal


def _pat():
    from shared.indicators import patterns as _p
    return _p


@register_signal(
    name="sr_support",
    category="structure",
    direction="bullish",
    params={"proximity_pct": 0.5},
    param_grid={"proximity_pct": [0.3, 0.5, 0.8]},
    tags=["support-resistance", "level"],
)
def sr_support(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pat().sr_near_price(df, symbol="", proximity_pct=params["proximity_pct"])


@register_signal(
    name="trendline_touch",
    category="structure",
    direction="bullish",
    params={"proximity_pct": 0.3},
    param_grid={"proximity_pct": [0.2, 0.3, 0.5]},
    tags=["trendline", "level"],
)
def trendline_touch(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    return _pat().near_trendline(df, proximity_pct=params["proximity_pct"])
