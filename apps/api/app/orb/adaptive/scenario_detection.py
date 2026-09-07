"""Complete A-G failure-scenario detector for the adaptive ORB engine.

Observed price/clock failures are calculated locally. External failures are
recognized only from causal, expiring Capability facts created by verified
upstream adapters. The detector deliberately distinguishes:

* OBSERVED_*        - the failure/risk is presently evidenced;
* RISK_ARMED_*      - a precursor is present but the failure has not occurred;
* NOT_OBSERVED      - enough data exists and the condition is absent;
* UNOBSERVABLE_*    - required independent input is missing.

No missing external state is interpreted as bullish, bearish, or safe.
"""
from __future__ import annotations

from .contracts import Capability


def _names(capabilities: tuple[Capability, ...], now: int) -> set[str]:
    return {
        c.name for c in capabilities
        if c.available_ns <= now < c.expires_ns and c.status in {"VALID", "BLOCKED"}
    }


def detect(features: dict, errors: tuple[str, ...], capabilities: tuple[Capability, ...], now: int) -> dict[str, str]:
    names = _names(capabilities, now)
    invalid = bool(errors)

    def ext(name: str, *, risk_only: bool = False) -> str:
        if name in names:
            return "RISK_ARMED_EXTERNAL" if risk_only else "OBSERVED_EXTERNAL_FLAG"
        return "UNOBSERVABLE_EXTERNAL_INPUT"

    gap_atr = float(features.get("gap_atr") or 0.0)
    failure_count = int(features.get("failure_count") or 0)
    observed_expansion = float(features.get("observed_expansion") or 0.0)
    or_width_atr = float(features.get("or_width_atr") or 0.0)
    first_bar_range_atr = float(features.get("first_bar_range_atr") or 0.0)
    elapsed = int(features.get("elapsed_minutes") or 0)
    range_locked = bool(features.get("range_locked"))

    out: dict[str, str] = {}

    # A. Regime
    out["A01"] = "OBSERVED_PRICE_FLAG" if features.get("chop_risk") else "NOT_OBSERVED_IN_VALID_PREFIX"
    out["A02"] = "OBSERVED_EXTERNAL_FLAG" if "VIX_COMA" in names else ("NOT_OBSERVED_VERIFIED_VIX" if "VIX" in names else "UNOBSERVABLE_EXTERNAL_INPUT")
    out["A03"] = "OBSERVED_EXTERNAL_FLAG" if {"VIX_SPIKE", "VIX_HIGH"} & names else ("NOT_OBSERVED_VERIFIED_VIX" if "VIX" in names else "UNOBSERVABLE_EXTERNAL_INPUT")
    if gap_atr > 1.5:
        out["A04"] = "RISK_ARMED_PRICE_FLAG"
    elif features.get("range_locked") or features.get("gap_class"):
        out["A04"] = "NOT_OBSERVED_IN_VALID_PREFIX"
    else:
        out["A04"] = "UNOBSERVABLE_INVALID_INPUT" if invalid else "UNOBSERVABLE_INCOMPLETE_PREFIX"
    if "NEWS_SHOCK" in names or "VIX_SPIKE" in names or observed_expansion > 2.0:
        out["A05"] = "OBSERVED_SHOCK_FLAG"
    elif "VIX" in names:
        out["A05"] = "NOT_OBSERVED_IN_AVAILABLE_INPUTS"
    else:
        out["A05"] = "UNOBSERVABLE_NEWS_INPUT_PRICE_PROXY_ONLY"

    # B. Signal
    out["B01"] = "OBSERVED_PRICE_FLAG" if failure_count > 0 else "NOT_OBSERVED_IN_VALID_PREFIX"
    out["B02"] = "OBSERVED_PRICE_FLAG" if range_locked and or_width_atr > 1.0 else ("NOT_OBSERVED_IN_VALID_PREFIX" if range_locked else "UNOBSERVABLE_INCOMPLETE_PREFIX")
    out["B03"] = "OBSERVED_PRICE_FLAG" if range_locked and or_width_atr < 0.25 else ("NOT_OBSERVED_IN_VALID_PREFIX" if range_locked else "UNOBSERVABLE_INCOMPLETE_PREFIX")
    out["B04"] = "OBSERVED_PRICE_FLAG" if first_bar_range_atr > 2.0 else "NOT_OBSERVED_IN_VALID_PREFIX"
    # 09:15 + 135 minutes = 11:30. This is scenario staleness, independent of
    # the selected policy's potentially earlier last-entry cutoff.
    out["B05"] = "OBSERVED_CLOCK_FLAG" if elapsed >= 135 else "NOT_OBSERVED_IN_VALID_PREFIX"
    out["B06"] = "OBSERVED_PRICE_FLAG" if failure_count >= 2 else "NOT_OBSERVED_IN_VALID_PREFIX"

    # C. Event
    if "RESULT_DAY" in names:
        out["C01"] = "OBSERVED_EVENT_AND_WHIPSAW" if failure_count > 0 or features.get("two_sided_bar") else "RISK_ARMED_EXTERNAL"
    else:
        out["C01"] = "UNOBSERVABLE_EXTERNAL_INPUT"
    out["C02"] = ext("RBI_MPC_WINDOW", risk_only=True)
    out["C03"] = ext("MACRO_EVENT_DAY", risk_only=True)
    if "EX_DIVIDEND_UNADJUSTED" in names:
        out["C04"] = "OBSERVED_EXTERNAL_FLAG"
    elif "EX_DIVIDEND_ADJUSTED" in names:
        out["C04"] = "NOT_OBSERVED_VERIFIED_ADJUSTMENT"
    elif "EX_DIVIDEND" in names:
        out["C04"] = "RISK_ARMED_EXTERNAL"
    else:
        out["C04"] = "UNOBSERVABLE_EXTERNAL_INPUT"

    # D. Instrument
    out["D01"] = ext("CIRCUIT_LOCK")
    out["D02"] = ext("SURVEILLANCE_RESTRICTED")
    out["D03"] = ext("ILLIQUID_OR_SLIPPAGE", risk_only=True)
    out["D04"] = ext("FNO_BAN")

    # E. Data / execution
    out["E01"] = "OBSERVED_DATA_INTEGRITY_FAILURE" if invalid or {"FEED_LAG", "BAD_TICK"} & names else "NOT_OBSERVED_IN_VALID_PREFIX"
    if {"ORDER_REJECTED", "BROKER_SQUAREOFF_RISK"} & names:
        out["E02"] = "OBSERVED_EXTERNAL_FLAG"
    else:
        out["E02"] = "UNOBSERVABLE_EXECUTION_INPUT"
    out["E03"] = "OBSERVED_EXTERNAL_FLAG" if "PIT_VIOLATION" in names else ("CAUSAL_PREFIX_GUARD_ENFORCED" if not invalid else "UNOBSERVABLE_INVALID_INPUT")
    out["E04"] = "OBSERVED_EXTERNAL_FLAG" if "BACKTEST_LIVE_MISMATCH" in names else "UNOBSERVABLE_REQUIRES_REPLAY_LIVE_COMPARISON"

    # F. Derivatives
    if "EXPIRY_DAY" in names and "MAX_PAIN_NEAR" in names:
        out["F01"] = "RISK_ARMED_DERIVATIVES"
    elif "EXPIRY_DAY" in names:
        out["F01"] = "RISK_ARMED_EXPIRY_WITHOUT_PINNING_CONFIRMATION"
    elif "MAX_PAIN_NEAR" in names:
        out["F01"] = "RISK_ARMED_MAX_PAIN_WITHOUT_EXPIRY_FLAG"
    else:
        out["F01"] = "UNOBSERVABLE_EXTERNAL_INPUT"
    if "GAMMA_SQUEEZE" in names:
        out["F02"] = "OBSERVED_EXTERNAL_FLAG"
    elif "NEGATIVE_DEALER_GAMMA" in names and ("VIX_SPIKE" in names or observed_expansion > 2.0):
        out["F02"] = "RISK_ARMED_DERIVATIVES_AND_PRICE"
    elif "DEALER_GEX" in names:
        out["F02"] = "NOT_OBSERVED_IN_AVAILABLE_INPUTS"
    else:
        out["F02"] = "UNOBSERVABLE_DEALER_SIGN_INPUT"
    out["F03"] = ext("OI_WALL_REJECTION")
    if "ROLLOVER_DISTORTION" in names:
        out["F04"] = "OBSERVED_EXTERNAL_FLAG"
    elif "ROLLOVER_STRONG_POSITIVE_BASIS" in names:
        out["F04"] = "RISK_ARMED_DERIVATIVES"
    elif "ROLLOVER" in names:
        out["F04"] = "NOT_OBSERVED_IN_AVAILABLE_INPUTS"
    else:
        out["F04"] = "UNOBSERVABLE_EXTERNAL_INPUT"

    # G. Statistical
    out["G01"] = ext("EDGE_DECAY")
    out["G02"] = ext("OVERFIT_RISK")
    out["G03"] = ext("SMALL_SAMPLE")

    if invalid:
        # Do not let ordinary price-derived NOT_OBSERVED states imply safety
        # when the price prefix itself is invalid.
        for key in ("A01", "A04", "A05", "B01", "B02", "B03", "B04", "B06"):
            if out[key].startswith("NOT_OBSERVED"):
                out[key] = "UNOBSERVABLE_INVALID_INPUT"
    return out
