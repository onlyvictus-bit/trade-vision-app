"""
research.signals.base — SignalDefinition dataclass + SignalRegistry singleton
=============================================================================
Each signal is a named, categorised, parameterised boolean-Series generator.
The registry auto-discovers signals decorated with @register_signal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


def _with_ohlcv_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Return a shallow copy with both lower and title OHLCV aliases."""
    pairs = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    if not any((a in df.columns and b not in df.columns) or (b in df.columns and a not in df.columns) for a, b in pairs.items()):
        return df
    out = df.copy(deep=False)
    for lower, title in pairs.items():
        if lower in out.columns and title not in out.columns:
            out[title] = out[lower]
        if title in out.columns and lower not in out.columns:
            out[lower] = out[title]
    return out


@dataclass
class SignalDefinition:
    """One tradeable signal (entry or exit condition)."""

    name: str                                      # e.g. "ema_cross_bull"
    category: str                                  # trend|momentum|volatility|volume|structure|pattern
    direction: str                                 # "bullish" | "bearish"
    params: Dict[str, Any] = field(default_factory=dict)       # tunable defaults
    param_grid: Dict[str, List] = field(default_factory=dict)  # grid-search values
    tags: List[str] = field(default_factory=list)              # ["crossover", "trend-following"]
    compute: Optional[Callable[[pd.DataFrame, Dict[str, Any]], pd.Series]] = None
    last_error: str | None = None
    last_count: int = 0

    # Per-instance result cache: (params_hash, df_id) → bool Series
    # Eliminates recomputing rsi(14) for every combo that uses it.
    _cache: Dict[tuple, pd.Series] = field(default_factory=dict, repr=False, compare=False)

    def clear_cache(self) -> None:
        """Call between jobs/datasets to free memory."""
        self._cache.clear()

    def __call__(
        self,
        df: pd.DataFrame,
        overrides: Dict[str, Any] | None = None,
        context_dfs: Dict[str, pd.DataFrame] | None = None
    ) -> pd.Series:
        """Compute boolean signal Series. Merges *overrides* into default params."""
        if self.compute is None:
            raise RuntimeError(f"Signal '{self.name}' has no compute function")

        merged = {**self.params, **(overrides or {})}

        # Cache key: stable hash of params + identity of df (same object = same data)
        try:
            params_hash = hash(frozenset(merged.items()))
        except TypeError:
            params_hash = hash(str(merged))
        cache_key = (params_hash, id(df))

        if cache_key in self._cache:
            return self._cache[cache_key]

        df_for_compute = _with_ohlcv_aliases(df)

        # Inspection to handle both (df, params) and (df, params, context_dfs) signatures
        import inspect
        spec = inspect.getfullargspec(self.compute)
        if "context_dfs" in spec.args or spec.varkw:
            result = self.compute(df_for_compute, merged, context_dfs=context_dfs)
        else:
            result = self.compute(df_for_compute, merged)

        result = result.reindex(df.index, fill_value=False).fillna(False).astype(bool)
        self.last_error = None
        self.last_count = int(result.sum())
        self._cache[cache_key] = result
        return result


class SignalRegistry:
    """Central catalogue of all available signals."""

    def __init__(self) -> None:
        self._signals: Dict[str, SignalDefinition] = {}

    # ── registration ──────────────────────────────────────────────────────
    def register(self, sig: SignalDefinition) -> None:
        if sig.name in self._signals:
            raise ValueError(f"Duplicate signal name: {sig.name}")
        self._signals[sig.name] = sig

    # ── lookup ────────────────────────────────────────────────────────────
    def get(self, name: str) -> SignalDefinition:
        if name not in self._signals:
            raise KeyError(f"Unknown signal: {name}")
        return self._signals[name]

    def list_all(self) -> List[SignalDefinition]:
        return list(self._signals.values())

    def list_by_category(self, cat: str) -> List[SignalDefinition]:
        return [s for s in self._signals.values() if s.category == cat]

    def list_names(self) -> List[str]:
        return list(self._signals.keys())

    def categories(self) -> List[str]:
        return sorted({s.category for s in self._signals.values()})

    # ── bulk compute (cache-friendly) ─────────────────────────────────────
    def compute_all(
        self,
        df: pd.DataFrame,
        context_dfs: Dict[str, pd.DataFrame] | None = None
    ) -> Dict[str, pd.Series]:
        """Pre-compute every registered signal. Returns {name: bool Series}."""
        cache: Dict[str, pd.Series] = {}
        for name, sig in self._signals.items():
            try:
                cache[name] = sig(df, context_dfs=context_dfs)
            except Exception:
                # Signal failed — mark as all-False
                cache[name] = pd.Series(False, index=df.index)
        return cache

    def _find_indicator_signal(self, indicator: str, direction: str) -> SignalDefinition:
        key = indicator.lower().replace(" ", "_").replace("-", "_")
        matches = [
            s for s in self._signals.values()
            if s.direction == direction
            and (s.name.startswith(key) or key in s.tags or key in s.name)
        ]
        if not matches:
            raise KeyError(f"No {direction} signal for indicator: {indicator}")
        return matches[0]

    def bullish(self, indicator: str, df: pd.DataFrame, params: Dict[str, Any] | None = None) -> pd.Series:
        """Call indicator bullish(df, params) through the registry."""
        return self._find_indicator_signal(indicator, "bullish")(df, params)

    def bearish(self, indicator: str, df: pd.DataFrame, params: Dict[str, Any] | None = None) -> pd.Series:
        """Call indicator bearish(df, params) through the registry."""
        return self._find_indicator_signal(indicator, "bearish")(df, params)

    def clear_all_caches(self) -> None:
        """Flush per-signal result caches. Call between jobs to free memory."""
        for sig in self._signals.values():
            sig.clear_cache()

    def __len__(self) -> int:
        return len(self._signals)

    def __contains__(self, name: str) -> bool:
        return name in self._signals


# ── module-level singleton ────────────────────────────────────────────────
registry = SignalRegistry()


def register_signal(
    name: str,
    category: str,
    direction: str,
    params: Dict[str, Any] | None = None,
    param_grid: Dict[str, List] | None = None,
    tags: List[str] | None = None,
):
    """Decorator: register a compute function as a signal."""
    def decorator(fn: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series]):
        sig = SignalDefinition(
            name=name,
            category=category,
            direction=direction,
            params=params or {},
            param_grid=param_grid or {},
            tags=tags or [],
            compute=fn,
        )
        registry.register(sig)
        return fn
    return decorator
