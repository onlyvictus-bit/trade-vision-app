"""Opening-scenario context for ORB (v2.01 track, M1 foundation).

Classifies every possible way a session can open so the engine never trades
blind: gap direction/size x position vs previous-day levels x CPR width class.

Single source of truth for gap/CPR math inside the orb domain. The behavior
layer may import this module; this module must never import the behavior
layer (prevents circular imports — see v1.99 PTA registry incident).

PIT discipline: every input must come from sessions strictly before the
current one. Callers pass adjusted-series aggregates (CTX-02); degenerate
prev-day input yields `context_suspect`, never fabricated context.

Rule provenance: ORB_STRATEGY_MEMORANDUM.md v2.4 (GAP-01, CPR-01..04,
Z1-Z5, CTX-02/03). Thresholds reuse the repo classifier semantics
(`behavior/context_engines.py::_gap_type`); parity-tested, never duplicated.
"""

from __future__ import annotations

import pandas as pd

GAP_FLAT_PCT = 0.1
GAP_LARGE_PCT_FLOOR = 1.0
GAP_LARGE_ATR_MULT = 1.4
CPR_NARROW_ATR = 0.5
CPR_WIDE_ATR = 1.0
CPR_WIDE_PCT = 0.6
CORPORATE_ACTION_GUARD_PCT = 20.0


def gap_state(gap_pct: float, atr_pct: float) -> str:
    """GAP-01 bias lock. Mirrors behavior._gap_type EXACTLY (parity-tested):
    FLAT boundary is inclusive (<= 0.1); LARGE >= max(1.0, 1.4 x ATR%)."""
    if abs(gap_pct) <= GAP_FLAT_PCT:
        return "FLAT"
    if abs(gap_pct) >= max(GAP_LARGE_PCT_FLOOR, GAP_LARGE_ATR_MULT * atr_pct):
        return "LARGE_GAP_UP" if gap_pct > 0 else "LARGE_GAP_DOWN"
    return "GAP_UP" if gap_pct > 0 else "GAP_DOWN"


def cpr_levels(pdh: float, pdl: float, pdc: float) -> tuple[float, float, float]:
    """Returns (pivot, bc, tc) ordered so TC < BC. Verified formula."""
    pivot = (pdh + pdl + pdc) / 3.0
    bc = (pdh + pdl) / 2.0
    tc = pivot + (pivot - bc)
    return pivot, min(bc, tc), max(bc, tc)


def cpr_class(width_atr: float, width_pct: float) -> str:
    """CPR-01 precedence partition: NARROW checked FIRST, then WIDE, else NORMAL.
    One day maps to exactly one class (fixes the v2.0 both-fire bug)."""
    if width_atr < CPR_NARROW_ATR:
        return "NARROW"
    if width_atr > CPR_WIDE_ATR or width_pct > CPR_WIDE_PCT:
        return "WIDE"
    return "NORMAL"


def zone_at(price: float, pdh: float, pdl: float, tc: float, bc: float) -> str:
    """Exclusive Z1-Z5 price zones (v2.1 partition). Exactly one fires."""
    if price >= pdh:
        return "Z1"
    if price >= bc:
        return "Z2"
    if price >= tc:
        return "Z3"
    if price >= pdl:
        return "Z4"
    return "Z5"


def atr_wilder(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Wilder ATR(14). Needs period + 1 daily bars minimum."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return float(tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().iloc[-1])


def classify_opening(
    *,
    symbol: str,
    session_date: str,
    prev_high: float,
    prev_low: float,
    prev_close: float,
    today_open: float,
    atr14: float,
) -> dict:
    """Full opening scenario for one session. Pure function, no I/O."""
    suspect_reason: str | None = None
    if prev_high <= 0 or prev_low <= 0 or prev_close <= 0 or atr14 <= 0:
        suspect_reason = "non_positive_input"
    elif prev_high == prev_low:
        suspect_reason = "degenerate_prev_day_pdh_eq_pdl"  # CTX-03
    gap_pct = (today_open - prev_close) / prev_close * 100.0
    if abs(gap_pct) > CORPORATE_ACTION_GUARD_PCT:
        suspect_reason = "corporate_action_suspect_abs_gap_gt_20"  # CTX-02
    atr_pct = atr14 / prev_close * 100.0 if atr14 > 0 else 0.0
    pivot, tc, bc = cpr_levels(prev_high, prev_low, prev_close)
    cpr_width = bc - tc
    width_atr = cpr_width / atr14 if atr14 > 0 else 0.0
    width_pct = cpr_width / prev_close * 100.0
    return {
        "symbol": symbol,
        "session_date": session_date,
        "gap_pct": round(gap_pct, 4),
        "gap_state": gap_state(gap_pct, atr_pct),
        "atr_pct": round(atr_pct, 4),
        "pdh": prev_high,
        "pdl": prev_low,
        "pdc": prev_close,
        "pivot": round(pivot, 4),
        "bc": round(bc, 4),
        "tc": round(tc, 4),
        "cpr_width": round(cpr_width, 4),
        "width_atr": round(width_atr, 4),
        "width_pct": round(width_pct, 4),
        "cpr_class": cpr_class(width_atr, width_pct),
        "zone_at_open": zone_at(today_open, prev_high, prev_low, tc, bc),
        "context_suspect": suspect_reason is not None,
        "suspect_reason": suspect_reason,
    }


def daily_from_intraday(frame: pd.DataFrame) -> pd.DataFrame:
    """Resample IST intraday OHLCV to daily session bars (date from index)."""
    daily = frame.resample("D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return daily.dropna(subset=["open", "high", "low", "close"])


def classify_history(    symbol: str,
    daily: pd.DataFrame,
    opens: dict[str, float],
    *,
    atr_period: int = 14,
) -> list[dict]:
    """Classify every session with enough history. `opens` maps YYYY-MM-DD ->
    that session's first-bar open. Sessions lacking D-1 data or ATR depth are
    skipped (never fabricated)."""
    records: list[dict] = []
    dates = list(daily.index)
    for i in range(atr_period + 1, len(dates)):
        prev = dates[i - 1]
        key = dates[i].strftime("%Y-%m-%d")
        if key not in opens:
            continue
        window = daily.iloc[i - atr_period - 1 : i]
        atr = atr_wilder(window["high"], window["low"], window["close"], atr_period)
        records.append(
            classify_opening(
                symbol=symbol,
                session_date=key,
                prev_high=float(window.loc[prev, "high"]),
                prev_low=float(window.loc[prev, "low"]),
                prev_close=float(window.loc[prev, "close"]),
                today_open=float(opens[key]),
                atr14=atr,
            )
        )
    return records


# --- Day-type prediction: combinations of behaviors -> TREND / RANGE --------

# Ex-post outcome thresholds. RESEARCH PRIORS (documented, calibratable) -
# they label completed sessions for validation only, never as live inputs.
TREND_MIN_RANGE_ATR = 1.0
RANGE_MAX_RANGE_ATR = 0.7
TREND_CLOSE_LOCATION = 0.67  # close in outer third = directional expansion


def predict_day_type(scenario: dict) -> dict:
    """Opening combination -> day-type prediction (memo CPR-02 + gap layer).

    Condition engine over behavior combinations - one code path for all 500
    stocks, no per-stock tuning. Precedence (memo ladder order):
    suspect > LARGE gap > Z3-inside > CPR class > default UNCLASSIFIED.
    Returns {prediction, direction, reasons} with memo rule IDs cited.
    """
    reasons: list[str] = []
    if scenario.get("context_suspect"):
        return {
            "prediction": "UNCLASSIFIED",
            "direction": "either",
            "reasons": [f"CTX-suspect ({scenario.get('suspect_reason')}) - never predict on bad context"],
        }
    gap_state = str(scenario.get("gap_state", "FLAT"))
    if gap_state in ("LARGE_GAP_UP", "LARGE_GAP_DOWN"):
        direction = "up" if gap_state.endswith("UP") else "down"
        return {
            "prediction": "TREND_DAY",
            "direction": direction,
            "reasons": ["GAP-02 trend branch prior: large gap holds into trend day more often than not"],
        }
    if str(scenario.get("zone_at_open")) == "Z3":
        return {
            "prediction": "RANGE_DAY",
            "direction": "either",
            "reasons": ["CPR-02: inside-CPR (Z3) breakouts OFF - mean-reversion regime"],
        }
    cpr_class = str(scenario.get("cpr_class", "NORMAL"))
    if cpr_class == "NARROW":
        direction = "up" if gap_state == "GAP_UP" else ("down" if gap_state == "GAP_DOWN" else "either")
        return {
            "prediction": "TREND_DAY",
            "direction": direction,
            "reasons": ["CPR-02: NARROW CPR - yesterday closed near mid-range, trend day likely"],
        }
    if cpr_class == "WIDE":
        return {
            "prediction": "RANGE_DAY",
            "direction": "either",
            "reasons": ["CPR-02: WIDE CPR - mean reversion likely, targets capped"],
        }
    return {
        "prediction": "UNCLASSIFIED",
        "direction": "either",
        "reasons": ["FLAT/NORMAL with no edge stated - no prediction is itself a decision"],
    }


def label_day_outcome(*, day_high: float, day_low: float, day_close: float, atr14: float) -> str:
    """Ex-post RESEARCH-ONLY label from a COMPLETED session. Never a live input.

    TREND_DAY: range >= 1.0x ATR with close in the outer third (directional
    expansion). RANGE_DAY: range < 0.7x ATR (contraction). Else MIXED.
    """
    if atr14 <= 0 or day_high < day_low:
        return "MIXED"
    range_atr = (day_high - day_low) / atr14
    if range_atr >= TREND_MIN_RANGE_ATR:
        location = (day_close - day_low) / (day_high - day_low) if day_high > day_low else 0.5
        if location >= TREND_CLOSE_LOCATION or location <= (1.0 - TREND_CLOSE_LOCATION):
            return "TREND_DAY"
        return "MIXED"
    if range_atr < RANGE_MAX_RANGE_ATR:
        return "RANGE_DAY"
    return "MIXED"
