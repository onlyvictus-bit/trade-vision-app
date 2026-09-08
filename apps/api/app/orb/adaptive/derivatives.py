"""Deterministic point-in-time derivatives intelligence for AFRE.

The module never routes orders and never converts missing market data into a
neutral value. It calculates factual derivatives state from canonical snapshots
and exports short-lived Capability records consumed by the existing AFRE data
and permission gates.

Dealer-signed GEX is only emitted when an upstream dealer-position sign is
explicitly supplied. Open interest by itself is not evidence of dealer side.
"""
from __future__ import annotations

from datetime import date
from enum import StrEnum
from statistics import mean
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import Capability, Frozen, Identifier, NonNegative, Positive, digest


class OptionType(StrEnum):
    CALL = "CALL"
    PUT = "PUT"


class OIBuildup(StrEnum):
    LONG_BUILDUP = "LONG_BUILDUP"
    SHORT_BUILDUP = "SHORT_BUILDUP"
    SHORT_COVERING = "SHORT_COVERING"
    LONG_UNWINDING = "LONG_UNWINDING"
    FLAT_OR_AMBIGUOUS = "FLAT_OR_AMBIGUOUS"


class VixRegime(StrEnum):
    BELOW_11 = "BELOW_11"
    V11_14 = "V11_14"
    V14_17 = "V14_17"
    V17_20 = "V17_20"
    V20_25 = "V20_25"
    ABOVE_25 = "ABOVE_25"


class OptionContract(Frozen):
    symbol: Identifier
    expiry: date
    strike: Positive
    option_type: OptionType
    open_interest: NonNegative
    implied_volatility: Annotated[float | None, Field(default=None, ge=0, le=10, allow_inf_nan=False)]
    delta: Annotated[float | None, Field(default=None, ge=-1, le=1, allow_inf_nan=False)]
    gamma: Annotated[float | None, Field(default=None, ge=0, allow_inf_nan=False)]
    vanna: Annotated[float | None, Field(default=None, allow_inf_nan=False)]
    charm: Annotated[float | None, Field(default=None, allow_inf_nan=False)]
    contract_multiplier: Positive = 1.0
    dealer_position_sign: Literal[-1, 1] | None = None


class FuturesLeg(Frozen):
    symbol: Identifier
    expiry: date
    price: Positive
    open_interest: NonNegative
    previous_price: Positive | None = None
    previous_open_interest: NonNegative | None = None


class DerivativesSnapshot(Frozen):
    symbol: Identifier
    session_date: date
    available_ns: Annotated[int, Field(strict=True, gt=0)]
    expires_ns: Annotated[int, Field(strict=True, gt=0)]
    source_id: Identifier
    spot: Positive
    prior_close: Positive
    atr14: Positive
    vix: Annotated[float | None, Field(default=None, gt=0, le=200, allow_inf_nan=False)]
    previous_vix: Annotated[float | None, Field(default=None, gt=0, le=200, allow_inf_nan=False)]
    iv_history: tuple[Annotated[float, Field(ge=0, le=10, allow_inf_nan=False)], ...] = ()
    previous_atm_iv: Annotated[float | None, Field(default=None, ge=0, le=10, allow_inf_nan=False)]
    options: tuple[OptionContract, ...] = ()
    futures: tuple[FuturesLeg, ...] = ()
    gift_reference: Positive | None = None
    index_open: Positive | None = None
    index_prior_close: Positive | None = None
    index_atr14: Positive | None = None
    fii_index_futures_long: NonNegative | None = None
    fii_index_futures_short: NonNegative | None = None
    fair_value_adjustment_bps: Annotated[float, Field(ge=-5000, le=5000)] = 0.0
    is_weekly_expiry: bool = False
    is_monthly_expiry: bool = False

    @model_validator(mode="after")
    def valid(self):
        if self.expires_ns <= self.available_ns:
            raise ValueError("DERIVATIVES_SNAPSHOT_EXPIRY_MUST_FOLLOW_AVAILABILITY")
        if self.symbol != self.symbol.upper():
            raise ValueError("DERIVATIVES_SYMBOL_MUST_BE_CANONICAL_UPPERCASE")
        for o in self.options:
            if o.symbol != self.symbol:
                raise ValueError("OPTION_UNDERLYING_IDENTITY_MISMATCH")
        for f in self.futures:
            if f.symbol != self.symbol:
                raise ValueError("FUTURES_UNDERLYING_IDENTITY_MISMATCH")
        return self


class DerivativesContext(Frozen):
    symbol: Identifier
    session_date: date
    available_ns: int
    expires_ns: int
    source_id: Identifier
    snapshot_hash: str
    vix_regime: VixRegime | None
    vix_change_pct: float | None
    iv_rank: float | None
    atm_iv: float | None
    iv_crush_pct: float | None
    term_structure_points: float | None
    term_structure_inverted: bool | None
    skew_25d_points: float | None
    pcr_oi: float | None
    max_pain_strike: float | None
    max_pain_distance_pct: float | None
    near_max_pain: bool | None
    oi_buildup: OIBuildup | None
    futures_basis_bps: float | None
    adjusted_basis_bps: float | None
    rollover_pct: float | None
    positive_basis_rollover: bool | None
    unsigned_gex: float | None
    dealer_signed_gex: float | None
    aggregate_vanna: float | None
    aggregate_charm: float | None
    gift_implied_gap_pct: float | None
    gift_gap_atr: float | None
    index_gap_pct: float | None
    fii_short_pct: float | None
    is_weekly_expiry: bool
    is_monthly_expiry: bool
    warnings: tuple[str, ...] = ()


def _vix_regime(vix: float | None) -> VixRegime | None:
    if vix is None:
        return None
    if vix < 11:
        return VixRegime.BELOW_11
    if vix < 14:
        return VixRegime.V11_14
    if vix < 17:
        return VixRegime.V14_17
    if vix < 20:
        return VixRegime.V17_20
    if vix <= 25:
        return VixRegime.V20_25
    return VixRegime.ABOVE_25


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous <= 0:
        return None
    return (current - previous) / previous * 100.0


def _front_options(options: tuple[OptionContract, ...]) -> tuple[OptionContract, ...]:
    if not options:
        return ()
    expiry = min(o.expiry for o in options)
    return tuple(o for o in options if o.expiry == expiry)


def _nearest_atm(options: tuple[OptionContract, ...], spot: float) -> tuple[OptionContract, ...]:
    if not options:
        return ()
    distance = min(abs(o.strike - spot) for o in options)
    return tuple(o for o in options if abs(o.strike - spot) <= distance + 1e-12)


def _atm_iv(options: tuple[OptionContract, ...], spot: float) -> float | None:
    vals = [o.implied_volatility for o in _nearest_atm(options, spot) if o.implied_volatility is not None]
    return mean(vals) if vals else None


def _iv_rank(current: float | None, history: tuple[float, ...]) -> float | None:
    if current is None or len(history) < 20:
        return None
    lo, hi = min(history), max(history)
    if hi <= lo:
        return 0.0
    return max(0.0, min(100.0, (current - lo) / (hi - lo) * 100.0))


def _term_structure(options: tuple[OptionContract, ...], spot: float) -> tuple[float | None, bool | None]:
    expiries = sorted({o.expiry for o in options})
    if len(expiries) < 2:
        return None, None
    near = tuple(o for o in options if o.expiry == expiries[0])
    far = tuple(o for o in options if o.expiry == expiries[1])
    n, f = _atm_iv(near, spot), _atm_iv(far, spot)
    if n is None or f is None:
        return None, None
    points = (n - f) * 100.0
    return points, points > 5.0


def _skew25(options: tuple[OptionContract, ...]) -> float | None:
    calls = [o for o in options if o.option_type == OptionType.CALL and o.delta is not None and o.implied_volatility is not None]
    puts = [o for o in options if o.option_type == OptionType.PUT and o.delta is not None and o.implied_volatility is not None]
    if not calls or not puts:
        return None
    call = min(calls, key=lambda o: abs(abs(o.delta or 0.0) - 0.25))
    put = min(puts, key=lambda o: abs(abs(o.delta or 0.0) - 0.25))
    return ((put.implied_volatility or 0.0) - (call.implied_volatility or 0.0)) * 100.0


def _pcr(options: tuple[OptionContract, ...]) -> float | None:
    call_oi = sum(o.open_interest for o in options if o.option_type == OptionType.CALL)
    put_oi = sum(o.open_interest for o in options if o.option_type == OptionType.PUT)
    if call_oi <= 0:
        return None
    return put_oi / call_oi


def _max_pain(options: tuple[OptionContract, ...], spot: float) -> tuple[float | None, float | None]:
    strikes = sorted({o.strike for o in options})
    if not strikes:
        return None, None
    best_strike, best_loss = None, None
    for settle in strikes:
        loss = 0.0
        for o in options:
            intrinsic = max(0.0, settle - o.strike) if o.option_type == OptionType.CALL else max(0.0, o.strike - settle)
            loss += intrinsic * o.open_interest * o.contract_multiplier
        if best_loss is None or loss < best_loss:
            best_loss, best_strike = loss, settle
    if best_strike is None:
        return None, None
    return best_strike, abs(spot - best_strike) / spot * 100.0


def _oi_buildup(futures: tuple[FuturesLeg, ...]) -> OIBuildup | None:
    if not futures:
        return None
    front = sorted(futures, key=lambda f: f.expiry)[0]
    if front.previous_price is None or front.previous_open_interest is None:
        return None
    dp = front.price - front.previous_price
    doi = front.open_interest - front.previous_open_interest
    eps_p = max(front.previous_price * 1e-8, 1e-12)
    eps_oi = max(front.previous_open_interest * 1e-8, 1e-12)
    if abs(dp) <= eps_p or abs(doi) <= eps_oi:
        return OIBuildup.FLAT_OR_AMBIGUOUS
    if dp > 0 and doi > 0:
        return OIBuildup.LONG_BUILDUP
    if dp < 0 and doi > 0:
        return OIBuildup.SHORT_BUILDUP
    if dp > 0 and doi < 0:
        return OIBuildup.SHORT_COVERING
    return OIBuildup.LONG_UNWINDING


def _basis_and_rollover(snapshot: DerivativesSnapshot) -> tuple[float | None, float | None, float | None, bool | None]:
    if not snapshot.futures:
        return None, None, None, None
    legs = sorted(snapshot.futures, key=lambda f: f.expiry)
    front = legs[0]
    raw = (front.price - snapshot.spot) / snapshot.spot * 10000.0
    adjusted = raw - snapshot.fair_value_adjustment_bps
    rollover = None
    positive_rollover = None
    if len(legs) >= 2:
        denom = legs[0].open_interest + legs[1].open_interest
        if denom > 0:
            rollover = legs[1].open_interest / denom * 100.0
            positive_rollover = rollover > 85.0 and adjusted > 0.0
    return raw, adjusted, rollover, positive_rollover


def _greek_exposure(options: tuple[OptionContract, ...], spot: float) -> tuple[float | None, float | None, float | None, float | None, tuple[str, ...]]:
    gamma_rows = [o for o in options if o.gamma is not None]
    unsigned = sum((o.gamma or 0.0) * o.open_interest * o.contract_multiplier * spot * spot * 0.01 for o in gamma_rows) if gamma_rows else None
    signed_rows = [o for o in gamma_rows if o.dealer_position_sign is not None]
    signed = None
    warnings: list[str] = []
    if gamma_rows and len(signed_rows) == len(gamma_rows):
        signed = sum((o.gamma or 0.0) * o.open_interest * o.contract_multiplier * spot * spot * 0.01 * int(o.dealer_position_sign or 0) for o in signed_rows)
    elif gamma_rows:
        warnings.append("DEALER_SIGNED_GEX_UNOBSERVABLE_WITHOUT_DEALER_POSITION_SIGN")
    vanna_rows = [o for o in options if o.vanna is not None]
    charm_rows = [o for o in options if o.charm is not None]
    vanna = sum((o.vanna or 0.0) * o.open_interest * o.contract_multiplier for o in vanna_rows) if vanna_rows else None
    charm = sum((o.charm or 0.0) * o.open_interest * o.contract_multiplier for o in charm_rows) if charm_rows else None
    return unsigned, signed, vanna, charm, tuple(warnings)


def calculate(snapshot: DerivativesSnapshot) -> DerivativesContext:
    front_options = _front_options(snapshot.options)
    atm = _atm_iv(front_options, snapshot.spot)
    iv_rank = _iv_rank(atm, snapshot.iv_history)
    term_points, inverted = _term_structure(snapshot.options, snapshot.spot)
    skew = _skew25(front_options)
    pcr = _pcr(front_options)
    max_pain, max_pain_distance = _max_pain(front_options, snapshot.spot)
    buildup = _oi_buildup(snapshot.futures)
    basis, adjusted_basis, rollover, positive_rollover = _basis_and_rollover(snapshot)
    unsigned_gex, signed_gex, vanna, charm, warnings = _greek_exposure(front_options, snapshot.spot)
    vix_change = _pct_change(snapshot.vix, snapshot.previous_vix)
    iv_crush = _pct_change(atm, snapshot.previous_atm_iv)
    gift_gap_pct = None
    gift_gap_atr = None
    if snapshot.gift_reference is not None:
        gift_gap_pct = (snapshot.gift_reference - snapshot.prior_close) / snapshot.prior_close * 100.0
        gift_gap_atr = abs(snapshot.gift_reference - snapshot.prior_close) / snapshot.atr14
    index_gap_pct = None
    if snapshot.index_open is not None and snapshot.index_prior_close is not None:
        index_gap_pct = (snapshot.index_open - snapshot.index_prior_close) / snapshot.index_prior_close * 100.0
    fii_short_pct = None
    if snapshot.fii_index_futures_long is not None and snapshot.fii_index_futures_short is not None:
        total = snapshot.fii_index_futures_long + snapshot.fii_index_futures_short
        if total > 0:
            fii_short_pct = snapshot.fii_index_futures_short / total * 100.0
    return DerivativesContext(
        symbol=snapshot.symbol,
        session_date=snapshot.session_date,
        available_ns=snapshot.available_ns,
        expires_ns=snapshot.expires_ns,
        source_id=snapshot.source_id,
        snapshot_hash=digest(snapshot),
        vix_regime=_vix_regime(snapshot.vix),
        vix_change_pct=vix_change,
        iv_rank=iv_rank,
        atm_iv=atm,
        iv_crush_pct=iv_crush,
        term_structure_points=term_points,
        term_structure_inverted=inverted,
        skew_25d_points=skew,
        pcr_oi=pcr,
        max_pain_strike=max_pain,
        max_pain_distance_pct=max_pain_distance,
        near_max_pain=None if max_pain_distance is None else max_pain_distance <= 0.5,
        oi_buildup=buildup,
        futures_basis_bps=basis,
        adjusted_basis_bps=adjusted_basis,
        rollover_pct=rollover,
        positive_basis_rollover=positive_rollover,
        unsigned_gex=unsigned_gex,
        dealer_signed_gex=signed_gex,
        aggregate_vanna=vanna,
        aggregate_charm=charm,
        gift_implied_gap_pct=gift_gap_pct,
        gift_gap_atr=gift_gap_atr,
        index_gap_pct=index_gap_pct,
        fii_short_pct=fii_short_pct,
        is_weekly_expiry=snapshot.is_weekly_expiry,
        is_monthly_expiry=snapshot.is_monthly_expiry,
        warnings=warnings,
    )


def _cap(ctx: DerivativesContext, name: str, *, blocked: bool = False, reason: str = "") -> Capability:
    return Capability(
        name=name,
        available_ns=ctx.available_ns,
        expires_ns=ctx.expires_ns,
        status="BLOCKED" if blocked else "VALID",
        evidence_hash=digest((ctx.snapshot_hash, name, reason, blocked)),
        blocks_new_entry=blocked,
        reason=reason[:300],
    )


def capabilities(ctx: DerivativesContext) -> tuple[Capability, ...]:
    """Convert calculated overlay into auditable facts for MarketSnapshot.

    Presence is factual. A scenario capability such as VIX_SPIKE only exists
    when its registered threshold is actually observed. Missing inputs remain
    absent, therefore required policies fail closed in validate_prefix().
    """
    out: list[Capability] = [_cap(ctx, "DERIVATIVES_CONTEXT", reason=f"calculated from {ctx.source_id}")]
    if ctx.vix_regime is not None:
        out.append(_cap(ctx, "VIX", reason=f"regime={ctx.vix_regime.value}"))
        if ctx.vix_regime == VixRegime.BELOW_11:
            out.append(_cap(ctx, "VIX_COMA", reason="India VIX < 11"))
        if ctx.vix_regime in {VixRegime.V20_25, VixRegime.ABOVE_25}:
            out.append(_cap(ctx, "VIX_HIGH", reason=f"India VIX regime {ctx.vix_regime.value}"))
    if ctx.vix_change_pct is not None and ctx.vix_change_pct >= 8.0:
        out.append(_cap(ctx, "VIX_SPIKE", blocked=True, reason=f"delta_vix_pct={ctx.vix_change_pct:.4f} >= 8"))
    if ctx.iv_rank is not None:
        out.append(_cap(ctx, "IV_RANK", reason=f"iv_rank={ctx.iv_rank:.4f}"))
        if ctx.iv_rank > 60:
            out.append(_cap(ctx, "IV_RANK_HIGH", reason=f"iv_rank={ctx.iv_rank:.4f} > 60"))
    if ctx.term_structure_inverted:
        out.append(_cap(ctx, "IV_TERM_INVERSION", reason=f"near_minus_next_vol_points={ctx.term_structure_points:.4f}"))
    if ctx.iv_crush_pct is not None and ctx.iv_crush_pct <= -20:
        out.append(_cap(ctx, "IV_CRUSH", reason=f"atm_iv_change_pct={ctx.iv_crush_pct:.4f}"))
    if ctx.skew_25d_points is not None:
        out.append(_cap(ctx, "SKEW_25D", reason=f"put_minus_call_vol_points={ctx.skew_25d_points:.4f}"))
    if ctx.pcr_oi is not None:
        out.append(_cap(ctx, "PCR", reason=f"pcr_oi={ctx.pcr_oi:.4f}"))
        if ctx.pcr_oi > 1.3:
            out.append(_cap(ctx, "PCR_EXTREME_HIGH", reason=f"pcr_oi={ctx.pcr_oi:.4f}"))
        elif ctx.pcr_oi < 0.7:
            out.append(_cap(ctx, "PCR_EXTREME_LOW", reason=f"pcr_oi={ctx.pcr_oi:.4f}"))
    if ctx.oi_buildup is not None:
        out.append(_cap(ctx, "OI_BUILDUP", reason=ctx.oi_buildup.value))
        out.append(_cap(ctx, f"OI_{ctx.oi_buildup.value}", reason=ctx.oi_buildup.value))
    if ctx.near_max_pain:
        out.append(_cap(ctx, "MAX_PAIN_NEAR", reason=f"distance_pct={ctx.max_pain_distance_pct:.4f} <= 0.5"))
    if ctx.dealer_signed_gex is not None:
        out.append(_cap(ctx, "DEALER_GEX", reason=f"signed_gex={ctx.dealer_signed_gex:.6g}"))
        if ctx.dealer_signed_gex > 0:
            out.append(_cap(ctx, "POSITIVE_DEALER_GAMMA", reason="dealer_signed_gex > 0"))
        elif ctx.dealer_signed_gex < 0:
            out.append(_cap(ctx, "NEGATIVE_DEALER_GAMMA", reason="dealer_signed_gex < 0"))
    if ctx.aggregate_vanna is not None:
        out.append(_cap(ctx, "VANNA", reason=f"aggregate_vanna={ctx.aggregate_vanna:.6g}"))
    if ctx.aggregate_charm is not None:
        out.append(_cap(ctx, "CHARM", reason=f"aggregate_charm={ctx.aggregate_charm:.6g}"))
    if ctx.is_weekly_expiry or ctx.is_monthly_expiry:
        out.append(_cap(ctx, "EXPIRY_DAY", reason="NSE equity-derivatives expiry flag supplied by verified calendar"))
    if ctx.rollover_pct is not None:
        out.append(_cap(ctx, "ROLLOVER", reason=f"next_month_share_pct={ctx.rollover_pct:.4f}"))
    if ctx.positive_basis_rollover:
        out.append(_cap(ctx, "ROLLOVER_STRONG_POSITIVE_BASIS", reason=f"rollover_pct={ctx.rollover_pct:.4f}; adjusted_basis_bps={ctx.adjusted_basis_bps:.4f}"))
    if ctx.adjusted_basis_bps is not None:
        out.append(_cap(ctx, "FUTURES_BASIS", reason=f"adjusted_basis_bps={ctx.adjusted_basis_bps:.4f}"))
        if ctx.adjusted_basis_bps > 15:
            out.append(_cap(ctx, "FUTURES_BASIS_POSITIVE", reason=f"adjusted_basis_bps={ctx.adjusted_basis_bps:.4f} > 15"))
        elif ctx.adjusted_basis_bps < 0:
            out.append(_cap(ctx, "FUTURES_BASIS_NEGATIVE", reason=f"adjusted_basis_bps={ctx.adjusted_basis_bps:.4f} < 0"))
    if ctx.gift_gap_atr is not None and ctx.gift_gap_atr > 1.5:
        out.append(_cap(ctx, "GIFT_GAP_EXTREME", reason=f"gift_gap_atr={ctx.gift_gap_atr:.4f} > 1.5"))
    if ctx.index_gap_pct is not None and abs(ctx.index_gap_pct) > 2.5:
        out.append(_cap(ctx, "INDEX_GAP_EXTREME", reason=f"index_gap_pct={ctx.index_gap_pct:.4f}"))
    if ctx.fii_short_pct is not None:
        out.append(_cap(ctx, "FII_INDEX_FUTURES", reason=f"fii_short_pct={ctx.fii_short_pct:.4f}"))
        if ctx.fii_short_pct > 80:
            out.append(_cap(ctx, "FII_SHORT_EXTREME", reason=f"fii_short_pct={ctx.fii_short_pct:.4f} > 80"))
        elif ctx.fii_short_pct < 30:
            out.append(_cap(ctx, "FII_SHORT_LIGHT", reason=f"fii_short_pct={ctx.fii_short_pct:.4f} < 30"))
    return tuple(out)
