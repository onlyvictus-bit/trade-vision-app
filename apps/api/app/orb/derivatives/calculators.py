from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

from .black76_extra import charm_black76_per_day, vanna_black76
from .contracts import (
    DerivativesContext,
    DerivativesEvidence,
    DerivativesPolicy,
    FuturesSnapshot,
    Greeks,
    OptionChainSnapshot,
    OptionType,
    Wall,
    digest,
)

EPS = 1e-12
MINUTES_PER_YEAR = 365.0 * 24.0 * 60.0


@dataclass(frozen=True, slots=True)
class ChainArrays:
    strikes: np.ndarray
    call_oi: np.ndarray
    put_oi: np.ndarray
    call_volume: np.ndarray
    put_volume: np.ndarray
    call_ltp: np.ndarray
    put_ltp: np.ndarray
    call_lot: np.ndarray
    put_lot: np.ndarray
    call_symbol: tuple[str | None, ...]
    put_symbol: tuple[str | None, ...]


def chain_arrays(chain: OptionChainSnapshot) -> ChainArrays:
    n = len(chain.rows)
    strikes = np.fromiter((r.strike for r in chain.rows), dtype=np.float64, count=n)
    def arr(side: str, field: str) -> np.ndarray:
        return np.fromiter(
            (float(getattr(getattr(r, side), field)) if getattr(r, side) is not None else 0.0 for r in chain.rows),
            dtype=np.float64,
            count=n,
        )
    return ChainArrays(
        strikes=strikes,
        call_oi=arr("ce", "oi"), put_oi=arr("pe", "oi"),
        call_volume=arr("ce", "volume"), put_volume=arr("pe", "volume"),
        call_ltp=arr("ce", "ltp"), put_ltp=arr("pe", "ltp"),
        call_lot=arr("ce", "lot_size"), put_lot=arr("pe", "lot_size"),
        call_symbol=tuple(r.ce.symbol if r.ce else None for r in chain.rows),
        put_symbol=tuple(r.pe.symbol if r.pe else None for r in chain.rows),
    )


def safe_ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator <= EPS else float(numerator / denominator)


def pcr(arr: ChainArrays) -> tuple[float | None, float | None, float, float, float, float]:
    co, po = float(arr.call_oi.sum()), float(arr.put_oi.sum())
    cv, pv = float(arr.call_volume.sum()), float(arr.put_volume.sum())
    return safe_ratio(po, co), safe_ratio(pv, cv), co, po, cv, pv


def oi_change_arrays(current: ChainArrays, previous: ChainArrays | None) -> tuple[np.ndarray, np.ndarray]:
    if previous is None:
        return np.zeros_like(current.call_oi), np.zeros_like(current.put_oi)
    if current.strikes.shape == previous.strikes.shape and np.allclose(current.strikes, previous.strikes, atol=1e-9, rtol=0.0):
        return current.call_oi - previous.call_oi, current.put_oi - previous.put_oi
    # Align changed strike universes without quadratic loops.
    prev_c = {float(k): float(v) for k, v in zip(previous.strikes, previous.call_oi)}
    prev_p = {float(k): float(v) for k, v in zip(previous.strikes, previous.put_oi)}
    dc = np.fromiter((v - prev_c.get(float(k), 0.0) for k, v in zip(current.strikes, current.call_oi)), dtype=np.float64)
    dp = np.fromiter((v - prev_p.get(float(k), 0.0) for k, v in zip(current.strikes, current.put_oi)), dtype=np.float64)
    return dc, dp


def _wall_state(change: float, oi: float) -> str:
    if oi <= EPS:
        return "UNKNOWN"
    ratio = change / max(oi - change, oi * 0.05, EPS)
    if ratio >= 0.10:
        return "STRENGTHENING"
    if ratio <= -0.10:
        return "UNWINDING"
    if change > EPS:
        return "FORMING"
    if change < -EPS:
        return "WEAKENING"
    return "STABLE"


def dominant_oi_wall(
    strikes: np.ndarray,
    oi: np.ndarray,
    oi_change: np.ndarray,
    spot: float,
    *,
    side: str,
    top_k: int,
    distance_decay_pct: float,
    previous_wall: "Wall | None" = None,
) -> Wall | None:
    if len(strikes) == 0 or float(oi.max(initial=0.0)) <= 0:
        return None
    distance_pct = np.abs(strikes - spot) / spot * 100.0
    # Robust score: absolute OI dominates; positive change and proximity refine it.
    oi_scale = max(float(np.percentile(oi[oi > 0], 90)) if np.any(oi > 0) else 1.0, EPS)
    change_pos = np.maximum(oi_change, 0.0)
    change_scale = max(float(np.percentile(change_pos[change_pos > 0], 90)) if np.any(change_pos > 0) else 1.0, EPS)
    proximity = np.exp(-distance_pct / max(distance_decay_pct, 1e-6))
    score = 0.65 * np.clip(oi / oi_scale, 0.0, 3.0) + 0.20 * np.clip(change_pos / change_scale, 0.0, 3.0) + 0.15 * proximity
    # Calls are most relevant at/above spot, puts at/below spot; do not hard-exclude
    # the other side because spot may have crossed a wall between snapshots.
    structural = np.where(strikes >= spot, 1.0, 0.75) if side == "CALL" else np.where(strikes <= spot, 1.0, 0.75)
    score *= structural
    # G12: top_k bounds the candidate set to the top-k strikes by OI; the winner is
    # the max score within that set (previously top_k was accepted but unused).
    k = max(1, min(int(top_k), len(strikes)))
    candidates = set(int(i) for i in np.argsort(oi)[-k:].tolist())
    pool = [(float(score[i]), i) for i in range(len(strikes)) if i in candidates]
    _, idx = max(pool, key=lambda t: (t[0], -t[1]))
    # G12: 1-step persistence — 1 when the wall strike is unchanged from the
    # previous snapshot's wall, else 0. Deeper multi-snapshot persistence is
    # explicitly out of scope (observable depth is one previous snapshot).
    persistence = 1 if (previous_wall is not None and math.isclose(previous_wall.strike, float(strikes[idx]), rel_tol=0.0, abs_tol=1e-9)) else 0
    return Wall(
        strike=float(strikes[idx]), strength=float(score[idx]),
        distance_pct=float((strikes[idx] - spot) / spot * 100.0),
        oi=float(oi[idx]), oi_change=float(oi_change[idx]), persistence=persistence,
        state=_wall_state(float(oi_change[idx]), float(oi[idx])),
    )


def oi_concentration_pct(call_oi: np.ndarray, put_oi: np.ndarray, top_k: int = 3) -> float | None:
    combined = call_oi + put_oi
    total = float(combined.sum())
    if total <= EPS:
        return None
    k = min(top_k, len(combined))
    if k <= 0:
        return None
    top = np.partition(combined, -k)[-k:]
    return float(top.sum() / total * 100.0)


def max_pain(strikes: np.ndarray, call_oi: np.ndarray, put_oi: np.ndarray) -> float | None:
    """O(n) max-pain payout calculation over sorted strikes.

    For each possible settlement strike S:
      call payout = sum_{K<S} (S-K)*CallOI(K)
      put payout  = sum_{K>S} (K-S)*PutOI(K)
    """
    if len(strikes) == 0 or float(call_oi.sum() + put_oi.sum()) <= EPS:
        return None
    order = np.argsort(strikes)
    k = strikes[order]
    c = call_oi[order]
    p = put_oi[order]
    c_oi_before = np.concatenate(([0.0], np.cumsum(c)[:-1]))
    c_koi_before = np.concatenate(([0.0], np.cumsum(c * k)[:-1]))
    p_oi_after = np.concatenate((np.cumsum(p[::-1])[::-1][1:], [0.0]))
    p_koi_after = np.concatenate((np.cumsum((p * k)[::-1])[::-1][1:], [0.0]))
    payout = k * c_oi_before - c_koi_before + p_koi_after - k * p_oi_after
    return float(k[int(np.argmin(payout))])


def atm_row_index(strikes: np.ndarray, atm_strike: float) -> int:
    return int(np.argmin(np.abs(strikes - atm_strike)))


def straddle_expected_move_pct(arr: ChainArrays, atm_strike: float, spot: float) -> float | None:
    i = atm_row_index(arr.strikes, atm_strike)
    premium = float(arr.call_ltp[i] + arr.put_ltp[i])
    return None if premium <= EPS else premium / spot * 100.0


def _greeks_maps(greeks: Sequence[Greeks]) -> tuple[dict[str, Greeks], dict[tuple[float, OptionType], Greeks]]:
    by_symbol = {g.symbol: g for g in greeks if g.status != "INVALID"}
    by_key = {(float(g.strike), g.option_type): g for g in greeks if g.status != "INVALID"}
    return by_symbol, by_key


def atm_iv(greeks: Sequence[Greeks], atm_strike: float) -> float | None:
    vals = [g.implied_volatility_pct for g in greeks if abs(g.strike - atm_strike) <= 1e-9 and g.implied_volatility_pct > 0]
    return float(np.mean(vals)) if vals else None


def iv_horizon_expected_move_pct(atm_iv_pct: float | None, horizon_minutes: int) -> float | None:
    if atm_iv_pct is None or atm_iv_pct <= 0 or horizon_minutes <= 0:
        return None
    return float(atm_iv_pct * math.sqrt(horizon_minutes / MINUTES_PER_YEAR))


def skew_25d_pct(greeks: Sequence[Greeks]) -> float | None:
    calls = [g for g in greeks if g.option_type == OptionType.CE and g.implied_volatility_pct > 0 and 0 < g.delta < 1]
    puts = [g for g in greeks if g.option_type == OptionType.PE and g.implied_volatility_pct > 0 and -1 < g.delta < 0]
    if not calls or not puts:
        return None
    call = min(calls, key=lambda g: abs(g.delta - 0.25))
    put = min(puts, key=lambda g: abs(g.delta + 0.25))
    if abs(call.delta - 0.25) > 0.15 or abs(put.delta + 0.25) > 0.15:
        return None
    return float(put.implied_volatility_pct - call.implied_volatility_pct)


def enrich_higher_greeks(greeks: Sequence[Greeks], annual_rate_pct: float = 0.0) -> tuple[Greeks, ...]:
    if not greeks:
        return ()
    out: list[Greeks] = []
    for kind in (OptionType.CE, OptionType.PE):
        group = [g for g in greeks if g.option_type == kind and g.implied_volatility_pct > 0 and g.days_to_expiry > 0]
        if not group:
            continue
        f = np.asarray([g.forward_price for g in group], dtype=float)
        k = np.asarray([g.strike for g in group], dtype=float)
        t = np.asarray([g.days_to_expiry / 365.0 for g in group], dtype=float)
        s = np.asarray([g.implied_volatility_pct / 100.0 for g in group], dtype=float)
        r = annual_rate_pct / 100.0
        vanna = vanna_black76(f, k, t, s, r, per_vol_point=True)
        charm = charm_black76_per_day(kind.value, f, k, t, s, r)
        for g, va, ch in zip(group, vanna, charm):
            out.append(g.model_copy(update={"vanna_per_vol_point": float(va), "charm_delta_per_day": float(ch)}))
    known = {g.symbol for g in out}
    out.extend(g for g in greeks if g.symbol not in known)
    return tuple(sorted(out, key=lambda g: (g.strike, g.option_type.value)))


def gamma_exposure(
    chain: ChainArrays,
    greeks: Sequence[Greeks],
    spot: float,
) -> tuple[np.ndarray, np.ndarray, float | None, float | None, float | None]:
    by_symbol, by_key = _greeks_maps(greeks)
    call_gamma = np.zeros_like(chain.strikes)
    put_gamma = np.zeros_like(chain.strikes)
    for i, strike in enumerate(chain.strikes):
        cg = by_symbol.get(chain.call_symbol[i]) if chain.call_symbol[i] else by_key.get((float(strike), OptionType.CE))
        pg = by_symbol.get(chain.put_symbol[i]) if chain.put_symbol[i] else by_key.get((float(strike), OptionType.PE))
        if cg is not None:
            call_gamma[i] = max(cg.gamma, 0.0) * chain.call_oi[i] * max(chain.call_lot[i], 1.0) * spot * spot * 0.01
        if pg is not None:
            put_gamma[i] = max(pg.gamma, 0.0) * chain.put_oi[i] * max(chain.put_lot[i], 1.0) * spot * spot * 0.01
    csum, psum = float(call_gamma.sum()), float(put_gamma.sum())
    balance = csum - psum if csum + psum > EPS else None
    # This is NOT dealer zero-gamma. It is the strike where cumulative call-vs-put
    # OI-gamma proxy is closest to balanced, useful only as a structural reference.
    level = None
    if csum + psum > EPS:
        cumulative = np.cumsum(call_gamma - put_gamma)
        level = float(chain.strikes[int(np.argmin(np.abs(cumulative)))])
    return call_gamma, put_gamma, csum or None, psum or None, balance


def gamma_wall(strikes: np.ndarray, exposure: np.ndarray, spot: float, oi: np.ndarray, oi_change: np.ndarray) -> Wall | None:
    if len(exposure) == 0 or float(exposure.max(initial=0.0)) <= EPS:
        return None
    idx = int(np.argmax(exposure))
    scale = max(float(np.percentile(exposure[exposure > 0], 90)) if np.any(exposure > 0) else 1.0, EPS)
    return Wall(
        strike=float(strikes[idx]), strength=float(exposure[idx] / scale),
        distance_pct=float((strikes[idx] - spot) / spot * 100.0),
        oi=float(oi[idx]), oi_change=float(oi_change[idx]), persistence=0,
        state=_wall_state(float(oi_change[idx]), float(oi[idx])),
    )


def futures_state(current: FuturesSnapshot | None, previous: FuturesSnapshot | None) -> tuple[str, float | None]:
    if current is None:
        return "UNKNOWN", None
    if previous is None or previous.ltp <= 0 or previous.oi <= 0:
        return "UNKNOWN", None
    price_change = (current.ltp - previous.ltp) / previous.ltp * 100.0
    oi_change = (current.oi - previous.oi) / previous.oi * 100.0
    dead = 1e-9
    if abs(price_change) <= dead or abs(oi_change) <= dead:
        state = "NEUTRAL"
    elif price_change > 0 and oi_change > 0:
        state = "LONG_BUILDUP"
    elif price_change < 0 and oi_change > 0:
        state = "SHORT_BUILDUP"
    elif price_change > 0 and oi_change < 0:
        state = "SHORT_COVERING"
    else:
        state = "LONG_UNWINDING"
    return state, oi_change


def historical_iv_stats(current_iv: float | None, history: Sequence[float]) -> tuple[float | None, float | None]:
    clean = np.asarray([x for x in history if x is not None and math.isfinite(x) and x > 0], dtype=float)
    if current_iv is None or current_iv <= 0 or clean.size < 20:
        return None, None
    lo, hi = float(clean.min()), float(clean.max())
    rank = 50.0 if hi - lo <= EPS else (current_iv - lo) / (hi - lo) * 100.0
    pctile = float(np.mean(clean < current_iv) * 100.0)
    return float(np.clip(rank, 0.0, 100.0)), float(np.clip(pctile, 0.0, 100.0))


def build_context(
    chain: OptionChainSnapshot,
    greeks: Sequence[Greeks],
    *,
    previous_chain: OptionChainSnapshot | None = None,
    futures: FuturesSnapshot | None = None,
    previous_futures: FuturesSnapshot | None = None,
    next_expiry_atm_iv_pct: float | None = None,
    iv_history: Sequence[float] = (),
    now_ns: int | None = None,
    horizon_minutes: int = 30,
    policy: DerivativesPolicy | None = None,
    # G11: caller-supplied per-input hashes (service.refresh computes them from the
    # exact raw objects). None = input absent (mirrors futures/previous None-ness).
    greeks_snapshot_hash: str | None = None,
    next_expiry_snapshot_hash: str | None = None,
) -> DerivativesContext:
    policy = policy or DerivativesPolicy()
    now_ns = chain.received_ns if now_ns is None else now_ns
    age_seconds = max(0.0, (now_ns - chain.as_of_ns) / 1_000_000_000)
    arr = chain_arrays(chain)
    prev_arr = chain_arrays(previous_chain) if previous_chain is not None else None
    dc, dp = oi_change_arrays(arr, prev_arr)
    pcr_oi, pcr_vol, co, po, cv, pv = pcr(arr)
    call_wall = dominant_oi_wall(arr.strikes, arr.call_oi, dc, chain.underlying_ltp, side="CALL", top_k=policy.wall_top_k, distance_decay_pct=policy.wall_distance_decay_pct)
    put_wall = dominant_oi_wall(arr.strikes, arr.put_oi, dp, chain.underlying_ltp, side="PUT", top_k=policy.wall_top_k, distance_decay_pct=policy.wall_distance_decay_pct)
    if prev_arr is not None and previous_chain is not None:
        # G12: recompute previous-snapshot walls (zero own-change) so current walls
        # carry 1-step persistence. Previous spot comes from the previous snapshot.
        _zero_c = np.zeros_like(prev_arr.call_oi)
        _zero_p = np.zeros_like(prev_arr.put_oi)
        _prev_call = dominant_oi_wall(prev_arr.strikes, prev_arr.call_oi, _zero_c, previous_chain.underlying_ltp,
                                      side="CALL", top_k=policy.wall_top_k, distance_decay_pct=policy.wall_distance_decay_pct)
        _prev_put = dominant_oi_wall(prev_arr.strikes, prev_arr.put_oi, _zero_p, previous_chain.underlying_ltp,
                                     side="PUT", top_k=policy.wall_top_k, distance_decay_pct=policy.wall_distance_decay_pct)
        call_wall = dominant_oi_wall(arr.strikes, arr.call_oi, dc, chain.underlying_ltp, side="CALL", top_k=policy.wall_top_k,
                                     distance_decay_pct=policy.wall_distance_decay_pct, previous_wall=_prev_call)
        put_wall = dominant_oi_wall(arr.strikes, arr.put_oi, dp, chain.underlying_ltp, side="PUT", top_k=policy.wall_top_k,
                                    distance_decay_pct=policy.wall_distance_decay_pct, previous_wall=_prev_put)
    pain = max_pain(arr.strikes, arr.call_oi, arr.put_oi)
    pain_dist = None if pain is None else abs(pain - chain.underlying_ltp) / chain.underlying_ltp * 100.0
    enriched = enrich_higher_greeks(greeks)
    atmiv = atm_iv(enriched, chain.atm_strike)
    iv_rank, iv_percentile = historical_iv_stats(atmiv, iv_history)
    skew = skew_25d_pct(enriched)
    term = None if atmiv is None or next_expiry_atm_iv_pct is None else atmiv - next_expiry_atm_iv_pct
    call_gex, put_gex, cg_sum, pg_sum, balance = gamma_exposure(arr, enriched, chain.underlying_ltp)
    call_gwall = gamma_wall(arr.strikes, call_gex, chain.underlying_ltp, arr.call_oi, dc)
    put_gwall = gamma_wall(arr.strikes, put_gex, chain.underlying_ltp, arr.put_oi, dp)
    gamma_balance_level = None
    if cg_sum is not None or pg_sum is not None:
        cumulative = np.cumsum(call_gex - put_gex)
        gamma_balance_level = float(arr.strikes[int(np.argmin(np.abs(cumulative)))])
    fstate, foi = futures_state(futures, previous_futures)
    basis = None if futures is None else (futures.ltp - chain.underlying_ltp) / chain.underlying_ltp * 100.0
    status = "AVAILABLE"
    reasons: list[str] = []
    if len(chain.rows) < policy.minimum_chain_rows:
        status, reasons = "PARTIAL", ["CHAIN_TOO_SHALLOW"]
    valid_greeks = sum(1 for g in enriched if g.status != "INVALID")
    option_legs = sum((1 if r.ce else 0) + (1 if r.pe else 0) for r in chain.rows)
    coverage = valid_greeks / max(option_legs, 1)
    if coverage < policy.minimum_greeks_coverage:
        status = "PARTIAL" if status != "STALE" else status
        reasons.append("GREEKS_COVERAGE_LOW")
    if age_seconds > policy.max_chain_age_seconds:
        status = "STALE"
        reasons.append("CHAIN_STALE")
    if co + po <= EPS:
        status = "UNAVAILABLE"
        reasons.append("NO_OPEN_INTEREST")

    source_hash = digest({
        "chain": chain.snapshot_hash,
        "futures": futures.snapshot_hash if futures else None,
        "previous_chain": previous_chain.snapshot_hash if previous_chain else None,
        "previous_futures": previous_futures.snapshot_hash if previous_futures else None,
        "policy": policy.policy_hash,
    })
    return DerivativesContext(
        symbol=chain.underlying.upper(), expiry_date=chain.expiry_date, as_of_ns=chain.as_of_ns,
        source_hash=source_hash, chain_snapshot_hash=chain.snapshot_hash,
        futures_snapshot_hash=futures.snapshot_hash if futures else None,
        greeks_snapshot_hash=greeks_snapshot_hash,
        previous_chain_hash=previous_chain.snapshot_hash if previous_chain else None,
        previous_futures_hash=previous_futures.snapshot_hash if previous_futures else None,
        iv_history_hash=digest({"iv_history": [float(v) for v in iv_history]}) if iv_history else None,
        next_expiry_snapshot_hash=next_expiry_snapshot_hash,
        status=status, stale_seconds=age_seconds, reason_codes=tuple(dict.fromkeys(reasons)),
        underlying_ltp=chain.underlying_ltp, futures_ltp=futures.ltp if futures else None,
        futures_basis_pct=basis, futures_oi_change_pct=foi, futures_state=fstate,
        pcr_oi=pcr_oi, pcr_volume=pcr_vol, call_oi_total=co, put_oi_total=po,
        call_volume_total=cv, put_volume_total=pv, call_oi_change=float(dc.sum()), put_oi_change=float(dp.sum()),
        call_oi_wall=call_wall, put_oi_wall=put_wall,
        call_gamma_wall=call_gwall, put_gamma_wall=put_gwall,
        oi_concentration_pct=oi_concentration_pct(arr.call_oi, arr.put_oi, policy.wall_top_k),
        max_pain=pain, max_pain_distance_pct=pain_dist,
        atm_straddle_expected_move_pct=straddle_expected_move_pct(arr, chain.atm_strike, chain.underlying_ltp),
        iv_horizon_expected_move_pct=iv_horizon_expected_move_pct(atmiv, horizon_minutes),
        expected_move_horizon_minutes=horizon_minutes,
        atm_iv_pct=atmiv, iv_rank=iv_rank, iv_percentile=iv_percentile,
        skew_25d_pct=skew, term_structure_spread_pct=term,
        call_gamma_exposure_proxy=cg_sum, put_gamma_exposure_proxy=pg_sum,
        gamma_balance_proxy=balance, gamma_balance_level=gamma_balance_level,
    )
