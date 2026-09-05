"""
shared.indicators.self_indc — Wrappers for D:\\Projects\\test1\\self indc indicators.

All functions:
  - Accept a pandas DataFrame with OHLCV columns (Open/High/Low/Close/Volume)
  - Normalize to lowercase before passing to each indicator module
  - Return standardized output:
      * Marker events: [{time, name, direction}]  (shown on candlestick chart)
      * Sub-pane data: {values: [...], ...}        (oscillator panel)
      * Level data:    {p, bp, tp, r1, s1, ...}    (price lines)
  - Silently return [] / {} on any error
"""
from __future__ import annotations

import sys
import types
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

_WARMUP_BARS = 20
_SKIP_SESSION_OPEN_BARS = 1
_MARKER_COOLDOWN_BARS = 50

# ── paths ──────────────────────────────────────────────────────────────────
_SELF_INDC_PATH = Path(r"D:\Projects\test1\self indc")
_SMC_PATH = Path(r"D:\Projects\test1\opensource_indicators\smart-money-concepts\smartmoneyconcepts\smc.py")


# ── helpers ────────────────────────────────────────────────────────────────

def _norm(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase for self-indc modules."""
    rename = {}
    for col in df.columns:
        lc = col.lower()
        if lc in ("open", "high", "low", "close", "volume"):
            rename[col] = lc
    return df.rename(columns=rename)


def _time_str(idx, i: int, is_intraday: bool) -> str:
    t = idx[i]
    if hasattr(t, "strftime"):
        if is_intraday:
            return t.strftime("%Y-%m-%d %H:%M")
        return t.strftime("%Y-%m-%d")
    s = str(t)
    return s[:16] if is_intraday else s[:10]


def _is_intraday(df: pd.DataFrame) -> bool:
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        diff = (df.index[1] - df.index[0]).total_seconds()
        return diff < 86400
    return False


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


def _load_module(name: str):
    """Import a module from _SELF_INDC_PATH by filename stem."""
    path = _SELF_INDC_PATH / f"{name}.py"
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    mod = types.ModuleType(name)
    mod.__file__ = str(path)
    sys.modules[name] = mod
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def _load_smc():
    """Load the SMC library."""
    with open(_SMC_PATH, "r", encoding="utf-8") as f:
        src = f.read()
    mod = types.ModuleType("_smc_lib")
    mod.__file__ = str(_SMC_PATH)
    sys.modules["_smc_lib"] = mod
    exec(compile(src, str(_SMC_PATH), "exec"), mod.__dict__)
    return mod.smc


def _sanitize_events(events: list, drop_conflicts: bool = True) -> list:
    """Deduplicate markers and remove same-candle bull+bear conflicts."""
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
        chosen = sorted(items, key=lambda x: (str(x.get("direction", "")), str(x.get("name", ""))))[0]
        clean.append(chosen)
    return sorted(clean, key=lambda x: str(x.get("time", "")))


def _append_event_with_cooldown(events: list, idx, i: int, intraday: bool, name: str, direction: str, last_seen: dict):
    if i < _WARMUP_BARS:
        return
    if intraday and _is_session_open_bar(idx, i):
        return
    key = (name, direction)
    last_i = last_seen.get(key, -10**9)
    if i - last_i < _MARKER_COOLDOWN_BARS:
        return
    events.append({"index": int(i), "time": _time_str(idx, i, intraday), "name": name, "direction": direction})
    last_seen[key] = i


def _session_open_times(df: pd.DataFrame) -> set[str]:
    intraday = _is_intraday(df)
    if not intraday:
        return set()
    idx = df.index
    out = set()
    for i in range(len(idx)):
        if _is_session_open_bar(idx, i):
            out.add(_time_str(idx, i, intraday))
    return out


def _drop_session_open_events(events: list, open_times: set[str]) -> list:
    if not open_times or not events:
        return events
    return [e for e in events if not isinstance(e, dict) or e.get("time") not in open_times]


def _sanitize_payload(value, open_times: set[str] | None = None):
    if isinstance(value, list):
        return _sanitize_events(_drop_session_open_events(value, open_times or set()))
    if isinstance(value, dict):
        cleaned = dict(value)
        if isinstance(cleaned.get("signals"), list):
            cleaned["signals"] = _sanitize_events(_drop_session_open_events(cleaned["signals"], open_times or set()))
        return cleaned
    return value


def _to_events(df_norm: pd.DataFrame, bull_col: str, bear_col: str,
               bull_name: str, bear_name: str,
               neutral_col: str | None = None, neutral_name: str | None = None) -> list:
    """Convert boolean signal columns to marker event list."""
    intraday = _is_intraday(df_norm)
    events = []
    idx = df_norm.index
    n = len(df_norm)
    last_seen = {}
    if bull_col in df_norm.columns:
        for i in range(_WARMUP_BARS, n):
            if df_norm[bull_col].iloc[i]:
                _append_event_with_cooldown(events, idx, i, intraday, bull_name, "bull", last_seen)
    if bear_col in df_norm.columns:
        for i in range(_WARMUP_BARS, n):
            if df_norm[bear_col].iloc[i]:
                _append_event_with_cooldown(events, idx, i, intraday, bear_name, "bear", last_seen)
    if neutral_col and neutral_name and neutral_col in df_norm.columns:
        for i in range(_WARMUP_BARS, n):
            if df_norm[neutral_col].iloc[i]:
                _append_event_with_cooldown(events, idx, i, intraday, neutral_name, "neutral", last_seen)
    return _sanitize_events(events)


# ── 1. CDL Patterns (15 patterns, Pine port) ──────────────────────────────

_CDL_BULL = {"bullish_harami", "bullish_engulfing", "piercing_line",
             "bullish_belt", "bullish_kicker", "morning_star", "hammer", "inverted_hammer"}
_CDL_BEAR = {"bearish_harami", "bearish_engulfing", "bearish_kicker",
             "hanging_man", "evening_star", "shooting_star"}
_CDL_NEUTRAL = {"doji"}

_CDL_LABELS = {
    "doji": "Doji", "bearish_harami": "B.Harami", "bullish_harami": "B.Harami",
    "bearish_engulfing": "Bear Engulf", "bullish_engulfing": "Bull Engulf",
    "piercing_line": "Piercing", "bullish_belt": "Bull Belt",
    "bullish_kicker": "Bull Kick", "bearish_kicker": "Bear Kick",
    "hanging_man": "Hang Man", "evening_star": "Eve Star",
    "morning_star": "Morn Star", "shooting_star": "Shoot Star",
    "hammer": "Hammer", "inverted_hammer": "Inv Hammer",
}

_CDL_PRIORITY = {
    "Morn Star": 100,
    "Eve Star": 100,
    "Bull Kick": 96,
    "Bear Kick": 96,
    "Bull Engulf": 90,
    "Bear Engulf": 90,
    "Piercing": 86,
    "Hammer": 82,
    "Shoot Star": 82,
    "Inv Hammer": 78,
    "Hang Man": 78,
    "B.Harami": 68,
    "Bull Belt": 58,
    "Doji": 30,
}


def _select_best_cdl_events(events: list, cooldown_bars: int = 30) -> list:
    """One production-ready candle-pattern marker per candle, then global cooldown."""
    if not events:
        return []
    by_time = {}
    for event in events:
        t = event.get("time")
        if t is None:
            continue
        old = by_time.get(t)
        old_score = _CDL_PRIORITY.get(str(old.get("name")), 0) if old else -1
        new_score = _CDL_PRIORITY.get(str(event.get("name")), 0)
        if old is None or new_score > old_score:
            by_time[t] = event

    selected = []
    last_index = -10**9
    for event in sorted(by_time.values(), key=lambda x: (int(x.get("index", -1)), str(x.get("time", "")))):
        i = int(event.get("index", -1))
        if i >= 0 and i - last_index < cooldown_bars:
            continue
        selected.append(event)
        if i >= 0:
            last_index = i
    return selected


def cdl_patterns_adv(df: pd.DataFrame, cooldown_bars: int = 30) -> list:
    """15 candlestick patterns from candlestick_patterns_identified.py → marker events."""
    try:
        mod = _load_module("candlestick_patterns_identified")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        events = []
        last_seen = {}
        for col in ("doji", "bearish_harami", "bullish_harami", "bearish_engulfing",
                    "bullish_engulfing", "piercing_line", "bullish_belt", "bullish_kicker",
                    "bearish_kicker", "hanging_man", "evening_star", "morning_star",
                    "shooting_star", "hammer", "inverted_hammer"):
            if col not in result.columns:
                continue
            direction = "bull" if col in _CDL_BULL else ("bear" if col in _CDL_BEAR else "neutral")
            label = _CDL_LABELS.get(col, col)
            mask = result[col].fillna(False).astype(bool)
            for i in mask[mask].index:
                loc = result.index.get_loc(i)
                before = len(events)
                _append_event_with_cooldown(events, idx, loc, intraday, label, direction, last_seen)
                if len(events) > before:
                    events[-1]["index"] = int(loc)
        return _select_best_cdl_events(_sanitize_events(events, drop_conflicts=True), cooldown_bars=cooldown_bars)
    except Exception:
        return []


# ── 2. Outside Reversal ───────────────────────────────────────────────────

def outside_reversal(df: pd.DataFrame, use_fixed_logic: bool = True) -> list:
    """Frank Ochoa Outside Reversal markers."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return []
        intraday = _is_intraday(work)
        idx = work.index
        prev_low = work["low"].shift(1)
        prev_high = work["high"].shift(1)
        prev_close = work["close"].shift(1)
        prev_open = work["open"].shift(1)

        bull_open_filter = work["open"] < (prev_open if use_fixed_logic else prev_close)
        reversal_long = (
            (work["low"] < prev_low)
            & (work["close"] > prev_high)
            & bull_open_filter
        ).fillna(False)
        reversal_short = (
            (work["high"] > prev_high)
            & (work["close"] < prev_low)
            & (work["open"] > prev_open)
        ).fillna(False)

        events = []
        for i in range(1, len(work)):
            if intraday and _is_session_open_bar(idx, i):
                continue
            if bool(reversal_long.iloc[i]) and not bool(reversal_short.iloc[i]):
                events.append({"time": _time_str(idx, i, intraday), "name": "Out Rev Bull", "direction": "bull", "index": i})
            elif bool(reversal_short.iloc[i]) and not bool(reversal_long.iloc[i]):
                events.append({"time": _time_str(idx, i, intraday), "name": "Out Rev Bear", "direction": "bear", "index": i})
        return _sanitize_events(events)
    except Exception:
        return []


# ── 3. Three Inside (TradingFinder) ───────────────────────────────────────

def _three_inside_detect(df: pd.DataFrame, filter_mode: str = "On") -> pd.DataFrame:
    work = _norm(df).copy().sort_index()
    candle_range = (work["high"] - work["low"]).replace(0, np.nan)
    candle_body = work["close"] - work["open"]
    full_body = (candle_body.abs() / candle_range).fillna(0)
    high_1 = work["high"].shift(1)
    high_2 = work["high"].shift(2)
    low_1 = work["low"].shift(1)
    low_2 = work["low"].shift(2)
    neg_2 = (candle_body < 0).shift(2, fill_value=False).astype(bool)
    pos_2 = (candle_body > 0).shift(2, fill_value=False).astype(bool)

    bull_w = (
        neg_2 & (candle_body > 0)
        & (full_body >= 0.6) & (full_body <= 0.8)
        & (work["close"] > high_1)
        & (work["close"] > ((low_2 + high_2) / 2))
        & (high_1 < high_2) & (low_2 > low_1)
    ).fillna(False)
    bull_s = (
        neg_2 & (candle_body > 0)
        & (full_body > 0.8)
        & (work["close"] > high_1)
        & (work["close"] > ((low_2 + high_2) / 2))
        & (high_1 < high_2) & (low_2 > low_1)
    ).fillna(False)
    bear_w = (
        (candle_body < 0) & pos_2
        & (full_body >= 0.6) & (full_body <= 0.8)
        & (work["close"] < low_1)
        & (work["close"] < ((low_2 + high_2) / 2))
        & (high_1 > high_2) & (low_2 < low_1)
    ).fillna(False)
    bear_s = (
        (candle_body < 0) & pos_2
        & (full_body > 0.8)
        & (work["close"] < low_1)
        & (work["close"] < ((low_2 + high_2) / 2))
        & (high_1 > high_2) & (low_2 < low_1)
    ).fillna(False)

    if filter_mode == "On":
        work["bullish_signal"] = bull_s
        work["bearish_signal"] = bear_s
    else:
        work["bullish_signal"] = bull_s | bull_w
        work["bearish_signal"] = bear_s | bear_w
    work["inside_bar_Bull_W"] = bull_w
    work["inside_bar_Bull_S"] = bull_s
    work["inside_bar_Bear_W"] = bear_w
    work["inside_bar_Bear_S"] = bear_s
    return work


def three_inside(df: pd.DataFrame, filter_mode: str = "On", use_addon_filters: bool = False) -> list:
    """Three Inside Up/Down markers from TradingFinder-style Pine rules."""
    try:
        work = _three_inside_detect(df, filter_mode=filter_mode)
        intraday = _is_intraday(work)
        idx = work.index
        bull = work["bullish_signal"].copy()
        bear = work["bearish_signal"].copy()
        if use_addon_filters:
            ema20 = work["close"].ewm(span=20, adjust=False).mean()
            ema50 = work["close"].ewm(span=50, adjust=False).mean()
            volume = work["volume"] if "volume" in work.columns else pd.Series(1, index=work.index)
            vol_ok = volume > volume.rolling(20, min_periods=1).mean()
            bull = bull & (work["close"] > ema20) & (ema20 > ema50) & vol_ok
            bear = bear & (work["close"] < ema20) & (ema20 < ema50) & vol_ok
        events = []
        for i in range(2, len(work)):
            if intraday and _is_session_open_bar(idx, i):
                continue
            if bool(bull.iloc[i]) and not bool(bear.iloc[i]):
                label = "3-In Bull+" if use_addon_filters else "3-In Bull"
                events.append({"time": _time_str(idx, i, intraday), "name": label, "direction": "bull", "index": i})
            elif bool(bear.iloc[i]) and not bool(bull.iloc[i]):
                label = "3-In Bear+" if use_addon_filters else "3-In Bear"
                events.append({"time": _time_str(idx, i, intraday), "name": label, "direction": "bear", "index": i})
        return _sanitize_events(events)
    except Exception:
        return []


def three_inside_filtered(df: pd.DataFrame) -> list:
    """Three Inside add-on: strong pattern + EMA trend + volume confirmation."""
    return three_inside(df, filter_mode="On", use_addon_filters=True)


# ── 4. Dark Cloud / Piercing Line ─────────────────────────────────────────

def dark_cloud_piercing(df: pd.DataFrame) -> list:
    """Dark cloud cover + piercing line → marker events."""
    try:
        mod = _load_module("dark_cloud_piercing_line_tradingfinder")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        events = []
        intraday = _is_intraday(result)
        idx = result.index
        for col, label, direction in [
            ("strong_dark_cloud",   "Dark Cloud",    "bear"),
            ("weak_dark_cloud",     "Weak D.Cloud",  "bear"),
            ("strong_piercing_line","Piercing Line", "bull"),
            ("weak_piercing_line",  "Weak Pierce",   "bull"),
        ]:
            if col not in result.columns:
                continue
            mask = result[col].fillna(False).astype(bool)
            last_seen = {}
            for i in mask[mask].index:
                loc = result.index.get_loc(i)
                _append_event_with_cooldown(events, idx, loc, intraday, label, direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 5. Volume Exhaustion ──────────────────────────────────────────────────

def dark_cloud_piercing(df: pd.DataFrame) -> list:
    """Dark Cloud + Piercing Line markers from TradingFinder-style Pine rules."""
    try:
        work = _norm(df).copy().sort_index()
        rng = (work["high"] - work["low"]).replace(0, np.nan)
        body = work["close"] - work["open"]
        pos = body > 0
        neg = body < 0
        full_body = (body.abs() / rng).fillna(0) > 0.6
        full_body_prev = full_body.shift(1, fill_value=False).astype(bool)
        prev_mid = work["low"].shift(1) + (work["high"].shift(1) - work["low"].shift(1)) * 0.5

        first_dc = pos.shift(1, fill_value=False).astype(bool) & neg
        dc_open_weak = work["open"] >= work["close"].shift(1)
        dc_open_strong = work["open"] >= work["high"].shift(1)
        dc_high_break = work["high"] > work["high"].shift(1)
        dc_semi = (work["close"] < work["close"].shift(1)) & (work["close"] > prev_mid)
        dc_full = work["close"] <= prev_mid
        weak_dark = (
            first_dc & dc_high_break & full_body & full_body_prev
            & ((dc_open_weak & dc_semi) | (dc_open_strong & dc_semi) | (dc_open_weak & dc_full))
        ).fillna(False)
        strong_dark = (
            first_dc & dc_open_strong & dc_high_break & full_body & full_body_prev & dc_full
        ).fillna(False)
        weak_dark = weak_dark & ~strong_dark

        first_pl = pos & neg.shift(1, fill_value=False).astype(bool)
        pl_open_weak = work["open"] <= work["close"].shift(1)
        pl_open_strong = work["open"] <= work["low"].shift(1)
        pl_low_break = work["low"] < work["low"].shift(1)
        pl_semi = (work["close"] > work["close"].shift(1)) & (work["close"] < prev_mid)
        pl_full = work["close"] >= prev_mid
        weak_pierce = (
            first_pl & pl_low_break & full_body & full_body_prev
            & ((pl_open_weak & pl_semi) | (pl_open_strong & pl_semi) | (pl_open_weak & pl_full))
        ).fillna(False)
        strong_pierce = (
            first_pl & pl_open_strong & pl_low_break & full_body & full_body_prev & pl_full
        ).fillna(False)
        weak_pierce = weak_pierce & ~strong_pierce

        intraday = _is_intraday(work)
        idx = work.index
        events = []
        for i in range(1, len(work)):
            if intraday and _is_session_open_bar(idx, i):
                continue
            if bool(strong_dark.iloc[i]):
                events.append({"time": _time_str(idx, i, intraday), "name": "Dark Cloud", "direction": "bear", "index": i})
            elif bool(weak_dark.iloc[i]):
                events.append({"time": _time_str(idx, i, intraday), "name": "Weak D.Cloud", "direction": "bear", "index": i})
            elif bool(strong_pierce.iloc[i]):
                events.append({"time": _time_str(idx, i, intraday), "name": "Piercing Line", "direction": "bull", "index": i})
            elif bool(weak_pierce.iloc[i]):
                events.append({"time": _time_str(idx, i, intraday), "name": "Weak Pierce", "direction": "bull", "index": i})
        return _sanitize_events(events)
    except Exception:
        return []


def vol_exhaustion_markers(df: pd.DataFrame) -> list:
    """Volume exhaustion reversal → marker events."""
    try:
        mod = _load_module("volume_exhaustion")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_vol_exhaustion", "bearish_vol_exhaustion",
                          "Vol Exhaust Bull", "Vol Exhaust Bear")
    except Exception:
        return []


# ── 6. RSI Divergence (sub-pane) ──────────────────────────────────────────

def rsi_divergence_sub(df: pd.DataFrame) -> dict:
    """RSI Divergence (fast-slow) → {divergence: [...], zero: 0} for sub-pane."""
    try:
        mod = _load_module("rsi_divergence")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        div = result["divergence"].tolist()
        return {
            "divergence": [round(float(v), 4) if v == v else None for v in div],
            "rsi_fast":   [round(float(v), 4) if v == v else None for v in result["rsi_fast"].tolist()],
            "rsi_slow":   [round(float(v), 4) if v == v else None for v in result["rsi_slow"].tolist()],
        }
    except Exception:
        return {}


# ── 7. CPR Levels (price lines) ───────────────────────────────────────────

def cpr_levels(df: pd.DataFrame) -> dict:
    """
    Central Pivot Range from previous session OHLC → {p, bp, tp, r1, r2, s1, s2}.
    Uses simple daily resample — works for any timeframe.
    """
    try:
        work = df.copy()
        # try daily resample
        freq = "D"
        if isinstance(work.index, pd.DatetimeIndex):
            daily = work.resample(freq).agg(
                Open=("Open", "first"),
                High=("High", "max"),
                Low=("Low", "min"),
                Close=("Close", "last"),
            ).dropna(subset=["Close"])
        else:
            return {}
        if len(daily) < 2:
            return {}
        prev = daily.iloc[-2]
        H, L, C = float(prev["High"]), float(prev["Low"]), float(prev["Close"])
        P  = (H + L + C) / 3       # pivot
        BP = (H + L) / 2            # bottom central pivot (BC)
        TP = (P - BP) + P           # top central pivot (TC)
        R1 = 2 * P - L
        S1 = 2 * P - H
        R2 = P + H - L
        S2 = P - (H - L)
        R3 = H + 2 * (P - L)
        S3 = L - 2 * (H - P)
        return {
            "p":  round(P,  2), "bp": round(BP, 2), "tp": round(TP, 2),
            "r1": round(R1, 2), "s1": round(S1, 2),
            "r2": round(R2, 2), "s2": round(S2, 2),
            "r3": round(R3, 2), "s3": round(S3, 2),
        }
    except Exception:
        return {}


# ── 8. Swing Structure (SMC-based) ────────────────────────────────────────

def swing_structure(df: pd.DataFrame) -> list:
    """HH/HL/LH/LL structure shift → marker events. Requires SMC library."""
    try:
        smc = _load_smc()
        work = _norm(df).reset_index(drop=True)
        swing = smc.swing_highs_lows(work, swing_length=3)
        swing_hl = swing["HighLow"].fillna(0).values
        high_arr = work["high"].values
        low_arr  = work["low"].values
        n = len(work)

        bullish = np.zeros(n, dtype=int)
        bearish = np.zeros(n, dtype=int)

        sh_idxs = [i for i in range(n) if swing_hl[i] == 1]
        sl_idxs = [i for i in range(n) if swing_hl[i] == -1]

        prev_sh, prev_sh_type = None, None
        for idx in sh_idxs:
            p = high_arr[idx]
            if prev_sh is None:
                prev_sh, prev_sh_type = p, None
                continue
            t = "HH" if p > prev_sh else "LH"
            if t == "LH" and prev_sh_type == "HH":
                bearish[idx] = 1
            prev_sh, prev_sh_type = p, t

        prev_sl, prev_sl_type = None, None
        for idx in sl_idxs:
            p = low_arr[idx]
            if prev_sl is None:
                prev_sl, prev_sl_type = p, None
                continue
            t = "HL" if p > prev_sl else "LL"
            if t == "HL" and prev_sl_type == "LL":
                bullish[idx] = 1
            prev_sl, prev_sl_type = p, t

        orig_idx = df.index
        intraday = _is_intraday(df)
        events = []
        last_seen = {}
        for i in range(n):
            if bullish[i]:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "HL Structure", "bull", last_seen)
            elif bearish[i]:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "LH Structure", "bear", last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# Production override for Swing Structure.
# The legacy SMC wrapper above can emit time-only events, which breaks the
# frontend's index-based marker placement. Keep this direct detector close to
# the wrapper so compute_all resolves to the index-safe implementation.
def cpr_levels(df: pd.DataFrame) -> dict:
    """Daily CPR from previous session OHLC, with full stepped per-bar series."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {}
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {}

        daily = work.resample("D").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
        ).dropna(subset=["close"])
        if len(daily) < 2:
            return {}

        levels_by_day = {}
        for day, row in daily.shift(1).dropna(subset=["high", "low", "close"]).iterrows():
            H, L, C = float(row["high"]), float(row["low"]), float(row["close"])
            P = (H + L + C) / 3
            BC = (H + L) / 2
            TC = (P - BC) + P
            R1 = 2 * P - L
            S1 = 2 * P - H
            R2 = P + H - L
            S2 = P - (H - L)
            R3 = H + 2 * (P - L)
            S3 = L - 2 * (H - P)
            R4 = R3 + (R2 - R1)
            S4 = S3 - (S1 - S2)
            levels_by_day[day.date()] = {
                "p": P, "bc": BC, "tc": TC,
                "prev_day_high": H, "prev_day_low": L,
                "r1": R1, "r2": R2, "r3": R3, "r4": R4,
                "s1": S1, "s2": S2, "s3": S3, "s4": S4,
            }

        keys = ("p", "bc", "tc", "prev_day_high", "prev_day_low",
                "r1", "r2", "r3", "r4", "s1", "s2", "s3", "s4")
        series = {key: [] for key in keys}
        days = []
        for ts in work.index:
            levels = levels_by_day.get(ts.date())
            days.append(ts.date().isoformat())
            for key in keys:
                series[key].append(round(float(levels[key]), 2) if levels else None)

        latest = {}
        for key in keys:
            vals = [v for v in series[key] if v is not None]
            latest[key] = vals[-1] if vals else None

        return {
            **latest,
            "bp": latest.get("bc"),
            "series": series,
            "days": days,
            "formula": "previous_daily",
        }
    except Exception:
        return {}


def swing_structure(df: pd.DataFrame) -> list:
    """Confirmed HH/HL/LH/LL structure markers with exact candle indices."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"high", "low"}.issubset(work.columns):
            return []

        idx = work.index
        n = len(work)
        if n < 12:
            return []

        intraday = _is_intraday(work)
        if isinstance(idx, pd.DatetimeIndex) and n > 1:
            minutes = max(1, round((idx[1] - idx[0]).total_seconds() / 60))
            if minutes <= 5:
                pivot_len = 6
            elif minutes <= 30:
                pivot_len = 5
            elif minutes <= 90:
                pivot_len = 4
            else:
                pivot_len = 3
        else:
            pivot_len = 3

        high = work["high"].astype(float)
        low = work["low"].astype(float)
        events = []
        last_high = None
        last_low = None

        for i in range(pivot_len, n - pivot_len):
            if intraday and _is_session_open_bar(idx, i):
                continue

            hwin = high.iloc[i - pivot_len:i + pivot_len + 1]
            lwin = low.iloc[i - pivot_len:i + pivot_len + 1]
            is_swing_high = bool(high.iloc[i] == hwin.max())
            is_swing_low = bool(low.iloc[i] == lwin.min())

            if is_swing_high:
                current = float(high.iloc[i])
                if last_high is not None:
                    is_hh = current > last_high
                    events.append({
                        "time": _time_str(idx, i, intraday),
                        "name": "HH Structure" if is_hh else "LH Structure",
                        "direction": "bull" if is_hh else "bear",
                        "index": int(i),
                        "confirmed_index": int(min(i + pivot_len, n - 1)),
                        "price": round(current, 4),
                    })
                last_high = current

            if is_swing_low:
                current = float(low.iloc[i])
                if last_low is not None:
                    is_hl = current > last_low
                    events.append({
                        "time": _time_str(idx, i, intraday),
                        "name": "HL Structure" if is_hl else "LL Structure",
                        "direction": "bull" if is_hl else "bear",
                        "index": int(i),
                        "confirmed_index": int(min(i + pivot_len, n - 1)),
                        "price": round(current, 4),
                    })
                last_low = current

        return _sanitize_events(events)
    except Exception:
        return []


# ── 9. SMC Break of Structure ─────────────────────────────────────────────

def smc_bos_markers(df: pd.DataFrame) -> list:
    """SMC BOS signals → marker events. Requires SMC library."""
    try:
        smc = _load_smc()
        work = _norm(df).reset_index(drop=True)
        swing = smc.swing_highs_lows(work, swing_length=3)
        bos   = smc.bos_choch(work, swing, close_break=True)
        intraday = _is_intraday(df)
        orig_idx = df.index
        events = []
        bos_vals = bos["BOS"].fillna(0).values
        last_seen = {}
        for i in range(len(bos_vals)):
            if bos_vals[i] == 1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "BOS Bull", "bull", last_seen)
            elif bos_vals[i] == -1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "BOS Bear", "bear", last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 10. SMC Change of Character ───────────────────────────────────────────

def smc_choch_markers(df: pd.DataFrame) -> list:
    """SMC CHoCH signals → marker events. Requires SMC library."""
    try:
        smc = _load_smc()
        work = _norm(df).reset_index(drop=True)
        swing = smc.swing_highs_lows(work, swing_length=3)
        bos   = smc.bos_choch(work, swing, close_break=True)
        intraday = _is_intraday(df)
        orig_idx = df.index
        events = []
        choch_vals = bos["CHOCH"].fillna(0).values
        last_seen = {}
        for i in range(len(choch_vals)):
            if choch_vals[i] == 1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "CHoCH Bull", "bull", last_seen)
            elif choch_vals[i] == -1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "CHoCH Bear", "bear", last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 11. Previous candle inside/outside bar ────────────────────────────────

def inside_outside_bar(df: pd.DataFrame) -> list:
    """Inside and outside bar patterns → marker events."""
    try:
        o = df["Open"].values.astype(float)
        h = df["High"].values.astype(float)
        l = df["Low"].values.astype(float)
        c = df["Close"].values.astype(float)
        n = len(df)
        intraday = _is_intraday(df)
        idx = df.index
        events = []
        last_seen = {}
        for i in range(_WARMUP_BARS, n):
            # Inside bar: current high < prev high AND current low > prev low
            if h[i] < h[i-1] and l[i] > l[i-1]:
                _append_event_with_cooldown(events, idx, i, intraday, "Inside Bar", "neutral", last_seen)
            # Outside bar: current high > prev high AND current low < prev low
            elif h[i] > h[i-1] and l[i] < l[i-1]:
                direction = "bull" if c[i] > c[i-1] else "bear"
                _append_event_with_cooldown(events, idx, i, intraday, "Outside Bar", direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 12. SFP (Swing Failure Pattern) ──────────────────────────────────────

def inside_outside_bar(df: pd.DataFrame, highlight_last_n: int | None = None) -> dict:
    """Previous Candle + Inside/Outside [MK] signals and previous H/L/Mid lines."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {"signals": []}
        intraday = _is_intraday(work)
        idx = work.index
        prev_high = work["high"].shift(1)
        prev_low = work["low"].shift(1)
        prev_mid = (prev_high + prev_low) / 2

        bear_outside = (
            (work["high"] > prev_high)
            & (work["close"] < prev_mid)
            & (work["open"] > work["close"])
        ).fillna(False)
        bull_outside = (
            (work["low"] < prev_low)
            & (work["close"] > prev_mid)
            & (work["open"] < work["close"])
        ).fillna(False)
        inside_bar = (
            (work["high"] <= prev_high)
            & (work["low"] >= prev_low)
        ).fillna(False)
        prev_high_break = (work["high"] > prev_high).fillna(False)
        prev_low_break = (work["low"] < prev_low).fillna(False)
        abovemid = (work["close"] > prev_mid).fillna(False)
        belowmid = (work["close"] < prev_mid).fillna(False)

        start = 1 if highlight_last_n is None else max(1, len(work) - max(1, int(highlight_last_n)))
        signals = []
        for i in range(start, len(work)):
            if intraday and _is_session_open_bar(idx, i):
                continue
            if bool(bull_outside.iloc[i]) and not bool(bear_outside.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "MK Out Bull", "direction": "bull", "index": i})
            elif bool(bear_outside.iloc[i]) and not bool(bull_outside.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "MK Out Bear", "direction": "bear", "index": i})
            elif bool(inside_bar.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "MK Inside", "direction": "neutral", "index": i})
            if bool(prev_high_break.iloc[i]):
                direction = "bear" if work["close"].iloc[i] < prev_high.iloc[i] else "neutral"
                signals.append({"time": _time_str(idx, i, intraday), "name": "PH", "direction": direction, "index": i})
            if bool(prev_low_break.iloc[i]):
                direction = "bull" if work["close"].iloc[i] > prev_low.iloc[i] else "neutral"
                signals.append({"time": _time_str(idx, i, intraday), "name": "PL", "direction": direction, "index": i})

        latest_state = "BULL" if bool(abovemid.iloc[-1]) else "BEAR" if bool(belowmid.iloc[-1]) else "MID"
        return {
            "signals": _sanitize_events(signals, drop_conflicts=False),
            "prev_high": [round(float(v), 4) if v == v else None for v in prev_high.tolist()],
            "prev_low": [round(float(v), 4) if v == v else None for v in prev_low.tolist()],
            "prev_mid": [round(float(v), 4) if v == v else None for v in prev_mid.tolist()],
            "state": latest_state,
            "highlight_last_n": int(highlight_last_n) if highlight_last_n is not None else len(work),
        }
    except Exception:
        return {"signals": []}


def sfp_markers(df: pd.DataFrame) -> list:
    """Swing Failure Pattern (SFP) → marker events."""
    try:
        mod = _load_module("sfp_candelacharts")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_sfp", "bearish_sfp", "SFP Bull", "SFP Bear")
    except Exception:
        return []


# ── 13. Candlestick Multi-Bar ─────────────────────────────────────────────

def sfp_markers(df: pd.DataFrame) -> list:
    """ICT sweep-liquidity SFP markers with doji confirmation."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return []
        n = len(work)
        if n < 15:
            return []

        intraday = _is_intraday(work)
        idx = work.index
        h = work["high"].astype(float)
        l = work["low"].astype(float)
        o = work["open"].astype(float)
        c = work["close"].astype(float)
        if isinstance(idx, pd.DatetimeIndex) and n > 1:
            minutes = max(1, round((idx[1] - idx[0]).total_seconds() / 60))
            swing_period = 5 if minutes <= 5 else 8 if minutes <= 30 else 13 if minutes <= 90 else 21
        else:
            swing_period = 21
        max_sweep_age = 50
        max_swing_back = 100
        doji_threshold = 0.4

        tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(55, min_periods=1).mean()

        swing_high = pd.Series(False, index=work.index)
        swing_low = pd.Series(False, index=work.index)
        for i in range(swing_period, n - swing_period):
            high_win = h.iloc[i - swing_period:i + swing_period + 1]
            low_win = l.iloc[i - swing_period:i + swing_period + 1]
            swing_high.iloc[i] = bool(h.iloc[i] == high_win.max() and h.iloc[max(0, i - swing_period)] != h.iloc[i])
            swing_low.iloc[i] = bool(l.iloc[i] == low_win.min() and l.iloc[max(0, i - swing_period)] != l.iloc[i])

        def _is_doji(i: int) -> bool:
            rng = h.iloc[i] - l.iloc[i]
            if rng <= 0:
                return False
            return abs(c.iloc[i] - o.iloc[i]) / rng <= doji_threshold

        swing_highs = []
        swing_lows = []
        events = []
        for i in range(n):
            if bool(swing_high.iloc[i]):
                swing_highs.append({"price": float(h.iloc[i]), "close": float(c.iloc[i]), "open": float(o.iloc[i]), "index": i, "permit": True, "aoi": -1})
            if bool(swing_low.iloc[i]):
                swing_lows.append({"price": float(l.iloc[i]), "close": float(c.iloc[i]), "open": float(o.iloc[i]), "index": i, "permit": True, "aoi": -1})
            if len(swing_highs) > max_swing_back:
                swing_highs.pop(0)
            if len(swing_lows) > max_swing_back:
                swing_lows.pop(0)
            if i < _WARMUP_BARS or (intraday and _is_session_open_bar(idx, i)):
                continue

            for swing in reversed(swing_highs):
                if not swing["permit"] or i - swing["index"] > max_sweep_age:
                    continue
                if swing["price"] < h.iloc[i] and swing["price"] > c.iloc[i] and swing["aoi"] == -1 and _is_doji(i):
                    swing_body_top = max(swing["open"], swing["close"])
                    if c.iloc[i] < swing["price"] and c.iloc[i] > swing_body_top:
                        events.append({
                            "time": _time_str(idx, i, intraday),
                            "name": "SFP Short",
                            "direction": "bear",
                            "index": i,
                            "sweep_level": round(float(swing["price"]), 4),
                            "swing_index": int(swing["index"]),
                            "atr": round(float(atr.iloc[i]), 4) if atr.iloc[i] == atr.iloc[i] else None,
                        })
                        swing["permit"] = False
                        break
                if c.iloc[i] > swing["price"] and swing["aoi"] == -1:
                    swing["aoi"] = i

            for swing in reversed(swing_lows):
                if not swing["permit"] or i - swing["index"] > max_sweep_age:
                    continue
                if swing["price"] > l.iloc[i] and swing["price"] < c.iloc[i] and swing["aoi"] == -1 and _is_doji(i):
                    swing_body_bottom = min(swing["open"], swing["close"])
                    if c.iloc[i] > swing["price"] and c.iloc[i] < swing_body_bottom:
                        events.append({
                            "time": _time_str(idx, i, intraday),
                            "name": "SFP Long",
                            "direction": "bull",
                            "index": i,
                            "sweep_level": round(float(swing["price"]), 4),
                            "swing_index": int(swing["index"]),
                            "atr": round(float(atr.iloc[i]), 4) if atr.iloc[i] == atr.iloc[i] else None,
                        })
                        swing["permit"] = False
                        break
                if c.iloc[i] < swing["price"] and swing["aoi"] == -1:
                    swing["aoi"] = i

        return _sanitize_events(events)
    except Exception:
        return []


def cdl_multibar_markers(df: pd.DataFrame) -> list:
    """Multi-bar candlestick patterns → marker events."""
    try:
        mod = _load_module("candlestick_multibar")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_cdl_multibar", "bearish_cdl_multibar",
                          "MB Bull CDL", "MB Bear CDL")
    except Exception:
        try:
            work = _norm(df)
            o, h, l, c = (work[x].astype(float).to_numpy() for x in ("open", "high", "low", "close"))
            body = np.abs(c - o)
            rng = np.maximum(h - l, 1e-9)
            intraday = _is_intraday(work)
            idx = work.index
            events, last_seen = [], {}
            for i in range(max(_WARMUP_BARS, 2), len(work)):
                bear1 = c[i - 2] < o[i - 2] and body[i - 2] > rng[i - 2] * 0.45
                bull1 = c[i - 2] > o[i - 2] and body[i - 2] > rng[i - 2] * 0.45
                small2 = body[i - 1] < rng[i - 1] * 0.35
                bull3 = c[i] > o[i] and c[i] > (o[i - 2] + c[i - 2]) / 2
                bear3 = c[i] < o[i] and c[i] < (o[i - 2] + c[i - 2]) / 2
                if bear1 and small2 and bull3:
                    _append_event_with_cooldown(events, idx, i, intraday, "Morning Star", "bull", last_seen)
                elif bull1 and small2 and bear3:
                    _append_event_with_cooldown(events, idx, i, intraday, "Evening Star", "bear", last_seen)
            return _sanitize_events(events)
        except Exception:
            return []


# ── 14. SI Fractal ────────────────────────────────────────────────────────

def si_fractal_markers(df: pd.DataFrame) -> list:
    """Fractal high/low signals → marker events."""
    try:
        mod = _load_module("si_fractal")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_si_fractal", "bearish_si_fractal",
                          "Fractal Bull", "Fractal Bear")
    except Exception:
        try:
            work = _norm(df)
            h = work["high"].astype(float).to_numpy()
            l = work["low"].astype(float).to_numpy()
            intraday = _is_intraday(work)
            idx = work.index
            events, last_seen = [], {}
            for pivot in range(max(_WARMUP_BARS, 2), len(work) - 2):
                confirm = pivot + 2
                if h[pivot] == np.max(h[pivot - 2:pivot + 3]):
                    _append_event_with_cooldown(events, idx, confirm, intraday, "Fractal High", "bear", last_seen)
                if l[pivot] == np.min(l[pivot - 2:pivot + 3]):
                    _append_event_with_cooldown(events, idx, confirm, intraday, "Fractal Low", "bull", last_seen)
            return _sanitize_events(events)
        except Exception:
            return []


# ── 15. Bollinger Band Breakout ───────────────────────────────────────────

def bb_breakout(df: pd.DataFrame) -> dict:
    """
    Bollinger Band Breakout → {
        basis/upper/lower: line series data,
        signals: marker events
    }
    """
    try:
        mod = _load_module("bollinger_band_breakout")
        work = _norm(df)
        result = mod.calculate_indicators(work, length=20, mult=2.0)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)

        def _series(col):
            vals = result[col].tolist() if col in result.columns else []
            return [{"time": _time_str(idx, i, intraday), "value": round(float(v), 4)}
                    for i, v in enumerate(vals) if v == v]

        events = []
        for i in range(n):
            if "long_entry_signal" in result.columns and result["long_entry_signal"].iloc[i]:
                events.append({"time": _time_str(idx, i, intraday), "name": "BB Break", "direction": "bull"})
            if "long_exit_signal" in result.columns and result["long_exit_signal"].iloc[i]:
                events.append({"time": _time_str(idx, i, intraday), "name": "BB Exit", "direction": "bear"})

        return {
            "basis":   _series("basis"),
            "upper":   _series("upper"),
            "lower":   _series("lower"),
            "signals": events,
        }
    except Exception:
        return {}


# ── 16. Bahai Reversal Points ─────────────────────────────────────────────

def bahai_reversal_markers(df: pd.DataFrame) -> list:
    """Bahai reversal buy/sell signals → marker events."""
    try:
        mod = _load_module("bahai_reversal_points")
        work = _norm(df)
        result = mod.calculate_indicators(work, length=10, lookback_length=5, threshold_level=0.5)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        for col, label, direction in [
            ("Buy", "Bahai Buy", "bull"),
            ("Strong_Buy_Signal", "Bahai Str Buy", "bull"),
            ("Sell", "Bahai Sell", "bear"),
            ("Strong_Sell_Signal", "Bahai Str Sell", "bear"),
        ]:
            if col not in result.columns:
                continue
            last_seen = {}
            for i in range(n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        events = _sanitize_events(events)
        if events:
            return events
        raise RuntimeError("reversal radar external module produced no mapped events")
    except Exception:
        return []


# ── 17. Chart Pattern Head & Shoulders ───────────────────────────────────

def chart_hs_markers(df: pd.DataFrame) -> list:
    """H&S / Inverse H&S chart pattern → marker events."""
    try:
        mod = _load_module("chart_pattern_hs")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_chart_hs", "bearish_chart_hs",
                          "Inv H&S", "H&S")
    except Exception:
        try:
            work = _norm(df)
            h = work["high"].astype(float).to_numpy()
            l = work["low"].astype(float).to_numpy()
            intraday = _is_intraday(work)
            idx = work.index
            pivots = []
            for i in range(max(_WARMUP_BARS, 3), len(work) - 3):
                if h[i] == np.max(h[i - 3:i + 4]):
                    pivots.append(("H", i, h[i]))
                if l[i] == np.min(l[i - 3:i + 4]):
                    pivots.append(("L", i, l[i]))
            pivots.sort(key=lambda x: x[1])
            events, last_seen = [], {}
            for a, b, c_, d, e in zip(pivots, pivots[1:], pivots[2:], pivots[3:], pivots[4:]):
                seq = "".join(x[0] for x in (a, b, c_, d, e))
                if seq == "HLHLH":
                    shoulder_ok = abs(a[2] - e[2]) / max(c_[2], 1e-9) < 0.04
                    head_ok = c_[2] > a[2] and c_[2] > e[2]
                    if shoulder_ok and head_ok:
                        _append_event_with_cooldown(events, idx, e[1], intraday, "H&S", "bear", last_seen)
                elif seq == "LHLHL":
                    shoulder_ok = abs(a[2] - e[2]) / max(abs(c_[2]), 1e-9) < 0.04
                    head_ok = c_[2] < a[2] and c_[2] < e[2]
                    if shoulder_ok and head_ok:
                        _append_event_with_cooldown(events, idx, e[1], intraday, "Inv H&S", "bull", last_seen)
            return _sanitize_events(events)
        except Exception:
            return []


# ── 18. Double Top / Bottom ───────────────────────────────────────────────

def double_top_bottom_markers(df: pd.DataFrame) -> list:
    """Double top/bottom patterns → marker events."""
    try:
        mod = _load_module("double_top_bottom_ultimate")
        work = _norm(df)
        result = mod.calculate_indicators(work, length=10)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        mapping = [
            ("double_bottom",               "Dbl Bot",      "bull"),
            ("double_bottom_confirmation",  "Dbl Bot Conf", "bull"),
            ("double_top",                  "Dbl Top",      "bear"),
            ("double_top_confirmation",     "Dbl Top Conf", "bear"),
            ("double_bottom_invalidation",  "Dbl Bot Inv",  "neutral"),
            ("double_top_invalidation",     "Dbl Top Inv",  "neutral"),
        ]
        last_seen = {}
        for col, label, direction in mapping:
            if col not in result.columns:
                continue
            for i in range(_WARMUP_BARS, n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 19. Reversal Radar v2 ─────────────────────────────────────────────────

def reversal_radar_markers(df: pd.DataFrame) -> list:
    """Reversal Radar multi-confluence signals → marker events."""
    try:
        mod = _load_module("reversal_radar_v2")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        mapping = [
            ("strong_long_entry",  "Str Rev Long",  "bull"),
            ("long_entry",         "Rev Long",       "bull"),
            ("strong_short_entry", "Str Rev Short", "bear"),
            ("short_entry",        "Rev Short",      "bear"),
        ]
        last_seen = {}
        for col, label, direction in mapping:
            if col not in result.columns:
                continue
            for i in range(_WARMUP_BARS, n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        events = _sanitize_events(events)
        if events:
            return events
        raise RuntimeError("reversal radar external module produced no mapped events")
    except Exception:
        try:
            work = _norm(df)
            o, h, l, c, v = (work[x].astype(float) for x in ("open", "high", "low", "close", "volume"))
            delta = c.diff()
            gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
            vol_spike = v > v.rolling(20, min_periods=20).mean() * 1.15
            rng = (h - l).replace(0, np.nan)
            lower_wick = (pd.concat([o, c], axis=1).min(axis=1) - l) / rng
            upper_wick = (h - pd.concat([o, c], axis=1).max(axis=1)) / rng
            bull = (rsi < 42) & (lower_wick > 0.30) & vol_spike & (c >= o)
            bear = (rsi > 58) & (upper_wick > 0.30) & vol_spike & (c <= o)
            intraday = _is_intraday(work)
            idx = work.index
            events, last_seen = [], {}
            for i in range(_WARMUP_BARS, len(work)):
                if bool(bull.iloc[i]):
                    _append_event_with_cooldown(events, idx, i, intraday, "Rev Radar Long", "bull", last_seen)
                elif bool(bear.iloc[i]):
                    _append_event_with_cooldown(events, idx, i, intraday, "Rev Radar Short", "bear", last_seen)
            return _sanitize_events(events)
        except Exception:
            return []


# ── 20. N-Bar Reversal (LuxAlgo) ─────────────────────────────────────────

def _nbar_supertrend(work: pd.DataFrame, atr_period: int = 10, factor: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """Supertrend direction used by LuxAlgo N-Bar Reversal."""
    high, low, close = work["high"], work["low"], work["close"]
    hl2 = (high + low) / 2.0
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period, min_periods=atr_period).mean()
    upper_band = hl2 + factor * atr
    lower_band = hl2 - factor * atr

    st = pd.Series(np.nan, index=work.index, dtype=float)
    direction = pd.Series(1, index=work.index, dtype=int)

    for i in range(len(work)):
        if i == 0 or pd.isna(atr.iloc[i]):
            st.iloc[i] = upper_band.iloc[i] if not pd.isna(upper_band.iloc[i]) else hl2.iloc[i]
            direction.iloc[i] = 1
            continue

        prev_st = st.iloc[i - 1]
        if pd.isna(prev_st):
            prev_st = upper_band.iloc[i]

        if close.iloc[i - 1] > prev_st:
            st.iloc[i] = max(lower_band.iloc[i], prev_st)
            direction.iloc[i] = -1
        else:
            st.iloc[i] = min(upper_band.iloc[i], prev_st)
            direction.iloc[i] = 1

        if close.iloc[i] > st.iloc[i]:
            direction.iloc[i] = -1
        elif close.iloc[i] < st.iloc[i]:
            direction.iloc[i] = 1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    return st, direction


def n_bar_reversal_markers(
    df: pd.DataFrame,
    num_bars: int = 7,
    min_bars_pct: float = 0.5,
    brp_type: str = "All",
    trend_type: str = "Supertrend",
    trend_filt: str = "Aligned",
    atr_period: int = 10,
    factor: float = 3.0,
) -> list:
    """LuxAlgo-style N-Bar reversal pattern markers."""
    try:
        work = _norm(df).copy()
        required = {"open", "high", "low", "close"}
        if len(work) < max(num_bars + 1, atr_period + 1) or not required.issubset(work.columns):
            return []

        n = max(2, int(num_bars))
        min_bars = float(min_bars_pct)
        brp = str(brp_type or "All")
        trend = str(trend_type or "Supertrend")
        filt = str(trend_filt or "Aligned")

        supertrend_val, direction = _nbar_supertrend(work, int(atr_period), float(factor))
        if trend == "Supertrend" and filt == "Aligned":
            c_downtrend = direction > 0
            c_uptrend = direction < 0
        elif trend == "Supertrend" and filt == "Opposite":
            c_downtrend = direction < 0
            c_uptrend = direction > 0
        else:
            c_downtrend = pd.Series(True, index=work.index)
            c_uptrend = pd.Series(True, index=work.index)

        intraday = _is_intraday(work)
        idx = work.index
        events = []

        for i in range(n, len(work)):
            first = i - n

            bull_low_val = float(work["low"].iloc[first])
            bear_count = 0
            bull_reversal = True
            for j in range(1, n):
                k = first + j
                if work["high"].iloc[k] > work["high"].iloc[first]:
                    bull_reversal = False
                    break
                bull_low_val = min(bull_low_val, float(work["low"].iloc[k]))
                if work["open"].iloc[k] > work["close"].iloc[k]:
                    bear_count += 1
            bull_reversal = bull_reversal and (bear_count / (n - 1) >= min_bars)
            bull_confirmed = bull_reversal and work["high"].iloc[i] > work["high"].iloc[first]
            if brp == "Enhanced":
                bull_confirmed = bull_confirmed and work["close"].iloc[i] > work["high"].iloc[first]
            elif brp == "Normal":
                bull_confirmed = bull_confirmed and work["close"].iloc[i] <= work["high"].iloc[first]

            if bull_confirmed and bool(c_uptrend.iloc[i]):
                events.append({
                    "index": i,
                    "time": _time_str(idx, i, intraday),
                    "name": "N-Bar Bull",
                    "direction": "bull",
                    "support": round(float(min(bull_low_val, work["low"].iloc[i])), 4),
                    "supertrend": round(float(supertrend_val.iloc[i]), 4) if supertrend_val.iloc[i] == supertrend_val.iloc[i] else None,
                })

            bear_high_val = float(work["high"].iloc[first])
            bull_count = 0
            bear_reversal = True
            for j in range(1, n):
                k = first + j
                if work["low"].iloc[k] < work["low"].iloc[first]:
                    bear_reversal = False
                    break
                bear_high_val = max(bear_high_val, float(work["high"].iloc[k]))
                if work["open"].iloc[k] < work["close"].iloc[k]:
                    bull_count += 1
            bear_reversal = bear_reversal and (bull_count / (n - 1) >= min_bars)
            bear_confirmed = bear_reversal and work["low"].iloc[i] < work["low"].iloc[first]
            if brp == "Enhanced":
                bear_confirmed = bear_confirmed and work["close"].iloc[i] < work["low"].iloc[first]
            elif brp == "Normal":
                bear_confirmed = bear_confirmed and work["close"].iloc[i] >= work["low"].iloc[first]

            if bear_confirmed and bool(c_downtrend.iloc[i]):
                events.append({
                    "index": i,
                    "time": _time_str(idx, i, intraday),
                    "name": "N-Bar Bear",
                    "direction": "bear",
                    "resistance": round(float(max(bear_high_val, work["high"].iloc[i])), 4),
                    "supertrend": round(float(supertrend_val.iloc[i]), 4) if supertrend_val.iloc[i] == supertrend_val.iloc[i] else None,
                })

        return _sanitize_events(events)
    except Exception:
        return []


# ── 21. Impulse Trend / BOS Waves ────────────────────────────────────────

def impulse_trend_markers(df: pd.DataFrame) -> list:
    """Impulse trend long/short + retest markers."""
    try:
        mod = _load_module("impulse_trend_boswaves")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        mapping = [
            ("Impulse_Long",  "Impulse Long",  "bull"),
            ("Bull_Retest",   "Bull Retest",   "bull"),
            ("Impulse_Short", "Impulse Short", "bear"),
            ("Bear_Retest",   "Bear Retest",   "bear"),
        ]
        last_seen = {}
        for col, label, direction in mapping:
            if col not in result.columns:
                continue
            for i in range(_WARMUP_BARS, n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 22. CM Hourly Pivots (price lines) ───────────────────────────────────

def cm_hourly_pivots(df: pd.DataFrame, show_pivot: bool = True, show_r3_s3: bool = False) -> dict:
    """CM Hourly Pivots: previous hour classic pivots projected onto each bar."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {}
        if not {"open", "high", "low", "close"}.issubset(work.columns) or len(work) < 2:
            return {}

        hourly = work.resample("1h").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }).dropna()
        if hourly.empty:
            return {}

        hourly["pivot"] = (hourly["high"] + hourly["low"] + hourly["close"]) / 3.0
        hourly["r1"] = hourly["pivot"] + (hourly["pivot"] - hourly["low"])
        hourly["s1"] = hourly["pivot"] - (hourly["high"] - hourly["pivot"])
        hourly["r2"] = hourly["pivot"] + (hourly["high"] - hourly["low"])
        hourly["s2"] = hourly["pivot"] - (hourly["high"] - hourly["low"])
        hourly["r3"] = np.nan
        hourly["s3"] = np.nan
        if show_r3_s3:
            hourly["r3"] = hourly["r1"] + (hourly["high"] - hourly["low"])
            hourly["s3"] = hourly["s1"] - (hourly["high"] - hourly["low"])

        pivots = hourly[["pivot", "r1", "s1", "r2", "s2", "r3", "s3"]].shift(1)
        pivots = pivots.reindex(work.index, method="ffill")
        if not show_pivot:
            pivots.loc[:, :] = np.nan

        key_map = {
            "pivot": "hourly_pivot",
            "r1": "hourly_r1",
            "s1": "hourly_s1",
            "r2": "hourly_r2",
            "s2": "hourly_s2",
            "r3": "hourly_r3",
            "s3": "hourly_s3",
        }
        out = {}
        for src, key in key_map.items():
            vals = [round(float(v), 4) if v == v else None for v in pivots[src].tolist()]
            out[key] = vals
            out[f"{key}_last"] = next((v for v in reversed(vals) if v is not None), None)
        return out
    except Exception:
        return {}


def _classic_pivots(ohlc: pd.DataFrame, show_r3_s3: bool) -> pd.DataFrame:
    """Classic pivot calculations for weekly/daily/hourly pivot systems."""
    piv = pd.DataFrame(index=ohlc.index)
    piv["pivot"] = (ohlc["high"] + ohlc["low"] + ohlc["close"]) / 3.0
    piv["r1"] = 2 * piv["pivot"] - ohlc["low"]
    piv["s1"] = 2 * piv["pivot"] - ohlc["high"]
    piv["r2"] = piv["pivot"] + (ohlc["high"] - ohlc["low"])
    piv["s2"] = piv["pivot"] - (ohlc["high"] - ohlc["low"])
    piv["r3"] = np.nan
    piv["s3"] = np.nan
    if show_r3_s3:
        piv["r3"] = piv["r2"] + (ohlc["high"] - ohlc["low"])
        piv["s3"] = piv["s2"] - (ohlc["high"] - ohlc["low"])
    return piv


def _chrismoody_pivots(
    ohlc: pd.DataFrame,
    show_r3_s3: bool = True,
    show_filtered_pivots: bool = False,
) -> pd.DataFrame:
    """ChrisMoody filtered pivot calculations on a resampled OHLC frame."""
    piv = pd.DataFrame(index=ohlc.index)
    pivot = (ohlc["high"] + ohlc["low"] + ohlc["close"]) / 3.0
    price_range = ohlc["high"] - ohlc["low"]
    prev_pivot = pivot.shift(1)
    bull = pivot > ((pivot + prev_pivot) / 2.0 + 0.0025)
    bear = pivot < ((pivot + prev_pivot) / 2.0 - 0.0025)

    piv["pivot"] = pivot
    if show_filtered_pivots:
        piv["r1"] = np.where(bear, pivot + (pivot - ohlc["low"]), np.where(bull, pivot + price_range, pivot + (pivot - ohlc["low"])))
        piv["s1"] = np.where(bull, pivot - (ohlc["high"] - pivot), np.where(bear, pivot - price_range, pivot - (ohlc["high"] - pivot)))
    else:
        piv["r1"] = pivot + (pivot - ohlc["low"])
        piv["s1"] = pivot - (ohlc["high"] - pivot)
    piv["r2"] = pivot + price_range
    piv["s2"] = pivot - price_range
    piv["r3"] = np.nan
    piv["s3"] = np.nan
    if show_r3_s3:
        piv["r3"] = piv["r1"] + price_range
        piv["s3"] = piv["s1"] - price_range
    piv["pivot_avg"] = pivot.rolling(3).mean()
    return piv


def wekly_pivot(
    df: pd.DataFrame,
    show_weekly: bool = False,
    show_daily: bool = True,
    show_hourly_confluence: bool = True,
    show_r3_s3: bool = False,
    tolerance_pct: float = 0.15,
) -> dict:
    """Weekly + daily pivots with hourly confluence levels."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {}
        if not {"open", "high", "low", "close"}.issubset(work.columns) or len(work) < 2:
            return {}

        def _resample(rule: str) -> pd.DataFrame:
            return work.resample(rule).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
            }).dropna()

        weekly = _classic_pivots(_resample("1W"), show_r3_s3).shift(1).reindex(work.index, method="ffill")
        daily = _classic_pivots(_resample("1D"), show_r3_s3).shift(1).reindex(work.index, method="ffill")
        hourly = _classic_pivots(_resample("1h"), show_r3_s3).shift(1).reindex(work.index, method="ffill")

        if not show_weekly:
            weekly.loc[:, :] = np.nan
        if not show_daily:
            daily.loc[:, :] = np.nan

        hourly_conf = hourly.copy()
        hourly_conf.loc[:, :] = np.nan
        if show_hourly_confluence:
            base_cols = ["pivot", "r1", "s1", "r2", "s2"] + (["r3", "s3"] if show_r3_s3 else [])
            refs = daily[base_cols]
            for col in base_cols:
                h_vals = hourly[col]
                tol = h_vals.abs() * float(tolerance_pct) / 100.0
                near = pd.Series(False, index=work.index)
                for ref_col in refs.columns:
                    near = near | ((refs[ref_col] - h_vals).abs() <= tol)
                hourly_conf[col] = h_vals.where(near)

        out = {"tolerance_pct": float(tolerance_pct)}
        groups = [
            ("weekly", weekly),
            ("daily", daily),
            ("hourly_conf", hourly_conf),
        ]
        for prefix, frame in groups:
            for col in ["pivot", "r1", "s1", "r2", "s2", "r3", "s3"]:
                key = f"{prefix}_{col}"
                vals = [round(float(v), 4) if v == v else None for v in frame[col].tolist()]
                out[key] = vals
                out[f"{key}_last"] = next((v for v in reversed(vals) if v is not None), None)
        return out
    except Exception:
        return {}


def _vwap_bands(work: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Session VWAP with volume-weighted running standard deviation bands."""
    volume = work["volume"].astype(float) if "volume" in work.columns else pd.Series(1.0, index=work.index)
    volume = volume.replace(0, np.nan).ffill().fillna(1.0)
    typical = (work["high"] + work["low"] + work["close"]) / 3.0
    grouper = work.index.date if freq == "D" else work.index.to_period("W")
    tpv = typical * volume
    cum_tpv = tpv.groupby(grouper).cumsum()
    cum_vol = volume.groupby(grouper).cumsum()
    vwap = cum_tpv / cum_vol
    dev_sq_vol = ((typical - vwap) ** 2) * volume
    std = np.sqrt(dev_sq_vol.groupby(grouper).cumsum() / cum_vol)
    out = pd.DataFrame(index=work.index)
    out["vwap"] = vwap
    for i, mult in enumerate([0.5, 1.0, 1.5], 1):
        out[f"upper_{i}"] = vwap + mult * std
        out[f"lower_{i}"] = vwap - mult * std
    return out


@dataclass
class LiquidityEntrySettings:
    local_ema_length: int = 50
    use_local_ema_filter: bool = True
    pip_preset: str = "Auto Detect"
    pivot_length: int = 5
    stored_levels: int = 20
    min_sweep_distance_pips: int = 15
    reclaim_rule: str = "Close Back Inside"
    min_wick_percent: float = 0.30
    max_body_percent: float = 0.70
    min_candle_range_pips: int = 10
    require_bullish_body: bool = True
    require_bearish_body: bool = True
    confirmation_window: int = 2
    require_midline_break: bool = True
    signal_cooldown_bars: int = 5
    enable_simulation: bool = True
    take_profit_pips: int = 100
    stop_loss_pips: int = 30
    block_signals_in_trade: bool = True
    use_risk_reward: bool = True
    risk_reward_ratio: float = 2.0


def _liquidity_pip_size(preset: str, ticker: str, asset_type: str, min_tick: float) -> float:
    ticker_upper = str(ticker or "").upper()
    if preset == "FX 5-Digit":
        return 0.000001
    if preset == "FX JPY":
        return 0.0001
    if preset == "XAUUSD / Gold":
        return 0.01
    if preset == "Indices / CFD":
        return float(min_tick)
    if "XAU" in ticker_upper:
        return 0.01
    if asset_type == "forex":
        return 0.01 if "JPY" in ticker_upper else 0.0001
    return float(min_tick)


def _liq_clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


def _liquidity_quality_score(
    wick_pct: float,
    body_pct: float,
    range_pips: float,
    min_wick: float,
    max_body: float,
    min_range: float,
    ema_ok: bool,
    reclaim_ok: bool,
    mid_break_ok: bool,
) -> float:
    wick_score = _liq_clamp((wick_pct / min_wick) * 32.0, 0.0, 32.0) if min_wick > 0 else 32.0
    body_score = _liq_clamp(((max_body - body_pct) / max_body) * 24.0, 0.0, 24.0) if max_body > 0 else 24.0
    range_score = _liq_clamp((range_pips / min_range) * 18.0, 0.0, 18.0) if min_range > 0 else 18.0
    return _liq_clamp(wick_score + body_score + range_score + (10.0 if ema_ok else 0.0) + (10.0 if reclaim_ok else 0.0) + (6.0 if mid_break_ok else 0.0), 0.0, 100.0)


class LiquidityEntryZones:
    def __init__(self, settings: LiquidityEntrySettings, ticker: str = "STOCK", asset_type: str = "stock", min_tick: float = 0.01):
        self.s = settings
        self.pip_size = _liquidity_pip_size(self.s.pip_preset, ticker, asset_type, min_tick)
        self.tp_distance = self.s.take_profit_pips * self.pip_size
        self.sl_distance = self.s.stop_loss_pips * self.pip_size
        self.min_sweep_dist_px = self.s.min_sweep_distance_pips * self.pip_size
        self.min_range_dist_px = self.s.min_candle_range_pips * self.pip_size

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema"] = df["close"].ewm(span=self.s.local_ema_length, adjust=False).mean()
        tr1 = df["high"] - df["low"]
        tr2 = (df["high"] - df["close"].shift(1)).abs()
        tr3 = (df["low"] - df["close"].shift(1)).abs()
        df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr"] = df["tr"].rolling(window=14).mean()
        df["range"] = df["high"] - df["low"]
        df["body"] = (df["close"] - df["open"]).abs()
        df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
        df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
        df["body_pct"] = np.where(df["range"] > 0, df["body"] / df["range"], 0.0)
        df["upper_wick_pct"] = np.where(df["range"] > 0, df["upper_wick"] / df["range"], 0.0)
        df["lower_wick_pct"] = np.where(df["range"] > 0, df["lower_wick"] / df["range"], 0.0)
        df["range_pips"] = np.where(self.pip_size > 0, df["range"] / self.pip_size, 0.0)
        roll_window = 2 * self.s.pivot_length + 1
        df["rolling_max"] = df["high"].rolling(window=roll_window, center=True).max()
        df["rolling_min"] = df["low"].rolling(window=roll_window, center=True).min()
        df["pivot_high_val"] = np.where(df["high"] == df["rolling_max"], df["high"], np.nan)
        df["pivot_low_val"] = np.where(df["low"] == df["rolling_min"], df["low"], np.nan)
        df["pivot_high"] = df["pivot_high_val"].shift(self.s.pivot_length)
        df["pivot_low"] = df["pivot_low_val"].shift(self.s.pivot_length)
        return df

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.calculate_indicators(df)
        for col, default in [
            ("buy_signal", False), ("sell_signal", False), ("sweep_detected", False),
            ("sweep_type", ""), ("trade_result", ""),
        ]:
            df[col] = default
        for col in ["sweep_level", "sweep_high", "sweep_low", "trade_entry", "trade_sl", "trade_tp", "trade_exit", "quality_score"]:
            df[col] = np.nan

        stored_high_levels = deque(maxlen=self.s.stored_levels)
        stored_high_bars = deque(maxlen=self.s.stored_levels)
        stored_low_levels = deque(maxlen=self.s.stored_levels)
        stored_low_bars = deque(maxlen=self.s.stored_levels)
        empty_pending = {"bar": None, "high": None, "low": None, "mid": None, "level": None, "score": None}
        pending_bull = empty_pending.copy()
        pending_bear = empty_pending.copy()
        last_signal_bar = None
        active_trade = {"dir": 0, "entry": np.nan, "tp": np.nan, "sl": np.nan, "entry_bar": None}

        highs, lows, opens, closes = df["high"].values, df["low"].values, df["open"].values, df["close"].values
        emas, pivot_highs, pivot_lows = df["ema"].values, df["pivot_high"].values, df["pivot_low"].values
        body_pcts, upper_wick_pcts, lower_wick_pcts = df["body_pct"].values, df["upper_wick_pct"].values, df["lower_wick_pct"].values
        ranges, range_pips = df["range"].values, df["range_pips"].values

        for i in range(len(df)):
            if np.isnan(emas[i]):
                continue
            bar_index = i
            high, low, open_, close = highs[i], lows[i], opens[i], closes[i]
            ema = emas[i]

            if not np.isnan(pivot_highs[i]):
                stored_high_levels.append(pivot_highs[i])
                stored_high_bars.append(bar_index - self.s.pivot_length)
            if not np.isnan(pivot_lows[i]):
                stored_low_levels.append(pivot_lows[i])
                stored_low_bars.append(bar_index - self.s.pivot_length)

            swept_high_level = np.nan
            for lvl, bar in zip(reversed(stored_high_levels), reversed(stored_high_bars)):
                if bar < bar_index and high > lvl and (high - lvl) >= self.min_sweep_dist_px:
                    swept_high_level = lvl
                    break

            swept_low_level = np.nan
            for lvl, bar in zip(reversed(stored_low_levels), reversed(stored_low_bars)):
                if bar < bar_index and low < lvl and (lvl - low) >= self.min_sweep_dist_px:
                    swept_low_level = lvl
                    break

            mid_price = (high + low) / 2.0
            bearish_reclaim = not np.isnan(swept_high_level) and ((close < swept_high_level) if self.s.reclaim_rule == "Close Back Inside" else (close < swept_high_level and close < mid_price))
            bullish_reclaim = not np.isnan(swept_low_level) and ((close > swept_low_level) if self.s.reclaim_rule == "Close Back Inside" else (close > swept_low_level and close > mid_price))
            valid_sell_sweep = (not np.isnan(swept_high_level) and bearish_reclaim and upper_wick_pcts[i] >= self.s.min_wick_percent and body_pcts[i] <= self.s.max_body_percent and ranges[i] >= self.min_range_dist_px)
            valid_buy_sweep = (not np.isnan(swept_low_level) and bullish_reclaim and lower_wick_pcts[i] >= self.s.min_wick_percent and body_pcts[i] <= self.s.max_body_percent and ranges[i] >= self.min_range_dist_px)

            bull_ema_ok = (not self.s.use_local_ema_filter) or (close > ema)
            bear_ema_ok = (not self.s.use_local_ema_filter) or (close < ema)
            bull_mid_ok = (not self.s.require_midline_break) or (close > mid_price)
            bear_mid_ok = (not self.s.require_midline_break) or (close < mid_price)

            if valid_buy_sweep:
                score = _liquidity_quality_score(lower_wick_pcts[i], body_pcts[i], range_pips[i], self.s.min_wick_percent, self.s.max_body_percent, self.s.min_candle_range_pips, bull_ema_ok, bullish_reclaim, bull_mid_ok)
                df.at[df.index[i], "sweep_detected"] = True
                df.at[df.index[i], "sweep_type"] = "bull"
                df.at[df.index[i], "sweep_level"] = swept_low_level
                df.at[df.index[i], "sweep_high"] = high
                df.at[df.index[i], "sweep_low"] = low
                df.at[df.index[i], "quality_score"] = score
                pending_bull = {"bar": bar_index, "high": high, "low": low, "mid": mid_price, "level": swept_low_level, "score": score}

            if valid_sell_sweep:
                score = _liquidity_quality_score(upper_wick_pcts[i], body_pcts[i], range_pips[i], self.s.min_wick_percent, self.s.max_body_percent, self.s.min_candle_range_pips, bear_ema_ok, bearish_reclaim, bear_mid_ok)
                df.at[df.index[i], "sweep_detected"] = True
                df.at[df.index[i], "sweep_type"] = "bear"
                df.at[df.index[i], "sweep_level"] = swept_high_level
                df.at[df.index[i], "sweep_high"] = high
                df.at[df.index[i], "sweep_low"] = low
                df.at[df.index[i], "quality_score"] = score
                pending_bear = {"bar": bar_index, "high": high, "low": low, "mid": mid_price, "level": swept_high_level, "score": score}

            bull_window_open = pending_bull["bar"] is not None and (bar_index - pending_bull["bar"] <= self.s.confirmation_window)
            bear_window_open = pending_bear["bar"] is not None and (bar_index - pending_bear["bar"] <= self.s.confirmation_window)
            bull_body_ok = (not self.s.require_bullish_body) or (close > open_)
            bear_body_ok = (not self.s.require_bearish_body) or (close < open_)
            buy_confirmed = bull_window_open and bull_body_ok and bull_ema_ok and ((not self.s.require_midline_break) or close > pending_bull["mid"])
            sell_confirmed = bear_window_open and bear_body_ok and bear_ema_ok and ((not self.s.require_midline_break) or close < pending_bear["mid"])
            cooldown_passed = last_signal_bar is None or (bar_index - last_signal_bar > self.s.signal_cooldown_bars)
            allow_new_signals = not (self.s.block_signals_in_trade and active_trade["dir"] != 0)
            buy_signal = buy_confirmed and cooldown_passed and allow_new_signals
            sell_signal = sell_confirmed and cooldown_passed and (not buy_signal) and allow_new_signals

            if buy_signal or sell_signal:
                last_signal_bar = bar_index
                df.at[df.index[i], "buy_signal"] = buy_signal
                df.at[df.index[i], "sell_signal"] = sell_signal
                if self.s.enable_simulation:
                    entry_price = close
                    if buy_signal:
                        sl = pending_bull["low"] if self.s.use_risk_reward else entry_price - self.sl_distance
                        tp = entry_price + ((entry_price - sl) * self.s.risk_reward_ratio) if self.s.use_risk_reward else entry_price + self.tp_distance
                        active_trade = {"dir": 1, "entry": entry_price, "tp": tp, "sl": sl, "entry_bar": bar_index}
                    else:
                        sl = pending_bear["high"] if self.s.use_risk_reward else entry_price + self.sl_distance
                        tp = entry_price - ((sl - entry_price) * self.s.risk_reward_ratio) if self.s.use_risk_reward else entry_price - self.tp_distance
                        active_trade = {"dir": -1, "entry": entry_price, "tp": tp, "sl": sl, "entry_bar": bar_index}
                    df.at[df.index[i], "trade_entry"] = entry_price
                    df.at[df.index[i], "trade_sl"] = sl
                    df.at[df.index[i], "trade_tp"] = tp

            if active_trade["dir"] != 0:
                df.at[df.index[i], "trade_entry"] = active_trade["entry"]
                df.at[df.index[i], "trade_sl"] = active_trade["sl"]
                df.at[df.index[i], "trade_tp"] = active_trade["tp"]
                hit_tp = high >= active_trade["tp"] if active_trade["dir"] == 1 else low <= active_trade["tp"]
                hit_sl = low <= active_trade["sl"] if active_trade["dir"] == 1 else high >= active_trade["sl"]
                if hit_sl or hit_tp:
                    exit_price = active_trade["sl"] if hit_sl else active_trade["tp"]
                    df.at[df.index[i], "trade_exit"] = exit_price
                    df.at[df.index[i], "trade_result"] = "SL" if hit_sl else "TP"
                    active_trade = {"dir": 0, "entry": np.nan, "tp": np.nan, "sl": np.nan, "entry_bar": None}

            if pending_bull["bar"] is not None and (bar_index - pending_bull["bar"] > self.s.confirmation_window):
                pending_bull = empty_pending.copy()
            if pending_bear["bar"] is not None and (bar_index - pending_bear["bar"] > self.s.confirmation_window):
                pending_bear = empty_pending.copy()

        return df


def liquidity_entry(df: pd.DataFrame, ticker: str = "STOCK", asset_type: str = "stock", min_tick: float = 0.01) -> dict:
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex) or not {"open", "high", "low", "close"}.issubset(work.columns):
            return {"signals": [], "sweeps": [], "levels": [], "trade_lines": {"entry": [], "sl": [], "tp": []}, "quality": []}
        if "volume" not in work.columns:
            work["volume"] = 0
        result = LiquidityEntryZones(LiquidityEntrySettings(), ticker=ticker, asset_type=asset_type, min_tick=min_tick).run(work)
        idx = result.index
        intraday = _is_intraday(result)
        signals, sweeps, levels = [], [], []
        for i, row in enumerate(result.itertuples()):
            if bool(getattr(row, "sweep_detected")):
                direction = "bull" if getattr(row, "sweep_type") == "bull" else "bear"
                sweeps.append({
                    "time": _time_str(idx, i, intraday),
                    "name": "Bull Sweep" if direction == "bull" else "Bear Sweep",
                    "direction": direction,
                    "index": i,
                    "price": round(float(getattr(row, "sweep_level")), 4),
                    "quality": None if pd.isna(getattr(row, "quality_score")) else round(float(getattr(row, "quality_score")), 1),
                })
                levels.append({
                    "time": _time_str(idx, i, intraday),
                    "name": "Sweep Level",
                    "direction": "neutral",
                    "index": i,
                    "price": round(float(getattr(row, "sweep_level")), 4),
                })
            if bool(getattr(row, "buy_signal")) or bool(getattr(row, "sell_signal")):
                is_buy = bool(getattr(row, "buy_signal"))
                signals.append({
                    "time": _time_str(idx, i, intraday),
                    "name": "LIQ Buy" if is_buy else "LIQ Sell",
                    "direction": "bull" if is_buy else "bear",
                    "index": i,
                    "entry": round(float(getattr(row, "trade_entry")), 4),
                    "sl": round(float(getattr(row, "trade_sl")), 4),
                    "tp": round(float(getattr(row, "trade_tp")), 4),
                    "quality": None if pd.isna(getattr(row, "quality_score")) else round(float(getattr(row, "quality_score")), 1),
                    "sweep_level": None if pd.isna(getattr(row, "sweep_level")) else round(float(getattr(row, "sweep_level")), 4),
                })
            if getattr(row, "trade_result"):
                signals.append({
                    "time": _time_str(idx, i, intraday),
                    "name": f"LIQ Exit {getattr(row, 'trade_result')}",
                    "direction": "neutral",
                    "index": i,
                    "price": round(float(getattr(row, "trade_exit")), 4),
                    "result": getattr(row, "trade_result"),
                })

        def _arr(col: str) -> list:
            return [round(float(v), 4) if v == v else None for v in result[col].tolist()]

        return {
            "signals": _sanitize_events(signals, drop_conflicts=False),
            "sweeps": _sanitize_events(sweeps, drop_conflicts=False),
            "levels": _sanitize_events(levels, drop_conflicts=False),
            "trade_lines": {"entry": _arr("trade_entry"), "sl": _arr("trade_sl"), "tp": _arr("trade_tp")},
            "quality": _arr("quality_score"),
        }
    except Exception:
        return {"signals": [], "sweeps": [], "levels": [], "trade_lines": {"entry": [], "sl": [], "tp": []}, "quality": []}


@dataclass(frozen=True)
class DeltaVpParams:
    lookback: int = 3
    breakout_buffer: float = 0.0005
    buy_close_pos_min: float = 0.65
    sell_close_pos_max: float = 0.35
    rsi_dir_min: float = 65.0
    sl_atr: float = 2.0
    rr: float = 3.0
    risk_atr_min: float = 0.15
    risk_atr_max: float = 2.5
    hold_bars: int = 24
    retest_zone_atr: float = 0.5
    retest_lookahead: int = 12
    profile_lookback: int = 96
    profile_bins: int = 36
    value_area_pct: float = 0.70


def _delta_vp_ltf(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    tr = pd.concat([
        d["high"] - d["low"],
        (d["high"] - d["close"].shift()).abs(),
        (d["low"] - d["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    d["atr14"] = tr.rolling(14, min_periods=1).mean()
    d["ema9"] = d["close"].ewm(span=9, adjust=False).mean()
    d["ema20"] = d["close"].ewm(span=20, adjust=False).mean()
    d["ema50"] = d["close"].ewm(span=50, adjust=False).mean()
    session = pd.Series(d.index.date, index=d.index)
    pv = d["close"] * d["volume"]
    d["vwap"] = pv.groupby(session).cumsum() / d["volume"].replace(0, np.nan).groupby(session).cumsum()
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    close_pos = ((d["close"] - d["low"]) / rng).clip(0, 1).fillna(0.5)
    d["proxy_delta_ratio"] = 2 * close_pos - 1
    d["green_sell_delta_warning"] = (d["close"] > d["open"]) & (d["proxy_delta_ratio"] < -0.10)
    d["red_buy_delta_warning"] = (d["close"] < d["open"]) & (d["proxy_delta_ratio"] > 0.10)
    return d


def _delta_vp_supertrend_dir(df: pd.DataFrame, period: int = 5, mult: float = 2.0) -> pd.Series:
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    prev_c = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - prev_c), np.abs(l - prev_c)]), axis=0)
    atr = pd.Series(tr, index=df.index).ewm(alpha=1 / period, adjust=False, min_periods=period).mean().to_numpy(float)
    hl2 = (h + l) / 2.0
    bu = hl2 + mult * atr
    bl = hl2 - mult * atr
    fu = bu.copy()
    fl = bl.copy()
    st = np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for i in range(1, len(df)):
        if not np.isfinite(atr[i]):
            continue
        fu[i] = bu[i] if (not np.isfinite(fu[i - 1]) or bu[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = bl[i] if (not np.isfinite(fl[i - 1]) or bl[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if not np.isfinite(st[i - 1]):
            direction[i] = 1 if c[i] > fu[i] else -1
            st[i] = fl[i] if direction[i] == 1 else fu[i]
        elif st[i - 1] == fu[i - 1]:
            direction[i] = -1 if c[i] <= fu[i] else 1
            st[i] = fu[i] if direction[i] == -1 else fl[i]
        else:
            direction[i] = 1 if c[i] >= fl[i] else -1
            st[i] = fl[i] if direction[i] == 1 else fu[i]
    return pd.Series(direction, index=df.index)


def _delta_vp_htf(df: pd.DataFrame, period: str = "1h") -> pd.DataFrame:
    h = df.resample(period).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        atr14=("atr14", "last"),
        ema20=("ema20", "last"),
        ema50=("ema50", "last"),
    ).dropna()
    h["close_pos"] = np.where(h["high"] > h["low"], (h["close"] - h["low"]) / (h["high"] - h["low"]), 0.5)
    delta = h["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    h["rsi14"] = 100 - (100 / (1 + rs))
    mean = h["volume"].rolling(20, min_periods=10).mean()
    std = h["volume"].rolling(20, min_periods=10).std(ddof=0)
    h["vol_z20"] = (h["volume"] - mean) / std.replace(0, np.nan)
    return h


def _delta_vp_profile(df: pd.DataFrame, p: DeltaVpParams) -> pd.DataFrame:
    n = len(df)
    poc = np.full(n, np.nan)
    vah = np.full(n, np.nan)
    val = np.full(n, np.nan)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    for i in range(n):
        start = max(0, i - p.profile_lookback + 1)
        prices = c[start:i + 1]
        vols = v[start:i + 1]
        ok = np.isfinite(prices) & np.isfinite(vols) & (vols > 0)
        if ok.sum() < 5:
            continue
        prices = prices[ok]
        vols = vols[ok]
        lo, hi = float(np.min(prices)), float(np.max(prices))
        if hi <= lo:
            poc[i] = vah[i] = val[i] = hi
            continue
        bins = np.linspace(lo, hi, p.profile_bins + 1)
        hist, edges = np.histogram(prices, bins=bins, weights=vols)
        if hist.sum() <= 0:
            continue
        mids = (edges[:-1] + edges[1:]) / 2
        poc_idx = int(np.argmax(hist))
        poc[i] = float(mids[poc_idx])
        order = np.argsort(hist)[::-1]
        keep = []
        total = 0.0
        target = float(hist.sum()) * p.value_area_pct
        for bi in order:
            keep.append(int(bi))
            total += float(hist[bi])
            if total >= target:
                break
        val[i] = float(mids[min(keep)])
        vah[i] = float(mids[max(keep)])
    return pd.DataFrame({"poc": poc, "vah": vah, "pal": val, "val": val}, index=df.index)


def delta_vp(df: pd.DataFrame) -> dict:
    """Delta-volume-profile adaptive breakout indicator for chart answers and trade levels."""
    empty = {
        "signals": [],
        "levels": [],
        "trade_lines": {"entry": [], "sl": [], "target": [], "level": []},
        "poc": [],
        "vah": [],
        "pal": [],
        "answers": {},
        "latest": {},
    }
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex) or not {"open", "high", "low", "close"}.issubset(work.columns):
            return empty
        if "volume" not in work.columns:
            work["volume"] = 0.0
        work = work[["open", "high", "low", "close", "volume"]].astype(float).dropna()
        if len(work) < 80:
            return {**empty, "poc": [None] * len(work), "vah": [None] * len(work), "pal": [None] * len(work)}
        p = DeltaVpParams()
        intraday = _is_intraday(work)
        idx = work.index
        ltf = _delta_vp_ltf(work)
        ltf["st25_dir"] = _delta_vp_supertrend_dir(ltf)
        profile = _delta_vp_profile(ltf, p)
        htf = _delta_vp_htf(ltf)
        ltf_idx_np = ltf.index.values
        entry_line = np.full(len(ltf), np.nan)
        sl_line = np.full(len(ltf), np.nan)
        target_line = np.full(len(ltf), np.nan)
        level_line = np.full(len(ltf), np.nan)
        events = []
        levels = []
        trades = []

        for hi in range(p.lookback, len(htf)):
            t = htf.index[hi]
            cur = htf.iloc[hi]
            prev = htf.iloc[hi - p.lookback:hi]
            res = float(prev["high"].max())
            sup = float(prev["low"].min())
            ep = int(np.searchsorted(ltf_idx_np, np.datetime64(t), side="right"))
            if ep >= len(ltf):
                continue
            entry_time = idx[ep]
            side = None
            level = np.nan
            if (
                cur["high"] > res * (1 + p.breakout_buffer)
                and cur["close"] > res
                and cur["close_pos"] >= p.buy_close_pos_min
                and cur["ema20"] > cur["ema50"]
            ):
                rsi_dir = float(cur["rsi14"]) if pd.notna(cur["rsi14"]) else np.nan
                if pd.notna(rsi_dir) and rsi_dir >= p.rsi_dir_min:
                    side, level = "long", res
            rsi_short = 100 - float(cur["rsi14"]) if pd.notna(cur["rsi14"]) else np.nan
            if side is None and (
                cur["low"] < sup * (1 - p.breakout_buffer)
                and cur["close"] < sup
                and cur["close_pos"] <= p.sell_close_pos_max
                and cur["ema20"] < cur["ema50"]
                and pd.notna(rsi_short)
                and rsi_short >= p.rsi_dir_min
            ):
                side, level = "short", sup
            if side is None:
                continue

            atr = float(ltf["atr14"].iloc[ep])
            entry = float(ltf["open"].iloc[ep])
            if not np.isfinite(atr) or atr <= 0:
                continue
            if side == "long":
                stop = level - p.sl_atr * atr
                risk = entry - stop
                target = entry + p.rr * risk
            else:
                stop = level + p.sl_atr * atr
                risk = stop - entry
                target = entry - p.rr * risk
            risk_atr = risk / atr if atr else np.nan
            if not np.isfinite(risk_atr) or risk <= 0 or risk_atr < p.risk_atr_min or risk_atr > p.risk_atr_max:
                continue

            end = min(len(ltf) - 1, ep + p.hold_bars)
            outcome = "timeout"
            exit_i = end
            fake_or_weak = False
            weak_reasons = []
            if side == "long":
                if bool(ltf["red_buy_delta_warning"].iloc[ep]):
                    weak_reasons.append("red-buy delta warning")
                if pd.notna(cur.get("vol_z20", np.nan)) and float(cur["vol_z20"]) < 0:
                    weak_reasons.append("low 1H volume z-score")
                for j in range(ep + 1, end + 1):
                    if float(ltf["low"].iloc[j]) <= stop:
                        outcome, exit_i = "loss", j
                        break
                    if float(ltf["high"].iloc[j]) >= target:
                        outcome, exit_i = "win", j
                        break
                fake_or_weak = outcome == "loss" or any(float(x) < level for x in ltf["close"].iloc[ep + 1:min(end + 1, ep + 7)])
            else:
                if bool(ltf["green_sell_delta_warning"].iloc[ep]):
                    weak_reasons.append("green-sell delta warning")
                if pd.notna(cur.get("vol_z20", np.nan)) and float(cur["vol_z20"]) < 0:
                    weak_reasons.append("low 1H volume z-score")
                for j in range(ep + 1, end + 1):
                    if float(ltf["high"].iloc[j]) >= stop:
                        outcome, exit_i = "loss", j
                        break
                    if float(ltf["low"].iloc[j]) <= target:
                        outcome, exit_i = "win", j
                        break
                fake_or_weak = outcome == "loss" or any(float(x) > level for x in ltf["close"].iloc[ep + 1:min(end + 1, ep + 7)])
            if weak_reasons:
                fake_or_weak = True

            retest_i = None
            retest_entry = np.nan
            for j in range(ep + 1, min(len(ltf), ep + p.retest_lookahead + 1)):
                atr_j = float(ltf["atr14"].iloc[j])
                if not np.isfinite(atr_j) or atr_j <= 0:
                    continue
                if side == "long" and float(ltf["low"].iloc[j]) <= level + p.retest_zone_atr * atr_j and float(ltf["close"].iloc[j]) >= level and float(ltf["close"].iloc[j]) >= float(ltf["ema9"].iloc[j]) and int(ltf["st25_dir"].iloc[j]) == 1:
                    retest_i, retest_entry = j, level
                    break
                if side == "short" and float(ltf["high"].iloc[j]) >= level - p.retest_zone_atr * atr_j and float(ltf["close"].iloc[j]) <= level and float(ltf["close"].iloc[j]) <= float(ltf["ema9"].iloc[j]) and int(ltf["st25_dir"].iloc[j]) == -1:
                    retest_i, retest_entry = j, level
                    break

            entry_line[ep:exit_i + 1] = entry
            sl_line[ep:exit_i + 1] = stop
            target_line[ep:exit_i + 1] = target
            level_line[ep:exit_i + 1] = level
            name = "DeltaVP Buy" if side == "long" else "DeltaVP Sell"
            direction = "bull" if side == "long" else "bear"
            events.append({
                "time": _time_str(idx, ep, intraday),
                "name": name,
                "direction": direction,
                "index": ep,
                "entry": round(entry, 4),
                "sl": round(stop, 4),
                "target": round(target, 4),
                "level": round(level, 4),
                "poc": None if pd.isna(profile["poc"].iloc[ep]) else round(float(profile["poc"].iloc[ep]), 4),
                "pal": None if pd.isna(profile["pal"].iloc[ep]) else round(float(profile["pal"].iloc[ep]), 4),
                "breakout_confirmed": True,
                "should_enter": not fake_or_weak,
                "fake_or_weak": fake_or_weak,
                "retest_available": retest_i is not None,
                "reason": "weak/fake: " + ", ".join(weak_reasons) if weak_reasons else "confirmed breakout continuation",
            })
            levels.append({"time": _time_str(idx, ep, intraday), "name": "DeltaVP POC", "direction": "neutral", "index": ep, "price": events[-1]["poc"]})
            levels.append({"time": _time_str(idx, ep, intraday), "name": "DeltaVP PAL", "direction": "neutral", "index": ep, "price": events[-1]["pal"]})
            if retest_i is not None:
                events.append({
                    "time": _time_str(idx, retest_i, intraday),
                    "name": "DeltaVP Add-on",
                    "direction": direction,
                    "index": retest_i,
                    "entry": round(float(retest_entry), 4),
                    "level": round(level, 4),
                })
            if fake_or_weak:
                events.append({
                    "time": _time_str(idx, min(exit_i, len(idx) - 1), intraday),
                    "name": "DeltaVP Weak/Fake",
                    "direction": "neutral",
                    "index": int(min(exit_i, len(idx) - 1)),
                    "price": round(float(ltf["close"].iloc[min(exit_i, len(idx) - 1)]), 4),
                    "outcome": outcome,
                })
            trades.append({
                "signal_time": str(t),
                "entry_time": _time_str(idx, ep, intraday),
                "side": side,
                "entry": round(entry, 4),
                "sl": round(stop, 4),
                "target": round(target, 4),
                "level": round(level, 4),
                "outcome": outcome,
                "fake_or_weak": fake_or_weak,
                "retest_available": retest_i is not None,
                "retest_time": _time_str(idx, retest_i, intraday) if retest_i is not None else None,
            })

        def _arr(series) -> list:
            return [round(float(v), 4) if v == v else None for v in series]

        latest_trade = trades[-1] if trades else {}
        answers = {
            "breakout_confirmed": bool(latest_trade),
            "should_i_enter": bool(latest_trade) and not latest_trade.get("fake_or_weak", True),
            "entry": latest_trade.get("entry"),
            "sl": latest_trade.get("sl"),
            "target": latest_trade.get("target"),
            "retest_addon_available": latest_trade.get("retest_available", False),
            "fake_or_weak": latest_trade.get("fake_or_weak", False) if latest_trade else None,
            "side": latest_trade.get("side"),
            "poc": None if profile["poc"].dropna().empty else round(float(profile["poc"].dropna().iloc[-1]), 4),
            "pal": None if profile["pal"].dropna().empty else round(float(profile["pal"].dropna().iloc[-1]), 4),
            "vah": None if profile["vah"].dropna().empty else round(float(profile["vah"].dropna().iloc[-1]), 4),
        }
        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "levels": _sanitize_events([x for x in levels if x.get("price") is not None], drop_conflicts=False),
            "trade_lines": {"entry": _arr(entry_line), "sl": _arr(sl_line), "target": _arr(target_line), "level": _arr(level_line)},
            "poc": _arr(profile["poc"].tolist()),
            "vah": _arr(profile["vah"].tolist()),
            "pal": _arr(profile["pal"].tolist()),
            "answers": answers,
            "latest": answers,
            "trades": trades[-100:],
        }
    except Exception:
        return empty


@dataclass
class ProbabilityGridConfig:
    active_session: str = "0930-1600"
    opening_bars: int = 6
    max_history: int = 250
    atr_period: int = 14
    step_one: float = 0.25
    step_two: float = 0.50
    step_three: float = 0.75
    step_four: float = 1.00
    step_five: float = 1.25
    step_six: float = 1.50
    projection_bars: int = 24
    probability_gate: float = 0.48
    mintick: float = 0.01
    use_atr_for_daily: bool = True


class SessionProbabilityGrid:
    def __init__(self, config: ProbabilityGridConfig | None = None):
        self.config = config or ProbabilityGridConfig()
        self.session_start_time = None
        self.session_end_time = None
        if self.config.active_session and self.config.active_session != "0000-2359":
            parts = self.config.active_session.split("-")
            if len(parts) == 2:
                from datetime import time
                self.session_start_time = time(int(parts[0][:2]), int(parts[0][2:]))
                self.session_end_time = time(int(parts[1][:2]), int(parts[1][2:]))
        self.up_hits = np.zeros(6, dtype=np.int32)
        self.up_samples = np.zeros(6, dtype=np.int32)
        self.up_move_sum = np.zeros(6, dtype=np.float64)
        self.up_touched = np.zeros(6, dtype=np.bool_)
        self.up_levels_saved = np.full(6, np.nan)
        self.dn_hits = np.zeros(6, dtype=np.int32)
        self.dn_samples = np.zeros(6, dtype=np.int32)
        self.dn_move_sum = np.zeros(6, dtype=np.float64)
        self.dn_touched = np.zeros(6, dtype=np.bool_)
        self.dn_levels_saved = np.full(6, np.nan)
        self.session_bars = 0
        self.session_open = np.nan
        self.session_high = np.nan
        self.session_low = np.nan
        self.opening_high = np.nan
        self.opening_low = np.nan
        self.session_cum_pv = 0.0
        self.session_cum_vol = 0.0
        self.prev_in_session = False
        self.steps = np.array([
            self.config.step_one, self.config.step_two, self.config.step_three,
            self.config.step_four, self.config.step_five, self.config.step_six,
        ])

    def _in_session(self, timestamp: pd.Timestamp) -> bool:
        if self.session_start_time is None:
            return True
        t = timestamp.time()
        if self.session_start_time <= self.session_end_time:
            return self.session_start_time <= t < self.session_end_time
        return t >= self.session_start_time or t < self.session_end_time

    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / self.config.atr_period, min_periods=self.config.atr_period, adjust=False).mean()

    @staticmethod
    def _prob(hits: int, samples: int) -> float:
        return (hits + 1.0) / (samples + 2.0) if samples > 0 else 0.5

    @staticmethod
    def _expected(move_sum: float, hits: int) -> float:
        return move_sum / hits if hits > 0 else np.nan

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(x, hi))

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        n = len(df)
        atr_series = self._calculate_atr(df)
        in_session = np.zeros(n, dtype=np.bool_)
        new_session = np.zeros(n, dtype=np.bool_)
        ended_session = np.zeros(n, dtype=np.bool_)
        session_open_arr = np.full(n, np.nan)
        session_high_arr = np.full(n, np.nan)
        session_low_arr = np.full(n, np.nan)
        session_vwap_arr = np.full(n, np.nan)
        opening_high_arr = np.full(n, np.nan)
        opening_low_arr = np.full(n, np.nan)
        up_levels = np.full((n, 6), np.nan)
        dn_levels = np.full((n, 6), np.nan)
        up_chances = np.full((n, 6), 0.5)
        dn_chances = np.full((n, 6), 0.5)
        up_exp4 = np.full(n, np.nan)
        dn_exp4 = np.full(n, np.nan)
        anomaly_score = np.full(n, np.nan)
        above_open = np.zeros(n, dtype=np.bool_)
        below_open = np.zeros(n, dtype=np.bool_)
        upside_expansion = np.zeros(n, dtype=np.bool_)
        downside_expansion = np.zeros(n, dtype=np.bool_)
        upside_exhaustion = np.zeros(n, dtype=np.bool_)
        downside_exhaustion = np.zeros(n, dtype=np.bool_)
        signal = np.full(n, 0, dtype=np.int8)
        signal_strength = np.full(n, np.nan)
        opens = df["open"].to_numpy(float)
        highs = df["high"].to_numpy(float)
        lows = df["low"].to_numpy(float)
        closes = df["close"].to_numpy(float)
        volumes = df["volume"].to_numpy(float) if "volume" in df.columns else np.ones(n)
        hlc3 = (highs + lows + closes) / 3.0
        atr_arr = atr_series.to_numpy(float)
        daily_like = isinstance(df.index, pd.DatetimeIndex) and (len(df) < 2 or (df.index[1] - df.index[0]).total_seconds() >= 86400)

        prev_session_date = None
        for i, ts in enumerate(df.index):
            curr_in_session = self._in_session(ts)
            session_date = ts.date() if hasattr(ts, "date") else None
            date_changed = curr_in_session and self.prev_in_session and prev_session_date is not None and session_date != prev_session_date
            in_session[i] = curr_in_session
            new_session[i] = curr_in_session and (not self.prev_in_session or date_changed)
            ended_session[i] = ((not curr_in_session) and self.prev_in_session) or date_changed
            self.prev_in_session = curr_in_session

            if ended_session[i] and not np.isnan(self.session_high) and not np.isnan(self.session_low):
                for j in range(6):
                    accept_up = self.up_samples[j] < self.config.max_history
                    accept_dn = self.dn_samples[j] < self.config.max_history
                    if accept_up:
                        self.up_samples[j] += 1
                    if accept_dn:
                        self.dn_samples[j] += 1
                    if accept_up and self.up_touched[j] and not np.isnan(self.up_levels_saved[j]):
                        self.up_hits[j] += 1
                        self.up_move_sum[j] += max(self.session_high - self.up_levels_saved[j], 0.0)
                    if accept_dn and self.dn_touched[j] and not np.isnan(self.dn_levels_saved[j]):
                        self.dn_hits[j] += 1
                        self.dn_move_sum[j] += max(self.dn_levels_saved[j] - self.session_low, 0.0)
                    self.up_touched[j] = False
                    self.dn_touched[j] = False

            if new_session[i]:
                self.session_bars = 0
                self.session_open = opens[i]
                self.session_high = highs[i]
                self.session_low = lows[i]
                self.opening_high = highs[i]
                self.opening_low = lows[i]
                self.session_cum_pv = 0.0
                self.session_cum_vol = 0.0
            if curr_in_session:
                prev_session_date = session_date

            if curr_in_session:
                self.session_bars += 1
                self.session_high = max(self.session_high, highs[i]) if not np.isnan(self.session_high) else highs[i]
                self.session_low = min(self.session_low, lows[i]) if not np.isnan(self.session_low) else lows[i]
                self.session_cum_pv += hlc3[i] * volumes[i]
                self.session_cum_vol += volumes[i]
                if self.session_bars <= self.config.opening_bars:
                    self.opening_high = max(self.opening_high, highs[i]) if not np.isnan(self.opening_high) else highs[i]
                    self.opening_low = min(self.opening_low, lows[i]) if not np.isnan(self.opening_low) else lows[i]

            session_open_arr[i] = self.session_open
            session_high_arr[i] = self.session_high
            session_low_arr[i] = self.session_low
            opening_high_arr[i] = self.opening_high
            opening_low_arr[i] = self.opening_low
            session_vwap_arr[i] = self.session_cum_pv / self.session_cum_vol if self.session_cum_vol > 0 else np.nan

            opening_range = max(self.opening_high - self.opening_low, self.config.mintick) if not np.isnan(self.opening_high) and not np.isnan(self.opening_low) else self.config.mintick
            session_range = max(self.session_high - self.session_low, self.config.mintick) if not np.isnan(self.session_high) and not np.isnan(self.session_low) else self.config.mintick
            if self.config.use_atr_for_daily and daily_like:
                ladder_base = atr_arr[i] if not np.isnan(atr_arr[i]) and atr_arr[i] > 0 else opening_range
            else:
                ladder_base = opening_range if self.session_bars >= self.config.opening_bars else max(session_range, self.config.mintick)

            if not np.isnan(self.session_open):
                for j, step in enumerate(self.steps):
                    up_levels[i, j] = self.session_open + ladder_base * step
                    dn_levels[i, j] = self.session_open - ladder_base * step
                self.up_levels_saved = up_levels[i].copy()
                self.dn_levels_saved = dn_levels[i].copy()
                if curr_in_session:
                    for j in range(6):
                        if highs[i] >= up_levels[i, j]:
                            self.up_touched[j] = True
                        if lows[i] <= dn_levels[i, j]:
                            self.dn_touched[j] = True

            for j in range(6):
                up_chances[i, j] = self._prob(self.up_hits[j], self.up_samples[j])
                dn_chances[i, j] = self._prob(self.dn_hits[j], self.dn_samples[j])
            up_exp4[i] = self._expected(self.up_move_sum[3], self.up_hits[3])
            dn_exp4[i] = self._expected(self.dn_move_sum[3], self.dn_hits[3])
            atr_val = atr_arr[i] if not np.isnan(atr_arr[i]) else 0.0
            anomaly_score[i] = self._clamp((session_range / atr_val if atr_val > 0 else 0.0) / 1.75, 0.0, 2.0)
            above_open[i] = closes[i] > self.session_open if not np.isnan(self.session_open) else False
            below_open[i] = closes[i] < self.session_open if not np.isnan(self.session_open) else False
            if i > 0 and curr_in_session:
                prev_close = closes[i - 1]
                if closes[i] > up_levels[i, 3] and prev_close <= up_levels[i - 1, 3] and up_chances[i, 3] >= self.config.probability_gate:
                    upside_expansion[i] = True
                    signal[i] = 1
                    signal_strength[i] = up_chances[i, 3]
                if closes[i] < dn_levels[i, 3] and prev_close >= dn_levels[i - 1, 3] and dn_chances[i, 3] >= self.config.probability_gate:
                    downside_expansion[i] = True
                    signal[i] = -1
                    signal_strength[i] = dn_chances[i, 3]
                if highs[i] >= up_levels[i, 5] and closes[i] < up_levels[i, 4] and anomaly_score[i] > 1.0:
                    upside_exhaustion[i] = True
                    signal[i] = -1
                    signal_strength[i] = anomaly_score[i]
                if lows[i] <= dn_levels[i, 5] and closes[i] > dn_levels[i, 4] and anomaly_score[i] > 1.0:
                    downside_exhaustion[i] = True
                    signal[i] = 1
                    signal_strength[i] = anomaly_score[i]

        result = pd.DataFrame({
            "in_session": in_session, "new_session": new_session, "ended_session": ended_session,
            "session_open": session_open_arr, "session_high": session_high_arr, "session_low": session_low_arr,
            "session_vwap": session_vwap_arr, "opening_high": opening_high_arr, "opening_low": opening_low_arr,
            "atr": atr_arr, "anomaly_score": anomaly_score, "above_open": above_open, "below_open": below_open,
            "upside_expansion": upside_expansion, "downside_expansion": downside_expansion,
            "upside_exhaustion": upside_exhaustion, "downside_exhaustion": downside_exhaustion,
            "signal": signal, "signal_strength": signal_strength,
            "up_exp_4": up_exp4, "dn_exp_4": dn_exp4,
        }, index=df.index)
        for j in range(6):
            result[f"up_prob_{j + 1}"] = up_chances[:, j]
            result[f"dn_prob_{j + 1}"] = dn_chances[:, j]
            result[f"up_{j + 1}"] = up_levels[:, j]
            result[f"dn_{j + 1}"] = dn_levels[:, j]
        return result


def problty_grid(df: pd.DataFrame) -> dict:
    empty = {"signals": [], "levels": {}, "events": [], "dashboard": {}, "projection_boxes": []}
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex) or not {"open", "high", "low", "close"}.issubset(work.columns):
            return empty
        if "volume" not in work.columns:
            work["volume"] = 1.0
        work = work[["open", "high", "low", "close", "volume"]].astype(float).dropna()
        if len(work) < 20:
            return empty
        intraday = _is_intraday(work)
        cfg = ProbabilityGridConfig(
            active_session="0930-1600" if intraday else "0000-2359",
            opening_bars=6 if intraday else 1,
            probability_gate=0.48 if intraday else 0.30,
            use_atr_for_daily=not intraday,
        )
        engine = SessionProbabilityGrid(cfg)
        result = engine.run(work)
        idx = work.index
        signals = []
        events = []
        boxes = []
        for i, row in enumerate(result.itertuples()):
            if bool(getattr(row, "upside_expansion")):
                signals.append({"time": _time_str(idx, i, intraday), "name": "SPG Upside", "direction": "bull", "index": i, "probability": round(float(getattr(row, "up_prob_4")) * 100, 1), "price": round(float(work["close"].iloc[i]), 4)})
                boxes.append({"start": i, "end": min(i + cfg.projection_bars, len(work) - 1), "top": round(float(getattr(row, "up_5")), 4), "bottom": round(float(getattr(row, "up_4")), 4), "direction": "bull"})
            if bool(getattr(row, "downside_expansion")):
                signals.append({"time": _time_str(idx, i, intraday), "name": "SPG Downside", "direction": "bear", "index": i, "probability": round(float(getattr(row, "dn_prob_4")) * 100, 1), "price": round(float(work["close"].iloc[i]), 4)})
                boxes.append({"start": i, "end": min(i + cfg.projection_bars, len(work) - 1), "top": round(float(getattr(row, "dn_4")), 4), "bottom": round(float(getattr(row, "dn_5")), 4), "direction": "bear"})
            if bool(getattr(row, "upside_exhaustion")):
                signals.append({"time": _time_str(idx, i, intraday), "name": "SPG Fade Upper", "direction": "bear", "index": i, "probability": round(float(getattr(row, "anomaly_score")), 2), "price": round(float(work["high"].iloc[i]), 4)})
                boxes.append({"start": i, "end": min(i + cfg.projection_bars, len(work) - 1), "top": round(float(work["high"].iloc[i]), 4), "bottom": round(float(getattr(row, "up_5")), 4), "direction": "bear"})
            if bool(getattr(row, "downside_exhaustion")):
                signals.append({"time": _time_str(idx, i, intraday), "name": "SPG Fade Lower", "direction": "bull", "index": i, "probability": round(float(getattr(row, "anomaly_score")), 2), "price": round(float(work["low"].iloc[i]), 4)})
                boxes.append({"start": i, "end": min(i + cfg.projection_bars, len(work) - 1), "top": round(float(getattr(row, "dn_5")), 4), "bottom": round(float(work["low"].iloc[i]), 4), "direction": "bull"})
            if bool(getattr(row, "new_session")):
                events.append({"time": _time_str(idx, i, intraday), "name": "SPG Session", "direction": "neutral", "index": i, "price": round(float(getattr(row, "session_open")), 4)})

        def _arr(col: str) -> list:
            return [round(float(v), 4) if v == v else None for v in result[col].tolist()]

        levels = {
            "session_open": _arr("session_open"),
            "session_high": _arr("session_high"),
            "session_low": _arr("session_low"),
            "session_vwap": _arr("session_vwap"),
            "opening_high": _arr("opening_high"),
            "opening_low": _arr("opening_low"),
            "anomaly_score": _arr("anomaly_score"),
        }
        vwap_distance = []
        for close_v, vwap_v, atr_v in zip(work["close"].tolist(), result["session_vwap"].tolist(), result["atr"].tolist()):
            if vwap_v == vwap_v and atr_v == atr_v and atr_v > 0:
                vwap_distance.append(round(float(max(-2.0, min(2.0, (close_v - vwap_v) / atr_v))), 4))
            else:
                vwap_distance.append(0.0)
        probabilities = {}
        for j in range(1, 7):
            levels[f"up_{j}"] = _arr(f"up_{j}")
            levels[f"dn_{j}"] = _arr(f"dn_{j}")
            probabilities[f"up_{j}"] = [round(float(v), 4) if v == v else None for v in result[f"up_prob_{j}"].tolist()]
            probabilities[f"dn_{j}"] = [round(float(v), 4) if v == v else None for v in result[f"dn_prob_{j}"].tolist()]
        last = result.iloc[-1]
        dashboard = {
            "state": "Above Open" if bool(last["above_open"]) else ("Below Open" if bool(last["below_open"]) else "At Open"),
            "session_open": round(float(last["session_open"]), 4) if pd.notna(last["session_open"]) else None,
            "or_range": round(float(last["opening_high"] - last["opening_low"]), 4) if pd.notna(last["opening_high"]) and pd.notna(last["opening_low"]) else None,
            "session_range": round(float(last["session_high"] - last["session_low"]), 4) if pd.notna(last["session_high"]) and pd.notna(last["session_low"]) else None,
            "anomaly": round(float(last["anomaly_score"]), 3) if pd.notna(last["anomaly_score"]) else None,
            "u100_probability": round(float(last["up_prob_4"]) * 100, 2),
            "d100_probability": round(float(last["dn_prob_4"]) * 100, 2),
            "up_expected_move": round(float(last["up_exp_4"]), 4) if pd.notna(last["up_exp_4"]) else None,
            "dn_expected_move": round(float(last["dn_exp_4"]), 4) if pd.notna(last["dn_exp_4"]) else None,
            "session_vwap": round(float(last["session_vwap"]), 4) if pd.notna(last["session_vwap"]) else None,
            "samples": int(engine.up_samples[3]),
            "max_history": cfg.max_history,
        }
        return {
            "signals": _sanitize_events(signals, drop_conflicts=False),
            "events": _sanitize_events(events, drop_conflicts=False),
            "levels": levels,
            "probabilities": probabilities,
            "vwap_distance": vwap_distance,
            "projection_boxes": boxes[-100:],
            "dashboard": dashboard,
            "config": cfg.__dict__,
        }
    except Exception:
        return empty


def strg_pivt(
    df: pd.DataFrame,
    show_daily_pivot: bool = True,
    show_hourly_confluence: bool = True,
    show_daily_vwap: bool = True,
    show_weekly_vwap: bool = True,
    show_weekly_pivot: bool = True,
    show_r3_s3: bool = True,
    tolerance_pct: float = 0.15,
) -> dict:
    """Daily/weekly pivots + hourly confluence + daily/weekly VWAP bands."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {}
        if not {"open", "high", "low", "close"}.issubset(work.columns) or len(work) < 2:
            return {}
        if "volume" not in work.columns:
            work["volume"] = 1.0

        daily_ohlc = work.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        weekly_ohlc = work.resample("1W").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        hourly_ohlc = work.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        daily = _classic_pivots(daily_ohlc, show_r3_s3).shift(1).reindex(work.index, method="ffill")
        weekly = _classic_pivots(weekly_ohlc, show_r3_s3).shift(1).reindex(work.index, method="ffill")
        hourly = _classic_pivots(hourly_ohlc, show_r3_s3).shift(1).reindex(work.index, method="ffill")
        if not show_daily_pivot:
            daily.loc[:, :] = np.nan
        if not show_weekly_pivot:
            weekly.loc[:, :] = np.nan

        hourly_conf = hourly.copy()
        hourly_conf.loc[:, :] = np.nan
        if show_hourly_confluence:
            cols = ["pivot", "r1", "s1", "r2", "s2"] + (["r3", "s3"] if show_r3_s3 else [])
            refs = pd.concat([daily[cols].add_prefix("daily_"), weekly[cols].add_prefix("weekly_")], axis=1)
            for col in cols:
                h_vals = hourly[col]
                tol = h_vals.abs() * float(tolerance_pct) / 100.0
                near = pd.Series(False, index=work.index)
                for ref_col in refs.columns:
                    near = near | ((refs[ref_col] - h_vals).abs() <= tol)
                hourly_conf[col] = h_vals.where(near)

        if show_daily_vwap:
            daily_vwap = _vwap_bands(work, "D")
        else:
            daily_vwap = pd.DataFrame(index=work.index)
        if show_weekly_vwap:
            weekly_vwap = _vwap_bands(work, "W")
        else:
            weekly_vwap = pd.DataFrame(index=work.index)

        hourly_vwap_conf = hourly.copy()
        hourly_vwap_conf.loc[:, :] = np.nan
        if show_hourly_confluence:
            cols = ["pivot", "r1", "s1", "r2", "s2"] + (["r3", "s3"] if show_r3_s3 else [])
            vwap_refs = []
            for ref_prefix, frame in [("daily", daily_vwap), ("weekly", weekly_vwap)]:
                keep = [c for c in ["vwap", "upper_1", "upper_2", "upper_3", "lower_1", "lower_2", "lower_3"] if c in frame.columns]
                if keep:
                    vwap_refs.append(frame[keep].add_prefix(f"{ref_prefix}_"))
            refs = pd.concat(vwap_refs, axis=1) if vwap_refs else pd.DataFrame(index=work.index)
            for col in cols:
                h_vals = hourly[col]
                tol = h_vals.abs() * float(tolerance_pct) / 100.0
                near = pd.Series(False, index=work.index)
                for ref_col in refs.columns:
                    near = near | ((refs[ref_col] - h_vals).abs() <= tol)
                hourly_vwap_conf[col] = h_vals.where(near)

        out = {"tolerance_pct": float(tolerance_pct)}
        groups = [("daily", daily), ("weekly", weekly), ("hourly_conf", hourly_conf), ("hourly_vwap_conf", hourly_vwap_conf)]
        for prefix, frame in groups:
            for col in ["pivot", "r1", "s1", "r2", "s2", "r3", "s3"]:
                key = f"{prefix}_{col}"
                vals = [round(float(v), 4) if v == v else None for v in frame[col].tolist()]
                out[key] = vals
                out[f"{key}_last"] = next((v for v in reversed(vals) if v is not None), None)

        for prefix, frame in [("daily_vwap", daily_vwap), ("weekly_vwap", weekly_vwap)]:
            for col in ["vwap", "upper_1", "upper_2", "upper_3", "lower_1", "lower_2", "lower_3"]:
                key = f"{prefix}_{col}"
                if col not in frame.columns:
                    vals = [None] * len(work)
                else:
                    vals = [round(float(v), 4) if v == v else None for v in frame[col].tolist()]
                out[key] = vals
                out[f"{key}_last"] = next((v for v in reversed(vals) if v is not None), None)
        return out
    except Exception:
        return {}


# ── 23. Fibonacci Levels ──────────────────────────────────────────────────

def cm_strg_pivt(
    df: pd.DataFrame,
    show_daily_pivot: bool = True,
    show_hourly_confluence: bool = True,
    show_daily_vwap: bool = True,
    show_weekly_vwap: bool = True,
    show_weekly_pivot: bool = True,
    show_r3_s3: bool = True,
    show_filtered_pivots: bool = False,
    show_pivot_average: bool = True,
    tolerance_pct: float = 0.15,
) -> dict:
    """ChrisMoody filtered daily/weekly pivots with hourly pivot and VWAP confluence."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {}
        if not {"open", "high", "low", "close"}.issubset(work.columns) or len(work) < 2:
            return {}
        if "volume" not in work.columns:
            work["volume"] = 1.0

        daily_ohlc = work.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        weekly_ohlc = work.resample("1W").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        hourly_ohlc = work.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        daily = _chrismoody_pivots(daily_ohlc, show_r3_s3, show_filtered_pivots).shift(1).reindex(work.index, method="ffill")
        weekly = _chrismoody_pivots(weekly_ohlc, show_r3_s3, show_filtered_pivots).shift(1).reindex(work.index, method="ffill")
        hourly = _chrismoody_pivots(hourly_ohlc, show_r3_s3, show_filtered_pivots).shift(1).reindex(work.index, method="ffill")
        if not show_daily_pivot:
            daily.loc[:, :] = np.nan
        if not show_weekly_pivot:
            weekly.loc[:, :] = np.nan
        if not show_pivot_average:
            for frame in [daily, weekly, hourly]:
                frame["pivot_avg"] = np.nan

        cols = ["pivot", "pivot_avg", "r1", "s1", "r2", "s2"] + (["r3", "s3"] if show_r3_s3 else [])
        hourly_conf = hourly.copy()
        hourly_conf.loc[:, :] = np.nan
        if show_hourly_confluence:
            refs = pd.concat([daily[cols].add_prefix("daily_"), weekly[cols].add_prefix("weekly_")], axis=1)
            for col in cols:
                h_vals = hourly[col]
                tol = h_vals.abs() * float(tolerance_pct) / 100.0
                near = pd.Series(False, index=work.index)
                for ref_col in refs.columns:
                    near = near | ((refs[ref_col] - h_vals).abs() <= tol)
                hourly_conf[col] = h_vals.where(near)

        if show_daily_vwap:
            daily_vwap = _vwap_bands(work, "D")
        else:
            daily_vwap = pd.DataFrame(index=work.index)
        if show_weekly_vwap:
            weekly_vwap = _vwap_bands(work, "W")
        else:
            weekly_vwap = pd.DataFrame(index=work.index)

        hourly_vwap_conf = hourly.copy()
        hourly_vwap_conf.loc[:, :] = np.nan
        if show_hourly_confluence:
            vwap_refs = []
            for ref_prefix, frame in [("daily", daily_vwap), ("weekly", weekly_vwap)]:
                keep = [c for c in ["vwap", "upper_1", "upper_2", "upper_3", "lower_1", "lower_2", "lower_3"] if c in frame.columns]
                if keep:
                    vwap_refs.append(frame[keep].add_prefix(f"{ref_prefix}_"))
            refs = pd.concat(vwap_refs, axis=1) if vwap_refs else pd.DataFrame(index=work.index)
            for col in cols:
                h_vals = hourly[col]
                tol = h_vals.abs() * float(tolerance_pct) / 100.0
                near = pd.Series(False, index=work.index)
                for ref_col in refs.columns:
                    near = near | ((refs[ref_col] - h_vals).abs() <= tol)
                hourly_vwap_conf[col] = h_vals.where(near)

        out = {"tolerance_pct": float(tolerance_pct)}
        for prefix, frame in [("daily", daily), ("weekly", weekly), ("hourly_conf", hourly_conf), ("hourly_vwap_conf", hourly_vwap_conf)]:
            for col in ["pivot", "pivot_avg", "r1", "s1", "r2", "s2", "r3", "s3"]:
                key = f"{prefix}_{col}"
                vals = [round(float(v), 4) if v == v else None for v in frame[col].tolist()]
                out[key] = vals
                out[f"{key}_last"] = next((v for v in reversed(vals) if v is not None), None)

        for prefix, frame in [("daily_vwap", daily_vwap), ("weekly_vwap", weekly_vwap)]:
            for col in ["vwap", "upper_1", "upper_2", "upper_3", "lower_1", "lower_2", "lower_3"]:
                key = f"{prefix}_{col}"
                if col not in frame.columns:
                    vals = [None] * len(work)
                else:
                    vals = [round(float(v), 4) if v == v else None for v in frame[col].tolist()]
                out[key] = vals
                out[f"{key}_last"] = next((v for v in reversed(vals) if v is not None), None)
        return out
    except Exception:
        return {}


def fibonacci_markers(df: pd.DataFrame) -> list:
    """Fibonacci level entry signals → marker events."""
    try:
        mod = _load_module("fibonacci_levels")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        last_seen = {}
        for col, label, direction in [
            ("fib_long",  "Fib Long",  "bull"),
            ("fib_short", "Fib Short", "bear"),
        ]:
            if col not in result.columns:
                continue
            for i in range(_WARMUP_BARS, n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 24. Trend Signals TP/SL (UAlgo) ──────────────────────────────────────

def trend_signals_markers(df: pd.DataFrame) -> list:
    """UAlgo trend signals with TP/SL → marker events."""
    try:
        mod = _load_module("trend_signals_tp_sl_ualgo")
        work = _norm(df)
        result = mod.calculate_indicators(work, multiplier=3.0, atr_period=10)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        mapping = [
            ("buy_signal",       "TS Buy",          "bull"),
            ("UpTrend_Begins",   "UpTrend Begins",  "bull"),
            ("sell_signal",      "TS Sell",          "bear"),
            ("DownTrend_Begins", "DnTrend Begins",  "bear"),
        ]
        last_seen = {}
        for col, label, direction in mapping:
            if col not in result.columns:
                continue
            for i in range(_WARMUP_BARS, n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 25. VWAP + BB Confluence ──────────────────────────────────────────────

def vwap_bb_confluence(df: pd.DataFrame) -> dict:
    """
    VWAP + Bollinger Band confluence overlays → line series data.
    Returns {vwap, upper_conf, lower_conf} plus signals as markers.
    """
    try:
        mod = _load_module("vwap_bb_confluence")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)

        def _series(col):
            if col not in result.columns:
                return []
            return [{"time": _time_str(idx, i, intraday), "value": round(float(v), 4)}
                    for i, v in enumerate(result[col].tolist()) if v == v]

        return {
            "vwap":        _series("VWAP"),
            "upper_conf":  _series("Upper_Confluence"),
            "lower_conf":  _series("Lower_Confluence"),
            "vwap_upper1": _series("VWAP_Upper_1"),
            "vwap_lower1": _series("VWAP_Lower_1"),
        }
    except Exception:
        return {}


# ── 26. VWAP + BB Super Confluence 2 ─────────────────────────────────────

def vwap_bb_super_confluence(df: pd.DataFrame) -> dict:
    """
    VWAP + BB Super Confluence 2 overlays + reversal markers.
    Returns {vwap, upper_conf, lower_conf, signals}.
    """
    try:
        mod = _load_module("vwap_bb_super_confluence_2")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)

        def _series(col):
            if col not in result.columns:
                return []
            return [{"time": _time_str(idx, i, intraday), "value": round(float(v), 4)}
                    for i, v in enumerate(result[col].tolist()) if v == v]

        events = []
        last_seen = {}
        for col, label, direction in [
            ("upper_reversal", "VWAP Rev Bear", "bear"),
            ("lower_reversal", "VWAP Rev Bull", "bull"),
        ]:
            if col not in result.columns:
                continue
            for i in range(_WARMUP_BARS, n):
                v = result[col].iloc[i]
                if v and v == v:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)

        return {
            "vwap":        _series("VWAP"),
            "upper_conf":  _series("Upper_Confluence") if "Upper_Confluence" in result.columns else _series("VWAP_Upper_1"),
            "lower_conf":  _series("Lower_Confluence") if "Lower_Confluence" in result.columns else _series("VWAP_Lower_1"),
            "signals":     _sanitize_events(events),
        }
    except Exception:
        return {}


# ── 27. Market Profile Value Area ────────────────────────────────────────

def mp_value_area_markers(df: pd.DataFrame) -> list:
    """Market Profile Value Area signals → marker events."""
    work = _norm(df)
    idx = df.index
    intraday = _is_intraday(df)
    try:
        mod = _load_module("mp_value_area")
        result = mod.calculate_indicators(work)
        events = _to_events(result, "bullish_mp_va", "bearish_mp_va",
                            "MP VA Bull", "MP VA Bear")
        if events:
            return events
    except Exception:
        pass

    try:
        if not isinstance(work.index, pd.DatetimeIndex) or len(work) < 80:
            return []
        if not {"high", "low", "close", "volume"}.issubset(set(work.columns)):
            return []
        high_s = work["high"].astype(float)
        low_s = work["low"].astype(float)
        close = work["close"].astype(float)
        prev_close = close.shift(1)
        events = []
        sessions = list(work.groupby(work.index.date, sort=True).groups.items())
        bin_count = 24
        value_area_pct = 0.68

        def _profile(pos):
            low = float(low_s.iloc[pos].min())
            high = float(high_s.iloc[pos].max())
            if not np.isfinite(low) or not np.isfinite(high) or high <= low:
                return None
            bins = np.linspace(low, high, bin_count + 1)
            step = float((high - low) / bin_count)
            volume_by_bin = np.zeros(bin_count, dtype=float)
            volumes = work["volume"].astype(float).clip(lower=0)
            for row_pos in pos:
                bar_high = float(high_s.iloc[row_pos])
                bar_low = float(low_s.iloc[row_pos])
                bar_volume = float(volumes.iloc[row_pos])
                if not np.isfinite(bar_high) or not np.isfinite(bar_low) or bar_volume <= 0:
                    continue
                candle_size = max(bar_high - bar_low, step)
                for level in range(bin_count):
                    price_low = bins[level]
                    price_high = bins[level + 1]
                    overlap = max(0.0, min(bar_high, price_high) - max(bar_low, price_low))
                    if overlap > 0:
                        volume_by_bin[level] += bar_volume * (overlap / candle_size)
            total_volume = float(volume_by_bin.sum())
            if total_volume <= 0:
                return None
            poc_bin = int(np.argmax(volume_by_bin))
            selected = {poc_bin}
            selected_volume = float(volume_by_bin[poc_bin])
            left = poc_bin - 1
            right = poc_bin + 1
            while selected_volume < total_volume * value_area_pct and (left >= 0 or right < bin_count):
                left_volume = volume_by_bin[left] if left >= 0 else -1
                right_volume = volume_by_bin[right] if right < bin_count else -1
                if right_volume >= left_volume:
                    selected.add(right)
                    selected_volume += float(max(right_volume, 0))
                    right += 1
                else:
                    selected.add(left)
                    selected_volume += float(max(left_volume, 0))
                    left -= 1
            return float(bins[min(selected)]), float(bins[max(selected) + 1])

        for session_i in range(1, len(sessions)):
            prev_idx = work.index.get_indexer(list(sessions[session_i - 1][1]))
            curr_idx = work.index.get_indexer(list(sessions[session_i][1]))
            prev_idx = prev_idx[prev_idx >= 0]
            curr_idx = curr_idx[curr_idx >= 0]
            if len(prev_idx) < 10:
                continue
            levels = _profile(prev_idx)
            if levels is None:
                continue
            val, vah = levels
            for i in curr_idx:
                if i < _WARMUP_BARS or _is_session_open_bar(idx, i):
                    continue
                if prev_close.iloc[i] <= vah < close.iloc[i]:
                    events.append({"time": _time_str(idx, i, intraday), "name": "MP VA Break Bull", "direction": "bull"})
                elif prev_close.iloc[i] >= val > close.iloc[i]:
                    events.append({"time": _time_str(idx, i, intraday), "name": "MP VA Break Bear", "direction": "bear"})
        return _sanitize_events(events)
    except Exception:
        return []


# ── 28. SMC Fair Value Gap ────────────────────────────────────────────────

def smc_fvg_markers(df: pd.DataFrame) -> list:
    """SMC Fair Value Gap → marker events. Uses _load_smc() to bypass smc_fvg.py's broken path."""
    try:
        smc = _load_smc()
        work = _norm(df).reset_index(drop=True)
        fvg_result = smc.fvg(work, join_consecutive=False)
        orig_idx = df.index
        intraday = _is_intraday(df)
        events = []
        fvg_vals = fvg_result["FVG"].fillna(0).values
        last_seen = {}
        for i in range(len(fvg_vals)):
            if fvg_vals[i] == 1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "FVG Bull", "bull", last_seen)
            elif fvg_vals[i] == -1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "FVG Bear", "bear", last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 29. SMC Order Blocks ──────────────────────────────────────────────────

def smc_ob_markers(df: pd.DataFrame) -> list:
    """SMC Order Blocks → marker events. Uses _load_smc() to bypass smc_ob.py's broken path."""
    try:
        smc = _load_smc()
        work = _norm(df).reset_index(drop=True)
        swing = smc.swing_highs_lows(work, swing_length=3)
        ob_result = smc.ob(work, swing, close_mitigation=False)
        orig_idx = df.index
        intraday = _is_intraday(df)
        events = []
        ob_vals = ob_result["OB"].fillna(0).values
        last_seen = {}
        for i in range(_WARMUP_BARS, len(ob_vals)):
            if ob_vals[i] == 1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "OB Bull", "bull", last_seen)
            elif ob_vals[i] == -1:
                _append_event_with_cooldown(events, orig_idx, i, intraday, "OB Bear", "bear", last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 30. Twin Range Filter ─────────────────────────────────────────────────

def twin_range_filter_markers(df: pd.DataFrame) -> list:
    """Twin Range Filter long/short signals → marker events."""
    try:
        mod = _load_module("twin_range_filter")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "Long", "Short", "TRF Long", "TRF Short")
    except Exception:
        return []


# ── 31. Hybrid ML + VWAP + BB ─────────────────────────────────────────────

def hybrid_ml_vwap_bb_markers(df: pd.DataFrame) -> list:
    """Hybrid ML + VWAP + BB buy/sell signals → marker events."""
    try:
        mod = _load_module("hybrid_ml_vwap_bb")
        work = _norm(df).copy()
        # hybrid_ml requires tz-aware DatetimeIndex for session grouping
        if isinstance(work.index, pd.DatetimeIndex) and work.index.tz is None:
            work.index = work.index.tz_localize("UTC")
        result = mod.calculate_indicators(work)
        return _to_events(result, "Buy_Signal", "Sell_Signal", "HML Buy", "HML Sell")
    except Exception:
        return []


# ── 32. TTI Ichimoku TK Cross ─────────────────────────────────────────────

def tti_ichimoku_markers(df: pd.DataFrame) -> list:
    """Ichimoku Tenkan/Kijun cross signals → marker events."""
    try:
        work = _norm(df).copy()
        if not {"high", "low"}.issubset(work.columns):
            return []
        if not isinstance(work.index, pd.DatetimeIndex):
            work.index = pd.date_range("2020-01-01", periods=len(work), freq="D")

        high = work["high"].astype(float)
        low = work["low"].astype(float)
        tenkan = (high.rolling(9, min_periods=9).max() + low.rolling(9, min_periods=9).min()) / 2.0
        kijun = (high.rolling(26, min_periods=26).max() + low.rolling(26, min_periods=26).min()) / 2.0

        prev_tenkan = tenkan.shift(1)
        prev_kijun = kijun.shift(1)
        work["bullish_tti_ichimoku"] = (tenkan > kijun) & (prev_tenkan <= prev_kijun)
        work["bearish_tti_ichimoku"] = (tenkan < kijun) & (prev_tenkan >= prev_kijun)

        return _to_events(work, "bullish_tti_ichimoku", "bearish_tti_ichimoku",
                          "Ichi TK Bull", "Ichi TK Bear")
    except Exception:
        return []


# ── 33. Finta Chandelier Exit ─────────────────────────────────────────────

def finta_chandelier_markers(df: pd.DataFrame) -> list:
    """Chandelier Exit crossover signals → marker events."""
    try:
        mod = _load_module("finta_chandelier")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_finta_chandelier", "bearish_finta_chandelier",
                          "CE Bull", "CE Bear")
    except Exception:
        return []


# ── 34. Trend Line Breakout ───────────────────────────────────────────────

def _trendln_line_segments(work: pd.DataFrame, events: list, window: int | None = None) -> list:
    """Build finite support/resistance trendline segments for breakout markers."""
    if not events:
        return []
    n = len(work)
    if n < 10:
        return []
    high = work["high"].astype(float).reset_index(drop=True)
    low = work["low"].astype(float).reset_index(drop=True)
    close = work["close"].astype(float).reset_index(drop=True)
    window = int(window or (125 if n >= 200 else max(20, min(60, n // 4))))
    piv_span = 2
    segments = []

    def _pivot_points(series: pd.Series, start: int, end: int, is_high: bool):
        pts = []
        for j in range(max(start + piv_span, 0), min(end - piv_span, n - 1) + 1):
            vals = series.iloc[j - piv_span:j + piv_span + 1]
            val = float(series.iloc[j])
            if not np.isfinite(val):
                continue
            if (is_high and val >= float(vals.max())) or ((not is_high) and val <= float(vals.min())):
                pts.append((j, val))
        if len(pts) >= 2:
            return pts
        look = series.iloc[start:end + 1]
        if look.empty:
            return []
        ranked = look.nlargest(2) if is_high else look.nsmallest(2)
        return sorted((int(k), float(v)) for k, v in ranked.items())

    def _fit_line(points, start: int, end: int):
        uniq, seen = [], set()
        for x, y in points:
            if x not in seen:
                uniq.append((x, y))
                seen.add(x)
        if len(uniq) < 2:
            return None
        xs = np.array([p[0] for p in uniq[-4:]], dtype=float)
        ys = np.array([p[1] for p in uniq[-4:]], dtype=float)
        if len(np.unique(xs)) < 2:
            return None
        slope, intercept = np.polyfit(xs, ys, 1)
        return float(slope * start + intercept), float(slope * end + intercept)

    for event in events[-120:]:
        try:
            i = int(event.get("index"))
        except Exception:
            continue
        if i <= 1 or i >= n:
            continue
        is_bull = event.get("direction") == "bull"
        start = max(0, i - window)
        pivots = _pivot_points(high if is_bull else low, start, i - 1, is_high=is_bull)
        if len(pivots) < 2:
            continue
        line_start = pivots[-2][0]
        line_end = min(n - 1, i + max(8, min(40, window // 4)))
        fitted = _fit_line(pivots, line_start, line_end)
        if fitted is None:
            continue
        y0, y1 = fitted
        if not (np.isfinite(y0) and np.isfinite(y1)):
            continue
        segments.append({
            "start_index": int(line_start),
            "end_index": int(line_end),
            "break_index": int(i),
            "start_price": round(float(y0), 4),
            "end_price": round(float(y1), 4),
            "break_price": round(float(close.iloc[i]), 4),
            "line_type": "resistance" if is_bull else "support",
            "direction": event.get("direction"),
            "name": event.get("name", "Trendline Breakout"),
        })
    return segments


def trendln_breakout_markers(df: pd.DataFrame) -> dict:
    """Trend line breakout signals → marker events."""
    try:
        _trendln_path = Path(r"D:\Projects\test1\opensource_indicators\trendln")
        if _trendln_path.exists() and str(_trendln_path) not in sys.path:
            sys.path.insert(0, str(_trendln_path))
        mod = _load_module("trendln_breakout")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        events = _to_events(result, "bullish_trendln", "bearish_trendln",
                            "TL Break Bull", "TL Break Bear")
        if events:
            return {"signals": events, "lines": _trendln_line_segments(work, events)}

        # Fallback: practical rolling trendline breakout. Uses only prior bars.
        close = work["close"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)
        window = 125 if len(work) >= 200 else max(20, min(60, len(work) // 4))
        resistance = high.shift(1).rolling(window, min_periods=max(10, window // 3)).max()
        support = low.shift(1).rolling(window, min_periods=max(10, window // 3)).min()
        bull = (close > resistance) & (close.shift(1) <= resistance.shift(1))
        bear = (close < support) & (close.shift(1) >= support.shift(1))
        tmp = work.copy()
        tmp["bullish_trendln"] = bull.fillna(False)
        tmp["bearish_trendln"] = bear.fillna(False)
        events = _to_events(tmp, "bullish_trendln", "bearish_trendln",
                            "TL Break Bull", "TL Break Bear")
        return {"signals": events, "lines": _trendln_line_segments(work, events, window=window)}
    except Exception:
        return {"signals": [], "lines": []}


# ── 35. Curve / Circle Patterns ───────────────────────────────────────────

def curve_circle_markers(df: pd.DataFrame) -> list:
    """U-bottom / J-hook / Arch / Rollover curve patterns → marker events."""
    try:
        mod = _load_module("curve_circle_patterns")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        n = len(result)
        events = []
        for col, label, direction in [
            ("curve_semi_circle",          "Curve U-Bot",   "bull"),
            ("curve_quarter_circle",       "Curve J-Hook",  "bull"),
            ("curve_bear_semi_circle",     "Curve Arch",    "bear"),
            ("curve_bear_quarter_circle",  "Curve Rollover","bear"),
        ]:
            if col not in result.columns:
                continue
            last_seen = {}
            for i in range(n):
                if result[col].iloc[i]:
                    _append_event_with_cooldown(events, idx, i, intraday, label, direction, last_seen)
        return _sanitize_events(events)
    except Exception:
        return []


# ── 36. Harmonic Patterns (Gartley / Bat / Butterfly / Crab / Shark …) ───

def harmonic_pattern_markers(df: pd.DataFrame) -> list:
    """ZigZag-based harmonic patterns → marker events."""
    try:
        mod = _load_module("harmonic_patterns")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "harmonic_bullish", "harmonic_bearish",
                          "Harmonic Bull", "Harmonic Bear")
    except Exception:
        return []


# ── 37. SBS + Swing Areas / Trades ────────────────────────────────────────

def sbs_swing_markers(df: pd.DataFrame) -> list:
    """SBS + Swing Areas/Trades long/short entries → marker events."""
    try:
        mod = _load_module("sbs_swing_areas_trades")
        work = _norm(df).copy()
        # sbs_swing requires DatetimeIndex
        if not isinstance(work.index, pd.DatetimeIndex):
            work.index = pd.date_range("2020-01-01", periods=len(work), freq="D")
        result = mod.calculate_indicators(work)
        return _to_events(result, "long_entry", "short_entry", "SBS Long", "SBS Short")
    except Exception:
        return []


# ── Master compute ────────────────────────────────────────────────────────


# â”€â”€ Batch 4 (Missed/Redundant/Special) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def zigzag_swing_markers(df: pd.DataFrame) -> list:
    """ZigZag Swing Pivot Confirm signals â†’ marker events."""
    try:
        mod = _load_module("zigzag_swing")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_zigzag", "bearish_zigzag", "ZZ Bull", "ZZ Bear")
    except Exception:
        return []


def talipp_supertrend_markers(df: pd.DataFrame) -> list:
    """SuperTrend Direction Flip (talipp) â†’ marker events."""
    try:
        _path = r"D:\Projects\test1\opensource_indicators\talipp"
        if _path not in sys.path:
            sys.path.insert(0, _path)
        mod = _load_module("talipp_supertrend")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_talipp_supertrend", "bearish_talipp_supertrend",
                          "ST Bull", "ST Bear")
    except Exception:
        return []


def ta_macd_markers(df: pd.DataFrame) -> list:
    """MACD Signal Line Cross (ta-library) â†’ marker events."""
    try:
        _path = r"D:\Projects\test1\opensource_indicators\ta-library"
        if _path not in sys.path:
            sys.path.insert(0, _path)
        mod = _load_module("ta_macd_cross")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_ta_macd", "bearish_ta_macd",
                          "MACD Bull", "MACD Bear")
    except Exception:
        return []


def pyti_keltner_markers(df: pd.DataFrame) -> list:
    """Keltner Channel Cross (pyti) â†’ marker events."""
    try:
        _path = r"D:\Projects\test1\opensource_indicators\pyti"
        if _path not in sys.path:
            sys.path.insert(0, _path)
        mod = _load_module("pyti_keltner")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_pyti_keltner", "bearish_pyti_keltner",
                          "KC Bull", "KC Bear")
    except Exception:
        return []


def tapy_psar_markers(df: pd.DataFrame) -> list:
    """Parabolic SAR Flip (ta-py) â†’ marker events."""
    try:
        _path = r"D:\Projects\test1\opensource_indicators\ta-py"
        if _path not in sys.path:
            sys.path.insert(0, _path)
        mod = _load_module("tapy_psar")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_tapy_psar", "bearish_tapy_psar",
                          "SAR Bull", "SAR Bear")
    except Exception:
        return []


def stockstats_rsi_markers(df: pd.DataFrame) -> list:
    """RSI 30/70 Cross (stockstats) â†’ marker events."""
    try:
        _path = r"D:\Projects\test1\opensource_indicators\stockstats"
        if _path not in sys.path:
            sys.path.insert(0, _path)
        mod = _load_module("stockstats_rsi_cross")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_stockstats_rsi", "bearish_stockstats_rsi",
                          "RSI Bull", "RSI Bear")
    except Exception:
        return []


def harmonic_patterns_zz_markers(df: pd.DataFrame) -> list:
    """ZigZag-based harmonic patterns (simplified) â†’ marker events."""
    try:
        mod = _load_module("harmonic_patterns")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "harmonic_bullish", "harmonic_bearish",
                          "ZZ Har Bull", "ZZ Har Bear")
    except Exception:
        return []


def cpr_vedhaviyash4_levels(df: pd.DataFrame) -> dict:
    """Vedhaviyash4 Daily CPR â†’ price levels."""
    try:
        mod = _load_module("vedhaviyash4_daily_cpr")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        last = result.iloc[-1]
        return {
            "p":  round(float(last["daily_pivot"]), 2),
            "bc": round(float(last["daily_bc"]),    2),
            "tc": round(float(last["daily_tc"]),    2),
            "r1": round(float(last["daily_r1"]),    2),
            "s1": round(float(last["daily_s1"]),    2),
            "r2": round(float(last["daily_r2"]),    2),
            "s2": round(float(last["daily_s2"]),    2),
        }
    except Exception:
        return {}


def flowscope_markers(df: pd.DataFrame) -> list:
    """FlowScope [Hapharmonic] marker events."""
    try:
        mod = _load_module("flowscope_hapharmonic")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        intraday = _is_intraday(result)
        idx = result.index
        events = []
        if "Bar_Color" in result.columns:
            events.append({"time": _time_str(idx, 0, intraday), "name": "FlowScope Active", "direction": "neutral"})
        return events
    except Exception:
        return []


def inside_outside_mk_markers(df: pd.DataFrame) -> list:
    """Previous Candle + Inside/Outside [MK] â†’ marker events."""
    try:
        mod = _load_module("previous_candle_inside_outside_mk")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "outside_bull_raw", "outside_bear_raw", "MK Out Bull", "MK Out Bear",
                          neutral_col="inside_bar_raw", neutral_name="MK Inside")
    except Exception:
        return []


def pandas_ta_cdl_markers(df: pd.DataFrame) -> list:
    """Candlestick Engulfing Pattern (pandas-ta) â†’ marker events."""
    try:
        _path = r"D:\Projects\test1\opensource_indicators\pandas-ta-classic"
        if _path not in sys.path:
            sys.path.insert(0, _path)
        mod = _load_module("pandas_ta_cdl")
        work = _norm(df)
        result = mod.calculate_indicators(work)
        return _to_events(result, "bullish_pandas_ta_cdl", "bearish_pandas_ta_cdl",
                          "PTA Eng Bull", "PTA Eng Bear")
    except Exception:
        return []


def liquid_reversal_bands(df: pd.DataFrame,
                          fair_len: int = 50,
                          z_len: int = 100,
                          smooth_len: int = 18,
                          upper_mult: float = 2.4,
                          lower_mult: float = 2.4,
                          outer_upper_mult: float = 1.45,
                          outer_lower_mult: float = 1.45,
                          cooldown_bars: int = 0) -> dict:
    """Uptrick Liquid Reversal Bands overlay + close-crossing reversal markers."""
    try:
        work = _norm(df).copy().sort_index()
        intraday = _is_intraday(work)
        idx = work.index
        close = work["close"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)

        def ema(series, length):
            return series.ewm(span=max(1, int(length)), adjust=False).mean()

        def alma(series, length, offset=0.85, sigma=6.0):
            length = int(length)
            if length < 1:
                return series.copy()
            m = np.floor(offset * (length - 1))
            s = length / sigma
            weights = np.array([np.exp(-((i - m) ** 2) / (2 * s * s)) for i in range(length)], dtype=float)
            weights = weights / weights.sum()
            return series.rolling(window=length, min_periods=length).apply(lambda x: float(np.dot(x, weights)), raw=True)

        ema_fair = ema(close, fair_len)
        alma_fair = alma(close, fair_len, 0.85, 6.0)
        fair_raw = ema_fair * 0.55 + alma_fair * 0.45
        fair = ema(fair_raw, max(1, int(smooth_len / 2)))

        dev = close - fair
        dev_stdev = dev.rolling(window=z_len, min_periods=z_len).std()
        tr = pd.concat([(high - low), (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr_value = ema(tr, 14)
        abs_dev = ema(dev.abs(), z_len)
        range_energy = ema(high - low, smooth_len)
        base_width = dev_stdev * 0.60 + atr_value * 0.25 + abs_dev * 0.10 + range_energy * 0.05
        width = ema(base_width, smooth_len)

        upper = fair + width * upper_mult
        lower = fair - width * lower_mult
        outer_upper = fair + width * upper_mult * outer_upper_mult
        outer_lower = fair - width * lower_mult * outer_lower_mult

        raw_buy = (close.shift(1) <= lower.shift(1)) & (close > lower)
        raw_sell = (close.shift(1) >= upper.shift(1)) & (close < upper)
        final_buy = pd.Series(False, index=work.index)
        final_sell = pd.Series(False, index=work.index)
        last_signal = -10**9
        for i in range(1, len(work)):
            if intraday and _is_session_open_bar(idx, i):
                continue
            if i - last_signal < cooldown_bars:
                continue
            if bool(raw_buy.iloc[i]):
                final_buy.iloc[i] = True
                last_signal = i
            elif bool(raw_sell.iloc[i]):
                final_sell.iloc[i] = True
                last_signal = i

        def line(series):
            out = []
            for i, v in enumerate(series.tolist()):
                if v == v:
                    out.append({"time": _time_str(idx, i, intraday), "value": round(float(v), 4)})
            return out

        signals = []
        for i in range(len(work)):
            if bool(final_buy.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "LRB Up", "direction": "bull", "index": i})
            elif bool(final_sell.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "LRB Down", "direction": "bear", "index": i})

        return {
            "fair": line(fair),
            "upper": line(upper),
            "lower": line(lower),
            "outer_upper": line(outer_upper),
            "outer_lower": line(outer_lower),
            "signals": _sanitize_events(signals),
        }
    except Exception:
        return {}


def adaptive_flow(df: pd.DataFrame,
                  flow_len: int = 14,
                  fast_len: int = 2,
                  slow_len: int = 30,
                  atr_len: int = 14,
                  atr_mult: float = 2.5,
                  stop_lookback: int = 20,
                  noise_on: bool = True,
                  noise_thr: float = 0.3,
                  cooldown: int = 3,
                  bands_mult: float = 1.5,
                  pivot_left: int = 10,
                  pivot_right: int = 10) -> dict:
    """Adaptive Flow II: KAMA flow, dynamic stop, bands, VWAP/EMA context, signals and structure markers."""
    try:
        work = _norm(df).copy().sort_index()
        intraday = _is_intraday(work)
        idx = work.index
        close = work["close"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)
        volume = work["volume"].astype(float) if "volume" in work.columns else pd.Series(1.0, index=work.index)

        tr = pd.concat([(high - low), (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_len, min_periods=1).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()
        typical = (high + low + close) / 3
        day_key = idx.date if isinstance(idx, pd.DatetimeIndex) else pd.Series(range(len(work)), index=idx)
        vwap = (typical * volume).groupby(day_key).cumsum() / volume.groupby(day_key).cumsum().replace(0, np.nan)

        fast_sc = 2.0 / (fast_len + 1)
        slow_sc = 2.0 / (slow_len + 1)
        direction = (close - close.shift(flow_len)).abs()
        volatility = close.diff().abs().rolling(window=flow_len, min_periods=1).sum().replace(0, np.nan)
        er = (direction / volatility).fillna(0)
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
        kama = pd.Series(index=work.index, dtype=float)
        kama.iloc[0] = close.iloc[0]
        for i in range(1, len(work)):
            raw = kama.iloc[i - 1] + sc.iloc[i] * (close.iloc[i] - kama.iloc[i - 1])
            if noise_on and abs(raw - kama.iloc[i - 1]) <= atr.iloc[i] * noise_thr:
                kama.iloc[i] = kama.iloc[i - 1]
            else:
                kama.iloc[i] = raw

        stop = pd.Series(np.nan, index=work.index)
        trend = pd.Series(0, index=work.index, dtype=int)
        cur_trend = 1
        cur_stop = np.nan
        kama_high = kama.rolling(window=stop_lookback, min_periods=1).max()
        kama_low = kama.rolling(window=stop_lookback, min_periods=1).min()
        bull = pd.Series(False, index=work.index)
        bear = pd.Series(False, index=work.index)
        last_bull = last_bear = -10**9
        for i in range(max(flow_len, atr_len, 1), len(work)):
            prev_trend = cur_trend
            if cur_stop != cur_stop:
                cur_stop = kama.iloc[i] - atr.iloc[i] * atr_mult
            elif cur_trend == 1:
                new_stop = kama_high.iloc[i] - atr.iloc[i] * atr_mult
                if kama.iloc[i] < cur_stop:
                    cur_trend = -1
                    cur_stop = kama_low.iloc[i] + atr.iloc[i] * atr_mult
                else:
                    cur_stop = max(cur_stop, new_stop)
            else:
                new_stop = kama_low.iloc[i] + atr.iloc[i] * atr_mult
                if kama.iloc[i] > cur_stop:
                    cur_trend = 1
                    cur_stop = kama_high.iloc[i] - atr.iloc[i] * atr_mult
                else:
                    cur_stop = min(cur_stop, new_stop)
            trend.iloc[i] = cur_trend
            stop.iloc[i] = cur_stop
            if intraday and _is_session_open_bar(idx, i):
                continue
            if cur_trend == 1 and prev_trend == -1 and close.iloc[i] > ema200.iloc[i] and i - last_bull >= cooldown:
                bull.iloc[i] = True
                last_bull = i
            elif cur_trend == -1 and prev_trend == 1 and close.iloc[i] < ema200.iloc[i] and i - last_bear >= cooldown:
                bear.iloc[i] = True
                last_bear = i

        upper = kama + atr * bands_mult
        lower = kama - atr * bands_mult
        piv_h = pd.Series(False, index=work.index)
        piv_l = pd.Series(False, index=work.index)
        for j in range(pivot_left, len(work) - pivot_right):
            window = close.iloc[j - pivot_left:j + pivot_right + 1]
            piv_h.iloc[j] = close.iloc[j] == window.max()
            piv_l.iloc[j] = close.iloc[j] == window.min()
        struct_events = []
        last_h = last_l = None
        struct = 0
        for i in range(pivot_left + pivot_right, len(work)):
            pivot_i = i - pivot_right
            if bool(piv_h.iloc[pivot_i]):
                last_h = high.iloc[pivot_i]
            if bool(piv_l.iloc[pivot_i]):
                last_l = low.iloc[pivot_i]
            if last_h is not None and close.iloc[i] > last_h:
                name = "AF BOS" if struct == 1 else "AF CHoCH"
                struct = 1
                struct_events.append({"time": _time_str(idx, i, intraday), "name": name, "direction": "bull", "index": i})
                last_h = None
            elif last_l is not None and close.iloc[i] < last_l:
                name = "AF BOS" if struct == -1 else "AF CHoCH"
                struct = -1
                struct_events.append({"time": _time_str(idx, i, intraday), "name": name, "direction": "bear", "index": i})
                last_l = None

        def line(series):
            return [{"time": _time_str(idx, i, intraday), "value": round(float(v), 4)}
                    for i, v in enumerate(series.tolist()) if v == v]

        signals = []
        for i in range(len(work)):
            if bool(bull.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "AF Bull", "direction": "bull", "index": i})
            elif bool(bear.iloc[i]):
                signals.append({"time": _time_str(idx, i, intraday), "name": "AF Bear", "direction": "bear", "index": i})

        return {
            "kama": line(kama),
            "stop": line(stop),
            "upper": line(upper),
            "lower": line(lower),
            "ema200": line(ema200),
            "vwap": line(vwap),
            "signals": _sanitize_events(signals),
            "structure": _sanitize_events(struct_events),
        }
    except Exception:
        return {}


def liquidity_intelligence(df: pd.DataFrame,
                           pivot_len: int = 5,
                           atr_len: int = 14,
                           ema_fast_len: int = 50,
                           ema_slow_len: int = 200,
                           vol_len: int = 20,
                           rsi_len: int = 14,
                           rsi_os: float = 35,
                           rsi_ob: float = 65,
                           max_sweep_depth: float = 0.75,
                           min_rejection: float = 0.20,
                           vol_mult: float = 1.30,
                           fvg_recent_bars: int = 8,
                           disp_atr_min: float = 0.22,
                           disp_body_ratio: float = 0.50,
                           tp_atr: float = 3.0,
                           sl_atr: float = 1.5) -> dict:
    """Liquidity Intelligence: sweep-based active model with regime, quality, and trade levels."""
    try:
        work = _norm(df).copy().sort_index()
        intraday = _is_intraday(work)
        idx = work.index
        o = work["open"].astype(float)
        h = work["high"].astype(float)
        l = work["low"].astype(float)
        c = work["close"].astype(float)
        v = work["volume"].astype(float) if "volume" in work.columns else pd.Series(1.0, index=work.index)

        tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_len, min_periods=atr_len).mean()
        ema_fast = c.ewm(span=ema_fast_len, adjust=False).mean()
        ema_slow = c.ewm(span=ema_slow_len, adjust=False).mean()
        vol_sma = v.rolling(window=vol_len, min_periods=1).mean()
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(window=rsi_len, min_periods=rsi_len).mean()
        loss = (-delta.clip(upper=0)).rolling(window=rsi_len, min_periods=rsi_len).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        body = (c - o).abs()
        rng = (h - l).replace(0, np.nan)
        body_ratio = (body / rng).fillna(0)
        avg_body_ratio = body_ratio.rolling(20, min_periods=1).mean()
        atr_avg = atr.rolling(50, min_periods=1).mean()

        piv_h = pd.Series(np.nan, index=work.index)
        piv_l = pd.Series(np.nan, index=work.index)
        for j in range(pivot_len, len(work) - pivot_len):
            win_h = h.iloc[j - pivot_len:j + pivot_len + 1]
            win_l = l.iloc[j - pivot_len:j + pivot_len + 1]
            if h.iloc[j] == win_h.max():
                piv_h.iloc[j] = h.iloc[j]
            if l.iloc[j] == win_l.min():
                piv_l.iloc[j] = l.iloc[j]

        bull_fvg = (l > h.shift(2)) & ((l - h.shift(2)) >= atr * 0.05)
        bear_fvg = (h < l.shift(2)) & ((l.shift(2) - h) >= atr * 0.05)
        last_bull_fvg = last_bear_fvg = -10**9
        last_swing_h = last_swing_l = None
        last_side = "NONE"
        signals = []
        levels = []
        last_level_h = last_level_l = None

        for i in range(max(ema_slow_len, atr_len, pivot_len * 2 + 1), len(work)):
            if bool(bull_fvg.iloc[i]):
                last_bull_fvg = i
            if bool(bear_fvg.iloc[i]):
                last_bear_fvg = i

            pivot_i = i - pivot_len
            if pivot_i >= 0:
                if piv_h.iloc[pivot_i] == piv_h.iloc[pivot_i]:
                    level_type = "EQH" if last_level_h is not None and abs(piv_h.iloc[pivot_i] - last_level_h) <= atr.iloc[i] * 0.08 else "BSL"
                    last_level_h = float(piv_h.iloc[pivot_i])
                    levels.append({"time": _time_str(idx, pivot_i, intraday), "name": level_type, "direction": "bear", "index": pivot_i, "price": round(last_level_h, 4)})
                    last_swing_h = last_level_h
                if piv_l.iloc[pivot_i] == piv_l.iloc[pivot_i]:
                    level_type = "EQL" if last_level_l is not None and abs(piv_l.iloc[pivot_i] - last_level_l) <= atr.iloc[i] * 0.08 else "SSL"
                    last_level_l = float(piv_l.iloc[pivot_i])
                    levels.append({"time": _time_str(idx, pivot_i, intraday), "name": level_type, "direction": "bull", "index": pivot_i, "price": round(last_level_l, 4)})
                    last_swing_l = last_level_l

            if atr.iloc[i] != atr.iloc[i] or atr.iloc[i] <= 0:
                continue
            candle_range = max(float(h.iloc[i] - l.iloc[i]), 1e-10)
            upper_rej = float(h.iloc[i] - max(o.iloc[i], c.iloc[i])) / candle_range
            lower_rej = float(min(o.iloc[i], c.iloc[i]) - l.iloc[i]) / candle_range
            buy_sweep = (
                last_swing_l is not None and l.iloc[i] < last_swing_l and c.iloc[i] > last_swing_l
                and ((last_swing_l - l.iloc[i]) / atr.iloc[i]) <= max_sweep_depth
                and lower_rej >= min_rejection
            )
            sell_sweep = (
                last_swing_h is not None and h.iloc[i] > last_swing_h and c.iloc[i] < last_swing_h
                and ((h.iloc[i] - last_swing_h) / atr.iloc[i]) <= max_sweep_depth
                and upper_rej >= min_rejection
            )
            bull_disp = c.iloc[i] > o.iloc[i] and body.iloc[i] >= atr.iloc[i] * disp_atr_min and body_ratio.iloc[i] >= disp_body_ratio
            bear_disp = c.iloc[i] < o.iloc[i] and body.iloc[i] >= atr.iloc[i] * disp_atr_min and body_ratio.iloc[i] >= disp_body_ratio
            trend_long = ema_fast.iloc[i] > ema_slow.iloc[i]
            trend_short = ema_fast.iloc[i] < ema_slow.iloc[i]
            vol_spike = v.iloc[i] > vol_sma.iloc[i] * vol_mult
            bull_fvg_recent = i - last_bull_fvg <= fvg_recent_bars
            bear_fvg_recent = i - last_bear_fvg <= fvg_recent_bars
            rsi_long = rsi.iloc[i] <= rsi_os
            rsi_short = rsi.iloc[i] >= rsi_ob

            high_vol = atr.iloc[i] > atr_avg.iloc[i] * 1.25 if atr_avg.iloc[i] == atr_avg.iloc[i] else False
            low_vol = atr.iloc[i] < atr_avg.iloc[i] * 0.75 if atr_avg.iloc[i] == atr_avg.iloc[i] else False
            if trend_long and not high_vol:
                regime, bias = "Trend Up", "LONG Bias"
            elif trend_short and not high_vol:
                regime, bias = "Trend Down", "SHORT Bias"
            elif high_vol:
                regime, bias = "High Vol", "Aggressive"
            elif low_vol:
                regime, bias = "Low Vol", "Patience"
            elif avg_body_ratio.iloc[i] <= 0.35:
                regime, bias = "Choppy", "Avoid / Wait"
            else:
                regime, bias = "Range", "Mean Reversion"

            side = None
            if buy_sweep and last_side != "LONG":
                side = "LONG"
            elif sell_sweep and last_side != "SHORT":
                side = "SHORT"
            if side is None:
                continue

            q = 25.0
            if side == "LONG":
                q += 15 if trend_long else 0
                q += 15 if bull_fvg_recent else 0
                q += 10 if vol_spike else 0
                q += 10 if rsi_long else 0
                q += 10 if bull_disp else 0
                q += 15 if regime in ("Trend Up", "Range", "Low Vol") else -10 if regime == "Trend Down" else 0
                sl = c.iloc[i] - atr.iloc[i] * sl_atr
                tp1 = c.iloc[i] + atr.iloc[i] * tp_atr
                tp2 = c.iloc[i] + atr.iloc[i] * tp_atr * 2
                tp3 = c.iloc[i] + atr.iloc[i] * tp_atr * 3
                direction = "bull"
            else:
                q += 15 if trend_short else 0
                q += 15 if bear_fvg_recent else 0
                q += 10 if vol_spike else 0
                q += 10 if rsi_short else 0
                q += 10 if bear_disp else 0
                q += 15 if regime in ("Trend Down", "Range", "Low Vol") else -10 if regime == "Trend Up" else 0
                sl = c.iloc[i] + atr.iloc[i] * sl_atr
                tp1 = c.iloc[i] - atr.iloc[i] * tp_atr
                tp2 = c.iloc[i] - atr.iloc[i] * tp_atr * 2
                tp3 = c.iloc[i] - atr.iloc[i] * tp_atr * 3
                direction = "bear"

            last_side = side
            signals.append({
                "time": _time_str(idx, i, intraday),
                "name": f"LIQ {side}",
                "direction": direction,
                "index": i,
                "quality": round(float(max(0, min(100, q))), 1),
                "regime": regime,
                "bias": bias,
                "entry": round(float(c.iloc[i]), 4),
                "sl": round(float(sl), 4),
                "tp1": round(float(tp1), 4),
                "tp2": round(float(tp2), 4),
                "tp3": round(float(tp3), 4),
            })

        latest = signals[-1] if signals else {}
        return {
            "signals": _sanitize_events(signals),
            "levels": levels[-60:],
            "latest": latest,
        }
    except Exception:
        return {}


_RSI_DIV_AUTO_PARAMS = {
    "3m":  {"rsi_length": 11, "pivot_left": 6,  "pivot_right": 6,  "hold_bars": 20, "description": "Scalping"},
    "5m":  {"rsi_length": 9,  "pivot_left": 12, "pivot_right": 10, "hold_bars": 15, "description": "Day Trading"},
    "15m": {"rsi_length": 9,  "pivot_left": 8,  "pivot_right": 6,  "hold_bars": 10, "description": "Intraday Swing"},
    "30m": {"rsi_length": 11, "pivot_left": 10, "pivot_right": 8,  "hold_bars": 8,  "description": "Short-term Swing"},
    "1h":  {"rsi_length": 14, "pivot_left": 12, "pivot_right": 10, "hold_bars": 6,  "description": "Medium-term Swing"},
    "1d":  {"rsi_length": 30, "pivot_left": 14, "pivot_right": 12, "hold_bars": 5,  "description": "Positional"},
}


def _infer_rsi_div_timeframe(index) -> str:
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return "5m"
    minutes = max(1, round((index[1] - index[0]).total_seconds() / 60))
    if minutes <= 3:
        return "3m"
    if minutes <= 5:
        return "5m"
    if minutes <= 15:
        return "15m"
    if minutes <= 30:
        return "30m"
    if minutes <= 90:
        return "1h"
    return "1d"


def rsi_div_auto(df: pd.DataFrame) -> dict:
    """Auto-parameter RSI divergence strategy markers with confirmed pivot delay."""
    try:
        work = _norm(df).copy().sort_index()
        intraday = _is_intraday(work)
        idx = work.index
        tf = _infer_rsi_div_timeframe(idx)
        params = _RSI_DIV_AUTO_PARAMS[tf]
        rsi_len = params["rsi_length"]
        left = params["pivot_left"]
        right = params["pivot_right"]
        close = work["close"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)

        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1 / rsi_len, min_periods=rsi_len, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / rsi_len, min_periods=rsi_len, adjust=False).mean()
        rsi = 100 - (100 / (1 + avg_gain / avg_loss.replace(0, np.nan)))

        price_low = pd.Series(np.nan, index=work.index)
        rsi_low = pd.Series(np.nan, index=work.index)
        price_high = pd.Series(np.nan, index=work.index)
        rsi_high = pd.Series(np.nan, index=work.index)
        for i in range(left, len(work) - right):
            if low.iloc[i] <= low.iloc[i - left:i].min() and low.iloc[i] <= low.iloc[i + 1:i + right + 1].min():
                price_low.iloc[i] = low.iloc[i]
            if rsi.iloc[i] == rsi.iloc[i] and rsi.iloc[i] <= rsi.iloc[i - left:i].min() and rsi.iloc[i] <= rsi.iloc[i + 1:i + right + 1].min():
                rsi_low.iloc[i] = rsi.iloc[i]
            if high.iloc[i] >= high.iloc[i - left:i].max() and high.iloc[i] >= high.iloc[i + 1:i + right + 1].max():
                price_high.iloc[i] = high.iloc[i]
            if rsi.iloc[i] == rsi.iloc[i] and rsi.iloc[i] >= rsi.iloc[i - left:i].max() and rsi.iloc[i] >= rsi.iloc[i + 1:i + right + 1].max():
                rsi_high.iloc[i] = rsi.iloc[i]

        lows_seen = []
        highs_seen = []
        signals = []
        for pivot_i in range(len(work)):
            signal_i = pivot_i + right
            if signal_i >= len(work):
                continue
            if intraday and _is_session_open_bar(idx, signal_i):
                continue
            if price_low.iloc[pivot_i] == price_low.iloc[pivot_i] and rsi_low.iloc[pivot_i] == rsi_low.iloc[pivot_i]:
                if lows_seen:
                    prev_price, prev_rsi = lows_seen[-1][1], lows_seen[-1][2]
                    if price_low.iloc[pivot_i] < prev_price and rsi_low.iloc[pivot_i] > prev_rsi:
                        signals.append({
                            "time": _time_str(idx, signal_i, intraday),
                            "name": "RSI Div Bull",
                            "direction": "bull",
                            "index": signal_i,
                            "pivot_index": pivot_i,
                            "price": round(float(price_low.iloc[pivot_i]), 4),
                            "rsi": round(float(rsi_low.iloc[pivot_i]), 2),
                            "tf": tf,
                            "delay_bars": right,
                        })
                lows_seen.append((pivot_i, float(price_low.iloc[pivot_i]), float(rsi_low.iloc[pivot_i])))
            if price_high.iloc[pivot_i] == price_high.iloc[pivot_i] and rsi_high.iloc[pivot_i] == rsi_high.iloc[pivot_i]:
                if highs_seen:
                    prev_price, prev_rsi = highs_seen[-1][1], highs_seen[-1][2]
                    if price_high.iloc[pivot_i] > prev_price and rsi_high.iloc[pivot_i] < prev_rsi:
                        signals.append({
                            "time": _time_str(idx, signal_i, intraday),
                            "name": "RSI Div Bear",
                            "direction": "bear",
                            "index": signal_i,
                            "pivot_index": pivot_i,
                            "price": round(float(price_high.iloc[pivot_i]), 4),
                            "rsi": round(float(rsi_high.iloc[pivot_i]), 2),
                            "tf": tf,
                            "delay_bars": right,
                        })
                highs_seen.append((pivot_i, float(price_high.iloc[pivot_i]), float(rsi_high.iloc[pivot_i])))

        return {
            "signals": _sanitize_events(signals),
            "params": params | {"timeframe": tf},
            "rsi": [round(float(v), 4) if v == v else None for v in rsi.tolist()],
        }
    except Exception:
        return {}


def swing_breakout_sequence(df: pd.DataFrame, swing_length: int = 5, internal_length: int = 2,
                            strict_threshold: float = 0.50) -> dict:
    """LuxAlgo-style Swing Breakout Sequence markers with entry/SL/target metadata."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {}

        idx = work.index
        intraday = _is_intraday(work)
        n = len(work)
        if n < max(40, swing_length * 8):
            return {"signals": [], "sequences": []}

        swing_length = max(2, int(swing_length))
        internal_length = max(2, min(int(internal_length), swing_length))
        high = work["high"].astype(float)
        low = work["low"].astype(float)
        close = work["close"].astype(float)

        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=200, min_periods=1).mean()

        raw_pivots = []
        for i in range(swing_length, n - swing_length):
            hwin = high.iloc[i - swing_length:i + swing_length + 1]
            lwin = low.iloc[i - swing_length:i + swing_length + 1]
            is_high = bool(high.iloc[i] == hwin.max())
            is_low = bool(low.iloc[i] == lwin.min())
            if is_high and is_low:
                if high.iloc[i] - high.iloc[i - 1] >= low.iloc[i - 1] - low.iloc[i]:
                    is_low = False
                else:
                    is_high = False
            if is_high:
                raw_pivots.append({"index": i, "kind": "H", "price": float(high.iloc[i])})
            elif is_low:
                raw_pivots.append({"index": i, "kind": "L", "price": float(low.iloc[i])})

        pivots = []
        for p in raw_pivots:
            if not pivots:
                pivots.append(p)
                continue
            last = pivots[-1]
            if p["kind"] != last["kind"]:
                pivots.append(p)
            elif p["kind"] == "H" and p["price"] > last["price"]:
                pivots[-1] = p
            elif p["kind"] == "L" and p["price"] < last["price"]:
                pivots[-1] = p

        sequences = []
        seen_entries = set()

        def _inside(price: float, top: float, bottom: float) -> bool:
            return min(top, bottom) <= price <= max(top, bottom)

        def _rr_targets(points, bullish: bool):
            entry = float(points[-1]["price"])
            zone_top = max(float(points[0]["price"]), float(points[1]["price"]))
            zone_bottom = min(float(points[0]["price"]), float(points[1]["price"]))
            zone_height = max(zone_top - zone_bottom, 1e-9)
            if bullish:
                stop = min(float(p["price"]) for p in points)
                risk = max(entry - stop, 1e-9)
                target = max(zone_top + zone_height, entry + risk * 1.5)
            else:
                stop = max(float(p["price"]) for p in points)
                risk = max(stop - entry, 1e-9)
                target = min(zone_bottom - zone_height, entry - risk * 1.5)
            return entry, stop, target, zone_top, zone_bottom

        for start in range(0, max(0, len(pivots) - 4)):
            pts = pivots[start:start + 5]
            if len(pts) < 5:
                continue
            kinds = [p["kind"] for p in pts]
            if kinds not in (["L", "H", "L", "H", "L"], ["H", "L", "H", "L", "H"]):
                continue

            A, B, p2, p3, p4 = pts
            zone_top = max(A["price"], B["price"])
            zone_bottom = min(A["price"], B["price"])
            atr_val = float(atr.iloc[p4["index"]]) if atr.iloc[p4["index"]] == atr.iloc[p4["index"]] else 0.0
            eq_thr = max(atr_val * strict_threshold, (zone_top - zone_bottom) * 0.10)

            bullish = (
                A["kind"] == "L"
                and _inside(p2["price"], zone_top, zone_bottom)
                and p3["price"] > zone_top
                and _inside(p4["price"], zone_top, zone_bottom)
                and abs(p4["price"] - p2["price"]) <= max(eq_thr, 1e-9)
            )
            bearish = (
                A["kind"] == "H"
                and _inside(p2["price"], zone_top, zone_bottom)
                and p3["price"] < zone_bottom
                and _inside(p4["price"], zone_top, zone_bottom)
                and abs(p4["price"] - p2["price"]) <= max(eq_thr, 1e-9)
            )

            entry_points = pts
            signal_idx = None
            if bullish:
                for j in range(p4["index"] + 1, min(n, p4["index"] + max(8, swing_length * 6))):
                    if close.iloc[j] > p3["price"]:
                        signal_idx = j
                        break
            elif bearish:
                for j in range(p4["index"] + 1, min(n, p4["index"] + max(8, swing_length * 6))):
                    if close.iloc[j] < p3["price"]:
                        signal_idx = j
                        break

            if (not bullish and not bearish) or signal_idx is None:
                continue

            entry_idx = int(signal_idx)
            if signal_idx in seen_entries:
                continue
            if intraday and _is_session_open_bar(idx, signal_idx):
                continue

            entry, stop, target, zone_top, zone_bottom = _rr_targets(entry_points, bullish)
            entry = float(close.iloc[signal_idx])
            if bullish:
                stop = min(float(p["price"]) for p in entry_points)
                risk = max(entry - stop, 1e-9)
                target = max(zone_top + (zone_top - zone_bottom), entry + risk * 1.5)
            else:
                stop = max(float(p["price"]) for p in entry_points)
                risk = max(stop - entry, 1e-9)
                target = min(zone_bottom - (zone_top - zone_bottom), entry - risk * 1.5)
            risk = abs(entry - stop)
            rr = abs(target - entry) / risk if risk > 0 else 0.0
            if rr < 1.0:
                continue

            point_payload = []
            for label, point in zip(["A", "B", "2", "3", "4"], entry_points):
                point_payload.append({
                    "label": label,
                    "index": int(point["index"]),
                    "time": _time_str(idx, int(point["index"]), intraday),
                    "price": round(float(point["price"]), 4),
                    "kind": point["kind"],
                })

            seen_entries.add(signal_idx)
            sequences.append({
                "time": _time_str(idx, signal_idx, intraday),
                "name": "Swing Break Long" if bullish else "Swing Break Short",
                "direction": "bull" if bullish else "bear",
                "index": int(signal_idx),
                "entry_index": int(entry_idx),
                "confirmed_index": int(signal_idx),
                "entry": round(float(entry), 4),
                "stop": round(float(stop), 4),
                "target": round(float(target), 4),
                "risk_reward": round(float(rr), 2),
                "zone_top": round(float(zone_top), 4),
                "zone_bottom": round(float(zone_bottom), 4),
                "points": point_payload,
            })

        clean = _sanitize_events(sequences)
        return {
            "signals": clean,
            "sequences": clean[-40:],
            "params": {
                "swing_length": swing_length,
                "internal_length": internal_length,
                "strict_threshold": strict_threshold,
            },
        }
    except Exception:
        return {}


def bahai_reversal_markers(df: pd.DataFrame) -> list:
    """Baha'i Reversal Points [CC] markers using the Pine-compatible 19/9 logic."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"high", "low"}.issubset(work.columns):
            return []

        length = 19
        lb_length = 9
        h = work["high"].astype(float)
        l = work["low"].astype(float)

        low_lb = l.shift(lb_length).fillna(0)
        high_lb = h.shift(lb_length).fillna(0)
        lp_sum = (l < low_lb).rolling(window=length, min_periods=length).sum()
        hp_sum = (h > high_lb).rolling(window=length, min_periods=length).sum()

        slo = pd.Series(
            np.where(lp_sum >= length, 1, np.where(hp_sum >= length, -1, 0)),
            index=work.index,
        )
        slo_prev = slo.shift(1).fillna(0)
        sig = pd.Series(0, index=work.index, dtype=int)
        sig[(slo > 0) & (slo > slo_prev)] = 2
        sig[(slo > 0) & (slo <= slo_prev)] = 1
        sig[(slo < 0) & (slo < slo_prev)] = -2
        sig[(slo < 0) & (slo >= slo_prev)] = -1

        shape_buy = (slo > 0) & (slo_prev <= 0)
        shape_sell = (slo < 0) & (slo_prev >= 0)

        intraday = _is_intraday(work)
        idx = work.index
        events = []
        for i in range(len(work)):
            if i < _WARMUP_BARS or (intraday and _is_session_open_bar(idx, i)):
                continue
            if bool(shape_buy.iloc[i]):
                events.append({
                    "time": _time_str(idx, i, intraday),
                    "name": "Bahai Buy",
                    "direction": "bull",
                    "index": i,
                    "slo": int(slo.iloc[i]),
                    "sig": int(sig.iloc[i]),
                    "lpSum": int(lp_sum.iloc[i]) if lp_sum.iloc[i] == lp_sum.iloc[i] else None,
                    "hpSum": int(hp_sum.iloc[i]) if hp_sum.iloc[i] == hp_sum.iloc[i] else None,
                })
            elif bool(shape_sell.iloc[i]):
                events.append({
                    "time": _time_str(idx, i, intraday),
                    "name": "Bahai Sell",
                    "direction": "bear",
                    "index": i,
                    "slo": int(slo.iloc[i]),
                    "sig": int(sig.iloc[i]),
                    "lpSum": int(lp_sum.iloc[i]) if lp_sum.iloc[i] == lp_sum.iloc[i] else None,
                    "hpSum": int(hp_sum.iloc[i]) if hp_sum.iloc[i] == hp_sum.iloc[i] else None,
                })
        return _sanitize_events(events)
    except Exception:
        return []


def sfp_hybrid_markers(df: pd.DataFrame, trend_fast_len: int = 9, trend_slow_len: int = 18,
                       trend_filter_type: str = "EMA") -> dict:
    """Hybrid SFP: ICT sweep + opposing price state + dual trend filter."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {"signals": []}
        n = len(work)
        if n < 25:
            return {"signals": []}

        trend_fast_len = max(1, int(trend_fast_len))
        trend_slow_len = max(trend_fast_len, int(trend_slow_len))
        intraday = _is_intraday(work)
        idx = work.index
        h = work["high"].astype(float)
        l = work["low"].astype(float)
        o = work["open"].astype(float)
        c = work["close"].astype(float)
        vol = work["volume"].astype(float) if "volume" in work.columns else pd.Series(1.0, index=work.index)
        if isinstance(idx, pd.DatetimeIndex) and n > 1:
            minutes = max(1, round((idx[1] - idx[0]).total_seconds() / 60))
            swing_period = 5 if minutes <= 5 else 8 if minutes <= 30 else 13 if minutes <= 90 else 21
        else:
            swing_period = 21

        def _wma(series: pd.Series, length: int) -> pd.Series:
            weights = np.arange(1, length + 1)
            return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

        def _hma(series: pd.Series, length: int) -> pd.Series:
            half = max(1, int(length / 2))
            root = max(1, int(np.sqrt(length)))
            return _wma(2 * _wma(series, half) - _wma(series, length), root)

        def _vwap() -> pd.Series:
            typical = (h + l + c) / 3
            if isinstance(idx, pd.DatetimeIndex):
                day = pd.Series(idx.date, index=idx)
                tpv = (typical * vol).groupby(day).cumsum()
                vv = vol.groupby(day).cumsum()
                return tpv / vv.replace(0, np.nan)
            return (typical * vol).cumsum() / vol.cumsum().replace(0, np.nan)

        ftype = str(trend_filter_type or "EMA").upper()
        if ftype == "OFF":
            trend_fast = pd.Series(np.nan, index=work.index)
            trend_slow = pd.Series(np.nan, index=work.index)
            uptrend = pd.Series(True, index=work.index)
            downtrend = pd.Series(True, index=work.index)
        elif ftype == "SMA":
            trend_fast = c.rolling(trend_fast_len).mean()
            trend_slow = c.rolling(trend_slow_len).mean()
            uptrend = (c > trend_fast) & (c > trend_slow)
            downtrend = (c < trend_fast) & (c < trend_slow)
        elif ftype == "HMA":
            trend_fast = _hma(c, trend_fast_len)
            trend_slow = _hma(c, trend_slow_len)
            uptrend = (c > trend_fast) & (c > trend_slow)
            downtrend = (c < trend_fast) & (c < trend_slow)
        elif ftype == "VWAP":
            trend_fast = _vwap()
            trend_slow = trend_fast
            uptrend = c > trend_fast
            downtrend = c < trend_fast
        else:
            trend_fast = c.ewm(span=trend_fast_len, adjust=False).mean()
            trend_slow = c.ewm(span=trend_slow_len, adjust=False).mean()
            uptrend = (c > trend_fast) & (c > trend_slow)
            downtrend = (c < trend_fast) & (c < trend_slow)

        tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(55, min_periods=1).mean()
        swing_high = pd.Series(False, index=work.index)
        swing_low = pd.Series(False, index=work.index)
        for i in range(swing_period, n - swing_period):
            swing_high.iloc[i] = bool(h.iloc[i] == h.iloc[i - swing_period:i + swing_period + 1].max() and h.iloc[max(0, i - swing_period)] != h.iloc[i])
            swing_low.iloc[i] = bool(l.iloc[i] == l.iloc[i - swing_period:i + swing_period + 1].min() and l.iloc[max(0, i - swing_period)] != l.iloc[i])

        def _is_doji(i: int) -> bool:
            rng = h.iloc[i] - l.iloc[i]
            return bool(rng > 0 and abs(c.iloc[i] - o.iloc[i]) / rng <= 0.4)

        highs, lows, events = [], [], []
        for i in range(n):
            if bool(swing_high.iloc[i]):
                start = max(0, i - 500)
                highs.append({"price": float(h.iloc[i]), "open": float(o.iloc[i]), "close": float(c.iloc[i]), "opposing": float(l.iloc[start:i].min()) if i > start else float(l.iloc[i]), "index": i, "permit": True, "aoi": -1, "active": True, "confirmed": False})
            if bool(swing_low.iloc[i]):
                start = max(0, i - 500)
                lows.append({"price": float(l.iloc[i]), "open": float(o.iloc[i]), "close": float(c.iloc[i]), "opposing": float(h.iloc[start:i].max()) if i > start else float(h.iloc[i]), "index": i, "permit": True, "aoi": -1, "active": True, "confirmed": False})
            highs = highs[-100:]
            lows = lows[-100:]
            if i < _WARMUP_BARS or (intraday and _is_session_open_bar(idx, i)):
                continue

            for swing in reversed(highs):
                if not swing["permit"] or i - swing["index"] > 50:
                    continue
                if swing["active"] and not swing["confirmed"]:
                    if c.iloc[i] < swing["opposing"]:
                        swing["confirmed"] = True
                        swing["active"] = False
                    elif i - swing["index"] > 500 or c.iloc[i] > swing["price"]:
                        swing["active"] = False
                if swing["price"] < h.iloc[i] and swing["price"] > c.iloc[i] and swing["aoi"] == -1:
                    if _is_doji(i) and c.iloc[i] < swing["price"] and c.iloc[i] > swing["opposing"] and bool(downtrend.iloc[i]):
                        events.append({"time": _time_str(idx, i, intraday), "name": "SFB Hybrid Short", "direction": "bear", "index": i, "sweep_level": round(float(swing["price"]), 4), "swing_index": int(swing["index"]), "atr": round(float(atr.iloc[i]), 4) if atr.iloc[i] == atr.iloc[i] else None})
                        swing["permit"] = False
                        break
                if c.iloc[i] > swing["price"] and swing["aoi"] == -1:
                    swing["aoi"] = i

            for swing in reversed(lows):
                if not swing["permit"] or i - swing["index"] > 50:
                    continue
                if swing["active"] and not swing["confirmed"]:
                    if c.iloc[i] > swing["opposing"]:
                        swing["confirmed"] = True
                        swing["active"] = False
                    elif i - swing["index"] > 500 or c.iloc[i] < swing["price"]:
                        swing["active"] = False
                if swing["price"] > l.iloc[i] and swing["price"] < c.iloc[i] and swing["aoi"] == -1:
                    if _is_doji(i) and c.iloc[i] > swing["price"] and c.iloc[i] < swing["opposing"] and bool(uptrend.iloc[i]):
                        events.append({"time": _time_str(idx, i, intraday), "name": "SFB Hybrid Long", "direction": "bull", "index": i, "sweep_level": round(float(swing["price"]), 4), "swing_index": int(swing["index"]), "atr": round(float(atr.iloc[i]), 4) if atr.iloc[i] == atr.iloc[i] else None})
                        swing["permit"] = False
                        break
                if c.iloc[i] < swing["price"] and swing["aoi"] == -1:
                    swing["aoi"] = i

        return {
            "signals": _sanitize_events(events),
            "trend_fast": [round(float(v), 4) if v == v else None for v in trend_fast.tolist()],
            "trend_slow": [round(float(v), 4) if v == v else None for v in trend_slow.tolist()],
            "params": {"trend_fast_len": trend_fast_len, "trend_slow_len": trend_slow_len, "trend_filter_type": ftype, "swing_period": swing_period},
        }
    except Exception:
        return {"signals": []}


def ctz_gann_swing(df: pd.DataFrame, label_layer: str = "F2", min_swing_pct: float = 1.5,
                   use_atr: bool = False, atr_len: int = 14, atr_mult: float = 0.5,
                   use_rsi: bool = False, rsi_len: int = 14, rsi_bull: float = 40.0,
                   rsi_bear: float = 60.0, use_qtrend: bool = False,
                   qtrend_period: int = 200, qtrend_mult: float = 1.0) -> dict:
    """CTZ Gann Swing multi-layer structure, labels, MSB, and SMCD marker payload."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {"signals": []}
        n = len(work)
        if n < 40:
            return {"signals": []}

        idx = work.index
        intraday = _is_intraday(work)
        h = work["high"].astype(float)
        l = work["low"].astype(float)
        c = work["close"].astype(float)
        v = work["volume"].astype(float) if "volume" in work.columns else pd.Series(1.0, index=idx)

        tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(atr_len, min_periods=1).mean()
        atr_base = atr.rolling(10, min_periods=1).mean()
        atr_ok = pd.Series(True, index=idx) if not use_atr else (atr >= atr_base * atr_mult)

        delta = c.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / max(1, rsi_len), adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / max(1, rsi_len), adjust=False).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        rsi = rsi.fillna(50)
        rsi_bull_ok = pd.Series(True, index=idx) if not use_rsi else (rsi <= rsi_bull)
        rsi_bear_ok = pd.Series(True, index=idx) if not use_rsi else (rsi >= rsi_bear)

        q_mid = c.rolling(qtrend_period, min_periods=1).mean()
        q_eps = atr.rolling(20, min_periods=1).mean() * qtrend_mult
        q_bias = pd.Series("N", index=idx)
        q_bias[c > q_mid + q_eps] = "B"
        q_bias[c < q_mid - q_eps] = "S"
        qtrend_bull = pd.Series(True, index=idx) if not use_qtrend else (q_bias == "B")
        qtrend_bear = pd.Series(True, index=idx) if not use_qtrend else (q_bias == "S")

        layer_lengths = {"F1": 3, "SF1": 5, "F2": 8, "SF2": 13, "F3": 21, "SF3": 34}

        def _confirmed_pivots(left: int) -> list[dict]:
            right = left
            out = []
            for piv in range(left, n - right):
                hi_win = h.iloc[piv - left:piv + right + 1]
                lo_win = l.iloc[piv - left:piv + right + 1]
                confirm = piv + right
                if h.iloc[piv] == hi_win.max():
                    out.append({"pivot": piv, "confirm": confirm, "price": float(h.iloc[piv]), "kind": "high"})
                if l.iloc[piv] == lo_win.min():
                    out.append({"pivot": piv, "confirm": confirm, "price": float(l.iloc[piv]), "kind": "low"})
            return sorted(out, key=lambda x: (x["confirm"], x["pivot"], x["kind"]))

        layers = {}
        layer_points = {}
        for layer, length in layer_lengths.items():
            vals = [None] * n
            points = []
            last_kind = None
            for p in _confirmed_pivots(length):
                # Collapse same-kind continuation pivots into the more extreme point.
                if points and p["kind"] == last_kind:
                    replace = (p["kind"] == "high" and p["price"] >= points[-1]["price"]) or (p["kind"] == "low" and p["price"] <= points[-1]["price"])
                    if replace:
                        points[-1] = p
                        vals[p["confirm"]] = round(p["price"], 4)
                    continue
                points.append(p)
                last_kind = p["kind"]
                vals[p["confirm"]] = round(p["price"], 4)
            layers[layer] = vals
            layer_points[layer] = points

        events = []
        long_sig = [False] * n
        short_sig = [False] * n
        target = layer_points.get(str(label_layer).upper(), layer_points["F2"])
        last_label = {"BUY": -10**9, "SELL": -10**9}
        for prev, curr in zip(target, target[1:]):
            i = curr["confirm"]
            if i < _WARMUP_BARS or (intraday and _is_session_open_bar(idx, i)):
                continue
            base = abs(prev["price"]) if prev["price"] else 1.0
            swing_pct = abs(curr["price"] - prev["price"]) / base * 100
            if swing_pct < float(min_swing_pct):
                continue
            if curr["price"] > prev["price"] and bool(atr_ok.iloc[i]) and bool(rsi_bull_ok.iloc[i]) and bool(qtrend_bull.iloc[i]):
                if i - last_label["BUY"] >= _MARKER_COOLDOWN_BARS:
                    events.append({"time": _time_str(idx, i, intraday), "name": "CTZ Buy", "direction": "bull", "index": i, "layer": label_layer, "swing_pct": round(float(swing_pct), 2), "price": round(float(curr["price"]), 4)})
                    long_sig[i] = True
                    last_label["BUY"] = i
            elif curr["price"] < prev["price"] and bool(atr_ok.iloc[i]) and bool(rsi_bear_ok.iloc[i]) and bool(qtrend_bear.iloc[i]):
                if i - last_label["SELL"] >= _MARKER_COOLDOWN_BARS:
                    events.append({"time": _time_str(idx, i, intraday), "name": "CTZ Sell", "direction": "bear", "index": i, "layer": label_layer, "swing_pct": round(float(swing_pct), 2), "price": round(float(curr["price"]), 4)})
                    short_sig[i] = True
                    last_label["SELL"] = i

        # ChoCh/MSB from the target layer's latest swing levels.
        swing_high_ref = pd.Series(np.nan, index=idx)
        swing_low_ref = pd.Series(np.nan, index=idx)
        for p in target:
            if p["kind"] == "high":
                swing_high_ref.iloc[p["confirm"]] = p["price"]
            else:
                swing_low_ref.iloc[p["confirm"]] = p["price"]
        swing_high_ref = swing_high_ref.ffill()
        swing_low_ref = swing_low_ref.ffill()
        msb_bull = (c > swing_high_ref.shift(1)) & atr_ok
        msb_bear = (c < swing_low_ref.shift(1)) & atr_ok
        last_msb = {"bull": -10**9, "bear": -10**9}
        for i in range(_WARMUP_BARS, n):
            if intraday and _is_session_open_bar(idx, i):
                continue
            if bool(msb_bull.iloc[i]) and i - last_msb["bull"] >= _MARKER_COOLDOWN_BARS:
                events.append({"time": _time_str(idx, i, intraday), "name": "CTZ MSB Bull", "direction": "bull", "index": i, "price": round(float(c.iloc[i]), 4)})
                last_msb["bull"] = i
            elif bool(msb_bear.iloc[i]) and i - last_msb["bear"] >= _MARKER_COOLDOWN_BARS:
                events.append({"time": _time_str(idx, i, intraday), "name": "CTZ MSB Bear", "direction": "bear", "index": i, "price": round(float(c.iloc[i]), 4)})
                last_msb["bear"] = i

        # SMCD approximation: RSI divergence on confirmed F1 pivots with volume spike.
        vol_ma = v.rolling(14, min_periods=1).mean()
        vol_spike = v > vol_ma * 1.5
        lows_seen, highs_seen = [], []
        for p in layer_points["F1"]:
            i = p["confirm"]
            if i < _WARMUP_BARS:
                continue
            if p["kind"] == "low":
                if lows_seen and p["price"] < lows_seen[-1]["price"] and rsi.iloc[p["pivot"]] > lows_seen[-1]["rsi"] and bool(vol_spike.iloc[i]):
                    events.append({"time": _time_str(idx, i, intraday), "name": "CTZ SMCD Bull", "direction": "bull", "index": i, "price": round(float(p["price"]), 4)})
                lows_seen.append({"price": p["price"], "rsi": float(rsi.iloc[p["pivot"]])})
            else:
                if highs_seen and p["price"] > highs_seen[-1]["price"] and rsi.iloc[p["pivot"]] < highs_seen[-1]["rsi"] and bool(vol_spike.iloc[i]):
                    events.append({"time": _time_str(idx, i, intraday), "name": "CTZ SMCD Bear", "direction": "bear", "index": i, "price": round(float(p["price"]), 4)})
                highs_seen.append({"price": p["price"], "rsi": float(rsi.iloc[p["pivot"]])})

        return {
            "signals": _sanitize_events(events),
            "long": long_sig,
            "short": short_sig,
            "layers": layers,
            "q_mid": [round(float(x), 4) if x == x else None for x in q_mid.tolist()],
            "rsi": [round(float(x), 2) if x == x else None for x in rsi.tolist()],
            "params": {"label_layer": label_layer, "min_swing_pct": min_swing_pct},
        }
    except Exception:
        return {"signals": []}


def opening_range_reversal(df: pd.DataFrame, or_start: str = "09:30", or_end: str = "10:00",
                           entry_start: str = "10:00", entry_end: str = "11:30",
                           l1_mult: float = 1.272, one_trade_per_day: bool = True) -> dict:
    """Opening Range Reversal red-entry strategy: enter at OR High/Low, TP at L1 midpoint."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {"signals": []}
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {"signals": []}
        n = len(work)
        if n < 20:
            return {"signals": []}

        def _parse_t(value: str) -> tuple[int, int]:
            hh, mm = str(value).split(":")[:2]
            return int(hh), int(mm)

        def _mins(ts) -> int:
            return int(ts.hour) * 60 + int(ts.minute)

        def _in_window(ts, start: str, end: str) -> bool:
            sh, sm = _parse_t(start)
            eh, em = _parse_t(end)
            cur = _mins(ts)
            a = sh * 60 + sm
            b = eh * 60 + em
            return (a <= cur < b) if a <= b else (cur >= a or cur < b)

        idx = work.index
        intraday = _is_intraday(work)
        h = work["high"].astype(float)
        l = work["low"].astype(float)
        c = work["close"].astype(float)

        or_high_series = [None] * n
        or_low_series = [None] * n
        tp_series = [None] * n
        sl_series = [None] * n
        l1_up_series = [None] * n
        l1_dn_series = [None] * n
        long_sig = [False] * n
        short_sig = [False] * n
        exit_sig = [False] * n
        events = []
        trades = []

        cur_day = None
        or_high = None
        or_low = None
        l1_up = None
        l1_dn = None
        tp = None
        traded = False
        active = None

        for i, ts in enumerate(idx):
            day = ts.date()
            if cur_day != day:
                if active is not None:
                    active["exit_index"] = i - 1
                    active["exit_time"] = _time_str(idx, i - 1, intraday)
                    active["exit_price"] = round(float(c.iloc[i - 1]), 4)
                    active["exit_reason"] = "eod"
                    active["pnl"] = round((active["exit_price"] - active["entry_price"]) if active["direction"] == "long" else (active["entry_price"] - active["exit_price"]), 4)
                    trades.append(active)
                    active = None
                cur_day = day
                or_high = None
                or_low = None
                l1_up = None
                l1_dn = None
                tp = None
                traded = False

            if _in_window(ts, or_start, or_end):
                or_high = float(h.iloc[i]) if or_high is None else max(or_high, float(h.iloc[i]))
                or_low = float(l.iloc[i]) if or_low is None else min(or_low, float(l.iloc[i]))

            if not _in_window(ts, or_start, or_end) and or_high is not None and or_low is not None and tp is None:
                or_range = or_high - or_low
                if or_range > 0:
                    l1_up = or_low + or_range * float(l1_mult)
                    l1_dn = or_high - or_range * float(l1_mult)
                    tp = (l1_up + l1_dn) / 2

            if or_high is not None:
                or_high_series[i] = round(float(or_high), 4)
            if or_low is not None:
                or_low_series[i] = round(float(or_low), 4)
            if tp is not None:
                tp_series[i] = round(float(tp), 4)
                l1_up_series[i] = round(float(l1_up), 4)
                l1_dn_series[i] = round(float(l1_dn), 4)

            if active is None and tp is not None and _in_window(ts, entry_start, entry_end) and (not one_trade_per_day or not traded):
                if float(l.iloc[i]) <= or_low:
                    entry = or_low
                    sl = or_low - (tp - or_low)
                    active = {"entry_index": i, "entry_time": _time_str(idx, i, intraday), "direction": "long", "entry_price": round(float(entry), 4), "tp_price": round(float(tp), 4), "sl_price": round(float(sl), 4)}
                    long_sig[i] = True
                    traded = True
                    sl_series[i] = round(float(sl), 4)
                    events.append({"time": _time_str(idx, i, intraday), "name": "ORR Long", "direction": "bull", "index": i, "entry": round(float(entry), 4), "tp": round(float(tp), 4), "sl": round(float(sl), 4), "or_high": round(float(or_high), 4), "or_low": round(float(or_low), 4)})
                elif float(h.iloc[i]) >= or_high:
                    entry = or_high
                    sl = or_high + (or_high - tp)
                    active = {"entry_index": i, "entry_time": _time_str(idx, i, intraday), "direction": "short", "entry_price": round(float(entry), 4), "tp_price": round(float(tp), 4), "sl_price": round(float(sl), 4)}
                    short_sig[i] = True
                    traded = True
                    sl_series[i] = round(float(sl), 4)
                    events.append({"time": _time_str(idx, i, intraday), "name": "ORR Short", "direction": "bear", "index": i, "entry": round(float(entry), 4), "tp": round(float(tp), 4), "sl": round(float(sl), 4), "or_high": round(float(or_high), 4), "or_low": round(float(or_low), 4)})

            if active is not None:
                sl_series[i] = active["sl_price"]
                exited = False
                if active["direction"] == "long":
                    if float(h.iloc[i]) >= active["tp_price"]:
                        reason, exit_price = "tp", active["tp_price"]
                        exited = True
                    elif float(l.iloc[i]) <= active["sl_price"]:
                        reason, exit_price = "sl", active["sl_price"]
                        exited = True
                else:
                    if float(l.iloc[i]) <= active["tp_price"]:
                        reason, exit_price = "tp", active["tp_price"]
                        exited = True
                    elif float(h.iloc[i]) >= active["sl_price"]:
                        reason, exit_price = "sl", active["sl_price"]
                        exited = True
                if exited:
                    active["exit_index"] = i
                    active["exit_time"] = _time_str(idx, i, intraday)
                    active["exit_price"] = round(float(exit_price), 4)
                    active["exit_reason"] = reason
                    active["pnl"] = round((exit_price - active["entry_price"]) if active["direction"] == "long" else (active["entry_price"] - exit_price), 4)
                    trades.append(active)
                    exit_sig[i] = True
                    events.append({"time": _time_str(idx, i, intraday), "name": f"ORR Exit {reason.upper()}", "direction": "neutral", "index": i, "price": round(float(exit_price), 4), "result": reason})
                    active = None

        if active is not None:
            active["exit_index"] = n - 1
            active["exit_time"] = _time_str(idx, n - 1, intraday)
            active["exit_price"] = round(float(c.iloc[-1]), 4)
            active["exit_reason"] = "eod"
            active["pnl"] = round((active["exit_price"] - active["entry_price"]) if active["direction"] == "long" else (active["entry_price"] - active["exit_price"]), 4)
            trades.append(active)

        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "long": long_sig,
            "short": short_sig,
            "exit": exit_sig,
            "or_high": or_high_series,
            "or_low": or_low_series,
            "tp": tp_series,
            "sl": sl_series,
            "l1_up": l1_up_series,
            "l1_dn": l1_dn_series,
            "trades": trades[-200:],
            "params": {"or_start": or_start, "or_end": or_end, "entry_start": entry_start, "entry_end": entry_end, "l1_mult": l1_mult},
        }
    except Exception:
        return {"signals": []}


def hyb_opening_range_reversal(
    df: pd.DataFrame,
    or_start: str = "09:30",
    or_end: str = "10:00",
    entry_start: str = "10:00",
    entry_end: str = "11:30",
    l1_mult: float = 1.272,
    or_min_pct: float = 0.0015,
    or_max_pct: float = 0.025,
    volume_mult: float = 1.5,
    atr_min_mult: float = 0.7,
    use_vwap_filter: bool = True,
    use_rsi_filter: bool = True,
    rsi_long_min: float = 30.0,
    rsi_long_max: float = 65.0,
    rsi_short_min: float = 35.0,
    rsi_short_max: float = 70.0,
    max_attempts_per_day: int = 2,
    cooldown_bars: int = 5,
    consecutive_loss_cooldown: int = 2,
    one_trade_per_day: bool = True,
) -> dict:
    """Hybrid Opening Range Reversal: red-entry ORR plus volume/ATR/VWAP/RSI/cooldown filters."""
    try:
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex):
            return {"signals": []}
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {"signals": []}
        n = len(work)
        if n < 20:
            return {"signals": []}

        def _parse_t(value: str) -> tuple[int, int]:
            hh, mm = str(value).split(":")[:2]
            return int(hh), int(mm)

        def _mins(ts) -> int:
            return int(ts.hour) * 60 + int(ts.minute)

        def _in_window(ts, start: str, end: str) -> bool:
            sh, sm = _parse_t(start)
            eh, em = _parse_t(end)
            cur = _mins(ts)
            a = sh * 60 + sm
            b = eh * 60 + em
            return (a <= cur < b) if a <= b else (cur >= a or cur < b)

        idx = work.index
        intraday = _is_intraday(work)
        h = work["high"].astype(float)
        l = work["low"].astype(float)
        c = work["close"].astype(float)
        v = work["volume"].astype(float) if "volume" in work.columns else pd.Series(1.0, index=idx)

        typical = (h + l + c) / 3
        day_key = pd.Series(idx.date, index=idx)
        vwap = (typical * v).groupby(day_key).cumsum() / v.groupby(day_key).cumsum().replace(0, np.nan)
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        rsi = rsi.fillna(50)
        tr = pd.concat([(h - l), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14, min_periods=1).mean()
        atr20 = tr.rolling(20, min_periods=1).mean()

        def _score(direction: str, i: int, or_avg_vol: float) -> tuple[bool, list[str], float, str]:
            filters = []
            score = 35.0
            if or_avg_vol > 0 and float(v.iloc[i]) < or_avg_vol * float(volume_mult):
                return False, [], 0.0, "volume"
            filters.append("volume")
            score += 15

            if atr.iloc[i] == atr.iloc[i] and atr20.iloc[i] == atr20.iloc[i] and float(atr.iloc[i]) < float(atr20.iloc[i]) * float(atr_min_mult):
                return False, [], 0.0, "atr"
            filters.append("atr")
            score += 15

            if use_vwap_filter and vwap.iloc[i] == vwap.iloc[i]:
                if direction == "long" and float(c.iloc[i]) < float(vwap.iloc[i]):
                    return False, [], 0.0, "vwap"
                if direction == "short" and float(c.iloc[i]) > float(vwap.iloc[i]):
                    return False, [], 0.0, "vwap"
                filters.append("vwap")
                score += 20

            if use_rsi_filter and rsi.iloc[i] == rsi.iloc[i]:
                rv = float(rsi.iloc[i])
                if direction == "long" and not (float(rsi_long_min) <= rv <= float(rsi_long_max)):
                    return False, [], 0.0, "rsi"
                if direction == "short" and not (float(rsi_short_min) <= rv <= float(rsi_short_max)):
                    return False, [], 0.0, "rsi"
                filters.append("rsi")
                score += 15
            return True, filters, min(score, 100.0), ""

        or_high_series = [None] * n
        or_low_series = [None] * n
        tp_series = [None] * n
        sl_series = [None] * n
        l1_up_series = [None] * n
        l1_dn_series = [None] * n
        quality_series = [None] * n
        long_sig = [False] * n
        short_sig = [False] * n
        exit_sig = [False] * n
        events = []
        trades = []
        rejected = []

        cur_day = None
        or_high = or_low = l1_up = l1_dn = tp = None
        traded = False
        active = None
        or_volumes = []
        attempts_today = 0
        last_attempt_i = -10**9
        consecutive_losses = 0
        skip_day = None

        for i, ts in enumerate(idx):
            day = ts.date()
            if cur_day != day:
                if active is not None:
                    active["exit_index"] = i - 1
                    active["exit_time"] = _time_str(idx, i - 1, intraday)
                    active["exit_price"] = round(float(c.iloc[i - 1]), 4)
                    active["exit_reason"] = "eod"
                    active["pnl"] = round((active["exit_price"] - active["entry_price"]) if active["direction"] == "long" else (active["entry_price"] - active["exit_price"]), 4)
                    trades.append(active)
                    active = None
                cur_day = day
                or_high = or_low = l1_up = l1_dn = tp = None
                traded = False
                or_volumes = []
                attempts_today = 0

            if _in_window(ts, or_start, or_end):
                or_high = float(h.iloc[i]) if or_high is None else max(or_high, float(h.iloc[i]))
                or_low = float(l.iloc[i]) if or_low is None else min(or_low, float(l.iloc[i]))
                or_volumes.append(float(v.iloc[i]))

            if not _in_window(ts, or_start, or_end) and or_high is not None and or_low is not None and tp is None:
                or_range = or_high - or_low
                mid_price = (or_high + or_low) / 2
                or_pct = or_range / mid_price if mid_price else 0
                if or_range > 0 and float(or_min_pct) <= or_pct <= float(or_max_pct):
                    l1_up = or_low + or_range * float(l1_mult)
                    l1_dn = or_high - or_range * float(l1_mult)
                    tp = (l1_up + l1_dn) / 2
                else:
                    rejected.append({"time": _time_str(idx, i, intraday), "direction": "range", "index": i, "reason": "or_size", "or_pct": round(float(or_pct), 6)})
                    or_high = None
                    or_low = None

            if or_high is not None:
                or_high_series[i] = round(float(or_high), 4)
            if or_low is not None:
                or_low_series[i] = round(float(or_low), 4)
            if tp is not None:
                tp_series[i] = round(float(tp), 4)
                l1_up_series[i] = round(float(l1_up), 4)
                l1_dn_series[i] = round(float(l1_dn), 4)

            can_try = (
                active is None and tp is not None and _in_window(ts, entry_start, entry_end)
                and (not one_trade_per_day or not traded)
                and attempts_today < int(max_attempts_per_day)
                and i - last_attempt_i >= int(cooldown_bars)
                and skip_day != day
            )

            if can_try:
                or_avg_vol = float(np.mean(or_volumes)) if or_volumes else 0.0
                setup = None
                entry = sl = None
                if float(l.iloc[i]) <= or_low:
                    setup = "long"
                    entry = or_low
                    sl = or_low - (tp - or_low)
                elif float(h.iloc[i]) >= or_high:
                    setup = "short"
                    entry = or_high
                    sl = or_high + (or_high - tp)

                if setup:
                    passed, filters, score, reason = _score(setup, i, or_avg_vol)
                    if not passed:
                        rejected.append({"time": _time_str(idx, i, intraday), "direction": setup, "index": i, "price": round(float(entry), 4), "reason": reason})
                    else:
                        active = {"entry_index": i, "entry_time": _time_str(idx, i, intraday), "direction": setup, "entry_price": round(float(entry), 4), "tp_price": round(float(tp), 4), "sl_price": round(float(sl), 4), "filters": filters, "quality_score": round(float(score), 1)}
                        attempts_today += 1
                        last_attempt_i = i
                        traded = True
                        quality_series[i] = round(float(score), 1)
                        sl_series[i] = round(float(sl), 4)
                        if setup == "long":
                            long_sig[i] = True
                            direction = "bull"
                            name = "Hyb ORR Long"
                        else:
                            short_sig[i] = True
                            direction = "bear"
                            name = "Hyb ORR Short"
                        events.append({"time": _time_str(idx, i, intraday), "name": name, "direction": direction, "index": i, "entry": round(float(entry), 4), "tp": round(float(tp), 4), "sl": round(float(sl), 4), "quality": round(float(score), 1), "filters": ",".join(filters), "or_high": round(float(or_high), 4), "or_low": round(float(or_low), 4)})

            if active is not None:
                sl_series[i] = active["sl_price"]
                quality_series[i] = active["quality_score"]
                exited = False
                if active["direction"] == "long":
                    if float(h.iloc[i]) >= active["tp_price"]:
                        reason, exit_price = "tp", active["tp_price"]
                        exited = True
                    elif float(l.iloc[i]) <= active["sl_price"]:
                        reason, exit_price = "sl", active["sl_price"]
                        exited = True
                else:
                    if float(l.iloc[i]) <= active["tp_price"]:
                        reason, exit_price = "tp", active["tp_price"]
                        exited = True
                    elif float(h.iloc[i]) >= active["sl_price"]:
                        reason, exit_price = "sl", active["sl_price"]
                        exited = True
                if exited:
                    active["exit_index"] = i
                    active["exit_time"] = _time_str(idx, i, intraday)
                    active["exit_price"] = round(float(exit_price), 4)
                    active["exit_reason"] = reason
                    active["pnl"] = round((exit_price - active["entry_price"]) if active["direction"] == "long" else (active["entry_price"] - exit_price), 4)
                    if reason == "sl":
                        consecutive_losses += 1
                        if consecutive_losses >= int(consecutive_loss_cooldown):
                            skip_day = day
                    else:
                        consecutive_losses = 0
                    trades.append(active)
                    exit_sig[i] = True
                    events.append({"time": _time_str(idx, i, intraday), "name": f"Hyb ORR Exit {reason.upper()}", "direction": "neutral", "index": i, "price": round(float(exit_price), 4), "result": reason, "quality": active["quality_score"]})
                    active = None

        if active is not None:
            active["exit_index"] = n - 1
            active["exit_time"] = _time_str(idx, n - 1, intraday)
            active["exit_price"] = round(float(c.iloc[-1]), 4)
            active["exit_reason"] = "eod"
            active["pnl"] = round((active["exit_price"] - active["entry_price"]) if active["direction"] == "long" else (active["entry_price"] - active["exit_price"]), 4)
            trades.append(active)

        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "long": long_sig,
            "short": short_sig,
            "exit": exit_sig,
            "or_high": or_high_series,
            "or_low": or_low_series,
            "tp": tp_series,
            "sl": sl_series,
            "l1_up": l1_up_series,
            "l1_dn": l1_dn_series,
            "quality": quality_series,
            "vwap": [round(float(x), 4) if x == x else None for x in vwap.tolist()],
            "rsi": [round(float(x), 2) if x == x else None for x in rsi.tolist()],
            "atr": [round(float(x), 4) if x == x else None for x in atr.tolist()],
            "trades": trades[-200:],
            "rejected": rejected[-200:],
            "params": {"or_start": or_start, "or_end": or_end, "entry_start": entry_start, "entry_end": entry_end, "l1_mult": l1_mult, "volume_mult": volume_mult, "atr_min_mult": atr_min_mult},
        }
    except Exception:
        return {"signals": []}


@dataclass
class HybridMlCprConfig:
    enable_global_ml: bool = True
    ml_min_confidence: float = 50.0
    ml_learning_window: int = 150
    ml_adaptation_rate: float = 0.08
    entry_mode: str = "close"


@dataclass
class HybridMlCprWeights:
    w_price: float = 1.0
    w_volume: float = 1.0
    w_trend: float = 1.0
    w_volatility: float = 1.0
    w_momentum: float = 1.0
    w_delta: float = 1.0
    w_confluence: float = 1.0
    w_pattern: float = 1.0
    w_time: float = 1.0
    w_vwap: float = 1.0


@dataclass
class HybridMlCprFeatures:
    price_position: float = 0.5
    volume_strength: float = 1.0
    trend_alignment: float = 0.0
    volatility: float = 0.5
    momentum: float = 0.0
    delta_pressure: float = 0.0
    confluence_score: float = 0.0
    pattern_strength: float = 0.3
    time_factor: float = 1.0
    vwap_distance: float = 0.5


def _hybrid_ml_cpr_rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1 / length, adjust=False).mean()


def _hybrid_ml_cpr_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return _hybrid_ml_cpr_rma(tr, length)


def _hybrid_ml_cpr_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = _hybrid_ml_cpr_rma(gain, length)
    avg_loss = _hybrid_ml_cpr_rma(loss, length)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def _hybrid_ml_cpr_safe_float(x, default: float = 0.0) -> float:
    try:
        if pd.isna(x) or np.isinf(x):
            return default
        return float(x)
    except Exception:
        return default


def _hybrid_ml_cpr_add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    session = pd.Series(d.index.date if isinstance(d.index, pd.DatetimeIndex) else np.arange(len(d)), index=d.index)
    d["atr_14"] = _hybrid_ml_cpr_atr(d, 14)
    d["avg_vol_20"] = d["volume"].rolling(20, min_periods=20).mean()
    d["ema9"] = d["close"].ewm(span=9, adjust=False).mean()
    d["ema21"] = d["close"].ewm(span=21, adjust=False).mean()
    d["ema50"] = d["close"].ewm(span=50, adjust=False).mean()
    d["rsi_14"] = _hybrid_ml_cpr_rsi(d["close"], 14)
    d["bb_basis_20"] = d["close"].rolling(20, min_periods=20).mean()
    d["bb_stdev_20"] = d["close"].rolling(20, min_periods=20).std(ddof=0)
    d["bb_up"] = d["bb_basis_20"] + d["bb_stdev_20"] * 2
    d["bb_dn"] = d["bb_basis_20"] - d["bb_stdev_20"] * 2
    pv = d["close"] * d["volume"]
    d["vwap"] = pv.groupby(session).cumsum() / d["volume"].replace(0, np.nan).groupby(session).cumsum()
    d["vwap_up"] = d["vwap"] + d["bb_stdev_20"] * 2
    d["vwap_dn"] = d["vwap"] - d["bb_stdev_20"] * 2
    d["daily_high"] = d["high"].groupby(session).cummax()
    d["daily_low"] = d["low"].groupby(session).cummin()
    return d


def _hybrid_ml_cpr_features(df: pd.DataFrame, i: int) -> HybridMlCprFeatures:
    r = df.iloc[i]
    prev = df.iloc[i - 1] if i > 0 else r
    safe = _hybrid_ml_cpr_safe_float
    daily_range = safe(r.daily_high - r.daily_low)
    price_position = safe(r.close - r.daily_low) / daily_range if daily_range > 0 else 0.5
    avg_vol = max(safe(r.avg_vol_20), 1.0)
    volume_strength = min(2.0, safe(r.volume) / avg_vol)
    trend_score = 0.0
    trend_score += 1.0 if r.ema9 > r.ema21 else -1.0
    trend_score += 1.0 if r.ema21 > r.ema50 else -1.0
    trend_score += 0.5 if r.close > r.ema9 else -0.5
    trend_alignment = trend_score / 2.5
    volatility = min(1.0, safe(r.atr_14 / r.close * 100, 0.5)) if r.close > 0 else 0.5
    momentum = (safe(r.rsi_14, 50.0) - 50.0) / 50.0
    body = safe(r.close - r.open)
    candle_range = safe(r.high - r.low)
    body_ratio = body / candle_range if candle_range > 0 else 0.0
    delta_pressure = body_ratio * (safe(r.volume) / avg_vol)
    bb_dev = safe(r.bb_stdev_20) * 2
    confluence_score = 1.0 / 3.0 if r.close > r.bb_basis_20 - bb_dev and r.close < r.bb_basis_20 + bb_dev else 0.0
    is_hammer = (min(r.open, r.close) - r.low) > (r.high - max(r.open, r.close)) * 2
    is_shooting = (r.high - max(r.open, r.close)) > (min(r.open, r.close) - r.low) * 2
    is_engulfing = abs(body) > abs(safe(prev.close - prev.open)) * 1.5
    pattern_strength = 1.0 if (is_hammer or is_shooting or is_engulfing) else 0.3
    hour_val = df.index[i].hour if isinstance(df.index, pd.DatetimeIndex) else 0
    time_factor = 1.2 if ((9 <= hour_val <= 10) or (14 <= hour_val <= 15)) else 1.0
    vwap_dev = safe(r.bb_stdev_20)
    vwap_distance = abs(safe(r.close - r.vwap)) / vwap_dev if vwap_dev > 0 else 0.5
    return HybridMlCprFeatures(
        price_position=safe(price_position, 0.5),
        volume_strength=safe(volume_strength, 1.0),
        trend_alignment=safe(trend_alignment),
        volatility=safe(volatility, 0.5),
        momentum=safe(momentum),
        delta_pressure=safe(delta_pressure),
        confluence_score=safe(confluence_score),
        pattern_strength=safe(pattern_strength, 0.3),
        time_factor=safe(time_factor, 1.0),
        vwap_distance=safe(vwap_distance, 0.5),
    )


def _hybrid_ml_cpr_confidence(feat: HybridMlCprFeatures, w: HybridMlCprWeights, signal_type: str) -> float:
    score = 0.0
    total = 0.0
    score += w.w_price * ((1.0 - feat.price_position) if signal_type == "BUY" else (feat.price_position if signal_type == "SELL" else 0.5)); total += w.w_price
    score += w.w_volume * min(1.0, feat.volume_strength / 1.5); total += w.w_volume
    score += w.w_trend * (max(0.0, feat.trend_alignment) if signal_type == "BUY" else (max(0.0, -feat.trend_alignment) if signal_type == "SELL" else 0.5)); total += w.w_trend
    vol_score = feat.volatility / 0.3 if feat.volatility < 0.3 else (1.0 - feat.volatility) / 0.7
    score += w.w_volatility * vol_score; total += w.w_volatility
    score += w.w_momentum * (((feat.momentum + 1.0) / 2.0) if signal_type == "BUY" else (((1.0 - feat.momentum) / 2.0) if signal_type == "SELL" else 0.5)); total += w.w_momentum
    delta_score = max(0.0, feat.delta_pressure) if signal_type == "BUY" else max(0.0, -feat.delta_pressure)
    score += w.w_delta * min(1.0, delta_score); total += w.w_delta
    score += w.w_confluence * feat.confluence_score; total += w.w_confluence
    score += w.w_pattern * feat.pattern_strength; total += w.w_pattern
    score += w.w_time * (feat.time_factor - 0.5); total += w.w_time
    vwap_score = 1.0 - min(1.0, feat.vwap_distance / 2.0) if signal_type in ("REVERSAL", "CONFLUENCE") else 0.5
    score += w.w_vwap * vwap_score; total += w.w_vwap
    return float(max(0.0, min(100.0, (score / total) * 100.0 if total else 0.0)))


def _hybrid_ml_cpr_clamp_weight(x: float) -> float:
    return float(max(0.1, min(3.0, x)))


def _hybrid_ml_cpr_update_weights(w: HybridMlCprWeights, feat: HybridMlCprFeatures, success: bool, lr: float) -> HybridMlCprWeights:
    adj = lr if success else -lr * 0.3
    w.w_price = _hybrid_ml_cpr_clamp_weight(w.w_price * 0.95 + 0.05 * (w.w_price + adj * feat.price_position))
    w.w_volume = _hybrid_ml_cpr_clamp_weight(w.w_volume * 0.95 + 0.05 * (w.w_volume + adj * feat.volume_strength))
    w.w_trend = _hybrid_ml_cpr_clamp_weight(w.w_trend * 0.95 + 0.05 * (w.w_trend + adj * abs(feat.trend_alignment)))
    w.w_volatility = _hybrid_ml_cpr_clamp_weight(w.w_volatility * 0.95 + 0.05 * (w.w_volatility + adj * (1.0 - feat.volatility)))
    w.w_momentum = _hybrid_ml_cpr_clamp_weight(w.w_momentum * 0.95 + 0.05 * (w.w_momentum + adj * abs(feat.momentum)))
    w.w_delta = _hybrid_ml_cpr_clamp_weight(w.w_delta * 0.95 + 0.05 * (w.w_delta + adj * abs(feat.delta_pressure)))
    w.w_confluence = _hybrid_ml_cpr_clamp_weight(w.w_confluence * 0.95 + 0.05 * (w.w_confluence + adj * feat.confluence_score))
    w.w_pattern = _hybrid_ml_cpr_clamp_weight(w.w_pattern * 0.95 + 0.05 * (w.w_pattern + adj * feat.pattern_strength))
    w.w_time = _hybrid_ml_cpr_clamp_weight(w.w_time * 0.95 + 0.05 * (w.w_time + adj * (feat.time_factor - 0.5)))
    w.w_vwap = _hybrid_ml_cpr_clamp_weight(w.w_vwap * 0.95 + 0.05 * (w.w_vwap + adj * (1.0 - feat.vwap_distance)))
    return w


def hybrid_ml_cpr(df: pd.DataFrame, cfg: HybridMlCprConfig | None = None) -> dict:
    """Hybrid ML CPR/VWAP+BB signal engine with ML confidence labels and trade lines."""
    empty = {"signals": [], "levels": {}, "trade_lines": {"entry": [], "sl": [], "target": []}, "trade_segments": [], "confidence": {}, "dashboard": {}}
    try:
        cfg = cfg or HybridMlCprConfig()
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex) or not {"open", "high", "low", "close"}.issubset(work.columns):
            return empty
        if "volume" not in work.columns:
            work["volume"] = 0.0
        work = work[["open", "high", "low", "close", "volume"]].astype(float).dropna()
        if len(work) < 30:
            n = len(work)
            return {**empty, "trade_lines": {"entry": [None] * n, "sl": [None] * n, "target": [None] * n}}

        out = _hybrid_ml_cpr_add_indicators(work)
        for col in ["buy_confidence", "sell_confidence", "confluence_confidence", "reversal_confidence", "success_after_10", "ml_success_rate", "w_trend", "w_volume", "w_delta"]:
            out[col] = np.nan
        out["signal"] = ""
        out["entry"] = np.nan
        out["sl"] = np.nan
        out["target"] = np.nan

        weights = HybridMlCprWeights()
        success_history = []
        last_signal_bar = None
        last_signal_type = None
        last_features = None
        last_buy_sell_bar = 0
        last_reversal_bar = 0
        events = []
        trade_segments = []
        intraday = _is_intraday(out)
        idx = out.index

        for i in range(len(out)):
            r = out.iloc[i]
            if pd.isna(r.bb_stdev_20) or pd.isna(r.avg_vol_20) or pd.isna(r.atr_14):
                continue
            feat = _hybrid_ml_cpr_features(out, i)
            safe = _hybrid_ml_cpr_safe_float

            if last_signal_bar is not None and (i - last_signal_bar) == 10:
                now_close = safe(out.iloc[i].close)
                past_close = safe(out.iloc[last_signal_bar].close)
                atr = safe(out.iloc[i].atr_14)
                success = False
                if last_signal_type == "BUY":
                    success = now_close > past_close + atr * 0.5
                elif last_signal_type == "SELL":
                    success = now_close < past_close - atr * 0.5
                elif last_signal_type == "REVERSAL":
                    success = abs(now_close - past_close) > atr * 0.3
                elif last_signal_type == "CONFLUENCE":
                    success = abs(now_close - past_close) < atr * 0.2
                success_history.append(1.0 if success else 0.0)
                if len(success_history) > cfg.ml_learning_window:
                    success_history.pop(0)
                if last_features is not None:
                    weights = _hybrid_ml_cpr_update_weights(weights, last_features, success, cfg.ml_adaptation_rate)
                out.iat[last_signal_bar, out.columns.get_loc("success_after_10")] = 1.0 if success else 0.0
                last_signal_bar = None
                last_signal_type = None
                last_features = None

            buy_conf = _hybrid_ml_cpr_confidence(feat, weights, "BUY")
            sell_conf = _hybrid_ml_cpr_confidence(feat, weights, "SELL")
            confl_conf = _hybrid_ml_cpr_confidence(feat, weights, "CONFLUENCE")
            rev_conf = _hybrid_ml_cpr_confidence(feat, weights, "REVERSAL")
            out.iat[i, out.columns.get_loc("buy_confidence")] = buy_conf
            out.iat[i, out.columns.get_loc("sell_confidence")] = sell_conf
            out.iat[i, out.columns.get_loc("confluence_confidence")] = confl_conf
            out.iat[i, out.columns.get_loc("reversal_confidence")] = rev_conf

            close, high, low, open_ = safe(r.close), safe(r.high), safe(r.low), safe(r.open)
            volume, avg_vol_20, atr_14 = safe(r.volume), safe(r.avg_vol_20), safe(r.atr_14)
            vwap_up, vwap_dn, bb_up, bb_dn = safe(r.vwap_up), safe(r.vwap_dn), safe(r.bb_up), safe(r.bb_dn)
            bull_base = ((close < vwap_dn) or (close < bb_dn)) and volume > avg_vol_20 * 0.8
            bear_base = ((close > vwap_up) or (close > bb_up)) and volume > avg_vol_20 * 0.8
            high_conf_buy = bull_base and (not cfg.enable_global_ml or buy_conf >= cfg.ml_min_confidence)
            high_conf_sell = bear_base and (not cfg.enable_global_ml or sell_conf >= cfg.ml_min_confidence)
            if high_conf_buy and high_conf_sell:
                if buy_conf >= sell_conf:
                    high_conf_sell = False
                else:
                    high_conf_buy = False

            signal = ""
            signal_conf = 0.0
            if (high_conf_buy or high_conf_sell) and (i - last_buy_sell_bar) > 3:
                last_buy_sell_bar = i
                last_signal_bar = i
                last_signal_type = "BUY" if high_conf_buy else "SELL"
                last_features = feat
                signal = last_signal_type
                signal_conf = buy_conf if high_conf_buy else sell_conf

            tolerance = atr_14 * 0.1
            upper_confl = any(high >= vwu - tolerance and low <= bbl + tolerance for vwu in [vwap_up, vwap_up * 1.01] for bbl in [bb_dn, bb_dn * 0.99])
            lower_confl = any(low <= vwl + tolerance and high >= bbu - tolerance for vwl in [vwap_dn, vwap_dn * 0.99] for bbu in [bb_up, bb_up * 1.01])
            ml_upper_confl = upper_confl and (not cfg.enable_global_ml or confl_conf >= cfg.ml_min_confidence)
            ml_lower_confl = lower_confl and (not cfg.enable_global_ml or confl_conf >= cfg.ml_min_confidence)
            if (ml_upper_confl or ml_lower_confl) and not signal:
                signal = "UPPER_CONFL" if ml_upper_confl else "LOWER_CONFL"
                signal_conf = confl_conf

            if i > 0:
                p = out.iloc[i - 1]
                touch_upper_prev = (safe(p.high) >= safe(p.vwap_up) - tolerance) or (safe(p.high) >= safe(p.bb_up) - tolerance)
                touch_lower_prev = (safe(p.low) <= safe(p.vwap_dn) + tolerance) or (safe(p.low) <= safe(p.bb_dn) + tolerance)
                is_uptrend = r.ema21 > r.ema50
                upper_reversal = touch_upper_prev and safe(p.close) > safe(p.open) and low < min(safe(p.low), safe(p.open)) and not is_uptrend
                lower_reversal = touch_lower_prev and safe(p.close) < safe(p.open) and high > max(safe(p.high), safe(p.open)) and is_uptrend
                ml_upper_reversal = upper_reversal and (not cfg.enable_global_ml or rev_conf >= cfg.ml_min_confidence)
                ml_lower_reversal = lower_reversal and (not cfg.enable_global_ml or rev_conf >= cfg.ml_min_confidence)
                if (ml_upper_reversal or ml_lower_reversal) and (i - last_reversal_bar) > 5:
                    last_reversal_bar = i
                    last_signal_bar = i
                    last_signal_type = "REVERSAL"
                    last_features = feat
                    if not signal:
                        signal = "DOWN_REV" if ml_upper_reversal else "UP_REV"
                        signal_conf = rev_conf

            if signal:
                out.iat[i, out.columns.get_loc("signal")] = signal
                direction = "bull" if signal in ("BUY", "UP_REV", "LOWER_CONFL") else "bear"
                label = {
                    "BUY": "HML BUY",
                    "SELL": "HML SELL",
                    "UPPER_CONFL": "HML Upper Confl",
                    "LOWER_CONFL": "HML Lower Confl",
                    "DOWN_REV": "HML Down Rev",
                    "UP_REV": "HML Up Rev",
                }.get(signal, signal)
                events.append({
                    "time": _time_str(idx, i, intraday),
                    "name": f"{label} {signal_conf:.0f}%",
                    "direction": direction,
                    "index": i,
                    "price": round(float(low if direction == "bull" else high), 4),
                    "signal": signal,
                    "confidence": round(float(signal_conf), 1),
                })
                if signal in ("BUY", "SELL"):
                    entry = safe(out.iloc[i + 1].open) if cfg.entry_mode == "next_open" and i + 1 < len(out) else close
                    if signal == "BUY":
                        sl = entry - atr_14
                        target = entry + 2.0 * (entry - sl)
                    else:
                        sl = entry + atr_14
                        target = entry - 2.0 * (sl - entry)
                    out.iat[i, out.columns.get_loc("entry")] = entry
                    out.iat[i, out.columns.get_loc("sl")] = sl
                    out.iat[i, out.columns.get_loc("target")] = target
                    end_i = min(i + 15, len(out) - 1)
                    trade_segments.append({
                        "start_index": i,
                        "end_index": end_i,
                        "start_time": _time_str(idx, i, intraday),
                        "end_time": _time_str(idx, end_i, intraday),
                        "side": signal.lower(),
                        "entry": round(float(entry), 4),
                        "sl": round(float(sl), 4),
                        "target": round(float(target), 4),
                    })

            sr = (sum(success_history) / len(success_history) * 100.0) if success_history else 0.0
            out.iat[i, out.columns.get_loc("ml_success_rate")] = sr
            out.iat[i, out.columns.get_loc("w_trend")] = weights.w_trend
            out.iat[i, out.columns.get_loc("w_volume")] = weights.w_volume
            out.iat[i, out.columns.get_loc("w_delta")] = weights.w_delta

        entry_line = np.full(len(out), np.nan)
        sl_line = np.full(len(out), np.nan)
        target_line = np.full(len(out), np.nan)
        for seg in trade_segments:
            start = int(seg["start_index"])
            end = int(seg["end_index"])
            entry_line[start:end + 1] = float(seg["entry"])
            sl_line[start:end + 1] = float(seg["sl"])
            target_line[start:end + 1] = float(seg["target"])

        def _arr(col: str, nd: int = 4) -> list:
            return [round(float(v), nd) if v == v and np.isfinite(v) else None for v in out[col].tolist()]

        last = out.iloc[-1]
        signals_tracked = int((out["signal"] != "").sum())
        avg_weight = float(np.nanmean([last.w_trend, last.w_volume, last.w_delta]))
        current_conf = float(np.nanmax([last.buy_confidence, last.sell_confidence, last.confluence_confidence, last.reversal_confidence]))
        dashboard = {
            "status": "READY" if current_conf >= cfg.ml_min_confidence else "LEARNING",
            "success_rate": round(_hybrid_ml_cpr_safe_float(last.ml_success_rate), 1),
            "signals_tracked": signals_tracked,
            "learning_progress": round(min(100.0, signals_tracked / max(1, cfg.ml_learning_window) * 100), 1),
            "top_feature": "Volume" if last.w_volume >= max(last.w_trend, last.w_delta) else ("Trend" if last.w_trend >= last.w_delta else "Delta"),
            "current_confidence": round(current_conf, 1),
            "avg_weight": round(avg_weight, 2),
            "min_threshold": round(cfg.ml_min_confidence, 1),
        }
        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "levels": {
                "vwap": _arr("vwap"),
                "vwap_up": _arr("vwap_up"),
                "vwap_dn": _arr("vwap_dn"),
                "bb_up": _arr("bb_up"),
                "bb_dn": _arr("bb_dn"),
                "bb_basis": _arr("bb_basis_20"),
            },
            "trade_lines": {
                "entry": [round(float(v), 4) if v == v and np.isfinite(v) else None for v in entry_line],
                "sl": [round(float(v), 4) if v == v and np.isfinite(v) else None for v in sl_line],
                "target": [round(float(v), 4) if v == v and np.isfinite(v) else None for v in target_line],
            },
            "trade_segments": trade_segments,
            "confidence": {
                "buy": _arr("buy_confidence", 1),
                "sell": _arr("sell_confidence", 1),
                "confluence": _arr("confluence_confidence", 1),
                "reversal": _arr("reversal_confidence", 1),
                "success_rate": _arr("ml_success_rate", 1),
            },
            "signal": out["signal"].fillna("").tolist(),
            "dashboard": dashboard,
            "params": {
                "ml_min_confidence": cfg.ml_min_confidence,
                "ml_learning_window": cfg.ml_learning_window,
                "entry_mode": cfg.entry_mode,
            },
        }
    except Exception:
        return empty


@dataclass
class VwapBbMlConfConfig:
    trend_length: int = 20
    vw_stdev_len: int = 20
    vwap_k1: float = 1.0
    vwap_k2: float = 2.0
    vwap_k3: float = 3.0
    bb_len1: int = 20
    bb_k1a: float = 1.0
    bb_k1b: float = 2.0
    atr_len: int = 14
    atr_pct: float = 0.10
    adx_len: int = 14
    rsi_len: int = 14
    vol_z_len: int = 20
    ema_fast: int = 9
    ema_slow: int = 21
    min_session_bars: int = 6
    huge_candle_atr: float = 2.0
    min_rr: float = 2.0
    min_confluence_score: float = 65.0
    min_ml_probability: float = 0.60
    wick_ratio_min: float = 0.35
    body_strength_min: float = 0.45
    breakout_adx_min: float = 23.0
    fade_adx_max: float = 24.0
    volume_z_min_breakout: float = 0.0
    sl_atr_mult_fade: float = 1.0
    sl_atr_mult_breakout: float = 1.0
    target_r: float = 2.5
    lookahead_bars: int = 30


def _vwap_bb_ml_rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def _vwap_bb_ml_true_range(df: pd.DataFrame) -> pd.Series:
    prev = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)


def _vwap_bb_ml_atr(df: pd.DataFrame, n: int) -> pd.Series:
    return _vwap_bb_ml_rma(_vwap_bb_ml_true_range(df), n)


def _vwap_bb_ml_rsi(close: pd.Series, n: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = _vwap_bb_ml_rma(gain, n)
    avg_loss = _vwap_bb_ml_rma(loss, n)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def _vwap_bb_ml_adx(df: pd.DataFrame, n: int) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)
    atr_n = _vwap_bb_ml_rma(_vwap_bb_ml_true_range(df), n)
    plus_di = 100 * _vwap_bb_ml_rma(plus_dm, n) / atr_n.replace(0, np.nan)
    minus_di = 100 * _vwap_bb_ml_rma(minus_dm, n) / atr_n.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _vwap_bb_ml_rma(dx, n).fillna(0)


def _vwap_bb_ml_volume_z(volume: pd.Series, n: int) -> pd.Series:
    mean = volume.rolling(n, min_periods=n).mean()
    std = volume.rolling(n, min_periods=n).std(ddof=0)
    return ((volume - mean) / std.replace(0, np.nan)).fillna(0)


def _vwap_bb_ml_entry(row: pd.Series, side: str, setup: str, cfg: VwapBbMlConfConfig) -> tuple[float, float, float, float]:
    entry = float(row["close"])
    atrv = float(row["atr"]) if np.isfinite(row["atr"]) and row["atr"] > 0 else max(entry * 0.002, 0.01)
    if side == "LONG":
        if setup == "FADE":
            sl = min(float(row["low"]), float(row.get("lower_meet", row["low"]))) - cfg.sl_atr_mult_fade * atrv
        else:
            sl = float(row.get("upper_meet", row["low"])) - cfg.sl_atr_mult_breakout * atrv
        risk = max(entry - sl, 0.01)
        target = entry + cfg.target_r * risk
    else:
        if setup == "FADE":
            sl = max(float(row["high"]), float(row.get("upper_meet", row["high"]))) + cfg.sl_atr_mult_fade * atrv
        else:
            sl = float(row.get("lower_meet", row["high"])) + cfg.sl_atr_mult_breakout * atrv
        risk = max(sl - entry, 0.01)
        target = entry - cfg.target_r * risk
    return entry, sl, target, abs(target - entry) / max(abs(entry - sl), 0.01)


def vwap_bb_ml_conf(df: pd.DataFrame, cfg: VwapBbMlConfConfig | None = None) -> dict:
    """Adaptive VWAP-BB neural confluence trader chart engine."""
    empty = {"signals": [], "levels": {}, "trade_lines": {"entry": [], "sl": [], "target": []}, "trade_segments": [], "dashboard": {}, "ml_meta": {}}
    try:
        cfg = cfg or VwapBbMlConfConfig()
        work = _norm(df).copy().sort_index()
        if not isinstance(work.index, pd.DatetimeIndex) or not {"open", "high", "low", "close"}.issubset(work.columns):
            return empty
        if "volume" not in work.columns:
            work["volume"] = 0.0
        x = work[["open", "high", "low", "close", "volume"]].astype(float).dropna()
        if len(x) < 50:
            return {**empty, "trade_lines": {"entry": [None] * len(x), "sl": [None] * len(x), "target": [None] * len(x)}}

        group = pd.Series(x.index.date, index=x.index)
        hlc3 = (x["high"] + x["low"] + x["close"]) / 3.0
        vol = x["volume"].replace(0, np.nan)
        x["session_bar"] = group.groupby(group).cumcount().values + 1
        sum_src_vol = (hlc3 * vol).groupby(group).cumsum()
        sum_vol = vol.groupby(group).cumsum()
        sum_src2_vol = ((hlc3 ** 2) * vol).groupby(group).cumsum()
        x["vwap"] = sum_src_vol / sum_vol
        variance = ((sum_src2_vol / sum_vol) - x["vwap"] ** 2).clip(lower=0)
        x["vwap_dev"] = np.sqrt(variance)
        x["VWU1"] = x["vwap"] + cfg.vwap_k1 * x["vwap_dev"]
        x["VWU2"] = x["vwap"] + cfg.vwap_k2 * x["vwap_dev"]
        x["VWU3"] = x["vwap"] + cfg.vwap_k3 * x["vwap_dev"]
        x["VWL1"] = x["vwap"] - cfg.vwap_k1 * x["vwap_dev"]
        x["VWL2"] = x["vwap"] - cfg.vwap_k2 * x["vwap_dev"]
        x["VWL3"] = x["vwap"] - cfg.vwap_k3 * x["vwap_dev"]
        x["trendicator"] = x["close"].rolling(cfg.trend_length, min_periods=cfg.trend_length).mean()
        x["trend_up"] = x["trendicator"] > x["trendicator"].shift(1)
        x["bb_basis1"] = x["close"].rolling(cfg.bb_len1, min_periods=cfg.bb_len1).mean()
        x["bb_dev1"] = x["close"].rolling(cfg.bb_len1, min_periods=cfg.bb_len1).std(ddof=0)
        x["BBU1a"] = x["bb_basis1"] + cfg.bb_k1a * x["bb_dev1"]
        x["BBU1b"] = x["bb_basis1"] + cfg.bb_k1b * x["bb_dev1"]
        x["BBL1a"] = x["bb_basis1"] - cfg.bb_k1a * x["bb_dev1"]
        x["BBL1b"] = x["bb_basis1"] - cfg.bb_k1b * x["bb_dev1"]
        x["atr"] = _vwap_bb_ml_atr(x, cfg.atr_len)
        x["tol"] = x["atr"] * cfg.atr_pct
        x["adx"] = _vwap_bb_ml_adx(x, cfg.adx_len)
        x["rsi"] = _vwap_bb_ml_rsi(x["close"], cfg.rsi_len)
        x["volume_z"] = _vwap_bb_ml_volume_z(x["volume"], cfg.vol_z_len)
        x["ema_fast"] = x["close"].ewm(span=cfg.ema_fast, adjust=False, min_periods=cfg.ema_fast).mean()
        x["ema_slow"] = x["close"].ewm(span=cfg.ema_slow, adjust=False, min_periods=cfg.ema_slow).mean()
        x["ema_fast_slope"] = x["ema_fast"].diff()
        x["ema_slow_slope"] = x["ema_slow"].diff()
        x["vwap_slope_atr"] = x["vwap"].diff() / x["atr"].replace(0, np.nan)
        x["bb_width1"] = (x["BBU1b"] - x["BBL1b"]) / x["bb_basis1"].replace(0, np.nan)
        x["atr_pct_price"] = x["atr"] / x["close"].replace(0, np.nan)
        rng = (x["high"] - x["low"]).replace(0, np.nan)
        body = (x["close"] - x["open"]).abs()
        x["body_ratio"] = (body / rng).fillna(0)
        x["upper_wick_ratio"] = ((x["high"] - x[["open", "close"]].max(axis=1)) / rng).fillna(0)
        x["lower_wick_ratio"] = ((x[["open", "close"]].min(axis=1) - x["low"]) / rng).fillna(0)
        x["candle_atr"] = (x["high"] - x["low"]) / x["atr"].replace(0, np.nan)
        x["ret3"] = x["close"].pct_change(3)
        x["ret5"] = x["close"].pct_change(5)
        x["dist_close_vwap_atr"] = (x["close"] - x["vwap"]) / x["atr"].replace(0, np.nan)

        upper_flags, upper_meets, upper_deltas, upper_pairs = [], [], [], []
        lower_flags, lower_meets, lower_deltas, lower_pairs = [], [], [], []
        for _, row in x.iterrows():
            tol = row["tol"]
            best_u, meet_u, pair_u = np.inf, np.nan, ""
            best_l, meet_l, pair_l = np.inf, np.nan, ""
            if np.isfinite(tol):
                for vc in ["VWU1", "VWU2", "VWU3"]:
                    for bc in ["BBU1a", "BBU1b"]:
                        dlt = abs(row[vc] - row[bc])
                        if np.isfinite(dlt) and dlt <= tol and dlt < best_u:
                            best_u, meet_u, pair_u = dlt, (row[vc] + row[bc]) / 2, f"{vc}:{bc}"
                for vc in ["VWL1", "VWL2", "VWL3"]:
                    for bc in ["BBL1a", "BBL1b"]:
                        dlt = abs(row[vc] - row[bc])
                        if np.isfinite(dlt) and dlt <= tol and dlt < best_l:
                            best_l, meet_l, pair_l = dlt, (row[vc] + row[bc]) / 2, f"{vc}:{bc}"
            upper_flags.append(np.isfinite(meet_u)); upper_meets.append(meet_u); upper_deltas.append(best_u if np.isfinite(best_u) else np.nan); upper_pairs.append(pair_u)
            lower_flags.append(np.isfinite(meet_l)); lower_meets.append(meet_l); lower_deltas.append(best_l if np.isfinite(best_l) else np.nan); lower_pairs.append(pair_l)
        x["upper_confl"] = upper_flags
        x["upper_meet"] = upper_meets
        x["upper_delta"] = upper_deltas
        x["upper_pair"] = upper_pairs
        x["lower_confl"] = lower_flags
        x["lower_meet"] = lower_meets
        x["lower_delta"] = lower_deltas
        x["lower_pair"] = lower_pairs

        bbw = x["bb_width1"].fillna(x["bb_width1"].median())
        bbw_ratio = bbw / bbw.rolling(80, min_periods=20).median().replace(0, np.nan)
        chaos = (x["candle_atr"] > cfg.huge_candle_atr) | (bbw_ratio > 1.8)
        trend_up = (x["vwap_slope_atr"] > 0.015) & (x["close"] > x["vwap"]) & x["trend_up"].fillna(False)
        trend_down = (x["vwap_slope_atr"] < -0.015) & (x["close"] < x["vwap"]) & (~x["trend_up"].fillna(True))
        range_mode = (x["adx"] < 20) & (x["vwap_slope_atr"].abs() < 0.02) & (~chaos)
        expansion = (x["adx"] >= cfg.breakout_adx_min) & (bbw_ratio > 1.05) & (~chaos)
        x["regime"] = np.select(
            [chaos, trend_up & expansion, trend_down & expansion, trend_up, trend_down, range_mode, expansion],
            ["CHAOS", "UPTREND_EXPANSION", "DOWNTREND_EXPANSION", "UPTREND", "DOWNTREND", "RANGE", "VOL_EXPANSION"],
            default="MIXED",
        )
        tight = np.maximum((1 - (x["upper_delta"] / x["tol"]).clip(0, 1)).fillna(0), (1 - (x["lower_delta"] / x["tol"]).clip(0, 1)).fillna(0))
        vol_score = np.clip((x["volume_z"] + 1.5) / 3.0, 0, 1)
        adx_score = np.clip(x["adx"] / 35.0, 0, 1)
        bb_score = np.clip(1 - (bbw_ratio - 1).abs() / 1.5, 0, 1)
        x["confluence_score"] = (35 * tight + 15 * np.where(x["session_bar"] >= cfg.min_session_bars, 1.0, 0.25) + 15 * vol_score + 15 * bb_score + 10 * adx_score + 10 * np.where(x["regime"] == "CHAOS", 0, 1)).clip(0, 100)

        mature = x["session_bar"] >= cfg.min_session_bars
        quality = x["confluence_score"] >= cfg.min_confluence_score
        lower_touch_reclaim = x["lower_confl"] & (x["low"] <= x["lower_meet"] + x["tol"]) & (x["close"] > x["lower_meet"]) & (x["lower_wick_ratio"] >= cfg.wick_ratio_min)
        upper_touch_reject = x["upper_confl"] & (x["high"] >= x["upper_meet"] - x["tol"]) & (x["close"] < x["upper_meet"]) & (x["upper_wick_ratio"] >= cfg.wick_ratio_min)
        strong_body = x["body_ratio"] >= cfg.body_strength_min
        buy_fade = lower_touch_reclaim & mature & (~chaos) & quality & (x["adx"] <= cfg.fade_adx_max) & (x["vwap_slope_atr"] > -0.04) & x["regime"].isin(["RANGE", "MIXED", "UPTREND"])
        sell_fade = upper_touch_reject & mature & (~chaos) & quality & (x["adx"] <= cfg.fade_adx_max) & (x["vwap_slope_atr"] < 0.04) & x["regime"].isin(["RANGE", "MIXED", "DOWNTREND"])
        buy_breakout = x["upper_confl"] & mature & (~chaos) & quality & (x["close"] > x["upper_meet"] + x["tol"] * 0.25) & strong_body & (x["volume_z"] >= cfg.volume_z_min_breakout) & (x["adx"] >= cfg.breakout_adx_min) & (x["vwap_slope_atr"] > 0) & x["trend_up"].fillna(False) & (x["ema_fast"] > x["ema_slow"])
        sell_breakdown = x["lower_confl"] & mature & (~chaos) & quality & (x["close"] < x["lower_meet"] - x["tol"] * 0.25) & strong_body & (x["volume_z"] >= cfg.volume_z_min_breakout) & (x["adx"] >= cfg.breakout_adx_min) & (x["vwap_slope_atr"] < 0) & (~x["trend_up"].fillna(True)) & (x["ema_fast"] < x["ema_slow"])

        rule_signal, reason, entry, sl, target, rr = [], [], [], [], [], []
        for _, row in x.iterrows():
            sig, why, side_setup = "NO_TRADE", "No valid confluence setup", None
            if bool(buy_breakout.loc[row.name]):
                sig, why, side_setup = "BUY_BREAKOUT", "Upper confluence breakout + trend/ADX/volume confirmation", ("LONG", "BREAKOUT")
            elif bool(sell_breakdown.loc[row.name]):
                sig, why, side_setup = "SELL_BREAKDOWN", "Lower confluence breakdown + trend/ADX/volume confirmation", ("SHORT", "BREAKOUT")
            elif bool(buy_fade.loc[row.name]):
                sig, why, side_setup = "BUY_FADE", "Lower confluence reclaim + rejection wick + non-chaos regime", ("LONG", "FADE")
            elif bool(sell_fade.loc[row.name]):
                sig, why, side_setup = "SELL_FADE", "Upper confluence rejection + wick + non-chaos regime", ("SHORT", "FADE")
            if side_setup:
                e, s, t, rrv = _vwap_bb_ml_entry(row, side_setup[0], side_setup[1], cfg)
                if rrv < cfg.min_rr:
                    sig, why, e, s, t, rrv = "NO_TRADE", f"Blocked: RR {rrv:.2f} below minimum {cfg.min_rr:.2f}", np.nan, np.nan, np.nan, np.nan
            else:
                e = s = t = rrv = np.nan
            rule_signal.append(sig); reason.append(why); entry.append(e); sl.append(s); target.append(t); rr.append(rrv)
        x["rule_signal"] = rule_signal
        x["entry"] = entry
        x["stop_loss"] = sl
        x["target"] = target
        x["risk_reward"] = rr
        x["reason"] = reason

        # Lightweight probability fallback: blends confluence, volume, trend, and ADX without training per request.
        direction_ok = np.where(x["rule_signal"].str.startswith("BUY"), x["rsi"] / 100, np.where(x["rule_signal"].str.startswith("SELL"), (100 - x["rsi"]) / 100, 0.5))
        rule_prob = (0.55 * (x["confluence_score"] / 100) + 0.15 * np.clip((x["volume_z"] + 1.5) / 3, 0, 1) + 0.15 * np.clip(x["adx"] / 35, 0, 1) + 0.15 * direction_ok).clip(0, 1)
        x["ml_probability"] = rule_prob
        x["final_probability"] = 0.75 * x["ml_probability"] + 0.25 * (x["confluence_score"] / 100)
        x["final_signal"] = x["rule_signal"]
        x.loc[(x["rule_signal"] != "NO_TRADE") & (x["final_probability"] < cfg.min_ml_probability), "final_signal"] = "NO_TRADE"

        events, trade_segments = [], []
        entry_line = np.full(len(x), np.nan)
        sl_line = np.full(len(x), np.nan)
        target_line = np.full(len(x), np.nan)
        idx = x.index
        intraday = _is_intraday(x)
        for i, row in enumerate(x.itertuples()):
            if bool(getattr(row, "upper_confl")):
                events.append({"time": _time_str(idx, i, intraday), "name": "VWBB Upper Conf", "direction": "bear", "index": i, "price": round(float(getattr(row, "upper_meet")), 4), "score": round(float(getattr(row, "confluence_score")), 1)})
            if bool(getattr(row, "lower_confl")):
                events.append({"time": _time_str(idx, i, intraday), "name": "VWBB Lower Conf", "direction": "bull", "index": i, "price": round(float(getattr(row, "lower_meet")), 4), "score": round(float(getattr(row, "confluence_score")), 1)})
            sig = getattr(row, "final_signal")
            if sig != "NO_TRADE" and np.isfinite(getattr(row, "entry")):
                direction = "bull" if sig.startswith("BUY") else "bear"
                end_i = min(i + cfg.lookahead_bars, len(x) - 1)
                events.append({"time": _time_str(idx, i, intraday), "name": f"VWBB {sig} {float(getattr(row, 'final_probability')) * 100:.0f}%", "direction": direction, "index": i, "entry": round(float(getattr(row, "entry")), 4), "sl": round(float(getattr(row, "stop_loss")), 4), "target": round(float(getattr(row, "target")), 4), "probability": round(float(getattr(row, "final_probability")), 3), "score": round(float(getattr(row, "confluence_score")), 1)})
                seg = {"start_index": i, "end_index": end_i, "side": "buy" if direction == "bull" else "sell", "entry": round(float(getattr(row, "entry")), 4), "sl": round(float(getattr(row, "stop_loss")), 4), "target": round(float(getattr(row, "target")), 4)}
                trade_segments.append(seg)
                entry_line[i:end_i + 1] = seg["entry"]; sl_line[i:end_i + 1] = seg["sl"]; target_line[i:end_i + 1] = seg["target"]

        def _arr(col: str, nd: int = 4) -> list:
            return [round(float(v), nd) if v == v and np.isfinite(v) else None for v in x[col].tolist()]

        trades = x[x["final_signal"] != "NO_TRADE"]
        dashboard = {
            "status": "READY" if len(trades) else "WAIT",
            "final_trades": int(len(trades)),
            "upper_confluence": int(x["upper_confl"].sum()),
            "lower_confluence": int(x["lower_confl"].sum()),
            "latest_signal": str(x["final_signal"].iloc[-1]),
            "latest_probability": round(float(x["final_probability"].iloc[-1]) * 100, 1) if np.isfinite(x["final_probability"].iloc[-1]) else 0,
            "latest_regime": str(x["regime"].iloc[-1]),
            "latest_score": round(float(x["confluence_score"].iloc[-1]), 1) if np.isfinite(x["confluence_score"].iloc[-1]) else 0,
        }
        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "levels": {
                "vwap": _arr("vwap"), "VWU1": _arr("VWU1"), "VWU2": _arr("VWU2"), "VWU3": _arr("VWU3"),
                "VWL1": _arr("VWL1"), "VWL2": _arr("VWL2"), "VWL3": _arr("VWL3"),
                "BBU1a": _arr("BBU1a"), "BBU1b": _arr("BBU1b"), "BBL1a": _arr("BBL1a"), "BBL1b": _arr("BBL1b"),
                "trendicator": _arr("trendicator"), "upper_meet": _arr("upper_meet"), "lower_meet": _arr("lower_meet"),
            },
            "trade_lines": {
                "entry": [round(float(v), 4) if v == v and np.isfinite(v) else None for v in entry_line],
                "sl": [round(float(v), 4) if v == v and np.isfinite(v) else None for v in sl_line],
                "target": [round(float(v), 4) if v == v and np.isfinite(v) else None for v in target_line],
            },
            "trade_segments": trade_segments,
            "probability": _arr("final_probability", 4),
            "score": _arr("confluence_score", 1),
            "regime": x["regime"].fillna("").tolist(),
            "final_signal": x["final_signal"].fillna("").tolist(),
            "dashboard": dashboard,
            "ml_meta": {"ml_status": "lightweight_rule_probability", "threshold": cfg.min_ml_probability},
            "params": {"min_ml_probability": cfg.min_ml_probability, "min_confluence_score": cfg.min_confluence_score},
        }
    except Exception:
        return empty


def dual_ma_osc(
    df: pd.DataFrame,
    fast_length: int = 1,
    slow_length: int = 30,
    smooth_length: int = 1,
    upper_sd_length: int = 25,
    lower_sd_length: int = 25,
) -> dict:
    """Dual MA SD Oscillator converted from the SchizoQuant TradingView script."""
    try:
        data = _norm(df).copy()
        if "close" not in data.columns or data.empty:
            return {"signals": []}

        close = pd.to_numeric(data["close"], errors="coerce").astype(float).to_numpy()
        n = len(close)
        intraday = _is_intraday(data)
        idx = data.index

        def _ema(values: np.ndarray, length: int) -> np.ndarray:
            length = max(int(length), 1)
            alpha = 2.0 / (length + 1.0)
            out = np.full(len(values), np.nan, dtype=float)
            if len(values) == 0:
                return out
            first = 0
            while first < len(values) and not np.isfinite(values[first]):
                first += 1
            if first >= len(values):
                return out
            out[first] = values[first]
            for i in range(first + 1, len(values)):
                out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1] if np.isfinite(values[i]) else out[i - 1]
            return out

        def _arr(values: np.ndarray, ndigits: int = 6) -> list:
            return [round(float(v), ndigits) if np.isfinite(v) else None for v in values]

        fast_ma = _ema(close, fast_length)
        slow_ma = _ema(close, slow_length)
        spread = fast_ma - slow_ma
        smoothed_ma = _ema(spread, smooth_length)
        smoothed_series = pd.Series(smoothed_ma)
        upper_band = smoothed_series.rolling(int(upper_sd_length), min_periods=int(upper_sd_length)).std(ddof=0).to_numpy()
        lower_band = -smoothed_series.rolling(int(lower_sd_length), min_periods=int(lower_sd_length)).std(ddof=0).to_numpy()

        sq = np.zeros(n, dtype=int)
        for i in range(n):
            if np.isfinite(upper_band[i]) and smoothed_ma[i] > upper_band[i]:
                sq[i] = 1
            elif np.isfinite(lower_band[i]) and smoothed_ma[i] < lower_band[i]:
                sq[i] = -1
            else:
                sq[i] = sq[i - 1] if i > 0 else 0

        long_signal = np.zeros(n, dtype=bool)
        short_signal = np.zeros(n, dtype=bool)
        events = []
        for i in range(1, n):
            long_signal[i] = sq[i] == 1 and sq[i - 1] != 1
            short_signal[i] = sq[i] == -1 and sq[i - 1] != -1
            if long_signal[i] or short_signal[i]:
                direction = "bull" if long_signal[i] else "bear"
                events.append({
                    "time": _time_str(idx, i, intraday),
                    "name": "DualMA Bull" if long_signal[i] else "DualMA Bear",
                    "direction": direction,
                    "index": i,
                    "price": round(float(close[i]), 4) if np.isfinite(close[i]) else None,
                    "osc": round(float(smoothed_ma[i]), 6) if np.isfinite(smoothed_ma[i]) else None,
                })

        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "fast_ma": _arr(fast_ma),
            "slow_ma": _arr(slow_ma),
            "spread": _arr(spread),
            "smoothed_ma": _arr(smoothed_ma),
            "upper_band": _arr(upper_band),
            "lower_band": _arr(lower_band),
            "zero": [0.0 if np.isfinite(v) else None for v in smoothed_ma],
            "sq": [int(v) for v in sq.tolist()],
            "long_signal": [bool(v) for v in long_signal.tolist()],
            "short_signal": [bool(v) for v in short_signal.tolist()],
            "signal": [1 if long_signal[i] else (-1 if short_signal[i] else 0) for i in range(n)],
            "params": {
                "fast_length": int(fast_length),
                "slow_length": int(slow_length),
                "smooth_length": int(smooth_length),
                "upper_sd_length": int(upper_sd_length),
                "lower_sd_length": int(lower_sd_length),
            },
        }
    except Exception:
        return {"signals": []}


def ichimoku_trend_oscillator(
    df: pd.DataFrame,
    tenkan_len: int = 9,
    kijun_len: int = 26,
    senkou_b_len: int = 52,
    force_smooth_len: int = 5,
    force_scale: float = 100.0,
    neutral_zone: float = 8.0,
    shift_threshold: float = 12.0,
) -> dict:
    """Ichimoku Trend Oscillator [Gabremoku] with force, histogram, and signal events."""
    try:
        work = _norm(df).copy()
        if not {"high", "low", "close"}.issubset(work.columns) or work.empty:
            return {"signals": []}

        high = pd.to_numeric(work["high"], errors="coerce").astype(float)
        low = pd.to_numeric(work["low"], errors="coerce").astype(float)
        close = pd.to_numeric(work["close"], errors="coerce").astype(float)
        idx = work.index
        intraday = _is_intraday(work)

        def _donchian_mid(length: int) -> pd.Series:
            length = max(int(length), 1)
            return (high.rolling(length, min_periods=1).max() + low.rolling(length, min_periods=1).min()) / 2.0

        def _ema(series: pd.Series, length: int) -> pd.Series:
            return series.ewm(span=max(int(length), 1), adjust=False, min_periods=1).mean()

        def _arr(series: pd.Series, ndigits: int = 4) -> list:
            return [round(float(v), ndigits) if pd.notna(v) and np.isfinite(v) else None for v in series.tolist()]

        tenkan = _donchian_mid(tenkan_len)
        kijun = _donchian_mid(kijun_len)
        senkou_a = (tenkan + kijun) / 2.0
        senkou_b = _donchian_mid(senkou_b_len)
        cloud_top = pd.Series(np.maximum(senkou_a, senkou_b), index=work.index)
        cloud_bot = pd.Series(np.minimum(senkou_a, senkou_b), index=work.index)
        cloud_size = (senkou_a - senkou_b).abs()

        price_vs_cloud = pd.Series(
            np.where(close > cloud_top, 1.0, np.where(close < cloud_bot, -1.0, 0.0)),
            index=work.index,
        )
        tk_bias = pd.Series(
            np.where(tenkan > kijun, 1.0, np.where(tenkan < kijun, -1.0, 0.0)),
            index=work.index,
        )
        cloud_bias = pd.Series(
            np.where(senkou_a > senkou_b, 1.0, np.where(senkou_a < senkou_b, -1.0, 0.0)),
            index=work.index,
        )

        prev_close = close.shift(1)
        tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
        atr_base = tr.ewm(alpha=1.0 / max(int(kijun_len), 1), adjust=False, min_periods=1).mean()
        norm_base = pd.Series(np.maximum(np.maximum(atr_base, cloud_size), 0.05), index=work.index)

        tk_spread_raw = ((tenkan - kijun) / norm_base) * float(force_scale)
        price_cloud_raw = pd.Series(
            np.where(
                close > cloud_top,
                ((close - cloud_top) / norm_base) * (float(force_scale) * 0.45),
                np.where(close < cloud_bot, ((close - cloud_bot) / norm_base) * (float(force_scale) * 0.45), 0.0),
            ),
            index=work.index,
        )
        cloud_structure_raw = cloud_bias * ((cloud_size / norm_base) * (float(force_scale) * 0.30))
        raw_force = tk_spread_raw + price_cloud_raw + cloud_structure_raw
        force_pre = raw_force.clip(-float(force_scale), float(force_scale))
        force = _ema(force_pre, force_smooth_len).clip(-100.0, 100.0)
        signal_line = _ema(force, max(2, int(force_smooth_len) * 2))
        hist = force - signal_line
        momentum_shift = force - force.shift(1)

        state = np.where(
            (force > neutral_zone) & (price_vs_cloud >= 0) & (tk_bias > 0),
            "Bullish Expansion",
            np.where(
                (force > neutral_zone) & (tk_bias > 0),
                "Bullish Pressure",
                np.where(
                    (force < -neutral_zone) & (price_vs_cloud <= 0) & (tk_bias < 0),
                    "Bearish Expansion",
                    np.where((force < -neutral_zone) & (tk_bias < 0), "Bearish Pressure", "Neutral"),
                ),
            ),
        )
        state_col = np.where(force > neutral_zone, "bull", np.where(force < -neutral_zone, "bear", "neutral"))
        trend_bias = np.where(
            (tk_bias > 0) & (price_vs_cloud >= 0),
            "Bull Bias",
            np.where((tk_bias < 0) & (price_vs_cloud <= 0), "Bear Bias", "Mixed"),
        )
        kumo = np.where(price_vs_cloud > 0, "Above Kumo", np.where(price_vs_cloud < 0, "Below Kumo", "Inside Kumo"))
        tk_text = np.where(tenkan > kijun, "Tenkan > Kijun", np.where(tenkan < kijun, "Tenkan < Kijun", "Tenkan = Kijun"))
        shift_text = np.where(momentum_shift > shift_threshold, "Bull Shift", np.where(momentum_shift < -shift_threshold, "Bear Shift", "Stable"))

        long_signal = (force > 0) & (force.shift(1) <= 0)
        short_signal = (force < 0) & (force.shift(1) >= 0)
        bull_shift = (momentum_shift > shift_threshold) & (force > 0) & (~long_signal)
        bear_shift = (momentum_shift < -shift_threshold) & (force < 0) & (~short_signal)

        events = []
        for i in range(1, len(work)):
            if bool(long_signal.iloc[i]) or bool(short_signal.iloc[i]) or bool(bull_shift.iloc[i]) or bool(bear_shift.iloc[i]):
                is_bull = bool(long_signal.iloc[i]) or bool(bull_shift.iloc[i])
                name = "Ichi Osc Bull" if bool(long_signal.iloc[i]) else (
                    "Ichi Osc Bear" if bool(short_signal.iloc[i]) else ("Ichi Bull Shift" if is_bull else "Ichi Bear Shift")
                )
                events.append({
                    "index": int(i),
                    "time": _time_str(idx, i, intraday),
                    "name": name,
                    "direction": "bull" if is_bull else "bear",
                    "force": round(float(force.iloc[i]), 4) if pd.notna(force.iloc[i]) else None,
                })

        last = len(work) - 1
        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "force": _arr(force),
            "signal_line": _arr(signal_line),
            "hist": _arr(hist),
            "zero": [0.0 if pd.notna(v) else None for v in force.tolist()],
            "upper_neutral": [float(neutral_zone) if pd.notna(v) else None for v in force.tolist()],
            "lower_neutral": [-float(neutral_zone) if pd.notna(v) else None for v in force.tolist()],
            "tenkan": _arr(tenkan),
            "kijun": _arr(kijun),
            "senkou_a": _arr(senkou_a),
            "senkou_b": _arr(senkou_b),
            "hist_color": ["#2196f3aa" if v >= 0 else "#f1ff30aa" for v in hist.fillna(0).tolist()],
            "state_color": state_col.tolist(),
            "state": state.tolist(),
            "trend_bias": trend_bias.tolist(),
            "kumo": kumo.tolist(),
            "tk_text": tk_text.tolist(),
            "shift_text": shift_text.tolist(),
            "long_signal": [bool(v) for v in long_signal.fillna(False).tolist()],
            "short_signal": [bool(v) for v in short_signal.fillna(False).tolist()],
            "bull_shift_signal": [bool(v) for v in bull_shift.fillna(False).tolist()],
            "bear_shift_signal": [bool(v) for v in bear_shift.fillna(False).tolist()],
            "dashboard": {
                "state": str(state[last]),
                "force": round(float(force.iloc[last]), 2) if pd.notna(force.iloc[last]) else None,
                "trend_bias": str(trend_bias[last]),
                "kumo": str(kumo[last]),
                "tk": str(tk_text[last]),
                "shift": str(shift_text[last]),
            },
            "params": {
                "tenkan_len": int(tenkan_len),
                "kijun_len": int(kijun_len),
                "senkou_b_len": int(senkou_b_len),
                "force_smooth_len": int(force_smooth_len),
                "neutral_zone": float(neutral_zone),
                "shift_threshold": float(shift_threshold),
            },
        }
    except Exception:
        return {"signals": []}


def _nt_tl_check(support: bool, pivot: int, slope: float, y: np.ndarray) -> float:
    intercept = -slope * pivot + y[pivot]
    line_vals = slope * np.arange(len(y)) + intercept
    diffs = line_vals - y
    if support and diffs.max() > 1e-5:
        return -1.0
    if not support and diffs.min() < -1e-5:
        return -1.0
    return float((diffs ** 2.0).sum())


def _nt_tl_optimize(support: bool, pivot: int, init_slope: float, y: np.ndarray) -> tuple[float, float]:
    slope_unit = (float(np.nanmax(y)) - float(np.nanmin(y))) / max(len(y), 1)
    if not np.isfinite(slope_unit) or slope_unit <= 0:
        slope_unit = 1e-6
    best_slope = float(init_slope)
    best_err = _nt_tl_check(support, pivot, best_slope, y)
    if best_err < 0.0:
        best_slope = 0.0
        best_err = _nt_tl_check(support, pivot, best_slope, y)
    if best_err < 0.0:
        return best_slope, float(-best_slope * pivot + y[pivot])
    curr_step = 1.0
    min_step = 0.0001
    get_derivative = True
    derivative = 0.0
    while curr_step > min_step:
        if get_derivative:
            slope_change = best_slope + slope_unit * min_step
            test_err = _nt_tl_check(support, pivot, slope_change, y)
            derivative = test_err - best_err
            if test_err < 0.0:
                slope_change = best_slope - slope_unit * min_step
                test_err = _nt_tl_check(support, pivot, slope_change, y)
                derivative = best_err - test_err
            if test_err < 0.0:
                break
            get_derivative = False
        test_slope = best_slope - slope_unit * curr_step if derivative > 0.0 else best_slope + slope_unit * curr_step
        test_err = _nt_tl_check(support, pivot, test_slope, y)
        if test_err < 0.0 or test_err >= best_err:
            curr_step *= 0.5
        else:
            best_err = test_err
            best_slope = test_slope
            get_derivative = True
    return float(best_slope), float(-best_slope * pivot + y[pivot])


def _nt_fit_trendlines(data: np.ndarray) -> tuple[tuple[float, float], tuple[float, float], int, int]:
    x = np.arange(len(data))
    coefs = np.polyfit(x, data, 1)
    line_points = coefs[0] * x + coefs[1]
    upper_pivot = int((data - line_points).argmax())
    lower_pivot = int((data - line_points).argmin())
    support = _nt_tl_optimize(True, lower_pivot, float(coefs[0]), data)
    resistance = _nt_tl_optimize(False, upper_pivot, float(coefs[0]), data)
    return support, resistance, lower_pivot, upper_pivot


def _nt_log_atr(work: pd.DataFrame, length: int) -> pd.Series:
    high = np.log(work["high"].astype(float).clip(lower=1e-9))
    low = np.log(work["low"].astype(float).clip(lower=1e-9))
    close = np.log(work["close"].astype(float).clip(lower=1e-9))
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def trendln_breakout_markers(df: pd.DataFrame) -> dict:
    """Neurotrader TrendlineBreakoutMetaLabel-style trendline breakout engine."""
    try:
        work = _norm(df)
        n = len(work)
        lookback = 72
        atr_len = 168
        hold_bars = 24
        atr_mult = 3.0
        min_gap = 12
        if n < lookback + 5:
            return {"signals": [], "lines": []}

        close_px = work["close"].astype(float).clip(lower=1e-9).reset_index(drop=True)
        close_log = np.log(close_px.to_numpy(dtype=float))
        atr_log = _nt_log_atr(work, atr_len).reset_index(drop=True)
        idx = work.index
        intraday = _is_intraday(work)
        signals: list[dict] = []
        lines: list[dict] = []
        last_sig_i = -10**9
        prev_res = np.nan
        prev_sup = np.nan
        start_i = max(lookback, min(atr_len, n - 1))

        for i in range(start_i, n):
            window = close_log[i - lookback:i]
            if not np.all(np.isfinite(window)):
                continue
            try:
                support, resistance, lower_pivot, upper_pivot = _nt_fit_trendlines(window)
            except Exception:
                continue
            s_val = support[1] + lookback * support[0]
            r_val = resistance[1] + lookback * resistance[0]
            if not (np.isfinite(s_val) and np.isfinite(r_val)):
                continue
            bull = np.isfinite(prev_res) and close_log[i] > r_val and close_log[i - 1] <= prev_res
            bear = np.isfinite(prev_sup) and close_log[i] < s_val and close_log[i - 1] >= prev_sup
            prev_res = r_val
            prev_sup = s_val
            if (not bull and not bear) or i - last_sig_i < min_gap:
                continue

            is_bull = bool(bull and not bear)
            coefs = resistance if is_bull else support
            pivot = upper_pivot if is_bull else lower_pivot
            direction = "bull" if is_bull else "bear"
            line_type = "resistance" if is_bull else "support"
            name = "TL Break Bull" if is_bull else "TL Break Bear"
            atr = float(atr_log.iloc[i]) if i < len(atr_log) and np.isfinite(atr_log.iloc[i]) else float(np.nanstd(window[-20:]))
            if not np.isfinite(atr) or atr <= 0:
                atr = max(abs(r_val - s_val) * 0.25, 1e-4)
            entry_log = float(close_log[i])
            entry = float(close_px.iloc[i])
            if is_bull:
                stop = float(np.exp(entry_log - atr * atr_mult))
                target1 = float(np.exp(entry_log + atr * atr_mult))
                target2 = float(np.exp(entry_log + atr * atr_mult * 2.0))
            else:
                stop = float(np.exp(entry_log + atr * atr_mult))
                target1 = float(np.exp(entry_log - atr * atr_mult))
                target2 = float(np.exp(entry_log - atr * atr_mult * 2.0))

            start_index = i - lookback
            pivot_index = start_index + int(pivot)
            line_start = max(start_index, min(pivot_index, i - lookback // 2))
            line_end = min(n - 1, i + hold_bars)
            y0 = float(np.exp(coefs[1] + (line_start - start_index) * coefs[0]))
            y1 = float(np.exp(coefs[1] + (line_end - start_index) * coefs[0]))
            signals.append({
                "index": int(i),
                "time": _time_str(idx, i, intraday),
                "name": name,
                "direction": direction,
                "entry": round(entry, 4),
                "sl": round(stop, 4),
                "tp": round(target1, 4),
            })
            lines.append({
                "start_index": int(line_start),
                "end_index": int(line_end),
                "break_index": int(i),
                "start_price": round(y0, 4),
                "end_price": round(y1, 4),
                "break_price": round(entry, 4),
                "line_type": line_type,
                "direction": direction,
                "name": name,
                "entry": round(entry, 4),
                "stop": round(stop, 4),
                "target1": round(target1, 4),
                "target2": round(target2, 4),
                "lookback": lookback,
                "atr_mult": atr_mult,
                "hold_bars": hold_bars,
            })
            last_sig_i = i
        return {"signals": _sanitize_events(signals), "lines": lines[-120:]}
    except Exception:
        return {"signals": [], "lines": []}


def _fmfm_pine_rma(series: pd.Series, length: int) -> pd.Series:
    x = series.astype(float)
    out = pd.Series(np.nan, index=x.index, dtype=float)
    if len(x) < length:
        return out
    out.iloc[length - 1] = x.iloc[:length].mean()
    alpha = 1.0 / float(length)
    for i in range(length, len(x)):
        out.iloc[i] = alpha * x.iloc[i] + (1.0 - alpha) * out.iloc[i - 1]
    return out


def _fmfm_atr(work: pd.DataFrame, length: int) -> pd.Series:
    prev = work["close"].shift(1)
    tr = pd.concat(
        [
            work["high"] - work["low"],
            (work["high"] - prev).abs(),
            (work["low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _fmfm_pine_rma(tr, length)


def _fmfm_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).fillna(0)
    loss = (-delta.clip(upper=0)).fillna(0)
    ag = _fmfm_pine_rma(gain, length)
    al = _fmfm_pine_rma(loss, length)
    rs = ag / al.replace(0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.where(al != 0, 100.0)
    return rsi.where(ag != 0, 0.0)


def _fmfm_supertrend(work: pd.DataFrame, factor: float = 3.0, length: int = 10):
    atr = _fmfm_atr(work, length)
    hl2 = (work["high"] + work["low"]) / 2.0
    upper = hl2 + factor * atr
    lower = hl2 - factor * atr
    final_upper = upper.copy()
    final_lower = lower.copy()
    st = pd.Series(np.nan, index=work.index)
    direction = pd.Series(np.nan, index=work.index)
    for i in range(1, len(work)):
        if pd.isna(atr.iloc[i]):
            continue
        pu = final_upper.iloc[i - 1]
        pl = final_lower.iloc[i - 1]
        pc = work["close"].iloc[i - 1]
        final_upper.iloc[i] = upper.iloc[i] if pd.isna(pu) or upper.iloc[i] < pu or pc > pu else pu
        final_lower.iloc[i] = lower.iloc[i] if pd.isna(pl) or lower.iloc[i] > pl or pc < pl else pl
        if pd.isna(st.iloc[i - 1]):
            direction.iloc[i] = 1 if work["close"].iloc[i] <= final_upper.iloc[i] else -1
        elif st.iloc[i - 1] == pu:
            direction.iloc[i] = -1 if work["close"].iloc[i] > final_upper.iloc[i] else 1
        else:
            direction.iloc[i] = 1 if work["close"].iloc[i] < final_lower.iloc[i] else -1
        st.iloc[i] = final_lower.iloc[i] if direction.iloc[i] < 0 else final_upper.iloc[i]
    return st, direction


def _fmfm_confirmed_pivot(series: pd.Series, left: int, right: int, high: bool) -> pd.Series:
    out = pd.Series(np.nan, index=series.index)
    for i in range(left, len(series) - right):
        window = series.iloc[i - left : i + right + 1]
        val = series.iloc[i]
        if (high and val == window.max()) or ((not high) and val == window.min()):
            out.iloc[i] = val
    return out


def _fmfm_dynamic_vwap(work: pd.DataFrame, swing_period: int = 50, base_apt: float = 20.0):
    n = len(work)
    if n == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float), []
    high = work["high"].to_numpy(float)
    low = work["low"].to_numpy(float)
    vol = work["volume"].to_numpy(float)
    hlc3 = ((work["high"] + work["low"] + work["close"]) / 3.0).to_numpy(float)
    alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, base_apt))
    ph = np.nan
    pl = np.nan
    ph_i = 0
    pl_i = 0
    prev_dir = np.nan
    p_acc = hlc3[0] * vol[0]
    v_acc = vol[0]
    vwap = np.full(n, np.nan)
    direction = np.full(n, np.nan)
    resets = []
    seg_values = {}
    for i in range(n):
        start = max(0, i - swing_period + 1)
        if high[i] >= np.nanmax(high[start : i + 1]):
            ph = high[i]
            ph_i = i
        if low[i] <= np.nanmin(low[start : i + 1]):
            pl = low[i]
            pl_i = i
        dir_v = 1 if ph_i > pl_i else -1
        direction[i] = dir_v
        if i > 0 and np.isfinite(prev_dir) and dir_v != prev_dir:
            anchor = pl_i if dir_v > 0 else ph_i
            y = pl if dir_v > 0 else ph
            p_acc = y * vol[anchor]
            v_acc = vol[anchor]
            resets.append({"index": int(anchor), "price": round(float(y), 4), "direction": "bull" if dir_v > 0 else "bear"})
            seg_values = {}
            for j in range(anchor, i + 1):
                p_acc = (1.0 - alpha) * p_acc + alpha * (hlc3[j] * vol[j])
                v_acc = (1.0 - alpha) * v_acc + alpha * vol[j]
                seg_values[j] = p_acc / v_acc if v_acc > 0 else np.nan
            for j, value in seg_values.items():
                vwap[j] = value
            prev_dir = dir_v
            continue
        p_acc = (1.0 - alpha) * p_acc + alpha * (hlc3[i] * vol[i])
        v_acc = (1.0 - alpha) * v_acc + alpha * vol[i]
        seg_values[i] = p_acc / v_acc if v_acc > 0 else np.nan
        vwap[i] = seg_values[i]
        prev_dir = dir_v
    return pd.Series(vwap, index=work.index), pd.Series(direction, index=work.index), resets[-40:]


def _fmfm_clean_series(series: pd.Series, decimals: int = 4) -> list:
    out = []
    for value in series:
        if value is None or pd.isna(value) or not np.isfinite(float(value)):
            out.append(None)
        else:
            out.append(round(float(value), decimals))
    return out


def _fmfm_segment_series(values: pd.Series, mask: pd.Series | np.ndarray, decimals: int = 4) -> list:
    return _fmfm_clean_series(values.where(mask), decimals)


def _fmfm_active_series(values: pd.Series, start_index: int, decimals: int = 4) -> list:
    out = pd.Series(np.nan, index=values.index, dtype=float)
    if 0 <= start_index < len(values):
        out.iloc[start_index:] = values.iloc[start_index:]
    return _fmfm_clean_series(out, decimals)


def _fmfm_active_vwap_from_pivot(work: pd.DataFrame, start_index: int, seed_price: float, base_apt: float = 20.0) -> pd.Series:
    out = pd.Series(np.nan, index=work.index, dtype=float)
    if start_index < 0 or start_index >= len(work):
        return out
    alpha = 1.0 - np.exp(-np.log(2.0) / max(1.0, base_apt))
    hlc3 = ((work["high"] + work["low"] + work["close"]) / 3.0).astype(float)
    vol = work["volume"].astype(float).fillna(0.0)
    p_acc = float(seed_price) * float(vol.iloc[start_index])
    v_acc = float(vol.iloc[start_index])
    for i in range(start_index, len(work)):
        p_acc = (1.0 - alpha) * p_acc + alpha * (float(hlc3.iloc[i]) * float(vol.iloc[i]))
        v_acc = (1.0 - alpha) * v_acc + alpha * float(vol.iloc[i])
        out.iloc[i] = p_acc / v_acc if v_acc > 0 else np.nan
    return out


def _fmfm_build_heatmap(work: pd.DataFrame, lookback: int = 100, bins: int = 50) -> dict:
    lb = min(lookback, len(work))
    if lb < 10:
        return {"bars": [], "poc": None}
    chunk = work.iloc[-lb:]
    top = float(chunk["high"].max())
    bot = float(chunk["low"].min())
    if top <= bot:
        return {"bars": [], "poc": None}
    volumes = np.zeros(bins, dtype=float)
    step = (top - bot) / bins
    for row in chunk.itertuples():
        a = int(np.clip((float(row.low) - bot) / step, 0, bins - 1))
        b = int(np.clip((float(row.high) - bot) / step, 0, bins - 1))
        width = max(1, b - a + 1)
        volumes[a : b + 1] += float(row.volume) / width
    maxv = float(volumes.max()) if volumes.size else 0.0
    close_now = float(work["close"].iloc[-1])
    bars = []
    for i, vol in enumerate(volumes):
        if vol <= 0 or maxv <= 0:
            continue
        price = bot + step * i + step / 2.0
        bars.append({
            "price": round(float(price), 4),
            "volume": round(float(vol), 2),
            "pct": round(float(vol / maxv * 100.0), 2),
            "side": "buy" if price < close_now else "sell",
        })
    return {"bars": bars, "poc": bars[int(np.argmax(volumes))] if bars else None, "top": round(top, 4), "bottom": round(bot, 4)}


def _fmfm_build_fvgs(work: pd.DataFrame, limit: int = 12) -> list:
    zones = []
    signs = np.sign(work["close"] - work["open"]).to_numpy()
    for i in range(2, len(work)):
        if signs[i] + signs[i - 1] + signs[i - 2] == -3:
            top = float(work["low"].iloc[i - 2])
            bottom = float(work["high"].iloc[i])
            if top > bottom:
                zones.append({"start_index": i - 1, "end_index": len(work) - 1, "top": round(top, 4), "bottom": round(bottom, 4), "direction": "bear", "label": "LIQUIDITY"})
        if signs[i] + signs[i - 1] + signs[i - 2] == 3:
            top = float(work["low"].iloc[i])
            bottom = float(work["high"].iloc[i - 2])
            if top > bottom:
                zones.append({"start_index": i - 1, "end_index": len(work) - 1, "top": round(top, 4), "bottom": round(bottom, 4), "direction": "bull", "label": "LIQUIDITY"})
    active = []
    for zone in zones:
        future = work.iloc[int(zone["start_index"]) :]
        filled = (future["low"] <= zone["bottom"]).any() if zone["direction"] == "bull" else (future["high"] >= zone["top"]).any()
        if not filled:
            active.append(zone)
    return active[-limit:]


def _fmfm_build_order_blocks(work: pd.DataFrame, atr: pd.Series, lookback: int = 9, limit: int = 3) -> list:
    ph = _fmfm_confirmed_pivot(work["high"], lookback, lookback, True).dropna()
    pl = _fmfm_confirmed_pivot(work["low"], lookback, lookback, False).dropna()
    zones = []
    for idx, value in pl.tail(limit).items():
        i = work.index.get_loc(idx)
        atr_v = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else float((work["high"] - work["low"]).rolling(14).mean().iloc[i])
        zones.append({"start_index": int(i), "end_index": len(work) - 1, "top": round(float(value + atr_v), 4), "bottom": round(float(value), 4), "direction": "bull", "label": "DEMAND ZONE"})
    for idx, value in ph.tail(limit).items():
        i = work.index.get_loc(idx)
        atr_v = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) else float((work["high"] - work["low"]).rolling(14).mean().iloc[i])
        zones.append({"start_index": int(i), "end_index": len(work) - 1, "top": round(float(value), 4), "bottom": round(float(value - atr_v), 4), "direction": "bear", "label": "SUPPLY ZONE"})
    return sorted(zones, key=lambda z: z["start_index"])[-limit * 2:]


def _fmfm_htf_levels(work: pd.DataFrame, selected_tf: str = "D", fib_period: int = 85) -> dict | None:
    try:
        if not isinstance(work.index, pd.DatetimeIndex) or len(work) < 2:
            return None
        rule = "1D" if selected_tf.upper() == "D" else "240min" if selected_tf == "240" else "60min"
        htf = work.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        if len(htf) < 2:
            return None
        prev = htf.iloc[-2]
        current = htf.iloc[-1]
        returns = ((htf["close"] - htf["open"]) / htf["open"].replace(0, np.nan)).dropna()
        lookback = min(max(1, fib_period), len(returns))
        stddev = float(returns.iloc[-lookback:].std(ddof=0) * current["open"]) if lookback else 0.0
        current_open = float(current["open"])
        levels = []
        for lv in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
            levels.append({"label": f"T{int(lv / 0.25)}", "price": round(current_open + stddev * lv, 4), "direction": "up"})
            levels.append({"label": f"T{int(lv / 0.25) + 1}", "price": round(current_open - stddev * lv, 4), "direction": "down"})
        return {
            "high": round(float(prev["high"]), 4),
            "low": round(float(prev["low"]), 4),
            "mid": round(float((prev["high"] + prev["low"]) / 2.0), 4),
            "open": round(current_open, 4),
            "stddev": round(stddev, 4),
            "levels": levels,
        }
    except Exception:
        return None


def _fmfm_closest_zones(zones: list[dict], close_now: float) -> list[dict]:
    if not zones:
        return []
    bulls = [z for z in zones if z.get("direction") == "bull"]
    bears = [z for z in zones if z.get("direction") == "bear"]

    def dist(zone):
        if zone["bottom"] <= close_now <= zone["top"]:
            return 0.0
        return min(abs(close_now - zone["bottom"]), abs(close_now - zone["top"]))

    selected = []
    if bulls:
        below_or_touch = [z for z in bulls if z["bottom"] <= close_now]
        selected.append(min(below_or_touch or bulls, key=dist))
    if bears:
        above_or_touch = [z for z in bears if z["top"] >= close_now]
        selected.append(min(above_or_touch or bears, key=dist))
    return sorted(selected, key=lambda z: z["start_index"])


def _fmfm_closest_fvgs(zones: list[dict], close_now: float, limit: int = 2) -> list[dict]:
    def dist(zone):
        if zone["bottom"] <= close_now <= zone["top"]:
            return 0.0
        return min(abs(close_now - zone["bottom"]), abs(close_now - zone["top"]))
    return sorted(zones, key=dist)[:limit]


def _fmfm_trendlines(work: pd.DataFrame, ph: pd.Series, pl: pd.Series) -> list[dict]:
    lines = []
    highs = ph.dropna()
    lows = pl.dropna()
    n = len(work)
    if len(lows) >= 2:
        i1 = work.index.get_loc(lows.index[-2])
        i2 = work.index.get_loc(lows.index[-1])
        y1 = float(lows.iloc[-2])
        y2 = float(lows.iloc[-1])
        if i2 > i1:
            slope = (y2 - y1) / (i2 - i1)
            if slope > 0:
                end_i = min(n - 1, i2 + 80)
                lines.append({
                    "type": "support",
                    "start_index": int(i1),
                    "end_index": int(end_i),
                    "start_price": round(y1, 4),
                    "end_price": round(float(y1 + slope * (end_i - i1)), 4),
                })
    if len(highs) >= 2:
        i1 = work.index.get_loc(highs.index[-2])
        i2 = work.index.get_loc(highs.index[-1])
        y1 = float(highs.iloc[-2])
        y2 = float(highs.iloc[-1])
        if i2 > i1:
            slope = (y2 - y1) / (i2 - i1)
            if slope < 0:
                end_i = min(n - 1, i2 + 80)
                lines.append({
                    "type": "resistance",
                    "start_index": int(i1),
                    "end_index": int(end_i),
                    "start_price": round(y1, 4),
                    "end_price": round(float(y1 + slope * (end_i - i1)), 4),
                })
    return lines


def fmfm300_indicator(df: pd.DataFrame) -> dict:
    """FMFM300 overlay translated from the supplied Pine-to-Python indicator."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close", "volume"}.issubset(work.columns) or len(work) < 30:
            return {"signals": [], "summary": {}, "series": {}, "zones": [], "heatmap": {"bars": []}}
        intraday = _is_intraday(work)
        idx = work.index
        open_ = work["open"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)
        close = work["close"].astype(float)
        volume = work["volume"].astype(float).fillna(0.0)

        atr14 = _fmfm_atr(work, 14)
        ema20 = close.ewm(span=20, adjust=False).mean()
        supertrend, st_dir = _fmfm_supertrend(work, 3.0, 10)
        bull = st_dir < 0
        ma1 = close.ewm(span=3, adjust=False).mean()
        ma2 = open_.ewm(span=7, adjust=False).mean()
        ma3 = close.ewm(span=14, adjust=False).mean()
        max_ma = pd.concat([ma1, ma2, ma3], axis=1).max(axis=1)
        min_ma = pd.concat([ma1, ma2, ma3], axis=1).min(axis=1)
        braid_diff = max_ma - min_ma
        braid_filter = atr14 * 0.40
        is_call = (ma1 > ma2) & (braid_diff > braid_filter)
        is_put = (ma2 > ma1) & (braid_diff > braid_filter)
        is_sideways = ~(is_call | is_put)

        demand = pd.Series(np.where(close > open_, (close - open_) * volume, 0.0), index=work.index).rolling(14).mean()
        supply = pd.Series(np.where(close < open_, (open_ - close) * volume, 0.0), index=work.index).rolling(14).mean()
        total = (demand + supply).replace(0, np.nan)
        demand_pct = (demand / total * 100.0).fillna(50.0)
        supply_pct = (supply / total * 100.0).fillna(50.0)
        rsi = _fmfm_rsi(close, 14)
        state = np.select(
            [bull & is_call, (~bull) & is_put, (~bull) & is_sideways, bull & is_sideways],
            ["BULLISH", "BEARISH", "SIDEWAYS BEAR", "SIDEWAYS BULL"],
            default="CAUTION",
        )
        dyn_vwap, vwap_dir, resets = _fmfm_dynamic_vwap(work)
        major_ph = _fmfm_confirmed_pivot(high, 20, 20, True)
        major_pl = _fmfm_confirmed_pivot(low, 20, 20, False)
        temp_ph = _fmfm_confirmed_pivot(high, 3, 3, True)
        temp_pl = _fmfm_confirmed_pivot(low, 3, 3, False)
        latest_bull = bool(bull.iloc[-1])
        active_pivots = major_pl.dropna() if latest_bull else major_ph.dropna()
        if len(active_pivots):
            active_anchor_ts = active_pivots.index[-1]
            active_anchor_index = int(work.index.get_loc(active_anchor_ts))
            active_anchor_price = float(active_pivots.iloc[-1])
        else:
            recent_start = max(0, len(work) - 80)
            recent = work.iloc[recent_start:]
            if latest_bull:
                active_anchor_ts = recent["low"].idxmin()
                active_anchor_index = int(work.index.get_loc(active_anchor_ts))
                active_anchor_price = float(work["low"].iloc[active_anchor_index])
            else:
                active_anchor_ts = recent["high"].idxmax()
                active_anchor_index = int(work.index.get_loc(active_anchor_ts))
                active_anchor_price = float(work["high"].iloc[active_anchor_index])
        active_vwap = _fmfm_active_vwap_from_pivot(work, active_anchor_index, active_anchor_price)
        st_switch_index = 0
        for j in range(len(work) - 1, 0, -1):
            if bool(bull.iloc[j]) != bool(bull.iloc[j - 1]):
                st_switch_index = j
                break

        signals = []
        for i in range(1, len(work)):
            if bool(bull.iloc[i]) and not bool(bull.iloc[i - 1]):
                signals.append({"time": _time_str(idx, i, intraday), "index": i, "name": "FMFM BULLISH", "direction": "bull"})
            elif (not bool(bull.iloc[i])) and bool(bull.iloc[i - 1]):
                signals.append({"time": _time_str(idx, i, intraday), "index": i, "name": "FMFM BEARISH", "direction": "bear"})
        for pivot_idx, value in major_pl.dropna().tail(20).items():
            i = work.index.get_loc(pivot_idx)
            signals.append({"time": _time_str(idx, i, intraday), "index": i, "name": "FMFM Major Low", "direction": "bull", "price": round(float(value), 4)})
        for pivot_idx, value in major_ph.dropna().tail(20).items():
            i = work.index.get_loc(pivot_idx)
            signals.append({"time": _time_str(idx, i, intraday), "index": i, "name": "FMFM Major High", "direction": "bear", "price": round(float(value), 4)})

        close_now = float(close.iloc[-1])
        htf = _fmfm_htf_levels(work, "D", 85)
        raw_zones = _fmfm_build_order_blocks(work, atr14, 9, 5)
        raw_fvgs = _fmfm_build_fvgs(work, 24)

        background = []
        for i in range(max(0, len(work) - 420), len(work)):
            if bool(bull.iloc[i]) and bool(is_call.iloc[i]):
                mode = "bull"
            elif (not bool(bull.iloc[i])) and bool(is_put.iloc[i]):
                mode = "bear"
            elif bool(bull.iloc[i]) and bool(is_sideways.iloc[i]):
                mode = "sideways_bull"
            elif (not bool(bull.iloc[i])) and bool(is_sideways.iloc[i]):
                mode = "sideways_bear"
            else:
                mode = "caution"
            background.append({"index": i, "time": _time_str(idx, i, intraday), "mode": mode})

        summary = {
            "state": str(state[-1]),
            "rsi": round(float(rsi.iloc[-1]), 2) if pd.notna(rsi.iloc[-1]) else None,
            "demand_pct": round(float(demand_pct.iloc[-1]), 2),
            "supply_pct": round(float(supply_pct.iloc[-1]), 2),
            "latest_close": round(float(close.iloc[-1]), 4),
        }
        return {
            "signals": _sanitize_events(signals, drop_conflicts=False),
            "summary": summary,
            "series": {
                "ema20": _fmfm_clean_series(ema20),
                "supertrend_bull": _fmfm_active_series(supertrend.where(bull), st_switch_index),
                "supertrend_bear": _fmfm_active_series(supertrend.where(~bull), st_switch_index),
                "dynamic_vwap_bull": _fmfm_active_series(active_vwap, active_anchor_index) if latest_bull else _fmfm_clean_series(pd.Series(np.nan, index=work.index)),
                "dynamic_vwap_bear": _fmfm_active_series(active_vwap, active_anchor_index) if not latest_bull else _fmfm_clean_series(pd.Series(np.nan, index=work.index)),
            },
            "background": background,
            "pivots": {
                "major_highs": [{"index": int(work.index.get_loc(i)), "price": round(float(v), 4)} for i, v in major_ph.dropna().tail(30).items()],
                "major_lows": [{"index": int(work.index.get_loc(i)), "price": round(float(v), 4)} for i, v in major_pl.dropna().tail(30).items()],
                "temp_highs": [{"index": int(work.index.get_loc(i)), "price": round(float(v), 4)} for i, v in temp_ph.dropna().tail(30).items()],
                "temp_lows": [{"index": int(work.index.get_loc(i)), "price": round(float(v), 4)} for i, v in temp_pl.dropna().tail(30).items()],
            },
            "vwap_resets": [{"index": active_anchor_index, "price": round(active_anchor_price, 4), "direction": "bull" if latest_bull else "bear"}],
            "trendlines": _fmfm_trendlines(work, major_ph, major_pl),
            "zones": _fmfm_closest_zones(raw_zones, close_now),
            "fvgs": _fmfm_closest_fvgs(raw_fvgs, close_now, 2),
            "heatmap": _fmfm_build_heatmap(work, 100, 50),
            "htf": htf,
            "latest_index": len(work) - 1,
        }
    except Exception:
        return {"signals": [], "summary": {}, "series": {}, "zones": [], "heatmap": {"bars": []}}


def inside_candle_strategy(df: pd.DataFrame) -> dict:
    """Inside candle breakout strategy with EMA and SuperTrend confirmation."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns):
            return {
                "signals": [],
                "setup_segments": [],
                "trade_segments": [],
                "ema9": [],
                "ema21": [],
                "ema200": [],
                "supertrend": [],
                "st_direction": [],
            }

        intraday = _is_intraday(work)
        idx = work.index
        open_ = work["open"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)
        close = work["close"].astype(float)
        n = len(work)

        ema9 = close.ewm(span=9, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()

        hl2 = (high + low) / 2.0
        tr = pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.ewm(alpha=1.0 / 10.0, adjust=False).mean()
        upper_band = hl2 + (2.0 * atr)
        lower_band = hl2 - (2.0 * atr)

        supertrend = np.full(n, np.nan, dtype=float)
        st_direction = np.full(n, 1, dtype=int)
        for i in range(n):
            if i == 0:
                supertrend[i] = float(upper_band.iloc[i]) if pd.notna(upper_band.iloc[i]) else np.nan
                continue
            prev_st = supertrend[i - 1]
            if np.isnan(prev_st):
                prev_st = float(close.iloc[i - 1])
            if close.iloc[i] > prev_st:
                floor = float(lower_band.iloc[i]) if pd.notna(lower_band.iloc[i]) else prev_st
                supertrend[i] = max(floor, prev_st)
                st_direction[i] = -1
            else:
                ceil = float(upper_band.iloc[i]) if pd.notna(upper_band.iloc[i]) else prev_st
                supertrend[i] = min(ceil, prev_st)
                st_direction[i] = 1

        rng = (high - low).replace(0.0, np.nan)
        body_ratio = ((close - open_).abs() / rng).fillna(0.0)
        setup_mask = (
            (body_ratio.shift(1) >= 0.60)
            & (high <= high.shift(1))
            & (low >= low.shift(1))
            & (body_ratio <= 0.50)
        ).fillna(False)

        def _line_values(series: pd.Series) -> list[float | None]:
            return [None if pd.isna(v) else round(float(v), 4) for v in series.tolist()]

        signals = []
        setup_segments = []
        trade_segments = []
        active_setup = None
        buy_count = 0
        sell_count = 0

        for i in range(1, n):
            if bool(setup_mask.iloc[i]):
                mother_high = float(high.iloc[i - 1])
                mother_low = float(low.iloc[i - 1])
                active_setup = {
                    "setup_index": int(i),
                    "mother_high": mother_high,
                    "mother_low": mother_low,
                }
                setup_segments.append({
                    "start_index": int(i),
                    "end_index": int(min(n - 1, i + 20)),
                    "high": round(mother_high, 4),
                    "low": round(mother_low, 4),
                })
                signals.append({
                    "index": int(i),
                    "time": _time_str(idx, i, intraday),
                    "name": "IC Setup",
                    "direction": "neutral",
                    "mother_high": round(mother_high, 4),
                    "mother_low": round(mother_low, 4),
                })

            if not active_setup:
                continue

            mother_high = float(active_setup["mother_high"])
            mother_low = float(active_setup["mother_low"])
            risk = max(abs(mother_high - mother_low), 1e-6)
            close_px = float(close.iloc[i])
            st_dir = int(st_direction[i])

            if close_px > mother_high and st_dir < 0:
                entry = mother_high
                stop = mother_low
                tp1 = entry + (risk * 1.5)
                tp2 = entry + (risk * 3.0)
                signals.append({
                    "index": int(i),
                    "time": _time_str(idx, i, intraday),
                    "name": "IC Buy",
                    "direction": "bull",
                    "entry": round(entry, 4),
                    "sl": round(stop, 4),
                    "tp": round(tp1, 4),
                    "tp2": round(tp2, 4),
                })
                trade_segments.append({
                    "index": int(i),
                    "start_index": int(i),
                    "end_index": int(min(n - 1, i + 10)),
                    "direction": "bull",
                    "entry": round(entry, 4),
                    "sl": round(stop, 4),
                    "tp1": round(tp1, 4),
                    "tp2": round(tp2, 4),
                })
                buy_count += 1
                active_setup = None
            elif close_px < mother_low and st_dir > 0:
                entry = mother_low
                stop = mother_high
                tp1 = entry - (risk * 1.5)
                tp2 = entry - (risk * 3.0)
                signals.append({
                    "index": int(i),
                    "time": _time_str(idx, i, intraday),
                    "name": "IC Sell",
                    "direction": "bear",
                    "entry": round(entry, 4),
                    "sl": round(stop, 4),
                    "tp": round(tp1, 4),
                    "tp2": round(tp2, 4),
                })
                trade_segments.append({
                    "index": int(i),
                    "start_index": int(i),
                    "end_index": int(min(n - 1, i + 10)),
                    "direction": "bear",
                    "entry": round(entry, 4),
                    "sl": round(stop, 4),
                    "tp1": round(tp1, 4),
                    "tp2": round(tp2, 4),
                })
                sell_count += 1
                active_setup = None

        return {
            "signals": _sanitize_events(signals, drop_conflicts=False),
            "setup_segments": setup_segments[-200:],
            "trade_segments": trade_segments[-120:],
            "ema9": _line_values(ema9),
            "ema21": _line_values(ema21),
            "ema200": _line_values(ema200),
            "supertrend": [None if np.isnan(v) else round(float(v), 4) for v in supertrend.tolist()],
            "st_direction": [int(v) for v in st_direction.tolist()],
            "summary": {
                "setups": int(setup_mask.sum()),
                "buy_signals": int(buy_count),
                "sell_signals": int(sell_count),
            },
        }
    except Exception:
        return {
            "signals": [],
            "setup_segments": [],
            "trade_segments": [],
            "ema9": [],
            "ema21": [],
            "ema200": [],
            "supertrend": [],
            "st_direction": [],
        }


def sweep_inside_rr_strategy(
    df: pd.DataFrame,
    rr: float = 5.0,
    ema_len: int = 9,
    body_mult: float = 1.5,
    sl_mode: str = "signal",
    entry_mode: str = "next_open",
    initial_balance: float = 10000.0,
) -> dict:
    """Sweep + Inside Pattern RR Dashboard strategy."""
    try:
        work = _norm(df).copy().sort_index()
        if not {"open", "high", "low", "close"}.issubset(work.columns) or work.empty:
            return {"signals": [], "trade_segments": [], "setup_segments": [], "trades": [], "dashboard": {}}

        idx = work.index
        intraday = _is_intraday(work)
        open_ = work["open"].astype(float)
        high = work["high"].astype(float)
        low = work["low"].astype(float)
        close = work["close"].astype(float)
        n = len(work)

        ema = close.ewm(span=max(int(ema_len), 1), adjust=False).mean()
        body = (close - open_).abs()
        signals_raw = []

        for i in range(3, n):
            strong_body = body.iloc[i] >= float(body_mult) * max(float(body.iloc[i - 1]), 1e-12)
            buy_sweep = (
                low.iloc[i] < low.iloc[i - 1]
                and close.iloc[i] > high.iloc[i - 1]
                and strong_body
                and close.iloc[i] >= ema.iloc[i]
            )
            sell_sweep = (
                high.iloc[i] > high.iloc[i - 1]
                and close.iloc[i] < low.iloc[i - 1]
                and strong_body
                and close.iloc[i] <= ema.iloc[i]
            )
            if buy_sweep:
                signals_raw.append({"index": i, "side": "buy", "kind": "BUY SWEEP", "signal_high": high.iloc[i], "signal_low": low.iloc[i], "pattern_high": high.iloc[i], "pattern_low": low.iloc[i]})
            if sell_sweep:
                signals_raw.append({"index": i, "side": "sell", "kind": "SELL SWEEP", "signal_high": high.iloc[i], "signal_low": low.iloc[i], "pattern_high": high.iloc[i], "pattern_low": low.iloc[i]})

            c3, c2, c1, c0 = i - 3, i - 2, i - 1, i
            range_high = high.iloc[c3]
            range_low = low.iloc[c3]
            c2_inside = high.iloc[c2] <= range_high and low.iloc[c2] >= range_low
            c2_sweep_high_reject = high.iloc[c2] > range_high and close.iloc[c2] < range_high
            c2_sweep_low_reject = low.iloc[c2] < range_low and close.iloc[c2] > range_low
            c1_body_strong = body.iloc[c1] >= float(body_mult) * max(float(body.iloc[c2]), 1e-12)
            sell_inside = (
                (c2_inside or c2_sweep_high_reject)
                and close.iloc[c1] < min(low.iloc[c2], range_low)
                and c1_body_strong
                and close.iloc[c0] < close.iloc[c1]
                and close.iloc[c0] <= ema.iloc[c0]
            )
            buy_inside = (
                (c2_inside or c2_sweep_low_reject)
                and close.iloc[c1] > max(high.iloc[c2], range_high)
                and c1_body_strong
                and close.iloc[c0] > close.iloc[c1]
                and close.iloc[c0] >= ema.iloc[c0]
            )
            pattern_high = max(high.iloc[c3], high.iloc[c2], high.iloc[c1])
            pattern_low = min(low.iloc[c3], low.iloc[c2], low.iloc[c1])
            if buy_inside:
                signals_raw.append({"index": i, "side": "buy", "kind": "BUY SWEEP+" if c2_sweep_low_reject else "BUY INSIDE", "signal_high": high.iloc[i], "signal_low": low.iloc[i], "pattern_high": pattern_high, "pattern_low": pattern_low})
            if sell_inside:
                signals_raw.append({"index": i, "side": "sell", "kind": "SELL SWEEP+" if c2_sweep_high_reject else "SELL INSIDE", "signal_high": high.iloc[i], "signal_low": low.iloc[i], "pattern_high": pattern_high, "pattern_low": pattern_low})

        priority = {"BUY SWEEP+": 3, "SELL SWEEP+": 3, "BUY INSIDE": 2, "SELL INSIDE": 2, "BUY SWEEP": 1, "SELL SWEEP": 1}
        best = {}
        for sig in signals_raw:
            k = (int(sig["index"]), sig["side"])
            if k not in best or priority.get(sig["kind"], 0) > priority.get(best[k]["kind"], 0):
                best[k] = sig
        signal_defs = sorted(best.values(), key=lambda s: int(s["index"]))

        sig_by_index = {}
        for sig in signal_defs:
            sig_by_index.setdefault(int(sig["index"]), []).append(sig)

        events = []
        setup_segments = []
        trade_segments = []
        trades = []
        active = []
        balance = float(initial_balance)

        for sig in signal_defs[-250:]:
            i = int(sig["index"])
            direction = "bull" if sig["side"] == "buy" else "bear"
            setup_segments.append({
                "start_index": max(0, i - 3),
                "end_index": min(n - 1, i + 12),
                "high": round(float(sig["pattern_high"]), 4),
                "low": round(float(sig["pattern_low"]), 4),
                "kind": sig["kind"],
                "direction": direction,
            })
            events.append({
                "index": i,
                "time": _time_str(idx, i, intraday),
                "name": sig["kind"],
                "direction": direction,
                "ema": round(float(ema.iloc[i]), 4) if pd.notna(ema.iloc[i]) else None,
                "pattern_high": round(float(sig["pattern_high"]), 4),
                "pattern_low": round(float(sig["pattern_low"]), 4),
            })

        for i in range(n):
            still_active = []
            for tr in active:
                hit_tp = high.iloc[i] >= tr["tp"] if tr["side"] == "buy" else low.iloc[i] <= tr["tp"]
                hit_sl = low.iloc[i] <= tr["sl"] if tr["side"] == "buy" else high.iloc[i] >= tr["sl"]
                if hit_tp or hit_sl:
                    outcome = "SL" if hit_tp and hit_sl else ("TP" if hit_tp else "SL")
                    exit_price = tr["tp"] if outcome == "TP" else tr["sl"]
                    pnl_points = exit_price - tr["entry"] if tr["side"] == "buy" else tr["entry"] - exit_price
                    pnl_rr = pnl_points / tr["risk"] if tr["risk"] > 0 else 0.0
                    balance += pnl_points * 100000 * 0.01
                    tr.update({
                        "exit_index": int(i),
                        "exit_time": _time_str(idx, i, intraday),
                        "status": outcome,
                        "pnl_points": round(float(pnl_points), 5),
                        "pnl_rr": round(float(pnl_rr), 3),
                        "pnl_pct": round(float((pnl_points * 100000) / max(balance, 1e-9) * 100), 3),
                    })
                    trades.append(tr)
                else:
                    still_active.append(tr)
            active = still_active

            for sig in sig_by_index.get(i, []):
                entry_i = i + 1 if entry_mode == "next_open" else i
                if entry_i >= n:
                    continue
                entry = float(open_.iloc[entry_i] if entry_mode == "next_open" else close.iloc[i])
                side = sig["side"]
                sl = float(sig["signal_low"] if side == "buy" and sl_mode == "signal" else sig["pattern_low"] if side == "buy" else sig["signal_high"] if sl_mode == "signal" else sig["pattern_high"])
                if side == "buy" and sl >= entry:
                    continue
                if side == "sell" and sl <= entry:
                    continue
                risk = abs(entry - sl)
                if risk <= 0:
                    continue
                tp = entry + float(rr) * risk if side == "buy" else entry - float(rr) * risk
                tr = {
                    "signal_index": int(i),
                    "entry_index": int(entry_i),
                    "exit_index": None,
                    "signal_time": _time_str(idx, i, intraday),
                    "entry_time": _time_str(idx, entry_i, intraday),
                    "exit_time": None,
                    "side": side,
                    "kind": sig["kind"],
                    "entry": round(float(entry), 4),
                    "sl": round(float(sl), 4),
                    "tp": round(float(tp), 4),
                    "risk": round(float(risk), 4),
                    "rr": round(float(rr), 2),
                    "status": "OPEN",
                    "pnl_points": 0.0,
                    "pnl_rr": 0.0,
                    "pnl_pct": 0.0,
                }
                active.append(tr)
                end_i = min(n - 1, entry_i + 20)
                trade_segments.append({
                    "start_index": int(entry_i),
                    "end_index": int(end_i),
                    "direction": "bull" if side == "buy" else "bear",
                    "kind": sig["kind"],
                    "entry": round(float(entry), 4),
                    "sl": round(float(sl), 4),
                    "tp": round(float(tp), 4),
                })

        trades.extend(active)
        tp_count = sum(1 for t in trades if t["status"] == "TP")
        sl_count = sum(1 for t in trades if t["status"] == "SL")
        closed_count = tp_count + sl_count
        gross_profit = sum(float(t["pnl_points"]) for t in trades if float(t["pnl_points"]) > 0)
        gross_loss = abs(sum(float(t["pnl_points"]) for t in trades if float(t["pnl_points"]) < 0))
        net_pnl = sum(float(t["pnl_points"]) for t in trades)
        timeframe = "Unknown"
        if isinstance(idx, pd.DatetimeIndex) and len(idx) >= 2:
            minutes = (idx[1] - idx[0]).total_seconds() / 60
            timeframe = {1: "1m", 5: "5m", 15: "15m", 30: "30m", 60: "1h", 240: "4h", 1440: "1D"}.get(int(minutes), f"{int(minutes)}m")
        dashboard = {
            "timeframe": timeframe,
            "rr": float(rr),
            "ema": int(ema_len),
            "sl_mode": sl_mode,
            "body_mult": float(body_mult),
            "total_buy_signals": sum(1 for s in signal_defs if s["side"] == "buy"),
            "total_sell_signals": sum(1 for s in signal_defs if s["side"] == "sell"),
            "total_signals": len(signal_defs),
            "total_trades": len(trades),
            "closed_trades": closed_count,
            "open_trades": sum(1 for t in trades if t["status"] == "OPEN"),
            "tp_count": tp_count,
            "sl_count": sl_count,
            "winrate_pct": round(tp_count / closed_count * 100, 2) if closed_count else 0.0,
            "tp_points": round(float(gross_profit), 5),
            "sl_points": round(float(gross_loss), 5),
            "net_points": round(float(net_pnl), 5),
            "net_rr": round(sum(float(t["pnl_rr"]) for t in trades), 3),
            "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else None,
        }

        def _line(series: pd.Series) -> list:
            return [None if pd.isna(v) else round(float(v), 4) for v in series.tolist()]

        return {
            "signals": _sanitize_events(events, drop_conflicts=False),
            "setup_segments": setup_segments[-180:],
            "trade_segments": trade_segments[-140:],
            "trades": trades[-220:],
            "ema": _line(ema),
            "dashboard": dashboard,
            "params": {"rr": float(rr), "ema_len": int(ema_len), "body_mult": float(body_mult), "sl_mode": sl_mode, "entry_mode": entry_mode},
        }
    except Exception:
        return {"signals": [], "trade_segments": [], "setup_segments": [], "trades": [], "dashboard": {}}


def _compute_all_legacy(df: pd.DataFrame, params: dict | None = None) -> dict:
    """
    Run all self-indc indicators. Returns dict consumed by server.py.
    Keys prefixed with 'si_' to avoid collision with existing indicators.
    """
    params = params or {}
    raw = {
        # ── Batch 1 (original 11) ──────────────────────────────────────────
        "si_cdl":         cdl_patterns_adv(df),
        "si_outside_rev": outside_reversal(df),
        "si_three_inside": three_inside(df),
        "si_three_inside_filtered": three_inside_filtered(df),
        "si_dark_cloud":  dark_cloud_piercing(df),
        "si_lrb":         liquid_reversal_bands(df),
        "si_adaptive_flow": adaptive_flow(df),
        "si_liq_intelg":  liquidity_intelligence(df),
        "si_rsi_div_auto": rsi_div_auto(df),
        "si_liquidity_entry": liquidity_entry(df),
        "si_delta_vp":    delta_vp(df),
        "si_problty_grid": problty_grid(df),
        "si_dual_ma_osc": dual_ma_osc(df),
        "si_ichi_trend_osc": ichimoku_trend_oscillator(df),
        "si_fmfm300": fmfm300_indicator(df),
        "si_inside_candle_strategy": inside_candle_strategy(df),
        "si_sweep_inside_rr": sweep_inside_rr_strategy(df),
        "si_hybrid_ml_cpr": hybrid_ml_cpr(df),
        "si_vwap_bb_ml_conf": vwap_bb_ml_conf(df),
        "si_swing_break": swing_breakout_sequence(df),
        "si_ctz_gann":    ctz_gann_swing(df),
        "si_opening_range_rev": opening_range_reversal(df),
        "si_hyb_opening_range_rev": hyb_opening_range_reversal(df),
        "si_sfb_hybrid": sfp_hybrid_markers(
            df,
            trend_fast_len=int(params.get("sfb_trend_fast_len", 9)),
            trend_slow_len=int(params.get("sfb_trend_slow_len", 18)),
        ),
        "si_vol_exh":     vol_exhaustion_markers(df),
        "si_rsi_div":     rsi_divergence_sub(df),
        "si_cpr":         cpr_levels(df),
        "si_swing_str":   swing_structure(df),
        "si_bos":         smc_bos_markers(df),
        "si_choch":       smc_choch_markers(df),
        "si_inside_out":  inside_outside_bar(df),
        # ── Batch 2 (new 16) ──────────────────────────────────────────────
        "si_sfp":         sfp_markers(df),
        "si_cdl_mb":      cdl_multibar_markers(df),
        "si_fractal":     si_fractal_markers(df),
        "si_bb_break":    bb_breakout(df),
        "si_bahai":       bahai_reversal_markers(df),
        "si_hs":          chart_hs_markers(df),
        "si_dbl":         double_top_bottom_markers(df),
        "si_rev_radar":   reversal_radar_markers(df),
        "si_nbar":        n_bar_reversal_markers(df),
        "si_impulse":     impulse_trend_markers(df),
        "si_hourly_pvt":  cm_hourly_pivots(df),
        "si_wekly_pivot": wekly_pivot(df),
        "si_strg_pivt":   strg_pivt(df),
        "si_cm_strg_pivt": cm_strg_pivt(df),
        "si_fib":         fibonacci_markers(df),
        "si_trend_sig":   trend_signals_markers(df),
        "si_vwap_conf":   vwap_bb_confluence(df),
        "si_vwap_super":  vwap_bb_super_confluence(df),
        "si_mp_va":       mp_value_area_markers(df),
        # ── Batch 3 (10 new indicators) ───────────────────────────────────
        "si_fvg":         smc_fvg_markers(df),
        "si_ob":          smc_ob_markers(df),
        "si_twin_range":  twin_range_filter_markers(df),
        "si_hybrid_ml":   hybrid_ml_vwap_bb_markers(df),
        "si_ichimoku":    tti_ichimoku_markers(df),
        "si_chandelier":  finta_chandelier_markers(df),
        "si_trendln":     trendln_breakout_markers(df),
        "si_curve":       curve_circle_markers(df),
        "si_harmonic":    harmonic_pattern_markers(df),
        "si_sbs":         sbs_swing_markers(df),
        # â”€â”€ Batch 4 (Missed/Redundant/Special) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        "si_zz_swing":    zigzag_swing_markers(df),
        "si_st_talipp":   talipp_supertrend_markers(df),
        "si_macd_ta":     ta_macd_markers(df),
        "si_kc_pyti":     pyti_keltner_markers(df),
        "si_sar_tapy":    tapy_psar_markers(df),
        "si_rsi_ss":      stockstats_rsi_markers(df),
        "si_har_zz":      harmonic_patterns_zz_markers(df),
        "si_cpr_v4":      cpr_vedhaviyash4_levels(df),
        "si_flowscope":   flowscope_markers(df),
        "si_mk_inside":   inside_outside_mk_markers(df),
        "si_pta_cdl":     pandas_ta_cdl_markers(df),

    }
    open_times = _session_open_times(df)
    return {k: _sanitize_payload(v, open_times) for k, v in raw.items()}


@dataclass(frozen=True)
class IndicatorMeta:
    key: str
    label: str
    category: str
    visual_type: str
    compute_fn: object
    default_params: dict
    supports_replay: bool = True
    is_canvas_overlay: bool = False


def _meta(
    key: str,
    label: str,
    category: str,
    visual_type: str,
    compute_fn,
    default_params: dict | None = None,
    supports_replay: bool = True,
    is_canvas_overlay: bool = False,
) -> IndicatorMeta:
    return IndicatorMeta(
        key=key,
        label=label,
        category=category,
        visual_type=visual_type,
        compute_fn=compute_fn,
        default_params=default_params or {},
        supports_replay=supports_replay,
        is_canvas_overlay=is_canvas_overlay,
    )


def _sfb_hybrid_compute(df: pd.DataFrame, params: dict | None = None):
    params = params or {}
    return sfp_hybrid_markers(
        df,
        trend_fast_len=int(params.get("sfb_trend_fast_len", params.get("trend_fast_len", 9))),
        trend_slow_len=int(params.get("sfb_trend_slow_len", params.get("trend_slow_len", 18))),
    )


SELF_INDC_REGISTRY: dict[str, IndicatorMeta] = {
    "si_cdl": _meta("si_cdl", "Advanced Candle Patterns", "pattern", "marker-only", cdl_patterns_adv),
    "si_outside_rev": _meta("si_outside_rev", "Outside Reversal", "pattern", "marker-only", outside_reversal),
    "si_three_inside": _meta("si_three_inside", "Three Inside", "pattern", "marker-only", three_inside),
    "si_three_inside_filtered": _meta("si_three_inside_filtered", "Three Inside Filtered", "pattern", "marker-only", three_inside_filtered),
    "si_dark_cloud": _meta("si_dark_cloud", "Dark Cloud / Piercing", "pattern", "marker-only", dark_cloud_piercing),
    "si_lrb": _meta("si_lrb", "Liquid Reversal Bands", "levels", "price-levels", liquid_reversal_bands),
    "si_adaptive_flow": _meta("si_adaptive_flow", "Adaptive Flow", "trend", "price-levels", adaptive_flow),
    "si_liq_intelg": _meta("si_liq_intelg", "Liquidity Intelligence", "liquidity", "trade-lines", liquidity_intelligence),
    "si_rsi_div_auto": _meta("si_rsi_div_auto", "RSI Divergence Auto", "momentum", "marker-only", rsi_div_auto),
    "si_liquidity_entry": _meta("si_liquidity_entry", "Liquidity Entry", "liquidity", "trade-lines", liquidity_entry),
    "si_delta_vp": _meta("si_delta_vp", "Delta Volume Profile", "volume", "price-levels", delta_vp),
    "si_problty_grid": _meta("si_problty_grid", "Probability Grid", "session", "canvas-overlay", problty_grid, is_canvas_overlay=True),
    "si_dual_ma_osc": _meta("si_dual_ma_osc", "Dual MA SD Oscillator", "momentum", "oscillator-pane", dual_ma_osc),
    "si_ichi_trend_osc": _meta("si_ichi_trend_osc", "Ichimoku Trend Oscillator", "momentum", "oscillator-pane", ichimoku_trend_oscillator),
    "si_fmfm300": _meta("si_fmfm300", "FMFM300", "pattern", "canvas-overlay", fmfm300_indicator, is_canvas_overlay=True),
    "si_inside_candle_strategy": _meta("si_inside_candle_strategy", "Inside Candle Strategy", "pattern", "trade-lines", inside_candle_strategy),
    "si_sweep_inside_rr": _meta("si_sweep_inside_rr", "SWEP+INSD", "pattern", "trade-lines", sweep_inside_rr_strategy),
    "si_hybrid_ml_cpr": _meta("si_hybrid_ml_cpr", "Hybrid ML CPR", "ml", "trade-lines", hybrid_ml_cpr),
    "si_vwap_bb_ml_conf": _meta("si_vwap_bb_ml_conf", "VWAP-BB ML Conf", "ml", "trade-lines", vwap_bb_ml_conf),
    "si_swing_break": _meta("si_swing_break", "Swing Breakout Sequence", "structure", "marker-only", swing_breakout_sequence),
    "si_ctz_gann": _meta("si_ctz_gann", "CTZ Gann Swing", "gann", "price-levels", ctz_gann_swing),
    "si_opening_range_rev": _meta("si_opening_range_rev", "Opening Range Reversal", "session", "trade-lines", opening_range_reversal),
    "si_hyb_opening_range_rev": _meta("si_hyb_opening_range_rev", "Hybrid Opening Range Reversal", "session", "trade-lines", hyb_opening_range_reversal),
    "si_sfb_hybrid": _meta("si_sfb_hybrid", "SFP Hybrid", "liquidity", "marker-only", _sfb_hybrid_compute, {"sfb_trend_fast_len": 9, "sfb_trend_slow_len": 18}),
    "si_vol_exh": _meta("si_vol_exh", "Volume Exhaustion", "volume", "marker-only", vol_exhaustion_markers),
    "si_rsi_div": _meta("si_rsi_div", "RSI Divergence", "momentum", "oscillator-pane", rsi_divergence_sub),
    "si_cpr": _meta("si_cpr", "CPR Levels", "levels", "price-levels", cpr_levels),
    "si_swing_str": _meta("si_swing_str", "Swing Structure", "structure", "marker-only", swing_structure),
    "si_bos": _meta("si_bos", "SMC BOS", "structure", "marker-only", smc_bos_markers),
    "si_choch": _meta("si_choch", "SMC CHOCH", "structure", "marker-only", smc_choch_markers),
    "si_inside_out": _meta("si_inside_out", "Inside / Outside Bar", "pattern", "marker-only", inside_outside_bar),
    "si_sfp": _meta("si_sfp", "Swing Failure Pattern", "liquidity", "marker-only", sfp_markers),
    "si_cdl_mb": _meta("si_cdl_mb", "Multi-Bar Candles", "pattern", "marker-only", cdl_multibar_markers),
    "si_fractal": _meta("si_fractal", "Fractals", "structure", "marker-only", si_fractal_markers),
    "si_bb_break": _meta("si_bb_break", "BB Breakout", "volatility", "main-line", bb_breakout),
    "si_bahai": _meta("si_bahai", "Bahai Reversal", "pattern", "marker-only", bahai_reversal_markers),
    "si_hs": _meta("si_hs", "Head and Shoulders", "pattern", "marker-only", chart_hs_markers),
    "si_dbl": _meta("si_dbl", "Double Top / Bottom", "pattern", "marker-only", double_top_bottom_markers),
    "si_rev_radar": _meta("si_rev_radar", "Reversal Radar", "pattern", "marker-only", reversal_radar_markers),
    "si_nbar": _meta("si_nbar", "N-Bar Reversal", "pattern", "marker-only", n_bar_reversal_markers),
    "si_impulse": _meta("si_impulse", "Impulse Trend", "trend", "marker-only", impulse_trend_markers),
    "si_hourly_pvt": _meta("si_hourly_pvt", "Hourly Pivots", "levels", "price-levels", cm_hourly_pivots),
    "si_wekly_pivot": _meta("si_wekly_pivot", "Weekly Pivot", "levels", "price-levels", wekly_pivot),
    "si_strg_pivt": _meta("si_strg_pivt", "Strong Pivot", "levels", "price-levels", strg_pivt),
    "si_cm_strg_pivt": _meta("si_cm_strg_pivt", "CM Strong Pivot", "levels", "price-levels", cm_strg_pivt),
    "si_fib": _meta("si_fib", "Fibonacci Markers", "levels", "price-levels", fibonacci_markers),
    "si_trend_sig": _meta("si_trend_sig", "Trend Signals", "trend", "marker-only", trend_signals_markers),
    "si_vwap_conf": _meta("si_vwap_conf", "VWAP Confluence", "vwap", "price-levels", vwap_bb_confluence),
    "si_vwap_super": _meta("si_vwap_super", "VWAP Super Confluence", "vwap", "price-levels", vwap_bb_super_confluence),
    "si_mp_va": _meta("si_mp_va", "Market Profile Value Area", "volume", "price-levels", mp_value_area_markers),
    "si_fvg": _meta("si_fvg", "SMC FVG", "structure", "marker-only", smc_fvg_markers),
    "si_ob": _meta("si_ob", "SMC Order Blocks", "structure", "marker-only", smc_ob_markers),
    "si_twin_range": _meta("si_twin_range", "Twin Range Filter", "trend", "marker-only", twin_range_filter_markers),
    "si_hybrid_ml": _meta("si_hybrid_ml", "Hybrid ML VWAP-BB", "ml", "trade-lines", hybrid_ml_vwap_bb_markers),
    "si_ichimoku": _meta("si_ichimoku", "Ichimoku", "trend", "marker-only", tti_ichimoku_markers),
    "si_chandelier": _meta("si_chandelier", "Chandelier Exit", "trend", "marker-only", finta_chandelier_markers),
    "si_trendln": _meta("si_trendln", "Trendline Breakout", "trendline", "canvas-overlay", trendln_breakout_markers, is_canvas_overlay=True),
    "si_curve": _meta("si_curve", "Curve Pattern", "pattern", "canvas-overlay", curve_circle_markers, is_canvas_overlay=True),
    "si_harmonic": _meta("si_harmonic", "Harmonic Pattern", "pattern", "canvas-overlay", harmonic_pattern_markers, is_canvas_overlay=True),
    "si_sbs": _meta("si_sbs", "SBS Swing", "structure", "marker-only", sbs_swing_markers),
    "si_zz_swing": _meta("si_zz_swing", "ZigZag Swing", "structure", "marker-only", zigzag_swing_markers),
    "si_st_talipp": _meta("si_st_talipp", "TALib Supertrend", "trend", "marker-only", talipp_supertrend_markers),
    "si_macd_ta": _meta("si_macd_ta", "TA MACD", "momentum", "marker-only", ta_macd_markers),
    "si_kc_pyti": _meta("si_kc_pyti", "PyTI Keltner", "volatility", "marker-only", pyti_keltner_markers),
    "si_sar_tapy": _meta("si_sar_tapy", "Tapy PSAR", "trend", "marker-only", tapy_psar_markers),
    "si_rsi_ss": _meta("si_rsi_ss", "Stockstats RSI", "momentum", "marker-only", stockstats_rsi_markers),
    "si_har_zz": _meta("si_har_zz", "Harmonic ZigZag", "pattern", "marker-only", harmonic_patterns_zz_markers),
    "si_cpr_v4": _meta("si_cpr_v4", "CPR v4", "levels", "price-levels", cpr_vedhaviyash4_levels),
    "si_flowscope": _meta("si_flowscope", "FlowScope", "volume", "marker-only", flowscope_markers),
    "si_mk_inside": _meta("si_mk_inside", "MK Inside / Outside", "pattern", "marker-only", inside_outside_mk_markers),
    "si_pta_cdl": _meta("si_pta_cdl", "Pandas TA Candles", "pattern", "marker-only", pandas_ta_cdl_markers),
}


def indicator_metadata() -> dict[str, dict]:
    return {
        key: {
            "key": meta.key,
            "label": meta.label,
            "category": meta.category,
            "visual_type": meta.visual_type,
            "default_params": dict(meta.default_params),
            "supports_replay": meta.supports_replay,
            "is_canvas_overlay": meta.is_canvas_overlay,
        }
        for key, meta in SELF_INDC_REGISTRY.items()
    }


def compute_selected(df: pd.DataFrame, keys: list[str], params: dict | None = None) -> dict:
    """
    Run only requested self-indc indicators. Unknown keys raise KeyError so API
    callers can return 404 instead of silently hiding integration mistakes.
    """
    params = params or {}
    open_times = _session_open_times(df)
    out = {}
    for key in keys:
        meta = SELF_INDC_REGISTRY.get(key)
        if meta is None:
            raise KeyError(key)
        key_params = dict(meta.default_params)
        if isinstance(params.get(key), dict):
            key_params.update(params[key])
        key_params.update({k: v for k, v in params.items() if not isinstance(v, dict)})
        try:
            if meta.default_params:
                value = meta.compute_fn(df, key_params)
            else:
                value = meta.compute_fn(df)
        except Exception:
            value = {}
        out[key] = _sanitize_payload(value, open_times)
    return out


def compute_all(df: pd.DataFrame, params: dict | None = None) -> dict:
    """
    Run all self-indc indicators. Returns dict consumed by server.py.
    Keys prefixed with 'si_' to avoid collision with existing indicators.
    """
    return compute_selected(df, list(SELF_INDC_REGISTRY.keys()), params=params)
