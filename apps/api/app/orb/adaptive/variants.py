"""Research assessment of the complete 18-variant ORB catalogue.

All variants are evaluated from the same causal MarketSnapshot. A variant being
CONFIRMED here is a research setup observation, not permission to create a live
order. Existing Policy/TradePlan proof remains the only path to a paper
candidate. Variants requiring independent event/index/expiry information fail
closed when the matching Capability is absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from statistics import mean

from .contracts import MarketSnapshot, Policy, Side, Template, MINUTE, clock_ns


class VariantState(StrEnum):
    UNOBSERVABLE = "UNOBSERVABLE"
    WAITING = "WAITING"
    ARMED = "ARMED"
    CONFIRMED = "CONFIRMED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class VariantAssessment:
    variant_id: str
    name: str
    state: VariantState
    side: Side | None
    template: Template | None
    reason: str


CATALOGUE: tuple[tuple[str, str], ...] = (
    ("V01", "Classic ORB-15"),
    ("V02", "ORB-5 micro"),
    ("V03", "ORB-30"),
    ("V04", "Volume-confirmed ORB"),
    ("V05", "VWAP-filtered ORB"),
    ("V06", "Index-aligned ORB"),
    ("V07", "Narrow-OR expansion"),
    ("V08", "Wide-OR reduced-risk"),
    ("V09", "Gap-and-go"),
    ("V10", "Gap-fade ORR"),
    ("V11", "False-breakout reversal"),
    ("V12", "Pullback/retest entry"),
    ("V13", "Second-chance re-entry"),
    ("V14", "Post-result ORB"),
    ("V15", "PDH/PDL breakout"),
    ("V16", "Expiry-day ORB"),
    ("V17", "Afternoon range breakout"),
    ("V18", "Extension no-chase"),
)


def _caps(snapshot: MarketSnapshot) -> set[str]:
    return {
        c.name for c in snapshot.capabilities
        if c.available_ns <= snapshot.as_of_ns < c.expires_ns and c.status in {"VALID", "BLOCKED"}
    }


def _range(snapshot: MarketSnapshot, start_minute: int, duration: int):
    bars = snapshot.bars
    if not bars:
        return None
    minutes = bars[0].minutes
    if duration % minutes or (start_minute - 555) % minutes:
        return None
    start = clock_ns(snapshot.session_date, start_minute)
    end = clock_ns(snapshot.session_date, start_minute + duration)
    rows = [b for b in bars if start <= b.open_ns and b.close_ns <= end]
    expected = duration // minutes
    if len(rows) != expected or rows[0].open_ns != start or rows[-1].close_ns != end:
        return None
    for a, b in zip(rows, rows[1:]):
        if a.close_ns != b.open_ns:
            return None
    return {
        "high": max(b.high for b in rows),
        "low": min(b.low for b in rows),
        "volume_mean": mean(b.volume for b in rows),
        "end_ns": end,
    }


def _break(snapshot: MarketSnapshot, rng: dict | None, tick: float) -> tuple[Side | None, object | None]:
    if rng is None:
        return None, None
    post = [b for b in snapshot.bars if b.open_ns >= rng["end_ns"]]
    if not post:
        return None, None
    last = post[-1]
    if last.close > rng["high"] + tick:
        return Side.LONG, last
    if last.close < rng["low"] - tick:
        return Side.SHORT, last
    return None, last


def _a(variant_id: str, state: VariantState, side: Side | None, template: Template | None, reason: str) -> VariantAssessment:
    name = dict(CATALOGUE)[variant_id]
    return VariantAssessment(variant_id, name, state, side, template, reason)


def assess(snapshot: MarketSnapshot, features: dict, policy: Policy) -> tuple[VariantAssessment, ...]:
    caps = _caps(snapshot)
    tick = snapshot.prior.tick_size
    r5 = _range(snapshot, 555, 5)
    r15 = _range(snapshot, 555, 15)
    r30 = _range(snapshot, 555, 30)
    b5, last5 = _break(snapshot, r5, tick)
    b15, last15 = _break(snapshot, r15, tick)
    b30, last30 = _break(snapshot, r30, tick)
    gap_side = Side(features["gap_direction"]) if features.get("gap_direction") in {"LONG", "SHORT"} else None
    gap_atr = float(features.get("gap_atr") or 0.0)
    result: list[VariantAssessment] = []

    result.append(_a("V01", VariantState.CONFIRMED if b15 else VariantState.WAITING if r15 else VariantState.UNOBSERVABLE,
                     b15, Template.FIRST_BREAK, "15-minute OR close breakout" if b15 else "waiting for valid OR15 breakout"))
    result.append(_a("V02", VariantState.CONFIRMED if b5 else VariantState.WAITING if r5 else VariantState.UNOBSERVABLE,
                     b5, Template.FIRST_BREAK, "5-minute micro-OR breakout" if b5 else "native bars cannot yet prove OR5 breakout"))
    result.append(_a("V03", VariantState.CONFIRMED if b30 else VariantState.WAITING if r30 else VariantState.UNOBSERVABLE,
                     b30, Template.ACCEPTANCE, "30-minute OR breakout" if b30 else "waiting for complete OR30 and breakout"))

    if b15 and last15 is not None:
        ratio = last15.volume / max(float(r15["volume_mean"]), 1e-12) if r15 else 0.0
        vol_state = VariantState.CONFIRMED if ratio >= policy.minimum_volume_ratio else VariantState.BLOCKED
        result.append(_a("V04", vol_state, b15, Template.ACCEPTANCE,
                         f"breakout volume ratio={ratio:.4f}; minimum={policy.minimum_volume_ratio:.4f}"))
        vwap = features.get("session_vwap")
        agree = vwap is not None and (last15.close - float(vwap)) * b15.sign > 0
        result.append(_a("V05", VariantState.CONFIRMED if agree else VariantState.BLOCKED, b15, Template.ACCEPTANCE,
                         "breakout agrees with causal session VWAP" if agree else "VWAP missing or opposes breakout"))
        aligned = (b15 == Side.LONG and "INDEX_ALIGNED_LONG" in caps) or (b15 == Side.SHORT and "INDEX_ALIGNED_SHORT" in caps)
        result.append(_a("V06", VariantState.CONFIRMED if aligned else VariantState.UNOBSERVABLE if not ({"INDEX_ALIGNED_LONG", "INDEX_ALIGNED_SHORT"} & caps) else VariantState.BLOCKED,
                         b15, Template.ACCEPTANCE, "verified index alignment agrees" if aligned else "index alignment absent or opposing"))
    else:
        for vid in ("V04", "V05", "V06"):
            result.append(_a(vid, VariantState.WAITING if r15 else VariantState.UNOBSERVABLE, None, Template.ACCEPTANCE, "requires OR15 breakout first"))

    width_atr = float(features.get("or_width_atr") or 0.0)
    narrow = bool(features.get("range_locked")) and width_atr < 0.25
    wide = bool(features.get("range_locked")) and width_atr > 1.0
    result.append(_a("V07", VariantState.CONFIRMED if narrow and b15 else VariantState.ARMED if narrow else VariantState.WAITING,
                     b15, Template.ACCEPTANCE, f"OR15 width/ATR={width_atr:.4f}; narrow threshold <0.25"))
    result.append(_a("V08", VariantState.CONFIRMED if wide and b15 else VariantState.ARMED if wide else VariantState.WAITING,
                     b15, Template.RETEST_HOLD, f"OR15 width/ATR={width_atr:.4f}; wide threshold >1.0; execution sizing remains risk-budget bounded"))

    gap_go = bool(b15 and gap_side == b15 and gap_atr > 0 and not features.get("gap_ever_touched_pdc"))
    result.append(_a("V09", VariantState.CONFIRMED if gap_go else VariantState.ARMED if gap_side and not features.get("gap_ever_touched_pdc") else VariantState.BLOCKED,
                     b15 if gap_go else gap_side, Template.ACCEPTANCE, f"gap_atr={gap_atr:.4f}; requires same-side OR acceptance and unfilled PDC"))
    result.append(_a("V10", VariantState.CONFIRMED if features.get("fade_ready") else VariantState.ARMED if features.get("failure_index", -1) >= 0 else VariantState.WAITING,
                     None if gap_side is None else (Side.SHORT if gap_side == Side.LONG else Side.LONG), Template.GAP_FADE,
                     "independent post-rejection gap-fade trigger" if features.get("fade_ready") else "waiting for independent rejection/fade confirmation"))
    result.append(_a("V11", VariantState.CONFIRMED if features.get("fade_ready") and features.get("failure_count", 0) > 0 else VariantState.ARMED if features.get("failure_count", 0) > 0 else VariantState.WAITING,
                     None if gap_side is None else (Side.SHORT if gap_side == Side.LONG else Side.LONG), Template.GAP_FADE,
                     "accepted breakout failed and independent reversal trigger confirmed" if features.get("fade_ready") and features.get("failure_count", 0) > 0 else "requires observed accepted-break failure plus reverse confirmation"))
    result.append(_a("V12", VariantState.CONFIRMED if features.get("retest_ready") else VariantState.WAITING,
                     gap_side, Template.RETEST_HOLD, "orderly OR boundary retest held" if features.get("retest_ready") else "waiting for held retest"))
    second = features.get("failure_index", -1) >= 0 and int(features.get("outside_count") or 0) >= policy.accepted_closes
    result.append(_a("V13", VariantState.CONFIRMED if second else VariantState.ARMED if features.get("failure_index", -1) >= 0 else VariantState.WAITING,
                     gap_side, Template.RECLAIM, "post-failure reclaim accepted" if second else "requires fresh acceptance after observed failure"))

    if "RESULT_DAY" not in caps:
        result.append(_a("V14", VariantState.UNOBSERVABLE, b15, Template.ACCEPTANCE, "verified result calendar capability required"))
    else:
        result.append(_a("V14", VariantState.CONFIRMED if b15 else VariantState.ARMED, b15, Template.ACCEPTANCE,
                         "result-day OR breakout confirmed" if b15 else "result day verified; waiting for OR confirmation"))

    pd_side = None
    if snapshot.bars:
        last = snapshot.bars[-1]
        if last.close > snapshot.prior.high + tick:
            pd_side = Side.LONG
        elif last.close < snapshot.prior.low - tick:
            pd_side = Side.SHORT
    result.append(_a("V15", VariantState.CONFIRMED if pd_side else VariantState.WAITING, pd_side, Template.PD_LEVEL_BREAK,
                     "closed beyond verified PDH/PDL" if pd_side else "waiting for PDH/PDL close breakout"))

    if "EXPIRY_DAY" not in caps:
        result.append(_a("V16", VariantState.UNOBSERVABLE, b15, Template.ACCEPTANCE, "verified NSE expiry-calendar capability required"))
    else:
        result.append(_a("V16", VariantState.CONFIRMED if b15 else VariantState.ARMED, b15, Template.ACCEPTANCE,
                         "expiry day verified and OR breakout confirmed" if b15 else "expiry day verified; waiting for OR confirmation"))

    # Afternoon breakout is research-only until its exact window is promoted
    # into Policy and therefore included in policy_hash. Default observation
    # window is 12:00-13:00 IST; no paper authority is granted by this status.
    afternoon = _range(snapshot, 720, 60)
    afternoon_side, _ = _break(snapshot, afternoon, tick)
    result.append(_a("V17", VariantState.CONFIRMED if afternoon_side else VariantState.WAITING if afternoon else VariantState.UNOBSERVABLE,
                     afternoon_side, Template.ACCEPTANCE,
                     "12:00-13:00 research range breakout observed; not paper-promoted" if afternoon_side else "waiting for complete afternoon research range/break"))

    extension = float(features.get("extension_or") or 0.0)
    if extension > policy.max_extension_or:
        result.append(_a("V18", VariantState.BLOCKED, b15 or gap_side, None,
                         f"NO_CHASE extension_or={extension:.4f} > {policy.max_extension_or:.4f}"))
    else:
        result.append(_a("V18", VariantState.CONFIRMED if b15 else VariantState.WAITING, b15, Template.RETEST_HOLD,
                         f"extension_or={extension:.4f} within no-chase ceiling; prefer non-chasing trigger"))

    if len(result) != 18 or {x.variant_id for x in result} != {x[0] for x in CATALOGUE}:
        raise RuntimeError("ORB_VARIANT_CATALOGUE_INCOMPLETE_OR_DUPLICATED")
    return tuple(sorted(result, key=lambda x: x.variant_id))


def feature_map(snapshot: MarketSnapshot, features: dict, policy: Policy) -> dict[str, str]:
    """Flatten variant assessments into Decision.features without schema drift."""
    out: dict[str, str] = {}
    for row in assess(snapshot, features, policy):
        key = row.variant_id.lower()
        out[f"{key}_state"] = row.state.value
        out[f"{key}_side"] = row.side.value if row.side else "NONE"
        out[f"{key}_template"] = row.template.value if row.template else "NONE"
        out[f"{key}_reason"] = row.reason
    return out
