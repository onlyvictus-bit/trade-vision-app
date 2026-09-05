"""
shared.indicators.pta_signal_markers
=====================================
Converts research-engine PTA signals into {time, name, direction} marker events
for both the home chart (index.html) and the research signal chart (research.html).

Each function returns a list of marker dicts:
    [{"time": "YYYY-MM-DD", "name": "RSX Bull", "direction": "bull"}, ...]

compute_all(df) returns a flat dict keyed by pta_* for easy merging into
server.py / research/api.py indicator response.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Ensure research package is importable when called from server.py root
_ROOT = Path(__file__).resolve().parents[2]   # stock-app/
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_WARMUP_BARS = 20
_SKIP_SESSION_OPEN_BARS = 1
_MARKER_COOLDOWN_BARS = 0


# ── lazy registry import ──────────────────────────────────────────────────────

_REGISTRY_CACHE = None


def _reg():
    """Return the populated signal registry (imports all signal modules)."""
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE
    from research.signals import base as _base
    # Force module registration by importing all signal files
    import research.signals.pta_signals          # noqa: F401
    try:
        import research.signals.classic_signals  # noqa: F401
    except ImportError:
        pass
    _REGISTRY_CACHE = _base.registry
    return _REGISTRY_CACHE


def _is_intraday(df: pd.DataFrame) -> bool:
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        return (df.index[1] - df.index[0]).total_seconds() < 86400
    return False


def _time_str(idx, i: int, intraday: bool) -> str:
    t = idx[i]
    if hasattr(t, "strftime"):
        return t.strftime("%Y-%m-%d %H:%M") if intraday else t.strftime("%Y-%m-%d")
    s = str(t)
    return s[:16] if intraday else s[:10]


def _is_session_open_bar(idx, i: int, bars: int = _SKIP_SESSION_OPEN_BARS) -> bool:
    if i <= 0 or bars <= 0:
        return i < bars
    try:
        day = idx[i].date()
        j = i
        while j > 0 and idx[j - 1].date() == day:
            j -= 1
        return (i - j) < bars
    except Exception:
        return False


def _signal_to_markers(df: pd.DataFrame, signal_name: str,
                        label: str, direction: str) -> list:
    """Run one registry signal on df → marker event list."""
    try:
        reg = _reg()
        if signal_name not in reg:
            return []
        sig_def = reg.get(signal_name)
        mask: pd.Series = sig_def(df)
        if mask is None or mask.empty:
            return []
        mask = mask.fillna(False).astype(bool)
        intraday = _is_intraday(df)
        idx = df.index
        events = []
        last_i = -10**9
        for i, v in enumerate(mask):
            if not v or i < _WARMUP_BARS:
                continue
            if intraday and _is_session_open_bar(idx, i):
                continue
            if i - last_i < _MARKER_COOLDOWN_BARS:
                continue
            events.append({
                "time": _time_str(idx, i, intraday),
                "index": i,
                "name": label,
                "direction": direction,
            })
            last_i = i
        return events
    except Exception:
        return []


def _sanitize_events(events: list, drop_conflicts: bool = True) -> list:
    """Deduplicate markers and drop same-candle bull+bear conflicts."""
    if not events:
        return []

    deduped = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        t = event.get("time")
        direction = event.get("direction")
        name = event.get("name")
        if t is None or direction is None:
            continue
        deduped[(t, direction, name)] = event

    if not drop_conflicts:
        return sorted(deduped.values(), key=lambda x: str(x.get("time", "")))

    by_time = {}
    for event in deduped.values():
        by_time.setdefault(event.get("time"), []).append(event)

    clean = []
    for items in by_time.values():
        dirs = {x.get("direction") for x in items}
        if "bull" in dirs and "bear" in dirs:
            continue
        clean.extend(items)
    return sorted(clean, key=lambda x: str(x.get("time", "")))


def _pair(df, bull_sig, bear_sig, bull_label, bear_label) -> list:
    events = _signal_to_markers(df, bull_sig, bull_label, "bull")
    events += _signal_to_markers(df, bear_sig, bear_label, "bear")
    return _sanitize_events(events)


# ── individual signal groups ──────────────────────────────────────────────────

def rsx_markers(df: pd.DataFrame) -> list:
    return _pair(df, "rsx_bull", "rsx_bear", "RSX Bull", "RSX Bear")

def fisher_signal_markers(df: pd.DataFrame) -> list:
    return _pair(df, "fisher_bull", "fisher_bear", "Fisher Bull", "Fisher Bear")

def kdj_markers(df: pd.DataFrame) -> list:
    return _pair(df, "kdj_bull", "kdj_bear", "KDJ Bull", "KDJ Bear")

def mfi_signal_markers(df: pd.DataFrame) -> list:
    return _pair(df, "mfi_bull", "mfi_bear", "MFI Bull", "MFI Bear")

def cmf_markers(df: pd.DataFrame) -> list:
    return _pair(df, "cmf_bull", "cmf_bear", "CMF Bull", "CMF Bear")

def vortex_markers(df: pd.DataFrame) -> list:
    return _pair(df, "vortex_bull", "vortex_bear", "Vortex Bull", "Vortex Bear")

def aroon_signal_markers(df: pd.DataFrame) -> list:
    return _pair(df, "aroon_bull", "aroon_bear", "Aroon Bull", "Aroon Bear")

def tsi_markers(df: pd.DataFrame) -> list:
    return _pair(df, "tsi_bull", "tsi_bear", "TSI Bull", "TSI Bear")

def chop_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "chop_trending", "CHOP Trend", "neutral")

def squeeze_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "squeeze_bull", "Squeeze Bull", "bull")

def zscore_markers(df: pd.DataFrame) -> list:
    return _pair(df, "zscore_extreme_bull", "zscore_extreme_bear",
                 "ZScore Bull", "ZScore Bear")

def kurtosis_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "kurtosis_spike", "Kurtosis Spike", "neutral")

def skew_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "skew_negative_bull", "Skew Bull", "bull")

def log_return_markers(df: pd.DataFrame) -> list:
    return _pair(df, "log_return_momentum_bull", "log_return_momentum_bear",
                 "LogRet Bull", "LogRet Bear")

def drawdown_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "drawdown_recovery_bull", "DD Recovery", "bull")

def hlc3_markers(df: pd.DataFrame) -> list:
    return _pair(df, "hlc3_ma_cross_bull", "hlc3_ma_cross_bear",
                 "HLC3 Bull", "HLC3 Bear")

def ebsw_markers(df: pd.DataFrame) -> list:
    return _pair(df, "ebsw_bull", "ebsw_bear", "EBSW Bull", "EBSW Bear")

def dsp_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "dsp_bull", "DSP Bull", "bull")

def amat_markers(df: pd.DataFrame) -> list:
    return _pair(df, "amat_bull", "amat_bear", "AMAT Bull", "AMAT Bear")

def ttm_trend_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "ttm_trend_bull", "TTM Trend", "bull")

def long_run_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "long_run_bull", "Long Run", "bull")

def short_run_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "short_run_bear", "Short Run", "bear")

def entropy_markers(df: pd.DataFrame) -> list:
    return _signal_to_markers(df, "entropy_low_bull", "Entropy Low", "bull")


# ── master compute ────────────────────────────────────────────────────────────

def _compute_all_legacy(df: pd.DataFrame) -> dict:
    """
    Run all PTA signal groups. Returns dict keyed by pta_* for merging
    into the main indicators response.
    """
    raw = {
        "pta_rsx":        rsx_markers(df),
        "pta_fisher_sig": fisher_signal_markers(df),
        "pta_kdj":        kdj_markers(df),
        "pta_mfi_sig":    mfi_signal_markers(df),
        "pta_cmf":        cmf_markers(df),
        "pta_vortex":     vortex_markers(df),
        "pta_aroon_sig":  aroon_signal_markers(df),
        "pta_tsi":        tsi_markers(df),
        "pta_chop":       chop_markers(df),
        "pta_squeeze":    squeeze_markers(df),
        "pta_zscore":     zscore_markers(df),
        "pta_kurtosis":   kurtosis_markers(df),
        "pta_skew":       skew_markers(df),
        "pta_log_ret":    log_return_markers(df),
        "pta_drawdown":   drawdown_markers(df),
        "pta_hlc3":       hlc3_markers(df),
        "pta_ebsw":       ebsw_markers(df),
        "pta_dsp":        dsp_markers(df),
        "pta_amat":       amat_markers(df),
        "pta_ttm":        ttm_trend_markers(df),
        "pta_long_run":   long_run_markers(df),
        "pta_short_run":  short_run_markers(df),
        "pta_entropy":    entropy_markers(df),
    }
    return {k: _sanitize_events(v) if isinstance(v, list) else v for k, v in raw.items()}


PTA_SIGNAL_REGISTRY = {
    "pta_rsx": rsx_markers,
    "pta_fisher_sig": fisher_signal_markers,
    "pta_kdj": kdj_markers,
    "pta_mfi_sig": mfi_signal_markers,
    "pta_cmf": cmf_markers,
    "pta_vortex": vortex_markers,
    "pta_aroon_sig": aroon_signal_markers,
    "pta_tsi": tsi_markers,
    "pta_chop": chop_markers,
    "pta_squeeze": squeeze_markers,
    "pta_zscore": zscore_markers,
    "pta_kurtosis": kurtosis_markers,
    "pta_skew": skew_markers,
    "pta_log_ret": log_return_markers,
    "pta_drawdown": drawdown_markers,
    "pta_hlc3": hlc3_markers,
    "pta_ebsw": ebsw_markers,
    "pta_dsp": dsp_markers,
    "pta_amat": amat_markers,
    "pta_ttm": ttm_trend_markers,
    "pta_long_run": long_run_markers,
    "pta_short_run": short_run_markers,
    "pta_entropy": entropy_markers,
}


PTA_SIGNAL_METADATA = {
    key: {
        "key": key,
        "label": key.replace("pta_", "").replace("_", " ").title(),
        "category": "pta",
        "visual_type": "marker-only",
        "default_params": {},
        "supports_replay": True,
        "is_canvas_overlay": False,
    }
    for key in PTA_SIGNAL_REGISTRY
}


def compute_selected(df: pd.DataFrame, keys: list[str]) -> dict:
    out = {}
    for key in keys:
        fn = PTA_SIGNAL_REGISTRY.get(key)
        if fn is None:
            raise KeyError(key)
        try:
            value = fn(df)
        except Exception:
            value = []
        out[key] = _sanitize_events(value) if isinstance(value, list) else value
    return out


def compute_all(df: pd.DataFrame) -> dict:
    """
    Run all PTA signal groups. Returns dict keyed by pta_* for merging
    into the main indicators response.
    """
    return compute_selected(df, list(PTA_SIGNAL_REGISTRY.keys()))
